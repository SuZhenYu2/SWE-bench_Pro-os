#!/usr/bin/env python3
"""
分布式 Worker - 从任务队列消费，独立处理

用法:
  # 启动 Fix worker (处理 mini-swe-agent 任务)
  python pipeline_worker.py --stage fix --worker-id 1 &
  python pipeline_worker.py --stage fix --worker-id 2 &
  python pipeline_worker.py --stage fix --worker-id 3 &

  # 启动 Verify worker (Docker 评估)
  python pipeline_worker.py --stage verify --worker-id 1
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
from pipeline_stages.task_queue import TaskQueue
from pipeline_stages.state_manager import StateManager, EventDriver


class PipelineWorker:
    """通用 Worker - 从队列取任务执行"""

    def __init__(self, stage_name: str, worker_id: str, config: dict):
        self.stage_name = stage_name
        self.worker_id = worker_id
        self.config = config
        self.data_dir = config["pipeline"]["data_dir"]
        self.queue = TaskQueue(stage_name, self.data_dir)
        self.state = StateManager(self.data_dir)
        self.events = EventDriver()
        self._running = True

        # 注册信号处理
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        print(f"\n👋 Worker {self.worker_id} 收到信号 {signum}，优雅退出...")
        self._running = False

    def run(self):
        """Worker 主循环"""
        print(f"🔧 Worker [{self.worker_id}] 启动, 阶段: {self.stage_name}")
        print(f"   队列: {self.queue.queue_key}")
        print(f"   等待任务...")

        consecutive_empty = 0
        max_empty = 30  # 30 次空轮询 = 150 秒后退出

        while self._running:
            task = self.queue.pop(timeout=5)

            if task is None:
                consecutive_empty += 1
                if consecutive_empty >= max_empty:
                    print(f"   ⏰ 队列空闲 {consecutive_empty} 次，Worker 退出")
                    break
                continue

            consecutive_empty = 0
            try:
                self._process_task(task)
                self.state.mark_item_done(self.stage_name, self.worker_id)
            except Exception as e:
                print(f"   ❌ 处理失败: {e}")
                # 失败的任务重新入队（可选）
                self.queue.push(task)

    def _process_task(self, task: dict):
        """处理单个任务"""
        instance_id = task.get("instance_id", "unknown")
        print(f"   🔨 [{self.worker_id}] 处理: {instance_id}")

        if self.stage_name == "fix":
            self._process_fix(task)
        elif self.stage_name == "verify":
            self._process_verify(task)
        else:
            self._process_generic(task)

    def _process_fix(self, task: dict):
        """处理修复任务"""
        from multi_model_evaluator import MODEL_CONFIGS

        model = task["model"]
        model_cfg = MODEL_CONFIGS.get(model, {})
        api_type = model_cfg.get("api_type", "anthropic")
        model_name = model_cfg.get("model_name", model)

        if api_type == "anthropic":
            prefix = "anthropic/"
        elif api_type in ("openai", "dashscope"):
            prefix = "openai/"
        else:
            prefix = ""

        env = os.environ.copy()
        if api_type == "dashscope":
            env["OPENAI_API_KEY"] = os.environ.get("DASHSCOPE_API_KEY", "")
            env["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        cmd = [
            "mini-swe-agent", "-y",
            "--model", f"{prefix}{model_name}",
            "--task", task.get("problem", f"Fix: {task['instance_id']}"),
            "--output", task["output"],
            "--cost-limit", "10.0",
        ]

        os.makedirs(os.path.dirname(task["output"]), exist_ok=True)
        log_file = task["output"].replace(".jsonl", ".log")
        with open(log_file, "w") as lf:
            sp = subprocess.run(cmd, env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=1200)

        # 后备: 从默认位置复制轨迹
        default_traj = os.path.expanduser("~/.config/mini-swe-agent/last_mini_run.traj.json")
        if not os.path.exists(task["output"]) and os.path.exists(default_traj):
            import shutil
            shutil.copy(default_traj, task["output"])

    def _process_verify(self, task: dict):
        """处理验证任务"""
        print(f"      Docker 评估: {task['instance_id']}")
        # TODO: 实际 Docker 调用

    def _process_generic(self, task: dict):
        """通用处理"""
        print(f"      处理: {json.dumps(task, ensure_ascii=False)[:100]}")


# ======================== CLI ========================

def main():
    parser = argparse.ArgumentParser(description="分布式流水线 Worker")
    parser.add_argument("--stage", "-s", required=True, help="阶段名 (discover/mine/classify/fix/verify/gate/package/qa)")
    parser.add_argument("--worker-id", "-w", default=f"worker-{os.getpid()}", help="Worker ID")
    parser.add_argument("--config", "-c", default="pipeline_config.yaml", help="配置文件")

    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    worker = PipelineWorker(args.stage, args.worker_id, config)
    worker.run()


if __name__ == "__main__":
    main()
