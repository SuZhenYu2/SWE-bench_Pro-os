"""
并发安全任务队列 - Redis 原子操作 + 文件 rename 原子操作

Redis 模式:  RPUSH / BLPOP 天然原子
文件模式:    rename O_APPEND 原子写入, rename 原子 pop
"""

import json
import os
import time
import fcntl
from typing import Optional


class TaskQueue:
    """并发安全任务队列"""

    def __init__(self, stage_name: str, data_dir: str,
                 redis_host="localhost", redis_port=6379, redis_password=""):
        self.stage_name = stage_name
        self.data_dir = data_dir
        self.queue_key = f"queue:swebench:{stage_name}"
        self.queue_dir = os.path.join(data_dir, "queues")
        self.tasks_file = os.path.join(self.queue_dir, f"{stage_name}.jsonl")
        self.lock_file = os.path.join(data_dir, "locks", f"queue_{stage_name}.lock")
        self._redis = None
        self._redis_host = redis_host
        self._redis_port = redis_port
        self._redis_password = redis_password
        os.makedirs(self.queue_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)

    @property
    def redis(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(
                    host=self._redis_host,
                    port=self._redis_port,
                    password=self._redis_password or None,
                    decode_responses=True,
                    socket_connect_timeout=3,
                )
                self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    # ====== Push (并发安全: Redis原子 + 文件 flock) ======

    def push(self, task: dict):
        """入队 (并发安全)"""
        if self.redis:
            try:
                self.redis.rpush(self.queue_key, json.dumps(task))
                return
            except Exception:
                pass
        # 文件模式: flock 保证原子追加
        with open(self.lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            with open(self.tasks_file, "a") as f:
                f.write(json.dumps(task) + "\n")
                f.flush()
                os.fsync(f.fileno())
            fcntl.flock(lf, fcntl.LOCK_UN)

    def push_batch(self, tasks: list):
        """批量入队 (并发安全)"""
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                for t in tasks:
                    pipe.rpush(self.queue_key, json.dumps(t))
                pipe.execute()
                return
            except Exception:
                pass
        with open(self.lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            with open(self.tasks_file, "a") as f:
                for t in tasks:
                    f.write(json.dumps(t) + "\n")
                f.flush()
                os.fsync(f.fileno())
            fcntl.flock(lf, fcntl.LOCK_UN)

    # ====== Pop (并发安全: Redis BLPOP原子 + 文件 rename原子) ======

    def pop(self, timeout: int = 5) -> Optional[dict]:
        """出队 (并发安全)"""
        # Redis 模式: BLPOP 天然原子
        if self.redis:
            try:
                result = self.redis.blpop(self.queue_key, timeout=timeout)
                if result:
                    return json.loads(result[1])
            except Exception:
                pass

        # 文件模式: 原子 rename 实现并发 pop
        # 每个 Worker 把 tasks_file rename 到自己的临时文件进行处理
        pid = os.getpid()
        claimed_file = os.path.join(self.queue_dir, f"{self.stage_name}_claimed_{pid}.jsonl")

        try:
            with open(self.lock_file, "w") as lf:
                fcntl.flock(lf, fcntl.LOCK_EX)
                # 检查是否有任务
                if not os.path.exists(self.tasks_file) or os.path.getsize(self.tasks_file) == 0:
                    fcntl.flock(lf, fcntl.LOCK_UN)
                    return None
                # 原子 rename: 把整个队列文件"拿走"
                try:
                    os.rename(self.tasks_file, claimed_file)
                except OSError:
                    fcntl.flock(lf, fcntl.LOCK_UN)
                    return None
                fcntl.flock(lf, fcntl.LOCK_UN)

            # 处理拿走的内容
            with open(claimed_file, "r") as f:
                lines = f.readlines()

            if not lines:
                os.remove(claimed_file)
                return None

            task = json.loads(lines[0])

            # 剩余任务写回队列
            if len(lines) > 1:
                self.push_batch([json.loads(l.strip()) for l in lines[1:] if l.strip()])

            os.remove(claimed_file)
            return task

        except (IOError, OSError):
            if os.path.exists(claimed_file):
                os.remove(claimed_file)
            return None

    # ====== 查询 ======

    def size(self) -> int:
        if self.redis:
            try:
                return self.redis.llen(self.queue_key)
            except Exception:
                pass
        if os.path.exists(self.tasks_file):
            return sum(1 for _ in open(self.tasks_file))
        return 0

    def clear(self):
        if self.redis:
            try:
                self.redis.delete(self.queue_key)
            except Exception:
                pass
        with open(self.lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            if os.path.exists(self.tasks_file):
                os.remove(self.tasks_file)
            # 清理残余 claimed 文件
            for f in os.listdir(self.queue_dir):
                if "claimed" in f:
                    os.remove(os.path.join(self.queue_dir, f))
            fcntl.flock(lf, fcntl.LOCK_UN)
