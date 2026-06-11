#!/usr/bin/env python3
"""
SWE-Bench Pro 评估执行器 - 一键执行完整评估流程

功能：
1. 扫描 GitHub PR（可选）
2. 获取 PR patch（可选）
3. 生成评估实例（可选）
4. 执行评估

用法：
python run_evaluation.py --scan --patch --generate --eval
python run_evaluation.py --eval --input-dir data/eval
python run_evaluation.py --quick --languages python --max-results 50
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
from datetime import datetime
from typing import Optional, List, Dict

# ==================== 配置 ====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HELPER_DIR = os.path.join(SCRIPT_DIR, "helper_code")
SCAN_SCRIPT = os.path.join(HELPER_DIR, "scan_github_prs.py")
PATCH_SCRIPT = os.path.join(HELPER_DIR, "fetch_pr_patch.py")
GENERATE_SCRIPT = os.path.join(HELPER_DIR, "generate_instances.py")
EVAL_SCRIPT = os.path.join(SCRIPT_DIR, "swe_bench_pro_eval.py")

DEFAULT_OUTPUT_DIR = "data/eval"


# ==================== 工具函数 ====================

def run_command(cmd: List[str], cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    """运行命令"""
    print(f"\n🔧 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if check and result.returncode != 0:
        print(f"❌ 命令执行失败: {result.stderr}")
        sys.exit(1)
    return result


def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def load_json(path: str) -> List[dict]:
    """加载 JSON/JSONL 文件"""
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith(".jsonl"):
            return [json.loads(line) for line in f]
        return json.load(f)


def save_json(data, path: str):
    """保存 JSON 文件"""
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== 步骤执行 ====================

def step_scan(args) -> str:
    """步骤1: 扫描 PR"""
    print("\n" + "=" * 60)
    print("📋 步骤 1: 扫描 GitHub PR")
    print("=" * 60)
    
    output_file = args.pr_output or os.path.join(DEFAULT_OUTPUT_DIR, "prs.jsonl")
    ensure_dir(os.path.dirname(output_file) or ".")
    
    cmd = [
        "python", SCAN_SCRIPT,
        "--output", output_file,
        "--min-lines", str(args.min_lines),
        "--balanced",
        "--max-results", str(args.max_results),
    ]
    
    if args.languages:
        cmd.extend(["--languages"] + args.languages)
    
    if args.licenses:
        cmd.extend(["--licenses"] + args.licenses)
    
    if args.token:
        cmd.extend(["--token", args.token])
    
    run_command(cmd, cwd=SCRIPT_DIR)
    
    print(f"\n✅ PR 扫描完成: {output_file}")
    return output_file


def step_fetch_patch(args, pr_input: str) -> str:
    """步骤2: 获取 Patch"""
    print("\n" + "=" * 60)
    print("📋 步骤 2: 获取 PR Patch")
    print("=" * 60)
    
    output_file = args.patch_output or os.path.join(DEFAULT_OUTPUT_DIR, "patches.json")
    ensure_dir(os.path.dirname(output_file) or ".")
    
    cmd = [
        "python", PATCH_SCRIPT,
        "--input", pr_input,
        "--output", output_file,
        "--format", "json",
        "--max-workers", str(args.max_workers),
    ]
    
    if args.clone_dir:
        cmd.extend(["--clone-dir", args.clone_dir])
    
    if args.token:
        cmd.extend(["--token", args.token])
    
    if args.language:
        cmd.extend(["--language", args.language])
    
    run_command(cmd, cwd=SCRIPT_DIR)
    
    print(f"\n✅ Patch 获取完成: {output_file}")
    return output_file


def step_generate(args, pr_input: str, patch_input: str = None) -> Dict[str, str]:
    """步骤3: 生成评估实例"""
    print("\n" + "=" * 60)
    print("📋 步骤 3: 生成评估实例")
    print("=" * 60)
    
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR
    ensure_dir(output_dir)
    
    cmd = [
        "python", GENERATE_SCRIPT,
        "--pr-data", pr_input,
        "--output-dir", output_dir,
    ]
    
    if patch_input:
        cmd.extend(["--patch-data", patch_input])
    
    if args.language:
        cmd.extend(["--language", args.language])
    
    run_command(cmd, cwd=SCRIPT_DIR)
    
    outputs = {
        "csv": os.path.join(output_dir, "instances.csv"),
        "json": os.path.join(output_dir, "instances.json"),
        "patches": os.path.join(output_dir, "gold_patches.json"),
    }
    
    print(f"\n✅ 实例生成完成:")
    for name, path in outputs.items():
        print(f"   {name}: {path}")
    
    return outputs


def step_evaluate(args, eval_dir: str = None) -> str:
    """步骤4: 执行评估"""
    print("\n" + "=" * 60)
    print("📋 步骤 4: 执行评估")
    print("=" * 60)
    
    if eval_dir is None:
        eval_dir = args.input_dir or DEFAULT_OUTPUT_DIR
    
    csv_file = os.path.join(eval_dir, "instances.csv")
    patches_file = os.path.join(eval_dir, "gold_patches.json")
    output_dir = os.path.join(eval_dir, "results")
    
    if not os.path.exists(csv_file):
        print(f"❌ 实例文件不存在: {csv_file}")
        sys.exit(1)
    
    ensure_dir(output_dir)
    
    cmd = [
        "python", EVAL_SCRIPT,
        "--raw_sample_path", csv_file,
        "--patch_path", patches_file,
        "--output_dir", output_dir,
        "--num_workers", str(args.num_workers),
    ]
    
    if args.use_local_docker:
        cmd.append("--use_local_docker")
    
    if args.dockerhub_username:
        cmd.extend(["--dockerhub_username", args.dockerhub_username])
    
    if args.eval_sample_size:
        cmd.extend(["--eval_sample_size", str(args.eval_sample_size)])
    
    run_command(cmd, cwd=SCRIPT_DIR)
    
    print(f"\n✅ 评估完成: {output_dir}")
    return output_dir


def generate_report(results_dir: str):
    """生成评估报告"""
    print("\n" + "=" * 60)
    print("📊 评估报告")
    print("=" * 60)
    
    results_file = os.path.join(results_dir, "results.json")
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            results = json.load(f)
        
        total = len(results)
        passed = sum(1 for r in results.values() if r.get("status") == "RESOLVED")
        failed = total - passed
        
        print(f"\n总计: {total}")
        print(f"通过: {passed} ({passed/total*100:.1f}%)")
        print(f"失败: {failed} ({failed/total*100:.1f}%)")
    else:
        print("\n⚠️ 结果文件未找到，请检查评估日志")


# ==================== CLI ====================

def parse_args():
    parser = argparse.ArgumentParser(
        description="SWE-Bench Pro 评估执行器 - 一键执行完整评估流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整流程（扫描 + 获取 patch + 生成实例 + 评估）
  python run_evaluation.py --scan --patch --generate --eval \\
      --languages python javascript \\
      --min-lines 110 --max-results 100

  # 快速评估（跳过扫描，使用已有数据）
  python run_evaluation.py --eval --input-dir data/eval

  # 仅扫描和生成（不执行评估）
  python run_evaluation.py --scan --patch --generate \\
      --languages python go rust \\
      --max-results 50

  # 使用 Docker Hub 镜像
  python run_evaluation.py --eval \\
      --dockerhub_username your-username \\
      --use_local_docker
        """
    )
    
    # 流程控制
    parser.add_argument("--scan", action="store_true",
                        help="执行 PR 扫描步骤")
    parser.add_argument("--patch", action="store_true",
                        help="执行 Patch 获取步骤")
    parser.add_argument("--generate", action="store_true",
                        help="执行实例生成步骤")
    parser.add_argument("--eval", action="store_true",
                        help="执行评估步骤")
    
    # 全流程快捷方式
    parser.add_argument("--full", action="store_true",
                        help="执行全部步骤（等同于 --scan --patch --generate --eval）")
    parser.add_argument("--quick", action="store_true",
                        help="快速模式：扫描少量数据进行测试")
    
    # 输入输出
    parser.add_argument("--input-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"输入目录 (默认: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"输出目录 (默认: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--pr-output",
                        help="PR 数据输出路径")
    parser.add_argument("--patch-output",
                        help="Patch 数据输出路径")
    
    # 扫描参数
    parser.add_argument("--languages", nargs="+",
                        help="要扫描的语言")
    parser.add_argument("--licenses", nargs="+",
                        help="要扫描的协议")
    parser.add_argument("--min-lines", type=int, default=110,
                        help="最少修改行数 (默认: 110)")
    parser.add_argument("--max-results", type=int, default=100,
                        help="最大结果数 (默认: 100)")
    
    # Patch 参数
    parser.add_argument("--clone-dir",
                        help="仓库克隆目录（用于复用）")
    parser.add_argument("--language", default="python",
                        help="默认语言 (默认: python)")
    parser.add_argument("--max-workers", type=int, default=4,
                        help="并发线程数 (默认: 4)")
    
    # 评估参数
    parser.add_argument("--num-workers", type=int, default=10,
                        help="评估并发数 (默认: 10)")
    parser.add_argument("--eval-sample-size", type=int,
                        help="评估样本大小（用于测试）")
    parser.add_argument("--use-local-docker", action="store_true",
                        help="使用本地 Docker 而非 Modal")
    parser.add_argument("--dockerhub-username",
                        help="Docker Hub 用户名")
    
    # 其他
    parser.add_argument("--token", "-t",
                        help="GitHub Token (或设置 GITHUB_TOKEN 环境变量)")
    parser.add_argument("--report", action="store_true",
                        help="从已有结果生成报告")
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # 处理快捷方式
    if args.full:
        args.scan = args.patch = args.generate = args.eval = True
    
    if args.quick:
        args.scan = args.patch = args.generate = True
        args.max_results = 10
        args.min_lines = 50
    
    # 如果什么都没指定，显示帮助
    if not any([args.scan, args.patch, args.generate, args.eval, args.report]):
        parse_args()  # 显示帮助
        print("\n⚠️ 请指定要执行的步骤（--scan, --patch, --generate, --eval）")
        print("   或使用 --full 执行完整流程，或使用 --report 生成报告")
        sys.exit(0)
    
    print("=" * 60)
    print("🚀 SWE-Bench Pro 评估执行器")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输出目录: {args.output_dir}")
    
    # 生成报告（不需要其他步骤）
    if args.report:
        generate_report(args.input_dir)
        return
    
    pr_file = None
    patch_file = None
    eval_dir = args.input_dir
    
    # 步骤1: 扫描
    if args.scan:
        pr_file = step_scan(args)
        eval_dir = os.path.dirname(pr_file) or DEFAULT_OUTPUT_DIR
    
    # 步骤2: 获取 Patch
    if args.patch:
        if not pr_file:
            pr_file = os.path.join(eval_dir, "prs.jsonl")
            if not os.path.exists(pr_file):
                print(f"❌ PR 文件不存在: {pr_file}")
                sys.exit(1)
        patch_file = step_fetch_patch(args, pr_file)
    
    # 步骤3: 生成实例
    if args.generate:
        if not pr_file:
            pr_file = os.path.join(eval_dir, "prs.jsonl")
            if not os.path.exists(pr_file):
                print(f"❌ PR 文件不存在: {pr_file}")
                sys.exit(1)
        
        if not patch_file:
            patch_file = os.path.join(eval_dir, "patches.json")
            if not os.path.exists(patch_file):
                print(f"⚠️ Patch 文件不存在，将使用 PR 数据生成")
                patch_file = None
        
        outputs = step_generate(args, pr_file, patch_file)
        eval_dir = os.path.dirname(outputs.get("csv")) or DEFAULT_OUTPUT_DIR
    
    # 步骤4: 评估
    if args.eval:
        step_evaluate(args, eval_dir)
        
        # 自动生成报告
        results_dir = os.path.join(eval_dir, "results")
        if os.path.exists(results_dir):
            generate_report(results_dir)
    
    print("\n" + "=" * 60)
    print("✅ 所有步骤执行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
