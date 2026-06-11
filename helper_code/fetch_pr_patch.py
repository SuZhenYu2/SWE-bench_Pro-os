#!/usr/bin/env python3
"""
GitHub PR Patch 提取工具 - 获取 PR 的实际代码变更

功能：
1. 从扫描的 PR 数据中提取完整的代码变更 (patch)
2. 获取测试相关的文件变更 (test_patch)
3. 克隆仓库并获取精确的 base_commit
4. 生成完整的 gold_patch JSON

用法：
python fetch_pr_patch.py --input prs.jsonl --output patches.json

与 scan_github_prs.py 结合使用：
python scan_github_prs.py --output data/prs.jsonl --min-lines 110 --balanced
python fetch_pr_patch.py --input data/prs.jsonl --output data/patches.json --clone-dir /tmp/repos
"""

import argparse
import json
import os
import sys
import subprocess
import shutil
import tempfile
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.parse
import urllib.error

# ==================== 配置 ====================

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "SWE-Bench-Patch-Fetcher/1.0"
}

GIT_TIMEOUT = 300  # 5 minutes for git operations


# ==================== 数据模型 ====================

@dataclass
class PatchInfo:
    """Patch 信息模型"""
    instance_id: str
    repo_owner: str
    repo_name: str
    pr_number: int
    base_branch: str
    head_branch: str
    base_commit: str = ""
    head_commit: str = ""
    patch: str = ""
    test_patch: str = ""
    test_files: List[str] = field(default_factory=list)
    all_files: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


# ==================== GitHub API 客户端 ====================

class GitHubAPIClient:
    """GitHub API 客户端"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.headers = DEFAULT_HEADERS.copy()
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def _make_request(self, url: str, params: dict = None) -> dict:
        """发送 API 请求"""
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"⚠️ API 限流，请等待或设置 GITHUB_TOKEN")
                return {}
            raise
        except urllib.error.URLError as e:
            print(f"❌ 网络错误: {e}")
            return {}
    
    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict:
        """获取 PR 详情"""
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}"
        )
    
    def get_pull_request_files(self, owner: str, repo: str, 
                               pr_number: int, per_page: int = 100) -> list:
        """获取 PR 变更的文件列表"""
        files = []
        page = 1
        while True:
            data = self._make_request(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": per_page, "page": page}
            )
            if not data:
                break
            files.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return files
    
    def get_compare(self, owner: str, repo: str, base: str, head: str) -> dict:
        """比较两个分支的差异"""
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/compare/{base}...{head}"
        )


# ==================== Git 操作工具 ====================

class GitOperator:
    """Git 操作工具"""
    
    def __init__(self, clone_dir: str = None):
        self.clone_dir = clone_dir or tempfile.mkdtemp(prefix="swebench_repos_")
        os.makedirs(self.clone_dir, exist_ok=True)
    
    def _run_cmd(self, cmd: List[str], cwd: str = None, timeout: int = GIT_TIMEOUT) -> subprocess.CompletedProcess:
        """运行命令"""
        try:
            return subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
            )
        except subprocess.TimeoutExpired:
            print(f"⏱️ 命令超时: {' '.join(cmd)}")
            raise
    
    def clone_or_update(self, owner: str, repo: str, branch: str = "main") -> Optional[str]:
        """克隆或更新仓库"""
        repo_path = os.path.join(self.clone_dir, f"{owner}__{repo}")
        
        if os.path.exists(repo_path):
            try:
                self._run_cmd(["git", "fetch", "origin"], cwd=repo_path)
                return repo_path
            except Exception:
                shutil.rmtree(repo_path)
        
        url = f"https://github.com/{owner}/{repo}.git"
        try:
            result = self._run_cmd(
                ["git", "clone", "--bare", "--depth=1000", url, repo_path],
                timeout=GIT_TIMEOUT
            )
            if result.returncode != 0:
                print(f"❌ 克隆失败: {owner}/{repo}")
                return None
            
            # 获取所有分支
            self._run_cmd(["git", "fetch", "origin", "+refs/heads/*:refs/heads/*"], cwd=repo_path)
            return repo_path
        except Exception as e:
            print(f"❌ 克隆出错: {e}")
            return None
    
    def get_file_patch(self, repo_path: str, base_commit: str, head_commit: str, 
                       file_path: str) -> Optional[str]:
        """获取单个文件的 patch"""
        try:
            result = self._run_cmd(
                ["git", "diff", base_commit, head_commit, "--", file_path],
                cwd=repo_path
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None
    
    def get_full_patch(self, repo_path: str, base_commit: str, 
                       head_commit: str, files: List[str] = None) -> str:
        """获取完整的 patch"""
        try:
            cmd = ["git", "diff", base_commit, head_commit]
            if files:
                cmd.extend(["--"])
                cmd.extend(files)
            
            result = self._run_cmd(cmd, cwd=repo_path)
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    
    def get_commit_hash(self, repo_path: str, ref: str) -> Optional[str]:
        """获取引用的 commit hash"""
        try:
            result = self._run_cmd(["git", "rev-parse", ref], cwd=repo_path)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None


# ==================== Patch 提取器 ====================

class PatchFetcher:
    """Patch 提取器"""
    
    # 测试文件模式
    TEST_PATTERNS = {
        "python": ["test_", "_test.py", "tests/", "/test/", "_tests/", "Test"],
        "javascript": ["test/", "spec/", ".test.", ".spec.", "__tests__/", ".tests."],
        "typescript": ["test/", "spec/", ".test.", ".spec.", "__tests__/", ".tests."],
        "java": ["Test.java", "test/", "/test/", "TestCase", "Tests.java"],
        "go": ["_test.go", "/test/", "Test"],
        "rust": ["#[test]", "mod tests", "_test.rs"],
        "ruby": ["_spec.rb", "_test.rb", "spec/", "test/"],
        "php": ["Test.php", "TestCase.php", "tests/", "/test/"],
        "dotnet": ["Test.cs", "Test.csproj", "tests/", "/test/"],
        "cpp": ["test/", "Test.cpp", "tests/", "gtest", "catch", "doctest"],
        "elixir": ["_test.exs", "test/", "describe ", "test "],
    }
    
    def __init__(self, github_token: Optional[str] = None, clone_dir: str = None):
        self.client = GitHubAPIClient(github_token)
        self.git = GitOperator(clone_dir)
        self.results: List[PatchInfo] = []
    
    def _is_test_file(self, filename: str, language: str) -> bool:
        """判断是否为测试文件"""
        patterns = self.TEST_PATTERNS.get(language, [])
        for pattern in patterns:
            if pattern in filename:
                return True
        return False
    
    def _extract_test_files(self, files: List[dict], language: str) -> List[str]:
        """提取测试文件列表"""
        test_files = []
        for f in files:
            filename = f.get("filename", "")
            if self._is_test_file(filename, language):
                test_files.append(filename)
        return test_files
    
    def fetch_patch(self, pr_data: dict, language: str = "python") -> PatchInfo:
        """获取单个 PR 的 patch"""
        instance_id = pr_data.get("instance_id", f"instance_{pr_data.get('repo_owner')}__{pr_data.get('repo_name')}__{pr_data.get('pr_number')}")
        
        patch_info = PatchInfo(
            instance_id=instance_id,
            repo_owner=pr_data.get("repo_owner", ""),
            repo_name=pr_data.get("repo_name", ""),
            pr_number=pr_data.get("pr_number", 0),
            base_branch=pr_data.get("base_branch", "main"),
            head_branch=pr_data.get("head_branch", ""),
        )
        
        try:
            owner = patch_info.repo_owner
            repo = patch_info.repo_name
            pr_number = patch_info.pr_number
            
            # 获取 PR 详情
            pr_detail = self.client.get_pull_request(owner, repo, pr_number)
            if not pr_detail:
                patch_info.error = "无法获取 PR 详情"
                return patch_info
            
            # 获取 base 和 head commit
            base_ref = pr_detail.get("base", {}).get("ref", "main")
            head_ref = pr_detail.get("head", {}).get("ref", "")
            patch_info.base_branch = base_ref
            patch_info.head_branch = head_ref
            
            # 克隆仓库
            repo_path = self.git.clone_or_update(owner, repo, base_ref)
            if not repo_path:
                patch_info.error = "无法克隆仓库"
                return patch_info
            
            # 获取 commit hash
            patch_info.base_commit = self.git.get_commit_hash(repo_path, f"origin/{base_ref}") or base_ref
            patch_info.head_commit = self.git.get_commit_hash(repo_path, head_ref) or head_ref
            
            # 获取 PR 变更的文件列表
            pr_files = self.client.get_pull_request_files(owner, repo, pr_number)
            patch_info.all_files = [f.get("filename", "") for f in pr_files]
            
            # 检测语言
            detected_lang = pr_data.get("detected_language") or language
            
            # 提取测试文件
            patch_info.test_files = self._extract_test_files(pr_files, detected_lang)
            
            # 获取完整 patch
            patch_info.patch = self.git.get_full_patch(repo_path, patch_info.base_commit, 
                                                        patch_info.head_commit)
            
            # 获取测试文件 patch
            if patch_info.test_files:
                patch_info.test_patch = self.git.get_full_patch(
                    repo_path, patch_info.base_commit, patch_info.head_commit,
                    patch_info.test_files
                )
            
        except Exception as e:
            patch_info.error = str(e)
        
        return patch_info
    
    def fetch_batch(self, pr_list: List[dict], language: str = "python",
                    max_workers: int = 4) -> List[PatchInfo]:
        """批量获取 patch"""
        self.results = []
        
        print(f"🔍 开始获取 {len(pr_list)} 个 PR 的 patch...")
        print(f"   克隆目录: {self.git.clone_dir}")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.fetch_patch, pr, language): pr 
                for pr in pr_list
            }
            
            for future in as_completed(futures):
                pr = futures[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    if result.error:
                        print(f"   ❌ {result.instance_id}: {result.error}")
                    else:
                        print(f"   ✅ {result.instance_id}: {len(result.patch)} 字节")
                        
                except Exception as e:
                    print(f"   ❌ 处理失败: {e}")
        
        success_count = sum(1 for r in self.results if not r.error)
        print(f"\n✅ 完成: 成功 {success_count}/{len(self.results)}")
        
        return self.results
    
    def save_results(self, output_path: str, format: str = "json"):
        """保存结果"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        elif format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for r in self.results:
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        elif format == "patches":
            # SWE-Bench 格式的 patch 文件
            patches = []
            for r in self.results:
                if not r.error and r.patch:
                    patches.append({
                        "instance_id": r.instance_id,
                        "patch": r.patch,
                    })
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(patches, f, ensure_ascii=False, indent=2)
        
        print(f"💾 已保存到 {output_path}")
    
    def save_clone_dir_info(self, output_path: str):
        """保存克隆目录信息"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.git.clone_dir)
        print(f"💾 克隆目录: {self.git.clone_dir}")


# ==================== CLI ====================

def parse_args():
    parser = argparse.ArgumentParser(
        description="获取 GitHub PR 的代码变更 (patch)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 JSONL 文件获取 patch
  python fetch_pr_patch.py --input prs.jsonl --output patches.json

  # 指定克隆目录（保留仓库以便复用）
  python fetch_pr_patch.py --input prs.jsonl --output patches.json --clone-dir /tmp/repos

  # 批量处理并只输出 patch（用于评估）
  python fetch_pr_patch.py --input prs.jsonl --output gold_patches.json --format patches
        """
    )
    
    parser.add_argument("--input", "-i", required=True,
                        help="输入的 PR 数据文件 (JSON 或 JSONL)")
    parser.add_argument("--output", "-o", default="patches.json",
                        help="输出文件路径 (默认: patches.json)")
    parser.add_argument("--clone-dir", 
                        help="仓库克隆目录 (默认: 临时目录)")
    parser.add_argument("--language", "-l", default="python",
                        help="默认语言 (默认: python)")
    parser.add_argument("--format", "-f", choices=["json", "jsonl", "patches"], 
                        default="json",
                        help="输出格式: json(完整信息), jsonl(逐行), patches(仅patch, 默认: json)")
    parser.add_argument("--max-workers", "-w", type=int, default=4,
                        help="并发线程数 (默认: 4)")
    parser.add_argument("--token", "-t",
                        help="GitHub Token (或设置 GITHUB_TOKEN 环境变量)")
    parser.add_argument("--save-clone-dir", action="store_true",
                        help="保存克隆目录路径到文件")
    
    return parser.parse_args()


def load_pr_data(input_path: str) -> List[dict]:
    """加载 PR 数据"""
    with open(input_path, "r", encoding="utf-8") as f:
        if input_path.endswith(".jsonl"):
            return [json.loads(line) for line in f]
        else:
            return json.load(f)


def main():
    args = parse_args()
    
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("⚠️  警告: 未设置 GITHUB_TOKEN，API 请求可能受限流影响")
    
    # 加载 PR 数据
    pr_list = load_pr_data(args.input)
    print(f"📂 已加载 {len(pr_list)} 个 PR 数据")
    
    # 创建提取器
    fetcher = PatchFetcher(token, args.clone_dir)
    
    # 获取 patch
    fetcher.fetch_batch(pr_list, args.language, args.max_workers)
    
    # 保存结果
    fetcher.save_results(args.output, args.format)
    
    if args.save_clone_dir:
        fetcher.save_clone_dir_info(args.output + ".clone_dir")
    
    # 统计
    lang_stats = {}
    for pr in pr_list:
        lang = pr.get("detected_language", "unknown")
        lang_stats[lang] = lang_stats.get(lang, 0) + 1
    
    print("\n📊 语言分布:")
    for lang, count in sorted(lang_stats.items(), key=lambda x: -x[1]):
        print(f"   {lang}: {count}")


if __name__ == "__main__":
    main()
