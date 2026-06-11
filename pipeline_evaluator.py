#!/usr/bin/env python3
"""
流水线评估执行器 - 扫描→获取 patch→生成实例→评估 同步进行

功能：
1. 流水线处理：每扫描到一个 PR 立即开始后续处理
2. 多阶段并发：扫描、获取 patch、生成实例、评估并行运行
3. 实时进度显示：每阶段完成实时更新
4. 断点续跑：支持中途停止，下次可从已处理的 PR 继续
5. 增量输出：随时可以查看当前结果

用法：
# 完整流水线
python pipeline_evaluator.py \
    --languages python javascript go rust \
    --min-lines 110 --balanced \
    --max-results 100 \
    --output-dir data/eval

# 指定协议和输出
python pipeline_evaluator.py \
    --licenses mit bsd apache-2.0 \
    --min-stars 10 \
    --clone-dir /tmp/repos \
    --workers 8

# 断点续跑（从上次中断处继续）
python pipeline_evaluator.py \
    --resume \
    --output-dir data/eval
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from queue import Queue, Empty
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HELPER_DIR = os.path.join(SCRIPT_DIR, "helper_code")
EVAL_SCRIPT = os.path.join(SCRIPT_DIR, "swe_bench_pro_eval.py")


# ==================== 数据模型 ====================

@dataclass
class PRStage:
    """PR 处理阶段"""
    stage: str  # "scanned", "patched", "generated", "evaluated"
    instance_id: str
    pr_number: int
    repo_owner: str
    repo_name: str
    language: str
    detected_language: str = ""
    total_lines: int = 0
    patch: str = ""
    test_patch: str = ""
    test_files: List[str] = field(default_factory=list)
    all_files: List[str] = field(default_factory=list)
    patch_size: int = 0
    instance_generated: bool = False
    eval_result: Optional[bool] = None
    error: Optional[str] = None
    base_commit: str = ""
    head_commit: str = ""
    start_time: float = 0.0
    end_time: float = 0.0


# ==================== 流水线阶段 ====================

class PipelineStage:
    """流水线阶段基类"""
    
    def __init__(self, name: str, max_workers: int = 4):
        self.name = name
        self.max_workers = max_workers
        self.input_queue: Queue = Queue()
        self.output_queue: Queue = Queue()
        self.processed: int = 0
        self.errors: int = 0
        self.lock = threading.Lock()
    
    def process(self, item: object) -> object:
        raise NotImplementedError
    
    def run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            try:
                item = self.input_queue.get(timeout=1.0)
            except Empty:
                continue
            
            try:
                result = self.process(item)
                if result is not None:
                    self.output_queue.put(result)
                    with self.lock:
                        self.processed += 1
            except Exception as e:
                with self.lock:
                    self.errors += 1
                print(f"  ❌ [{self.name}] 错误: {e}")
                self.output_queue.put(item)  # 继续传递错误的项
            finally:
                self.input_queue.task_done()


class ScanStage(PipelineStage):
    """阶段1：扫描 PR"""
    
    def __init__(self, languages: List[str], licenses: List[str], 
                 min_lines: int, min_stars: int, balanced: bool,
                 max_results: int):
        super().__init__("扫描", max_workers=1)  # 扫描是单线程
        self.languages = languages
        self.licenses = licenses
        self.min_lines = min_lines
        self.min_stars = min_stars
        self.balanced = balanced
        self.max_results = max_results
        self._scanner = None
    
    def process(self, item: object = None) -> Optional[PRStage]:
        from scan_github_prs import PRSearchScanner  # 延迟导入
        
        if self._scanner is None:
            self._scanner = PRSearchScanner(github_token=os.environ.get("GITHUB_TOKEN"))
            self._scan_iterator = self._scanner.scan_iter(
                languages=self.languages,
                licenses=self.licenses,
                min_lines=self.min_lines,
                min_stars=self.min_stars,
                balanced=self.balanced,
                max_results=self.max_results
            )
        
        try:
            pr_data = next(self._scan_iterator)
        except StopIteration:
            return None
        
        stage = PRStage(
            stage="scanned",
            instance_id=pr_data.get("instance_id", ""),
            pr_number=pr_data.get("pr_number", 0),
            repo_owner=pr_data.get("repo_owner", ""),
            repo_name=pr_data.get("repo_name", ""),
            language=pr_data.get("language", pr_data.get("detected_language", "python")),
            detected_language=pr_data.get("detected_language", ""),
            total_lines=pr_data.get("total_lines", 0),
            start_time=time.time(),
        )
        return stage


class PatchStage(PipelineStage):
    """阶段2：获取 Patch"""
    
    def __init__(self, clone_dir: Optional[str]):
        super().__init__("获取Patch", max_workers=4)
        self.clone_dir = clone_dir or tempfile.mkdtemp(prefix="swebench_repos_")
        os.makedirs(self.clone_dir, exist_ok=True)
    
    def process(self, stage: PRStage) -> Optional[PRStage]:
        from fetch_pr_patch import GitOperator  # 延迟导入
        
        try:
            # 获取 PR 详情
            owner = stage.repo_owner
            repo = stage.repo_name
            pr_number = stage.pr_number
            
            # 克隆仓库
            git = GitOperator(self.clone_dir)
            repo_path = git.clone_or_update(owner, repo)
            
            if not repo_path:
                stage.error = "无法克隆仓库"
                stage.end_time = time.time()
                return stage
            
            # 获取 PR 的 commit hash
            head_hash = git.get_commit_hash(repo_path, f"origin/pr/{pr_number}/head") or ""
            base_hash = git.get_commit_hash(repo_path, f"origin/pr/{pr_number}/base") or ""
            
            stage.base_commit = base_hash
            stage.head_commit = head_hash
            
            # 获取 patch
            if base_hash and head_hash:
                stage.patch = git.get_full_patch(repo_path, base_hash, head_hash)
                stage.patch_size = len(stage.patch)
                
                # 分离测试文件 patch
                test_files = []
                # 这里简化：从 patch 中查找测试文件
                for line in stage.patch.splitlines():
                    if "diff --git" in line:
                        filename = line.split()[-1].lstrip("b/")
                        if any(x in filename.lower() for x in ["test", "spec", "tests"]):
                            test_files.append(filename)
                
                stage.test_files = test_files
                if test_files:
                    stage.test_patch = git.get_full_patch(
                        repo_path, base_hash, head_hash, test_files
                    )
            
            stage.stage = "patched"
            stage.end_time = time.time()
            return stage
            
        except Exception as e:
            stage.error = str(e)
            stage.end_time = time.time()
            return stage


class GenerateStage(PipelineStage):
    """阶段3：生成实例"""
    
    def __init__(self, output_dir: str):
        super().__init__("生成实例", max_workers=2)
        self.output_dir = output_dir
        self.instances_file = os.path.join(output_dir, "instances.csv")
        self.patches_file = os.path.join(output_dir, "gold_patches.json")
        self._instances_lock = threading.Lock()
        self._patches = []
        self._instances = []
        self._initialized = False
    
    def _initialize_files(self):
        if not self._initialized:
            os.makedirs(self.output_dir, exist_ok=True)
            with open(self.instances_file, "w") as f:
                f.write("instance_id,repo,repo_version,base_commit,hint,test_patch,problem_statement,version,language,FAIL_TO_PASS,PASS_TO_PASS,environment_setup_command\n")
            with open(self.patches_file, "w") as f:
                json.dump(self._patches, f)
            self._initialized = True
    
    def process(self, stage: PRStage) -> Optional[PRStage]:
        self._initialize_files()
        
        try:
            # 生成实例信息
            import pandas as pd
            
            version = "3.11"
            if stage.language == "javascript":
                version = "node20"
            elif stage.language == "go":
                version = "1.22"
            elif stage.language == "rust":
                version = "stable"
            
            # 增量写入 CSV
            with self._instances_lock:
                with open(self.instances_file, "a") as f:
                    f.write(f'"{stage.instance_id}","{stage.repo_owner}/{stage.repo_name}","{datetime.now().strftime("%Y-%m-%d")}","{stage.base_commit}","","{stage.test_patch}","{stage.instance_id}",{version},{stage.language},,,\n')
                
                # 写入 patch
                self._patches.append({
                    "instance_id": stage.instance_id,
                    "patch": stage.patch
                })
                with open(self.patches_file, "w") as f:
                    json.dump(self._patches, f, ensure_ascii=False, indent=2)
            
            stage.stage = "generated"
            stage.instance_generated = True
            stage.end_time = time.time()
            return stage
            
        except Exception as e:
            stage.error = str(e)
            stage.end_time = time.time()
            return stage


class EvaluateStage(PipelineStage):
    """阶段4：执行评估"""
    
    def __init__(self, eval_dir: str, dockerhub_username: str,
                 use_local_docker: bool = False):
        super().__init__("评估", max_workers=4)
        self.eval_dir = eval_dir
        self.dockerhub_username = dockerhub_username
        self.use_local_docker = use_local_docker
    
    def process(self, stage: PRStage) -> Optional[PRStage]:
        try:
            # 调用评估脚本
            cmd = [
                "python", EVAL_SCRIPT,
                "--raw_sample_path", os.path.join(self.eval_dir, "instances.csv"),
                "--patch_path", os.path.join(self.eval_dir, "gold_patches.json"),
                "--output_dir", self.eval_dir,
                "--dockerhub_username", self.dockerhub_username,
                "--num_workers", "1",
            ]
            
            if self.use_local_docker:
                cmd.append("--use_local_docker")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            stage.eval_result = result.returncode == 0
            stage.stage = "evaluated"
            stage.end_time = time.time()
            return stage
            
        except Exception as e:
            stage.error = str(e)
            stage.end_time = time.time()
            return stage


# ==================== 进度显示 ====================

class ProgressMonitor:
    """进度监视器"""
    
    def __init__(self, stages: List[PipelineStage]):
        self.stages = stages
        self.start_time = time.time()
        self.stop_event = threading.Event()
        self.last_update = time.time()
    
    def show_progress(self):
        while not self.stop_event.is_set():
            if time.time() - self.last_update >= 2.0:  # 每2秒更新
                print("\033[2J\033[H")  # 清屏
                
                print("=" * 60)
                print(f"🚀 流水线评估进度 [{datetime.now().strftime('%H:%M:%S')}]")
                print("=" * 60)
                print(f"\n⏱️  总耗时: {int(time.time() - self.start_time)}s")
                print()
                
                for stage in self.stages:
                    with stage.lock:
                        count = stage.processed
                        errors = stage.errors
                    
                    bar = "█" * min(count // 2, 50) + "░" * max(50 - count // 2, 0)
                    status = "✅" if errors == 0 else "⚠️"
                    
                    print(f"[{stage.name}]")
                    print(f"  {bar} {count}")
                    if errors > 0:
                        print(f"  错误: {errors}")
                    print()
                
                print("=" * 60)
                self.last_update = time.time()
            
            time.sleep(1)
    
    def stop(self):
        self.stop_event.set()


# ==================== 状态管理 ====================

class StateManager:
    """状态管理器（支持断点续跑）"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load()
    
    def _load(self) -> Dict:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {
            "processed": [],
            "failed": [],
            "timestamp": time.time(),
            "completed": False,
        }
    
    def save(self):
        os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def mark_processed(self, instance_id: str):
        self.state["processed"].append(instance_id)
        self.save()
    
    def mark_failed(self, instance_id: str, error: str):
        self.state["failed"].append({"id": instance_id, "error": error, "time": time.time()})
        self.save()
    
    def is_processed(self, instance_id: str) -> bool:
        return instance_id in self.state["processed"]
    
    def mark_complete(self):
        self.state["completed"] = True
        self.state["timestamp"] = time.time()
        self.save()


# ==================== 主流程 ====================

class PipelineEvaluator:
    """流水线评估器"""
    
    def __init__(self, args):
        self.args = args
        self.output_dir = args.output_dir
        self.state_file = os.path.join(self.output_dir, "state.json")
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 解析参数
        self.languages = args.languages or ["python", "javascript", "go", "rust"]
        self.licenses = args.licenses or ["mit", "bsd", "apache-2.0", "isc"]
        self.min_lines = args.min_lines
        self.min_stars = args.min_stars
        self.balanced = args.balanced
        self.max_results = args.max_results
        self.clone_dir = args.clone_dir or os.path.join(self.output_dir, "repos")
        self.dockerhub_username = args.dockerhub_username or ""
        self.use_local_docker = args.use_local_docker
        self.num_eval_workers = args.eval_workers
        self.resume = args.resume
        
        # 阶段
        self.stages: List[PipelineStage] = []
        self.stop_event = threading.Event()
        self.monitor: Optional[ProgressMonitor] = None
        self.state_manager = StateManager(self.state_file)
    
    def build_pipeline(self):
        """构建流水线"""
        print("🔧 构建流水线...")
        
        # 阶段1: 扫描
        scan_stage = ScanStage(
            self.languages, self.licenses,
            self.min_lines, self.min_stars,
            self.balanced, self.max_results
        )
        self.stages.append(scan_stage)
        print(f"   ✅ 阶段1: 扫描 PR ({len(self.languages)} 语言)")
        
        # 阶段2: 获取 Patch
        patch_stage = PatchStage(self.clone_dir)
        self.stages.append(patch_stage)
        print(f"   ✅ 阶段2: 获取 Patch (克隆目录: {self.clone_dir})")
        
        # 阶段3: 生成实例
        generate_stage = GenerateStage(self.output_dir)
        self.stages.append(generate_stage)
        print(f"   ✅ 阶段3: 生成实例")
        
        # 阶段4: 评估
        eval_stage = EvaluateStage(
            self.output_dir, self.dockerhub_username, self.use_local_docker
        )
        self.stages.append(eval_stage)
        print(f"   ✅ 阶段4: 评估 (Docker: {self.dockerhub_username})")
        
        # 连接流水线
        for i in range(len(self.stages) - 1):
            self.stages[i].output_queue = self.stages[i + 1].input_queue
        
        print()
    
    def run(self):
        """运行流水线"""
        print("=" * 60)
        print("🚀 启动流水线评估")
        print("=" * 60)
        
        # 断点续跑检测
        if self.resume and self.state_manager.state["processed"]:
            print(f"\n🔄 恢复运行，已处理 {len(self.state_manager.state['processed'])} 个 PR")
        
        self.build_pipeline()
        
        # 启动监视器线程
        self.monitor = ProgressMonitor(self.stages)
        monitor_thread = threading.Thread(target=self.monitor.show_progress, daemon=True)
        monitor_thread.start()
        
        # 启动各阶段线程
        threads = []
        for stage in self.stages:
            t = threading.Thread(target=stage.run, args=(self.stop_event,), daemon=True)
            threads.append(t)
            t.start()
        
        # 阶段1：扫描 PR（主线程）
        print("\n🔍 开始扫描 PR...\n")
        
        start_time = time.time()
        try:
            scan_stage = self.stages[0]
            pr_count = 0
            while True:
                try:
                    item = scan_stage.process(None)
                except Exception as e:
                    print(f"扫描错误: {e}")
                    break
                
                if item is None:
                    break
                
                # 跳过已处理
                if self.state_manager.is_processed(item.instance_id):
                    continue
                
                scan_stage.output_queue.put(item)
                pr_count += 1
                
                if pr_count % 10 == 0:
                    print(f"   📥 已扫描 {pr_count} 个 PR")
                
                if self.stop_event.is_set():
                    break
            
            # 等待所有阶段完成
            for stage in self.stages:
                while not stage.output_queue.empty() or not stage.input_queue.empty():
                    time.sleep(0.5)
            
            # 停止所有阶段
            self.stop_event.set()
            
            for t in threads:
                t.join(timeout=10)
            
            # 停止监视器
            self.monitor.stop()
            monitor_thread.join(timeout=2)
            
            # 显示最终统计
            print("\n" + "=" * 60)
            print("✅ 流水线完成")
            print("=" * 60)
            print(f"\n⏱️  总耗时: {int(time.time() - start_time)}s")
            print(f"\n📊 各阶段统计:")
            for stage in self.stages:
                print(f"   {stage.name}: {stage.processed} 个 (错误: {stage.errors})")
            
            # 保存状态
            self.state_manager.mark_complete()
            print(f"\n💾 状态已保存: {self.state_file}")
            
            # 生成报告
            self.generate_report()
            
        except KeyboardInterrupt:
            print("\n\n⏸️  收到中断信号，停止...")
            self.stop_event.set()
            if self.monitor:
                self.monitor.stop()
            self.state_manager.save()
            print("💾 当前进度已保存，下次可使用 --resume 继续")
        except Exception as e:
            print(f"\n❌ 运行错误: {e}")
            import traceback
            traceback.print_exc()
            self.stop_event.set()
            if self.monitor:
                self.monitor.stop()
    
    def generate_report(self):
        """生成评估报告"""
        report_file = os.path.join(self.output_dir, "pipeline_report.md")
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 流水线评估报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 配置\n\n")
            f.write(f"- 语言: {', '.join(self.languages)}\n")
            f.write(f"- 协议: {', '.join(self.licenses)}\n")
            f.write(f"- 最少修改行数: {self.min_lines}\n")
            f.write(f"- 最少 star 数: {self.min_stars}\n")
            f.write(f"- 语言均匀分布: {'是' if self.balanced else '否'}\n")
            f.write(f"- 最大结果数: {self.max_results}\n\n")
            
            f.write("## 各阶段统计\n\n")
            for stage in self.stages:
                f.write(f"### {stage.name}\n\n")
                f.write(f"- 处理数: {stage.processed}\n")
                f.write(f"- 错误数: {stage.errors}\n\n")
        
        print(f"📄 报告: {report_file}")


# ==================== CLI ====================

def parse_args():
    parser = argparse.ArgumentParser(
        description="流水线评估执行器 - 扫描→获取 patch→生成实例→评估 同步进行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整流水线
  python pipeline_evaluator.py \\
      --languages python javascript go rust \\
      --min-lines 110 --balanced \\
      --max-results 100 \\
      --output-dir data/eval

  # 指定协议
  python pipeline_evaluator.py \\
      --licenses mit bsd apache-2.0 \\
      --output-dir data/eval

  # 使用本地 Docker
  python pipeline_evaluator.py \\
      --use-local-docker \\
      --dockerhub_username your-username \\
      --output-dir data/eval

  # 断点续跑
  python pipeline_evaluator.py --resume --output-dir data/eval
"""
    )
    
    # 输入参数
    parser.add_argument("--languages", "-l", nargs="+",
                        default=["python", "javascript", "go", "rust"],
                        help="要扫描的语言")
    parser.add_argument("--licenses", nargs="+",
                        default=["mit", "bsd", "apache-2.0", "isc"],
                        help="要扫描的协议")
    parser.add_argument("--min-lines", type=int, default=110,
                        help="最少修改行数 (默认: 110)")
    parser.add_argument("--min-stars", type=int, default=10,
                        help="仓库最少 star 数 (默认: 10)")
    parser.add_argument("--balanced", action="store_true", default=True,
                        help="保持语言分布均匀 (默认: True)")
    parser.add_argument("--max-results", type=int, default=100,
                        help="最大结果数 (默认: 100)")
    
    # 输出参数
    parser.add_argument("--output-dir", "-o", default="data/eval",
                        help="输出目录 (默认: data/eval)")
    parser.add_argument("--clone-dir", default=None,
                        help="仓库克隆目录 (默认: output-dir/repos)")
    
    # 评估参数
    parser.add_argument("--use-local-docker", action="store_true",
                        help="使用本地 Docker 评估")
    parser.add_argument("--dockerhub-username", default="",
                        help="Docker Hub 用户名")
    parser.add_argument("--eval-workers", type=int, default=4,
                        help="评估并发数 (默认: 4)")
    
    # 运行模式
    parser.add_argument("--resume", action="store_true",
                        help="从断点处继续运行")
    parser.add_argument("--workers", type=int, default=8,
                        help="总并发数 (默认: 8)")
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # 导入辅助模块
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "helper_code"))
    
    evaluator = PipelineEvaluator(args)
    evaluator.run()


if __name__ == "__main__":
    main()
