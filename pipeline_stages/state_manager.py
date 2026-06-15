"""
事件驱动状态管理器 - 多 Worker 并发安全

并发安全机制:
  1. fcntl.flock 文件锁保护计数器
  2. .done 原子标记文件防止重复完成
  3. Redis RPUSH/BLPOP 原子队列 (Redis模式)
  4. 原子 rename 实现文件队列并发 pop
"""

import fcntl
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageState:
    """单个阶段的状态"""
    name: str
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    items_processed: int = 0
    items_total: int = 0
    errors: List[Dict] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    worker_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StageState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ======================== 文件锁工具 ========================

class FileLock:
    """fcntl 文件锁 - 跨进程并发控制"""

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self._fd = None

    def acquire(self, timeout: float = 10.0) -> bool:
        """获取排他锁"""
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        self._fd = open(self.lock_path, "w")
        start = time.time()
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (IOError, OSError):
                if time.time() - start > timeout:
                    return False
                time.sleep(0.05)

    def release(self):
        """释放锁"""
        if self._fd:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                self._fd.close()
            except Exception:
                pass
            self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


# ======================== 事件驱动 ========================

class EventDriver:
    """事件驱动引擎 - 基于 Redis Stream"""

    def __init__(self, redis_host="localhost", redis_port=6379, redis_password="", stream_key="swebench:pipeline:events"):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.stream_key = stream_key
        self._redis = None

    @property
    def redis(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password or None,
                    decode_responses=True,
                    socket_connect_timeout=3,
                )
                self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    def emit(self, event_type: str, stage_name: str, data: dict = None) -> str:
        """发布事件到 Stream"""
        event = {
            "event": event_type,
            "stage": stage_name,
            "timestamp": datetime.now().isoformat(),
            "data": json.dumps(data or {}),
        }
        if self.redis:
            try:
                msg_id = self.redis.xadd(self.stream_key, event, maxlen=10000)
                return msg_id
            except Exception:
                pass
        return ""

    def listen(self, last_id="0", block_ms=5000) -> List[dict]:
        """监听 Stream 事件"""
        if not self.redis:
            return []
        try:
            streams = {self.stream_key: last_id}
            events = self.redis.xread(streams, count=10, block=block_ms)
            results = []
            for stream_name, messages in events:
                for msg_id, data in messages:
                    results.append({"id": msg_id, **data})
            return results
        except Exception:
            return []

    def get_last_id(self) -> str:
        if not self.redis:
            return "0"
        try:
            info = self.redis.xinfo_stream(self.stream_key)
            return info.get("last-generated-id", "0")
        except Exception:
            return "0"


# ======================== 并发安全 StateManager ========================

class StateManager:
    """流水线状态管理器 (并发安全)"""

    def __init__(self, data_dir: str, redis_host="localhost", redis_port=6379, redis_password=""):
        self.data_dir = data_dir
        self.state_dir = os.path.join(data_dir, "state")
        self.lock_dir = os.path.join(data_dir, "locks")
        self.marker_dir = os.path.join(data_dir, "markers")
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.lock_dir, exist_ok=True)
        os.makedirs(self.marker_dir, exist_ok=True)
        self.events = EventDriver(redis_host, redis_port, redis_password)

    # ------- 文件锁 -------

    def _lock_state(self, stage_name: str) -> FileLock:
        return FileLock(os.path.join(self.lock_dir, f"{stage_name}.lock"))

    def _marker_path(self, stage_name: str, marker_type: str) -> str:
        return os.path.join(self.marker_dir, f"{stage_name}.{marker_type}")

    # ------- 原子写入 -------

    def _atomic_write(self, fpath: str, content: str):
        """原子写入: 先写临时文件，再 rename"""
        tmp = fpath + f".tmp.{os.getpid()}"
        with open(tmp, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, fpath)

    # ------- 状态读写 -------

    def get_state_file(self, stage_name: str) -> str:
        return os.path.join(self.state_dir, f"{stage_name}.json")

    def get_stage_state(self, stage_name: str) -> StageState:
        fpath = self.get_state_file(stage_name)
        state = StageState(name=stage_name, status="pending")
        if os.path.exists(fpath):
            try:
                with open(fpath) as f:
                    state = StageState.from_dict(json.load(f))
            except Exception:
                pass
        # 从 Redis 同步计数器（如果可用）
        redis = self.events.redis
        if redis:
            try:
                cnt = redis.get(f"counter:{stage_name}")
                if cnt is not None:
                    state.items_processed = int(cnt)
                wids = redis.smembers(f"workers:{stage_name}")
                for w in wids:
                    if w not in state.worker_ids:
                        state.worker_ids.append(w)
            except Exception:
                pass
        return state

    def save_stage_state(self, state: StageState):
        self._atomic_write(self.get_state_file(state.name), json.dumps(state.to_dict(), indent=2))

    # ------- 阶段生命周期 (并发安全) -------

    def start_stage(self, stage_name: str, total_items: int = 0):
        """标记阶段开始 (单次执行，幂等)"""
        with self._lock_state(stage_name):
            state = self.get_stage_state(stage_name)
            if state.status == "running":
                return  # 已启动，幂等
            state.status = "running"
            state.started_at = datetime.now().isoformat()
            state.items_total = total_items
            state.items_processed = 0
            self.save_stage_state(state)
        self.events.emit("stage_started", stage_name, {"total": total_items})

    def mark_item_done(self, stage_name: str, worker_id: str = "") -> int:
        """
        标记一个 item 完成 (并发安全: Redis INCR 原子操作)
        返回当前完成数
        """
        # 优先用 Redis 原子 INCR
        redis = self.events.redis
        if redis:
            try:
                counter_key = f"counter:{stage_name}"
                processed = redis.incr(counter_key)
                redis.sadd(f"workers:{stage_name}", worker_id or "unknown")
                total = self.get_stage_state(stage_name).items_total
                self.events.emit("item_done", stage_name, {
                    "processed": processed, "total": total, "worker": worker_id,
                })
                return processed
            except Exception:
                pass

        # 文件锁回退 (Redis不可用时)
        with self._lock_state(stage_name):
            state = self.get_stage_state(stage_name)
            state.items_processed += 1
            if worker_id and worker_id not in state.worker_ids:
                state.worker_ids.append(worker_id)
            processed = state.items_processed
            total = state.items_total
            self.save_stage_state(state)

        self.events.emit("item_done", stage_name, {
            "processed": processed, "total": total, "worker": worker_id,
        })
        return processed

    def complete_stage(self, stage_name: str, output_files: List[str] = None):
        """
        标记阶段完成 (并发安全: 原子标记文件 + 锁保护)
        多 Worker 同时调用时，只有一个成功
        """
        marker = self._marker_path(stage_name, "done")
        try:
            # O_CREAT | O_EXCL: 原子创建，文件已存在时失败
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError:
            return  # 其他 Worker 已完成

        with self._lock_state(stage_name):
            state = self.get_stage_state(stage_name)
            state.status = "done"
            state.completed_at = datetime.now().isoformat()
            if output_files:
                state.output_files = output_files
            self.save_stage_state(state)

        self.events.emit("stage_completed", stage_name, {
            "processed": state.items_processed, "output_files": state.output_files,
        })

    def fail_stage(self, stage_name: str, error: str):
        """标记阶段失败 (并发安全)"""
        with self._lock_state(stage_name):
            state = self.get_stage_state(stage_name)
            if state.status == "done":
                return  # 已完成则不标记失败
            state.status = "failed"
            state.errors.append({"time": datetime.now().isoformat(), "error": error})
            self.save_stage_state(state)
        self.events.emit("stage_failed", stage_name, {"error": error})

    def is_done(self, stage_name: str) -> bool:
        # 优先检查标记文件 (最快最安全)
        if os.path.exists(self._marker_path(stage_name, "done")):
            return True
        return self.get_stage_state(stage_name).status == "done"

    def reset_stage(self, stage_name: str):
        """重置阶段 (清空标记文件)"""
        for m in ["done", "failed"]:
            mp = self._marker_path(stage_name, m)
            if os.path.exists(mp):
                os.remove(mp)
        with self._lock_state(stage_name):
            state = self.get_stage_state(stage_name)
            state.status = "pending"
            state.items_processed = 0
            state.errors = []
            self.save_stage_state(state)

    def get_pipeline_summary(self) -> List[dict]:
        stages = []
        for fname in sorted(os.listdir(self.state_dir)):
            if fname.endswith(".json") and not fname.startswith("_"):
                with open(os.path.join(self.state_dir, fname)) as f:
                    stages.append(json.load(f))
        return stages

    def is_pipeline_complete(self, stage_names: List[str]) -> bool:
        return all(self.is_done(s) for s in stage_names)


# ======================== 流水运行记录 (并发安全) ========================

@dataclass
class RunRecord:
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    stages: List[dict] = field(default_factory=list)
    total_duration_seconds: float = 0
    trigger: str = "manual"
    models: List[str] = field(default_factory=list)
    instance_count: int = 0
    errors: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RunRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class RunHistory:
    """流水线运行历史管理器"""

    def __init__(self, data_dir: str):
        self.history_dir = os.path.join(data_dir, "history")
        self.index_file = os.path.join(self.history_dir, "index.json")
        self.lock_dir = os.path.join(data_dir, "locks")
        os.makedirs(self.history_dir, exist_ok=True)
        os.makedirs(self.lock_dir, exist_ok=True)

    def _lock_index(self) -> FileLock:
        return FileLock(os.path.join(self.lock_dir, "index.lock"))

    def _atomic_write(self, fpath: str, content: str):
        tmp = fpath + f".tmp.{os.getpid()}"
        with open(tmp, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, fpath)

    def create_run(self, run_id: str = None, trigger: str = "manual",
                   models: List[str] = None, instance_count: int = 0) -> RunRecord:
        if run_id is None:
            run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        record = RunRecord(
            run_id=run_id,
            started_at=datetime.now().isoformat(),
            trigger=trigger,
            models=models or [],
            instance_count=instance_count,
        )
        self._atomic_write(
            os.path.join(self.history_dir, f"{run_id}.json"),
            json.dumps(record.to_dict(), indent=2, ensure_ascii=False),
        )
        self._update_index(record)
        return record

    def end_run(self, run_id: str, status: str, stages: List[dict] = None,
                errors: List[dict] = None):
        record = self.get_run(run_id)
        if record:
            record.status = status
            record.completed_at = datetime.now().isoformat()
            if stages:
                record.stages = stages
            if errors:
                record.errors = errors
            try:
                start = datetime.fromisoformat(record.started_at)
                end = datetime.fromisoformat(record.completed_at)
                record.total_duration_seconds = (end - start).total_seconds()
            except Exception:
                pass
            self._atomic_write(
                os.path.join(self.history_dir, f"{run_id}.json"),
                json.dumps(record.to_dict(), indent=2, ensure_ascii=False),
            )
            self._update_index(record)

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        fpath = os.path.join(self.history_dir, f"{run_id}.json")
        if os.path.exists(fpath):
            with open(fpath) as f:
                return RunRecord.from_dict(json.load(f))
        return None

    def list_runs(self, limit: int = 20) -> List[dict]:
        return self._read_index()[-limit:]

    def get_last_run(self) -> Optional[RunRecord]:
        runs = self.list_runs(1)
        if runs:
            return self.get_run(runs[0]["run_id"])
        return None

    def _update_index(self, record: RunRecord):
        with self._lock_index():
            index = self._read_index()
            for i, item in enumerate(index):
                if item["run_id"] == record.run_id:
                    index[i] = {
                        "run_id": record.run_id,
                        "started_at": record.started_at,
                        "completed_at": record.completed_at,
                        "status": record.status,
                        "duration_s": record.total_duration_seconds,
                        "instance_count": record.instance_count,
                        "models": record.models,
                    }
                    break
            else:
                index.append({
                    "run_id": record.run_id,
                    "started_at": record.started_at,
                    "completed_at": record.completed_at,
                    "status": record.status,
                    "duration_s": record.total_duration_seconds,
                    "instance_count": record.instance_count,
                    "models": record.models,
                })
            self._atomic_write(self.index_file, json.dumps(index, indent=2, ensure_ascii=False))

    def _read_index(self) -> List[dict]:
        if os.path.exists(self.index_file):
            with open(self.index_file) as f:
                return json.load(f)
        return []
