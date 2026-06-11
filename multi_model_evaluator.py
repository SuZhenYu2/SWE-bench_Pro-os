#!/usr/bin/env python3
"""
多模型评估执行器 - 支持 Qwen、Opus 等模型的多次评估

功能：
1. 支持多种模型 (Qwen, Opus, Claude, GPT 等)
2. 支持多轮次评估（同一模型多次运行）
3. 统计每个模型通过数量
4. 生成对比报告

用法：
python multi_model_evaluator.py \
    --model qwen --runs 4 \
    --model opus --runs 8 \
    --input-dir data/eval \
    --threshold "qwen:<3,opus:>=1"

模型配置：
- qwen: Qwen 模型
- opus: Claude Opus 模型
- sonnet: Claude Sonnet 模型
- gpt4: GPT-4 模型
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# ==================== 配置 ====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EVAL_SCRIPT = os.path.join(SCRIPT_DIR, "swe_bench_pro_eval.py")

# 模型配置
MODEL_CONFIGS = {
    "qwen": {
        "name": "Qwen",
        "api_type": "openai",  # OpenAI 兼容 API
        "model_name": "qwen-plus",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    "qwen-turbo": {
        "name": "Qwen Turbo",
        "api_type": "openai",
        "model_name": "qwen-turbo",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    "qwen-max": {
        "name": "Qwen Max",
        "api_type": "openai",
        "model_name": "qwen-max",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    "opus": {
        "name": "Claude Opus",
        "api_type": "anthropic",
        "model_name": "claude-3-opus-20240229",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "sonnet": {
        "name": "Claude Sonnet",
        "api_type": "anthropic",
        "model_name": "claude-3-sonnet-20240229",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "haiku": {
        "name": "Claude Haiku",
        "api_type": "anthropic",
        "model_name": "claude-3-haiku-20240307",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "gpt4": {
        "name": "GPT-4",
        "api_type": "openai",
        "model_name": "gpt-4",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    "gpt4-turbo": {
        "name": "GPT-4 Turbo",
        "api_type": "openai",
        "model_name": "gpt-4-turbo",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
}


# ==================== 数据模型 ====================

@dataclass
class ModelRun:
    """单次模型运行"""
    model: str
    run_id: int
    instance_id: str
    passed: bool
    result: Optional[dict] = None


@dataclass
class ModelStats:
    """模型统计"""
    model: str
    total_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    instances: List[str] = field(default_factory=list)
    passed_instances: List[str] = field(default_factory=list)
    results: Dict[str, ModelRun] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """评估结果"""
    model: str
    runs: int
    passed: int
    threshold: str
    passed_threshold: bool


# ==================== 评估器 ====================

class MultiModelEvaluator:
    """多模型评估器"""
    
    def __init__(self, input_dir: str, output_dir: str = None):
        self.input_dir = input_dir
        self.output_dir = output_dir or os.path.join(input_dir, "multi_model_results")
        self.model_configs: Dict[str, dict] = {}
        self.model_runs: Dict[str, List[ModelRun]] = {}
        self.model_stats: Dict[str, ModelStats] = {}
        
        os.makedirs(self.output_dir, exist_ok=True)
    
    def add_model(self, model: str, runs: int, **kwargs):
        """添加要评估的模型"""
        if model not in MODEL_CONFIGS:
            print(f"⚠️ 未知模型: {model}，将使用默认配置")
        
        config = MODEL_CONFIGS.get(model, {}).copy()
        config.update(kwargs)
        config["runs"] = runs
        self.model_configs[model] = config
        self.model_runs[model] = []
        
        print(f"✅ 添加模型: {model} x {runs} 次")
    
    def load_instances(self) -> List[str]:
        """加载评估实例"""
        csv_file = os.path.join(self.input_dir, "instances.csv")
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"实例文件不存在: {csv_file}")
        
        df = pd.read_csv(csv_file)
        return df["instance_id"].tolist()
    
    def run_single_evaluation(self, model: str, run_id: int, 
                              instance_id: str) -> ModelRun:
        """执行单次评估"""
        config = self.model_configs.get(model, {})
        
        print(f"\n🔄 [{model}] Run #{run_id}: {instance_id}")
        
        # 创建该模型/轮次的输出目录
        model_output = os.path.join(self.output_dir, model, f"run_{run_id}")
        os.makedirs(model_output, exist_ok=True)
        
        # 设置环境变量（API 配置）
        env = os.environ.copy()
        if config.get("api_type") == "anthropic":
            env["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")
            env["MODEL_TYPE"] = "anthropic"
        elif config.get("api_type") == "openai":
            env["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
            env["OPENAI_API_BASE"] = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
            env["MODEL_TYPE"] = "openai"
        
        env["MODEL_NAME"] = config.get("model_name", model)
        env["MODEL_TEMPERATURE"] = str(config.get("temperature", 0.2))
        
        # 这里需要调用实际的模型生成脚本
        # 假设有一个 generate_patch.py 脚本
        # 生成命令需要根据实际项目调整
        # 此处为示例
        
        result = ModelRun(
            model=model,
            run_id=run_id,
            instance_id=instance_id,
            passed=False,
            result=None
        )
        
        return result
    
    def run_model_evaluations(self, model: str) -> ModelStats:
        """运行单个模型的所有评估"""
        config = self.model_configs[model]
        runs = config["runs"]
        
        stats = ModelStats(model=model)
        
        # 加载实例
        instances = self.load_instances()
        stats.instances = instances
        
        print(f"\n{'='*60}")
        print(f"🤖 开始评估模型: {model} ({MODEL_CONFIGS.get(model, {}).get('name', model)})")
        print(f"   轮次: {runs}")
        print(f"   实例数: {len(instances)}")
        print(f"{'='*60}")
        
        for run_id in range(1, runs + 1):
            print(f"\n📊 第 {run_id}/{runs} 轮")
            
            passed_count = 0
            for idx, instance_id in enumerate(instances):
                run_result = self.run_single_evaluation(model, run_id, instance_id)
                self.model_runs[model].append(run_result)
                stats.results[f"{instance_id}_run{run_id}"] = run_result
                
                if run_result.passed:
                    passed_count += 1
                    if instance_id not in stats.passed_instances:
                        stats.passed_instances.append(instance_id)
                
                # 进度显示
                progress = (idx + 1) / len(instances) * 100
                print(f"   [{idx+1}/{len(instances)}] {progress:.1f}% - 通过: {passed_count}")
            
            stats.total_runs += len(instances)
        
        stats.passed_runs = len(stats.passed_instances)
        stats.failed_runs = stats.total_runs - stats.passed_runs
        
        return stats
    
    def run_all_evaluations(self) -> Dict[str, ModelStats]:
        """运行所有模型的评估"""
        for model in self.model_configs:
            stats = self.run_model_evaluations(model)
            self.model_stats[model] = stats
        
        return self.model_stats
    
    def check_thresholds(self, thresholds: Dict[str, str]) -> List[EvaluationResult]:
        """检查是否满足阈值条件"""
        results = []
        
        for model, threshold in thresholds.items():
            if model not in self.model_stats:
                print(f"⚠️ 模型 {model} 未评估")
                continue
            
            stats = self.model_stats[model]
            runs = self.model_configs[model]["runs"]
            passed = stats.passed_runs
            
            # 解析阈值条件
            if threshold.startswith("<="):
                target = int(threshold[2:])
                passed_check = passed <= target
                condition = f"通过数 ({passed}) <= {target}"
            elif threshold.startswith(">="):
                target = int(threshold[2:])
                passed_check = passed >= target
                condition = f"通过数 ({passed}) >= {target}"
            elif threshold.startswith("<"):
                target = int(threshold[1:])
                passed_check = passed < target
                condition = f"通过数 ({passed}) < {target}"
            elif threshold.startswith(">"):
                target = int(threshold[1:])
                passed_check = passed > target
                condition = f"通过数 ({passed}) > {target}"
            elif threshold.startswith("="):
                target = int(threshold[1:])
                passed_check = passed == target
                condition = f"通过数 ({passed}) == {target}"
            else:
                target = int(threshold)
                passed_check = passed >= target
                condition = f"通过数 ({passed}) >= {target}"
            
            result = EvaluationResult(
                model=model,
                runs=runs,
                passed=passed,
                threshold=condition,
                passed_threshold=passed_check
            )
            results.append(result)
        
        return results
    
    def generate_report(self, threshold_results: List[EvaluationResult] = None):
        """生成评估报告"""
        report_file = os.path.join(self.output_dir, "evaluation_report.md")
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 多模型评估报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 汇总表
            f.write("## 📊 评估汇总\n\n")
            f.write("| 模型 | 轮次 | 通过数 | 通过率 | 状态 |\n")
            f.write("|------|------|--------|--------|------|\n")
            
            for model, stats in self.model_stats.items():
                runs = self.model_configs[model]["runs"]
                total = len(stats.instances) * runs
                rate = stats.passed_runs / total * 100 if total > 0 else 0
                status = "✅ 通过" if stats.passed_runs > 0 else "❌ 未通过"
                
                f.write(f"| {model} | {runs} | {stats.passed_runs} | {rate:.1f}% | {status} |\n")
            
            f.write("\n## 📋 详细结果\n\n")
            
            for model, stats in self.model_stats.items():
                f.write(f"### {model}\n\n")
                f.write(f"- 模型名称: {MODEL_CONFIGS.get(model, {}).get('name', model)}\n")
                f.write(f"- API 类型: {self.model_configs[model].get('api_type', 'unknown')}\n")
                f.write(f"- 模型名: {self.model_configs[model].get('model_name', model)}\n")
                f.write(f"- 评估轮次: {self.model_configs[model]['runs']}\n")
                f.write(f"- 通过实例: {stats.passed_runs}/{len(stats.instances)}\n")
                f.write(f"- 通过率: {stats.passed_runs/len(stats.instances)*100:.1f}%\n\n")
                
                if stats.passed_instances:
                    f.write("**通过实例列表:**\n")
                    for inst in stats.passed_instances:
                        f.write(f"- `{inst}`\n")
                    f.write("\n")
            
            if threshold_results:
                f.write("## 🎯 阈值检查\n\n")
                for result in threshold_results:
                    status = "✅" if result.passed_threshold else "❌"
                    f.write(f"{status} **{result.model}**: {result.threshold}\n")
        
        print(f"\n📄 报告已生成: {report_file}")
        return report_file


# ==================== CLI ====================

def parse_args():
    parser = argparse.ArgumentParser(
        description="多模型评估执行器 - 支持 Qwen、Opus 等模型的多次评估",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # Qwen 4次, Opus 8次
  python multi_model_evaluator.py \\
      --model qwen --runs 4 \\
      --model opus --runs 8 \\
      --input-dir data/eval \\
      --threshold "qwen:<3,opus:>=1"

  # 使用自定义阈值
  python multi_model_evaluator.py \\
      --model qwen --runs 4 --model sonnet --runs 8 \\
      --threshold "qwen:<=1,sonnet:>=3" \\
      --input-dir data/eval

  # 评估报告
  python multi_model_evaluator.py --report --input-dir data/eval/multi_model_results

阈值语法:
  - qwen:<3      → Qwen 通过数 < 3
  - opus:>=1     → Opus 通过数 >= 1
  - gpt4:=0      → GPT-4 通过数 == 0
  - sonnet:>5    → Sonnet 通过数 > 5
        """
    )
    
    parser.add_argument("--input-dir", "-i", required=True,
                        help="输入目录 (包含 instances.csv)")
    parser.add_argument("--output-dir", "-o",
                        help="输出目录 (默认: input-dir/multi_model_results)")
    parser.add_argument("--model", "-m", action="append",
                        help="模型配置，格式: model_name:runs 或 model_name")
    parser.add_argument("--runs", type=int,
                        help="每个模型运行次数")
    parser.add_argument("--threshold", "-t",
                        help="阈值条件，格式: model:condition,model:condition...")
    parser.add_argument("--report", action="store_true",
                        help="仅生成报告")
    parser.add_argument("--runs-dir",
                        help="指定已有的运行结果目录用于生成报告")
    
    return parser.parse_args()


def parse_model_args(model_args: List[str]) -> Dict[str, int]:
    """解析模型参数"""
    models = {}
    for arg in model_args:
        parts = arg.split(":")
        model = parts[0]
        runs = int(parts[1]) if len(parts) > 1 else 1
        models[model] = runs
    return models


def parse_thresholds(threshold_str: str) -> Dict[str, str]:
    """解析阈值字符串"""
    thresholds = {}
    for part in threshold_str.split(","):
        if ":" in part:
            model, condition = part.split(":", 1)
            thresholds[model.strip()] = condition.strip()
    return thresholds


def main():
    args = parse_args()
    
    # 解析模型参数
    models_to_run = {}
    if args.model:
        models_to_run = parse_model_args(args.model)
    
    if args.runs and not args.model:
        print("⚠️ --runs 需要配合 --model 使用")
        sys.exit(1)
    
    # 创建评估器
    evaluator = MultiModelEvaluator(args.input_dir, args.output_dir)
    
    # 添加模型
    for model, runs in models_to_run.items():
        evaluator.add_model(model, runs)
    
    # 加载已有结果或运行评估
    if args.report:
        # 加载已有结果生成报告
        results_dir = args.runs_dir or evaluator.output_dir
        print(f"📊 从 {results_dir} 加载结果并生成报告...")
        
        # TODO: 实现从已有结果加载
        evaluator.generate_report()
        
    elif models_to_run:
        # 运行评估
        evaluator.run_all_evaluations()
        
        # 检查阈值
        if args.threshold:
            thresholds = parse_thresholds(args.threshold)
            results = evaluator.check_thresholds(thresholds)
            
            print("\n" + "="*60)
            print("🎯 阈值检查结果")
            print("="*60)
            
            for result in results:
                status = "✅" if result.passed_threshold else "❌"
                print(f"{status} {result.model}: {result.threshold}")
        
        # 生成报告
        evaluator.generate_report()
    
    else:
        print("⚠️ 请指定要评估的模型 (--model) 或使用 --report 生成报告")


if __name__ == "__main__":
    main()
