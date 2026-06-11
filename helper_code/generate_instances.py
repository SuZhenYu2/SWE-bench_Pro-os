#!/usr/bin/env python3
"""
SWE-Bench 实例生成器 - 将 PR 数据转换为完整的评估实例

功能：
1. 读取扫描的 PR 数据和提取的 patch
2. 生成符合 SWE-Bench 格式的 CSV 实例文件
3. 生成 gold_patches.json 文件
4. 配置 Dockerfile 和测试命令

用法：
python generate_instances.py \
    --pr-data prs.jsonl \
    --patch-data patches.json \
    --output-dir data/eval \
    --num-workers 10
"""

import argparse
import json
import os
import sys
import pandas as pd
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict
from datetime import datetime

# ==================== 配置 ====================

# 语言默认版本映射
DEFAULT_LANGUAGE_VERSIONS = {
    "python": "3.11",
    "javascript": "node20",
    "typescript": "node20",
    "java": "jdk17",
    "go": "1.22",
    "rust": "stable",
    "ruby": "3.2",
    "php": "8.2",
    "dotnet": "8.0",
    "cpp": "gcc12",
    "elixir": "1.16",
}

# 仓库到语言的映射
REPO_LANGUAGE_MAP = {
    "marko-js": ("javascript", "node20"),
    "publint": ("javascript", "node20"),
    "facebook/react": ("javascript", "node18"),
    "vuejs": ("javascript", "node18"),
    "angular": ("typescript", "node18"),
    "sveltejs": ("javascript", "node18"),
    "preactjs": ("javascript", "node18"),
    "expressjs": ("javascript", "node18"),
    "fastify": ("javascript", "node18"),
    "nestjs": ("typescript", "node18"),
    "nextjs": ("typescript", "node18"),
    "nuxt": ("typescript", "node18"),
    "vitejs": ("javascript", "node18"),
    "rollup": ("javascript", "node18"),
    "esbuild": ("javascript", "node18"),
    "babel": ("javascript", "node18"),
    "webpack": ("javascript", "node18"),
    "denoland": ("javascript", "node22"),
    "bun": ("javascript", "node22"),
    "golang": ("go", "1.22"),
    "kubernetes": ("go", "1.22"),
    "docker": ("go", "1.22"),
    "prometheus": ("go", "1.22"),
    "grafana": ("go", "1.22"),
    "terraform": ("go", "1.22"),
    "hashicorp": ("go", "1.22"),
    "rust-lang": ("rust", "stable"),
    "tokio-rs": ("rust", "stable"),
    "actix": ("rust", "stable"),
    "serde-rs": ("rust", "stable"),
    "rails": ("ruby", "3.2"),
    "sinatra": ("ruby", "3.2"),
    "jekyll": ("ruby", "3.2"),
    "laravel": ("php", "8.2"),
    "symfony": ("php", "8.2"),
    "composer": ("php", "8.2"),
    "phpunit": ("php", "8.2"),
    "spring-projects": ("java", "jdk17"),
    "gradle": ("java", "jdk17"),
    "junit-team": ("java", "jdk17"),
    "hibernate": ("java", "jdk17"),
    "dotnet": ("dotnet", "8.0"),
    "aspnet": ("dotnet", "8.0"),
    "nunit": ("dotnet", "8.0"),
    "xunit": ("dotnet", "8.0"),
    "elixir-lang": ("elixir", "1.16"),
    "phoenixframework": ("elixir", "1.16"),
    "opencv": ("cpp", "gcc12"),
    "llvm": ("cpp", "clang17"),
    "grpc": ("cpp", "gcc12"),
    "boostorg": ("cpp", "gcc12"),
}


# ==================== 数据模型 ====================

@dataclass
class SWEBenchInstance:
    """SWE-Bench 实例"""
    instance_id: str
    repo: str
    repo_version: str
    base_commit: str
    hint: str
    test_patch: str
    problem_statement: str
    version: str
    language: str
    FAIL_TO_PASS: str
    PASS_TO_PASS: str
    environment_setup_command: str
    
    # 额外字段（用于评估）
    patch: str = ""
    gold_patch: str = ""
    test_files: List[str] = field(default_factory=list)
    patch_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_csv_row(self) -> dict:
        """转换为 CSV 行"""
        return {
            "instance_id": self.instance_id,
            "repo": self.repo,
            "repo_version": self.repo_version,
            "base_commit": self.base_commit,
            "hint": self.hint,
            "test_patch": self.test_patch,
            "problem_statement": self.problem_statement,
            "version": self.version,
            "language": self.language,
            "FAIL_TO_PASS": self.FAIL_TO_PASS,
            "PASS_TO_PASS": self.PASS_TO_PASS,
            "environment_setup_command": self.environment_setup_command,
        }


# ==================== 实例生成器 ====================

class InstanceGenerator:
    """SWE-Bench 实例生成器"""
    
    def __init__(self):
        self.instances: List[SWEBenchInstance] = []
    
    def detect_language_version(self, repo_name: str, 
                                 detected_language: str = None) -> tuple[str, str]:
        """检测语言和版本"""
        repo_lower = repo_name.lower()
        
        # 先检查已知仓库映射
        for prefix, (lang, ver) in REPO_LANGUAGE_MAP.items():
            if prefix in repo_lower:
                return lang, ver
        
        # 从检测到的语言推断
        if detected_language and detected_language in DEFAULT_LANGUAGE_VERSIONS:
            return detected_language, DEFAULT_LANGUAGE_VERSIONS[detected_language]
        
        # 默认返回 Python
        return "python", DEFAULT_LANGUAGE_VERSIONS["python"]
    
    def _generate_test_commands(self, language: str, test_files: List[str]) -> tuple[str, str]:
        """生成测试命令"""
        if not test_files:
            return "", ""
        
        if language == "python":
            test_files_str = " ".join([f"'{f}'" for f in test_files[:10]])
            fail_cmd = f"python -m pytest {test_files_str} -x -v || true"
            pass_cmd = f"python -m pytest {test_files_str} -v || true"
        
        elif language in ["javascript", "typescript"]:
            test_files_str = " ".join([f"'{f}'" for f in test_files[:10]])
            fail_cmd = f"npm test -- {test_files_str} 2>&1 | head -100 || true"
            pass_cmd = f"npm test -- {test_files_str} 2>&1 | head -100 || true"
        
        elif language == "java":
            test_files_str = " ".join([f.replace("/", ".").rstrip(".java") for f in test_files[:10]])
            fail_cmd = f"mvn test -Dtest={test_files_str} -q || true"
            pass_cmd = f"mvn test -Dtest={test_files_str} -q || true"
        
        elif language == "go":
            fail_cmd = "go test ./... -v -count=1 2>&1 | head -100 || true"
            pass_cmd = "go test ./... -v -count=1 2>&1 | head -100 || true"
        
        elif language == "rust":
            fail_cmd = "cargo test 2>&1 | head -100 || true"
            pass_cmd = "cargo test 2>&1 | head -100 || true"
        
        elif language == "ruby":
            fail_cmd = "bundle exec rake test 2>&1 | head -100 || true"
            pass_cmd = "bundle exec rake test 2>&1 | head -100 || true"
        
        elif language == "php":
            fail_cmd = "vendor/bin/phpunit 2>&1 | head -100 || true"
            pass_cmd = "vendor/bin/phpunit 2>&1 | head -100 || true"
        
        elif language == "dotnet":
            fail_cmd = "dotnet test 2>&1 | head -100 || true"
            pass_cmd = "dotnet test 2>&1 | head -100 || true"
        
        elif language == "cpp":
            fail_cmd = "make test 2>&1 | head -100 || true"
            pass_cmd = "make test 2>&1 | head -100 || true"
        
        elif language == "elixir":
            fail_cmd = "mix test 2>&1 | head -100 || true"
            pass_cmd = "mix test 2>&1 | head -100 || true"
        
        else:
            fail_cmd = "echo 'Unknown language' && exit 1"
            pass_cmd = "echo 'Unknown language' && exit 1"
        
        return fail_cmd, pass_cmd
    
    def generate_from_pr_data(self, pr_data: dict, patch_data: dict = None) -> Optional[SWEBenchInstance]:
        """从 PR 数据生成实例"""
        try:
            repo_owner = pr_data.get("repo_owner", "")
            repo_name = pr_data.get("repo_name", "")
            repo = f"{repo_owner}/{repo_name}"
            
            instance_id = pr_data.get("instance_id") or f"instance_{repo_owner}__{repo_name}__{pr_data.get('pr_number')}"
            
            # 检测语言和版本
            detected_lang = pr_data.get("detected_language")
            language, version = self.detect_language_version(repo, detected_lang)
            
            # 获取 patch 数据
            patch = ""
            test_patch = ""
            test_files = []
            patch_files = []
            base_commit = ""
            
            if patch_data:
                patch = patch_data.get("patch", "")
                test_patch = patch_data.get("test_patch", "")
                test_files = patch_data.get("test_files", [])
                patch_files = patch_data.get("all_files", [])
                base_commit = patch_data.get("base_commit", "")
            
            # 生成问题描述
            pr_title = pr_data.get("pr_title", "")
            pr_body = pr_data.get("pr_body", "") or ""
            problem_statement = f"{pr_title}\n\n{pr_body[:5000]}" if pr_body else pr_title
            
            # 生成提示
            hint = pr_data.get("issue_url") or pr_data.get("pr_url", "")
            
            # 生成版本信息
            merged_at = pr_data.get("merged_at", "")
            repo_version = merged_at[:10] if merged_at else datetime.now().strftime("%Y-%m-%d")
            
            # 生成测试命令
            fail_cmd, pass_cmd = self._generate_test_commands(language, test_files)
            
            instance = SWEBenchInstance(
                instance_id=instance_id,
                repo=repo,
                repo_version=repo_version,
                base_commit=base_commit,
                hint=hint,
                test_patch=test_patch,
                problem_statement=problem_statement,
                version=version,
                language=language,
                FAIL_TO_PASS=fail_cmd,
                PASS_TO_PASS=pass_cmd,
                environment_setup_command="",
                patch=patch,
                gold_patch=patch,
                test_files=test_files,
                patch_files=patch_files,
            )
            
            return instance
            
        except Exception as e:
            print(f"⚠️ 生成实例失败: {e}")
            return None
    
    def generate_batch(self, pr_list: List[dict], 
                       patch_list: List[dict] = None,
                       language: str = "python") -> List[SWEBenchInstance]:
        """批量生成实例"""
        self.instances = []
        
        # 创建 patch 查找表
        patch_map = {}
        if patch_list:
            for p in patch_list:
                patch_map[p.get("instance_id", "")] = p
        
        print(f"🔍 开始生成 {len(pr_list)} 个实例...")
        
        for pr in pr_list:
            instance_id = pr.get("instance_id")
            patch_data = patch_map.get(instance_id) if instance_id else None
            
            instance = self.generate_from_pr_data(pr, patch_data)
            if instance:
                self.instances.append(instance)
                print(f"   ✅ {instance.instance_id}: {instance.language}/{instance.version}")
        
        print(f"\n✅ 生成完成，共 {len(self.instances)} 个实例")
        return self.instances
    
    def save_to_csv(self, output_path: str):
        """保存为 CSV 格式（用于评估脚本）"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        rows = [inst.to_csv_row() for inst in self.instances]
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        
        print(f"💾 CSV 已保存到 {output_path}")
        print(f"   行数: {len(df)}")
        return output_path
    
    def save_to_json(self, output_path: str):
        """保存为 JSON 格式（完整信息）"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([inst.to_dict() for inst in self.instances], f, ensure_ascii=False, indent=2)
        
        print(f"💾 JSON 已保存到 {output_path}")
        return output_path
    
    def save_gold_patches(self, output_path: str):
        """保存 gold patches（用于评估）"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        patches = []
        for inst in self.instances:
            if inst.patch:
                patches.append({
                    "instance_id": inst.instance_id,
                    "patch": inst.patch,
                })
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(patches, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Gold patches 已保存到 {output_path}")
        print(f"   数量: {len(patches)}")
        return output_path
    
    def generate_all(self, pr_list: List[dict], 
                     patch_list: List[dict] = None,
                     output_dir: str = "data/eval",
                     language: str = "python") -> Dict[str, str]:
        """生成所有格式的文件"""
        # 生成实例
        self.generate_batch(pr_list, patch_list, language)
        
        outputs = {}
        
        # 保存 CSV（主输入）
        csv_path = os.path.join(output_dir, "instances.csv")
        self.save_to_csv(csv_path)
        outputs["csv"] = csv_path
        
        # 保存 JSON（完整信息）
        json_path = os.path.join(output_dir, "instances.json")
        self.save_to_json(json_path)
        outputs["json"] = json_path
        
        # 保存 gold patches
        patches_path = os.path.join(output_dir, "gold_patches.json")
        self.save_gold_patches(patches_path)
        outputs["patches"] = patches_path
        
        return outputs


# ==================== CLI ====================

def parse_args():
    parser = argparse.ArgumentParser(
        description="生成 SWE-Bench 格式的评估实例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 PR 数据生成实例
  python generate_instances.py --pr-data prs.jsonl --output-dir data/eval

  # 结合 patch 数据
  python generate_instances.py --pr-data prs.jsonl --patch-data patches.json --output-dir data/eval

  # 完整流程
  python generate_instances.py --pr-data data/prs.jsonl --patch-data data/patches.json \\
      --output-dir data/eval --language python
        """
    )
    
    parser.add_argument("--pr-data", "-i", required=True,
                        help="输入的 PR 数据文件 (JSON 或 JSONL)")
    parser.add_argument("--patch-data", "-p",
                        help="输入的 patch 数据文件 (可选)")
    parser.add_argument("--output-dir", "-o", default="data/eval",
                        help="输出目录 (默认: data/eval)")
    parser.add_argument("--language", "-l", default="python",
                        help="默认语言 (默认: python)")
    parser.add_argument("--csv", default=None,
                        help="CSV 输出路径 (覆盖 output-dir)")
    parser.add_argument("--json", default=None,
                        help="JSON 输出路径 (覆盖 output-dir)")
    parser.add_argument("--patches", default=None,
                        help="Patches 输出路径 (覆盖 output-dir)")
    
    return parser.parse_args()


def load_json(input_path: str) -> List[dict]:
    """加载 JSON/JSONL 文件"""
    with open(input_path, "r", encoding="utf-8") as f:
        if input_path.endswith(".jsonl"):
            return [json.loads(line) for line in f]
        else:
            return json.load(f)


def main():
    args = parse_args()
    
    # 加载数据
    pr_list = load_json(args.pr_data)
    print(f"📂 已加载 {len(pr_list)} 条 PR 数据")
    
    patch_list = None
    if args.patch_data:
        patch_list = load_json(args.patch_data)
        print(f"📂 已加载 {len(patch_list)} 条 patch 数据")
    
    # 创建生成器
    generator = InstanceGenerator()
    
    # 生成实例
    outputs = generator.generate_all(
        pr_list, patch_list, 
        args.output_dir, 
        args.language
    )
    
    # 统计信息
    lang_stats = {}
    for inst in generator.instances:
        lang = inst.language
        lang_stats[lang] = lang_stats.get(lang, 0) + 1
    
    print("\n📊 语言分布:")
    for lang, count in sorted(lang_stats.items(), key=lambda x: -x[1]):
        print(f"   {lang}: {count}")
    
    print(f"\n✅ 输出文件:")
    for name, path in outputs.items():
        print(f"   {name}: {path}")


if __name__ == "__main__":
    main()
