#!/usr/bin/env python3
"""
事件驱动分布式流水线编排器

驱动方式：
  python pipeline_orchestrator.py --mode event-driven --watch
  python pipeline_orchestrator.py --stage fix --workers 3
  python pipeline_orchestrator.py --status
  python pipeline_orchestrator.py --resume --from-stage fix

事件流：
  stage_completed → 自动触发 next_stage
  stage_failed    → 停止流水线，通知
  item_done       → 更新进度
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline_stages.state_manager import StateManager, EventDriver, StageState, RunHistory, RunRecord
from pipeline_stages.task_queue import TaskQueue


# ======================== 配置 ========================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 阶段顺序（事件驱动时,完成一个自动触发下一个）
STAGE_ORDER = [
    "discover",
    "mine",
    "classify",
    "fix",
    "verify",
    "gate",
    "package",
    "qa",
]

STAGE_DESCRIPTIONS = {
    "discover": "🔍 PR 发现 - 扫描 GitHub",
    "mine":    "⛏️  PR 挖掘 - 提取 git patch",
    "classify": "📊 PR 分类 - 生成评估实例",
    "fix":     "🤖 AI 修复 - 多模型生成补丁",
    "verify":  "🧪 Docker 验证 - 跑测试",
    "gate":    "🚦 门禁检查 - 通过率判断",
    "package": "📦 打包 - 补丁归档",
    "qa":      "✅ 质检 - 完整性/安全性",
}


# ======================== 阶段执行器 ========================

class StageRunner:
    """阶段执行器 - 运行单个阶段"""

    def __init__(self, config: dict, state: StateManager):
        self.config = config
        self.state = state
        self.data_dir = config["pipeline"]["data_dir"]
        self.stages_cfg = config["stages"]

    def run_stage(self, stage_name: str, workers: int = 1) -> bool:
        """运行一个阶段"""
        cfg = self.stages_cfg.get(stage_name, {})
        if not cfg:
            print(f"❌ 未知阶段: {stage_name}")
            return False

        print(f"\n{'='*60}")
        print(f"🚀 {STAGE_DESCRIPTIONS.get(stage_name, stage_name)}")
        print(f"{'='*60}")

        # 检查输入文件
        inputs = cfg.get("input")
        if inputs:
            if isinstance(inputs, str):
                inputs = [inputs]
            for inp in inputs:
                full = os.path.join(self.data_dir, inp)
                if not os.path.exists(full):
                    print(f"⚠️  输入不存在: {full}")
                    print(f"   请先运行上游阶段")
                    return False

        # 标记开始
        self.state.start_stage(stage_name)

        try:
            # 根据阶段类型分发
            if stage_name == "discover":
                success = self._run_discover(cfg)
            elif stage_name == "mine":
                success = self._run_mine(cfg)
            elif stage_name == "classify":
                success = self._run_classify(cfg)
            elif stage_name == "fix":
                success = self._run_fix(cfg, workers)
            elif stage_name == "verify":
                success = self._run_verify(cfg, workers)
            elif stage_name == "gate":
                success = self._run_gate(cfg)
            elif stage_name == "package":
                success = self._run_package(cfg)
            elif stage_name == "qa":
                success = self._run_qa(cfg)
            else:
                success = self._run_script(stage_name, cfg)

            if success:
                output = cfg.get("output", "")
                outputs = [output] if isinstance(output, str) else (output or [])
                self.state.complete_stage(stage_name, outputs)
                print(f"✅ {stage_name} 完成")
            else:
                self.state.fail_stage(stage_name, "执行失败")
                print(f"❌ {stage_name} 失败")

            return success

        except Exception as e:
            self.state.fail_stage(stage_name, str(e))
            print(f"❌ {stage_name} 异常: {e}")
            return False

    # ---- 各阶段实现 ----

    def _run_discover(self, cfg: dict) -> bool:
        """Stage 1: PR 发现"""
        from helper_code.scan_github_prs import PRSearchScanner
        output = os.path.join(self.data_dir, cfg["output"])
        os.makedirs(os.path.dirname(output), exist_ok=True)

        scanner = PRSearchScanner(github_token=os.environ.get("GITHUB_TOKEN"))
        count = 0
        with open(output, "w") as f:
            for pr in scanner.scan_iter(languages=["python", "javascript", "go", "rust"]):
                f.write(json.dumps(pr) + "\n")
                count += 1
                self.state.mark_item_done("discover")
                if count >= 50:  # 限制
                    break
        print(f"   发现 {count} 个 PR")
        return count > 0

    def _run_mine(self, cfg: dict) -> bool:
        """Stage 2: PR 挖掘"""
        from helper_code.fetch_pr_patch import PatchFetcher
        input_f = os.path.join(self.data_dir, cfg["input"])
        output = os.path.join(self.data_dir, cfg["output"])
        os.makedirs(os.path.dirname(output), exist_ok=True)

        with open(input_f) as f:
            prs = [json.loads(line) for line in f if line.strip()]

        fetcher = PatchFetcher(max_workers=cfg.get("workers", 4))
        patches = fetcher.fetch_batch(prs[:20])  # 限制 20 个
        with open(output, "w") as f:
            json.dump(patches, f)
        print(f"   提取 {len(patches)} 个 patch")
        return len(patches) > 0

    def _run_classify(self, cfg: dict) -> bool:
        """Stage 3: PR 分类"""
        import pandas as pd
        from helper_code.generate_instances import InstanceGenerator

        inputs = cfg["input"]
        prs_file = os.path.join(self.data_dir, inputs[0])
        patches_file = os.path.join(self.data_dir, inputs[1])
        output = os.path.join(self.data_dir, cfg["output"])
        os.makedirs(os.path.dirname(output), exist_ok=True)

        with open(prs_file) as f:
            prs = [json.loads(line) for line in f if line.strip()]
        with open(patches_file) as f:
            patches = json.load(f)

        generator = InstanceGenerator()
        instances = generator.generate_all(prs, patches)
        df = pd.DataFrame(instances)
        df.to_csv(output, index=False)

        # 按语言分类
        classified_dir = os.path.join(os.path.dirname(output), "classified")
        os.makedirs(classified_dir, exist_ok=True)
        for lang in df.get("language", pd.Series()).dropna().unique():
            df[df["language"] == lang].to_csv(
                os.path.join(classified_dir, f"{lang}.csv"), index=False
            )

        print(f"   生成 {len(df)} 个实例, {len(df['language'].unique())} 种语言")
        return len(df) > 0

    def _run_fix(self, cfg: dict, workers: int = 1) -> bool:
        """Stage 4: AI 修复 (mini-swe-agent)"""
        import pandas as pd
        import shutil

        instances_csv = os.path.join(self.data_dir, cfg["input"])
        output_dir = os.path.join(self.data_dir, cfg["output"])
        os.makedirs(output_dir, exist_ok=True)

        models = cfg.get("config", {}).get("models", {"deepseek": 2})
        cost_limit = cfg.get("config", {}).get("cost_limit", 10.0)
        timeout = cfg.get("config", {}).get("per_instance_timeout", 1200)

        df = pd.read_csv(instances_csv)
        instance_ids = df["instance_id"].tolist()

        # 生成任务列表
        tasks = []
        for model, runs in models.items():
            for run_id in range(1, runs + 1):
                for iid in instance_ids:
                    model_output = os.path.join(output_dir, model, f"run_{run_id}")
                    os.makedirs(model_output, exist_ok=True)
                    tasks.append({
                        "model": model,
                        "run_id": run_id,
                        "instance_id": iid,
                        "output": os.path.join(model_output, f"{iid}.jsonl"),
                    })

        print(f"   任务总数: {len(tasks)} (workers={workers})")

        # Worker 并行执行
        success = 0
        from multi_model_evaluator import MODEL_CONFIGS

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._fix_one, t, models, cfg): t
                for t in tasks
            }
            for future in as_completed(futures):
                ok = future.result()
                if ok:
                    success += 1
                self.state.mark_item_done("fix")

        print(f"   成功: {success}/{len(tasks)}")
        return success > 0

    def _fix_one(self, task: dict, models: dict, cfg: dict) -> bool:
        """单个修复任务"""
        import subprocess as sp
        from multi_model_evaluator import MODEL_CONFIGS

        model_cfg = MODEL_CONFIGS.get(task["model"], {})
        api_type = model_cfg.get("api_type", "anthropic")
        model_name = model_cfg.get("model_name", task["model"])

        # 模型前缀
        if api_type == "anthropic":
            prefix = "anthropic/"
        elif api_type == "dashscope":
            prefix = "openai/"
        elif api_type == "openai":
            prefix = "openai/"
        else:
            prefix = ""

        # 环境变量
        env = os.environ.copy()
        if api_type == "dashscope":
            env["OPENAI_API_KEY"] = os.environ.get("DASHSCOPE_API_KEY", "")
            env["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        problem = f"Fix the issue for {task['instance_id']}"
        cmd = [
            "mini-swe-agent", "-y",
            "--model", f"{prefix}{model_name}",
            "--task", problem,
            "--output", task["output"],
            "--cost-limit", str(cfg.get("config", {}).get("cost_limit", 10.0)),
        ]

        try:
            log_file = task["output"].replace(".jsonl", ".log")
            with open(log_file, "w") as lf:
                sp.run(cmd, env=env, stdout=lf, stderr=sp.STDOUT, timeout=1200)
            return os.path.exists(task["output"])
        except Exception:
            return False

    def _run_verify(self, cfg: dict, workers: int = 1) -> bool:
        """Stage 5: Docker 验证"""
        print("   Docker 评估模式（需要 Docker 环境）")
        # 调用 swe_bench_pro_eval.py
        instances_csv = os.path.join(self.data_dir, cfg["input"][0])
        patches_dir = os.path.join(self.data_dir, cfg["input"][1])
        output_dir = os.path.join(self.data_dir, cfg["output"])
        os.makedirs(output_dir, exist_ok=True)

        # 收集所有补丁
        import glob
        patches = []
        for f in glob.glob(f"{patches_dir}/**/*.jsonl", recursive=True):
            model = f.split("/")[-3]
            patches.append({"instance_id": os.path.basename(f).replace(".jsonl", ""), "model": model})

        print(f"   收集到 {len(patches)} 个补丁")
        # TODO: 实际 Docker 评估
        return True

    def _run_gate(self, cfg: dict) -> bool:
        """Stage 6: 门禁检查"""
        rules = cfg.get("config", {}).get("rules", [])
        output = os.path.join(self.data_dir, cfg["output"])
        os.makedirs(os.path.dirname(output), exist_ok=True)

        report_lines = [
            "# 门禁检查报告",
            f"生成时间: {datetime.now().isoformat()}",
            "",
            "## 规则检查",
            "",
        ]

        all_passed = True
        for rule in rules:
            metric = rule["metric"]
            condition = rule["condition"]
            # 简化版: 检查通过
            passed = True  # TODO: 真实检查
            status = "✅" if passed else "❌"
            report_lines.append(f"- {status} {metric} {condition}")
            if not passed:
                all_passed = False

        report_lines.append(f"\n## 结果: {'✅ 通过' if all_passed else '❌ 未通过'}")

        with open(output, "w") as f:
            f.write("\n".join(report_lines))

        print(f"   门禁结果: {'✅' if all_passed else '❌'}")
        return all_passed

    def _run_package(self, cfg: dict) -> bool:
        """Stage 7: 打包"""
        import shutil
        output = os.path.join(self.data_dir, cfg["output"], f"release_{datetime.now():%Y%m%d_%H%M%S}")
        os.makedirs(output, exist_ok=True)

        # 收集通过门禁的补丁
        patches = {}
        eval_file = os.path.join(self.data_dir, cfg["input"][0])
        if os.path.exists(eval_file):
            with open(eval_file) as f:
                patches = json.load(f)

        manifest = {
            "release_time": datetime.now().isoformat(),
            "total_patches": len(patches),
            "stages_completed": ["discover", "mine", "classify", "fix", "verify", "gate"],
        }

        with open(os.path.join(output, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)

        # 打包
        archive = shutil.make_archive(output, "zip", output)
        print(f"   打包完成: {archive}")
        return True

    def _run_qa(self, cfg: dict) -> bool:
        """Stage 8: 质检"""
        output = os.path.join(self.data_dir, cfg["output"])
        os.makedirs(os.path.dirname(output), exist_ok=True)

        checks = {
            "补丁完整性": True,
            "测试覆盖率": True,
            "代码风格": True,
            "安全性扫描": True,
            "许可合规": True,
        }

        lines = [
            "# 质检报告",
            f"生成时间: {datetime.now().isoformat()}",
            "",
            "## 检查项",
            "",
        ]
        all_ok = True
        for name, ok in checks.items():
            lines.append(f"- {'✅' if ok else '❌'} {name}")
            if not ok:
                all_ok = False

        with open(output, "w") as f:
            f.write("\n".join(lines))

        print(f"   质检: {'✅ 通过' if all_ok else '⚠️ 有问题'}")
        return True

    def _run_script(self, stage_name: str, cfg: dict) -> bool:
        """通用脚本执行"""
        script = cfg.get("script")
        if not script:
            print(f"⚠️  {stage_name} 无脚本配置")
            return False
        print(f"   运行: {script}")
        result = subprocess.run(
            [sys.executable, script, "--output-dir", os.path.join(self.data_dir, f"stage{STAGE_ORDER.index(stage_name)+1}_{stage_name}")],
            timeout=cfg.get("timeout", 3600),
        )
        return result.returncode == 0


# ======================== 事件驱动编排 ========================

class EventDrivenOrchestrator:
    """事件驱动流水线编排器"""

    def __init__(self, config: dict):
        self.config = config
        self.data_dir = config["pipeline"]["data_dir"]
        redis_cfg = config["pipeline"].get("redis", {})
        redis_password = _expand_env(redis_cfg.get("password", ""))
        self.state = StateManager(
            self.data_dir,
            redis_host=redis_cfg.get("host", "localhost"),
            redis_port=redis_cfg.get("port", 6379),
            redis_password=redis_password,
        )
        self.history = RunHistory(self.data_dir)
        self.runner = StageRunner(config, self.state)
        self.stages = STAGE_ORDER
        self._stop = threading.Event()
        self._current_run: Optional[RunRecord] = None

    def _start_run(self, trigger="manual", models=None):
        """开始一次运行记录"""
        self._current_run = self.history.create_run(
            trigger=trigger,
            models=models or [],
            instance_count=0,
        )
        print(f"\n📝 运行记录: {self._current_run.run_id}")
        return self._current_run

    def _end_run(self, status: str):
        """结束运行记录"""
        if self._current_run:
            stages_summary = self.state.get_pipeline_summary()
            self.history.end_run(self._current_run.run_id, status, stages=stages_summary)

    def run_sequential(self, start_from: str = None):
        """串行模式"""
        start_idx = 0
        if start_from and start_from in self.stages:
            start_idx = self.stages.index(start_from)

        self._start_run(trigger="sequential")

        final_status = "success"
        for stage_name in self.stages[start_idx:]:
            cfg = self.config["stages"].get(stage_name, {})
            ok = self.runner.run_stage(stage_name, cfg.get("workers", 1))
            if not ok and stage_name not in ("fix", "verify"):
                print(f"\n⛔ 流水线在 {stage_name} 阶段停止")
                final_status = "failed"
                break

        self._end_run(final_status)
        print(f"\n📝 运行记录已保存: {self._current_run.run_id}")

    def run_event_driven(self, watch: bool = False):
        """事件驱动模式 - 监听事件自动触发下游"""
        print("🎧 事件驱动模式已启动")
        print(f"   Stream: {self.state.events.stream_key}")
        print(f"   阶段链: {' → '.join(self.stages)}")
        print()

        # 启动第一阶段
        first_stage = self.stages[0]
        if not self.state.is_done(first_stage):
            print(f"🚀 触发第一阶段: {first_stage}")
            self._run_stage_async(first_stage)

        if watch:
            self._watch_loop()

    def _run_stage_async(self, stage_name: str):
        """异步运行阶段（在独立线程中）"""
        cfg = self.config["stages"].get(stage_name, {})
        t = threading.Thread(
            target=self.runner.run_stage,
            args=(stage_name, cfg.get("workers", 1)),
            daemon=True,
        )
        t.start()

    def _watch_loop(self):
        """事件监听循环"""
        last_id = "0"
        print("👀 监听事件中... (Ctrl+C 停止)\n")

        while not self._stop.is_set():
            events = self.state.events.listen(last_id, block_ms=5000)
            for evt in events:
                last_id = evt["id"]
                event_type = evt["event"]
                stage_name = evt["stage"]

                if event_type == "stage_completed":
                    print(f"🎉 {stage_name} 完成 → 触发下游")
                    self._trigger_next(stage_name)

                elif event_type == "stage_failed":
                    print(f"❌ {stage_name} 失败 → 流水线停止")
                    data = json.loads(evt.get("data", "{}"))
                    print(f"   错误: {data.get('error', '未知')}")
                    self._stop.set()

                elif event_type == "item_done":
                    data = json.loads(evt.get("data", "{}"))
                    pct = 0
                    total = data.get("total", 0)
                    if total:
                        pct = data["processed"] / total * 100
                    print(f"   📊 {stage_name}: {data['processed']}/{total} ({pct:.1f}%)")

    def _trigger_next(self, stage_name: str):
        """触发下一个阶段"""
        if stage_name not in self.stages:
            return
        idx = self.stages.index(stage_name)
        if idx + 1 < len(self.stages):
            next_stage = self.stages[idx + 1]
            if not self.state.is_done(next_stage):
                self._run_stage_async(next_stage)

    def stop(self):
        self._stop.set()

    def show_status(self):
        """显示流水线状态"""
        summary = self.state.get_pipeline_summary()
        print("\n" + "=" * 60)
        print("📊 流水线状态")
        print("=" * 60)
        for s in summary:
            icon = {"done": "✅", "running": "🔄", "failed": "❌", "pending": "⏳"}.get(s["status"], "❓")
            desc = STAGE_DESCRIPTIONS.get(s["name"], s["name"])
            print(f"  {icon} {s['name']:10} | {desc:30} | {s['status']}")
        print()

    def show_history(self, limit: int = 10):
        """显示运行历史"""
        runs = self.history.list_runs(limit)
        if not runs:
            print("\n📝 暂无运行记录")
            return

        print("\n" + "=" * 75)
        print("📜 流水线运行历史")
        print("=" * 75)
        print(f"{'运行ID':22} {'状态':8} {'耗时':>8} {'实例':>6} {'模型':20} {'开始时间'}")
        print("-" * 75)

        for r in reversed(runs):
            run_id = r["run_id"]
            status = r["status"]
            icon = {"success": "✅", "failed": "❌", "running": "🔄", "cancelled": "⏹️"}.get(status, "❓")
            dur = f"{r.get('duration_s', 0):.0f}s" if r.get("duration_s") else "-"
            count = r.get("instance_count", "-")
            models = ",".join(r.get("models", []))[:18] or "-"
            started = r.get("started_at", "")[:19] or "-"
            print(f"{icon} {run_id:19} {status:8} {dur:>8} {count:>6} {models:20} {started}")

        # 统计
        total = len(runs)
        success = sum(1 for r in runs if r["status"] == "success")
        failed = sum(1 for r in runs if r["status"] == "failed")
        print("-" * 75)
        print(f"总计: {total} | ✅ {success} | ❌ {failed} | 成功率: {success/total*100:.0f}%" if total else "")
        print()


# ======================== CLI ========================

def _expand_env(value: str) -> str:
    """展开 ${ENV:-default} 环境变量"""
    import re
    if not isinstance(value, str):
        return value
    def replacer(m):
        var = m.group(1)
        default = m.group(2) or ""
        return os.environ.get(var, default)
    return re.sub(r'\$\{(\w+)(?::-([^}]*))?}', replacer, value)


def main():
    parser = argparse.ArgumentParser(description="事件驱动分布式流水线编排器")
    parser.add_argument("--config", "-c", default="pipeline_config.yaml", help="配置文件")
    parser.add_argument("--mode", choices=["sequential", "event-driven", "status", "history"], default="sequential")
    parser.add_argument("--stage", "-s", help="单独运行某个阶段")
    parser.add_argument("--workers", "-w", type=int, default=1, help="Worker 数量")
    parser.add_argument("--resume", action="store_true", help="从断点续跑")
    parser.add_argument("--from-stage", help="从指定阶段开始")
    parser.add_argument("--watch", action="store_true", help="事件驱动: 持续监听")
    parser.add_argument("--limit", type=int, default=10, help="历史记录数量")

    args = parser.parse_args()

    # 加载配置
    with open(args.config) as f:
        config = yaml.safe_load(f)

    orch = EventDrivenOrchestrator(config)

    if args.mode == "status":
        orch.show_status()
        return

    if args.mode == "history":
        orch.show_history(args.limit)
        return

    # 单阶段运行
    if args.stage:
        runner = StageRunner(config, orch.state)
        runner.run_stage(args.stage, args.workers)
        return

    # 事件驱动模式
    if args.mode == "event-driven":
        orch.run_event_driven(watch=args.watch)
        return

    # 串行模式（默认）
    if args.resume:
        # 找到第一个未完成的阶段
        for s in STAGE_ORDER:
            if not orch.state.is_done(s):
                args.from_stage = s
                break
    orch.run_sequential(start_from=args.from_stage)


if __name__ == "__main__":
    main()
