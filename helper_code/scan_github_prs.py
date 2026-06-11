#!/usr/bin/env python3
"""
GitHub PR 扫描工具 - 爬取符合 SWE-Bench 风格的多语言开源协议 PR

功能：
1. 搜索 GitHub 上宽泛协议（MIT、BSD、Apache 2.0、ISC等）的 merged PR
2. 按语言筛选和分类，支持语言分布均匀采样
3. 提取 PR 元数据（标题、描述、测试文件、issue 链接等）
4. 生成符合 SWE-Bench 实例格式的数据
5. 支持筛选修改行数 ≥ 110 的 PR

项目要求：
- 协议：MIT、BSD、Apache 2.0、ISC、BSD-3-Clause、BSD-2-Clause、Unlicense、CC0、MPL-2.0
- 语言：Python, JavaScript, TypeScript, Java, Go, Rust, Ruby, PHP, .NET, C++, Elixir
- 修改行数：≥ 110 行
- 语言分布：尽量均匀

用法：
# 扫描所有语言的 PR（修改行数≥110，语言均匀分布）
python scan_github_prs.py --output data/prs.jsonl --min-lines 110 --balanced

# 指定特定协议
python scan_github_prs.py --output data/prs.jsonl --licenses mit bsd apache-2.0 --min-lines 110

# 指定语言并生成 SWE-Bench 格式
python scan_github_prs.py --languages python javascript go --output data/instances.jsonl --swebench-format

# 设置 GitHub Token（建议使用，避免 API 限流）
export GITHUB_TOKEN=ghp_xxxx
python scan_github_prs.py --output data/prs.jsonl
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import urllib.request
import urllib.parse
import urllib.error

# ==================== 配置 ====================

# GitHub API 配置
GITHUB_API_BASE = "https://api.github.com"
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "SWE-Bench-PR-Scanner/1.1"
}

# 支持的宽泛开源协议
PERMISSIVE_LICENSES = {
    "mit": "MIT",
    "bsd": "BSD",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "apache-2.0": "Apache-2.0",
    "isc": "ISC",
    "unlicense": "Unlicense",
    "cc0-1.0": "CC0-1.0",
    "mpl-2.0": "MPL-2.0",
}

# 语言与文件扩展名/特征的映射
LANGUAGE_EXTENSIONS = {
    "python": {
        "extensions": [".py"],
        "test_patterns": ["test_", "_test.py", "tests/", "/test/", "_tests/"],
        "config_files": ["setup.py", "pyproject.toml", "requirements.txt", "setup.cfg", "tox.ini", "Pipfile"],
        "github_query_keywords": ["python", "py"]
    },
    "javascript": {
        "extensions": [".js", ".jsx", ".mjs", ".cjs"],
        "test_patterns": ["test/", "spec/", ".test.", ".spec.", "__tests__/"],
        "config_files": ["package.json", "yarn.lock", "pnpm-lock.yaml", "package-lock.json"],
        "github_query_keywords": ["javascript", "node", "npm", "js"]
    },
    "typescript": {
        "extensions": [".ts", ".tsx"],
        "test_patterns": ["test/", "spec/", ".test.", ".spec.", "__tests__/"],
        "config_files": ["package.json", "tsconfig.json", "tsconfig.", ".d.ts"],
        "github_query_keywords": ["typescript", "ts"]
    },
    "java": {
        "extensions": [".java"],
        "test_patterns": ["Test.java", "test/", "/test/", "TestCase"],
        "config_files": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
        "github_query_keywords": ["java", "maven", "gradle"]
    },
    "go": {
        "extensions": [".go"],
        "test_patterns": ["_test.go", "/test/", "Test"],
        "config_files": ["go.mod", "go.sum"],
        "github_query_keywords": ["golang", "go "]
    },
    "rust": {
        "extensions": [".rs"],
        "test_patterns": ["#[test]", "mod tests", "_test.rs"],
        "config_files": ["Cargo.toml", "Cargo.lock"],
        "github_query_keywords": ["rust", "cargo"]
    },
    "ruby": {
        "extensions": [".rb"],
        "test_patterns": ["_spec.rb", "_test.rb", "spec/", "test/"],
        "config_files": ["Gemfile", "Gemfile.lock", ".rspec"],
        "github_query_keywords": ["ruby", "rails", "gem"]
    },
    "php": {
        "extensions": [".php"],
        "test_patterns": ["Test.php", "TestCase.php", "tests/", "/test/"],
        "config_files": ["composer.json", "composer.lock", "phpunit.xml"],
        "github_query_keywords": ["php", "composer", "laravel", "symfony"]
    },
    "dotnet": {
        "extensions": [".cs", ".fs", ".vb"],
        "test_patterns": ["Test.cs", "Test.csproj", "tests/", "/test/"],
        "config_files": ["*.csproj", "*.sln", "*.fsproj"],
        "github_query_keywords": ["csharp", "dotnet", "aspnet"]
    },
    "cpp": {
        "extensions": [".cpp", ".cc", ".cxx", ".hpp", ".h", ".hxx"],
        "test_patterns": ["test/", "Test.cpp", "tests/", "gtest", "catch", "doctest"],
        "config_files": ["CMakeLists.txt", "Makefile", "configure", "meson.build"],
        "github_query_keywords": ["c++", "cpp", "cmake", "gcc", "clang"]
    },
    "elixir": {
        "extensions": [".ex", ".exs"],
        "test_patterns": ["_test.exs", "test/", "describe ", "test "],
        "config_files": ["mix.exs", "mix.lock"],
        "github_query_keywords": ["elixir", "phoenix", "mix"]
    }
}


# ==================== 数据模型 ====================

@dataclass
class PullRequest:
    """PR 数据模型"""
    repo_owner: str
    repo_name: str
    pr_number: int
    pr_title: str
    pr_body: str
    pr_url: str
    state: str
    merged_at: str
    created_at: str
    updated_at: str
    base_branch: str
    head_branch: str
    author: str
    additions: int
    deletions: int
    changed_files: int
    labels: list
    commits: int
    
    # 扩展信息
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    
    # 语言检测
    detected_language: Optional[str] = None
    has_tests: bool = False
    test_files: list = field(default_factory=list)
    
    # 实例生成用
    instance_id: Optional[str] = None
    gold_patch: Optional[str] = None
    
    @property
    def full_repo_name(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"
    
    def to_swebench_instance(self) -> dict:
        """转换为 SWE-Bench 实例格式"""
        return {
            "instance_id": self.instance_id or f"instance_{self.repo_owner}__{self.repo_name}__{self.pr_number}",
            "repo": self.full_repo_name,
            "repo_version": self.merged_at[:10] if self.merged_at else "",
            "base_commit": "",
            "hint": self.issue_url or "",
            "test_patch": "",
            "problem_statement": self.pr_body or self.pr_title,
            "version": self.detected_language or "python",
            "language": self.detected_language or "python",
            "FAIL_TO_PASS": "",
            "PASS_TO_PASS": "",
            "environment_setup_command": "",
        }


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
                sys.exit(1)
            raise
        except urllib.error.URLError as e:
            print(f"❌ 网络错误: {e}")
            sys.exit(1)
    
    def search_issues(self, query: str, sort: str = "updated", order: str = "desc", 
                     per_page: int = 100, pages: int = 10) -> list:
        """搜索 issues/PR"""
        results = []
        for page in range(1, pages + 1):
            data = self._make_request(
                f"{GITHUB_API_BASE}/search/issues",
                params={
                    "q": query,
                    "sort": sort,
                    "order": order,
                    "per_page": per_page,
                    "page": page
                }
            )
            results.extend(data.get("items", []))
            
            if len(data.get("items", [])) < per_page:
                break
                
            time.sleep(0.5)
            
        return results
    
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
            files.extend(data)
            if len(data) < per_page:
                break
            page += 1
            time.sleep(0.3)
        return files
    
    def get_compare(self, owner: str, repo: str, base: str, head: str) -> dict:
        """比较两个分支的差异"""
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/compare/{base}...{head}"
        )
    
    def get_repo_info(self, owner: str, repo: str) -> dict:
        """获取仓库信息"""
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        )


# ==================== PR 扫描器 ====================

class PRSearchScanner:
    """PR 扫描器"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.client = GitHubAPIClient(github_token)
        self.scanned_prs: list[PullRequest] = []
    
    def _build_license_query(self, licenses: List[str]) -> str:
        """构建协议查询字符串"""
        if not licenses:
            licenses = list(PERMISSIVE_LICENSES.keys())
        
        valid_licenses = [l for l in licenses if l in PERMISSIVE_LICENSES]
        if not valid_licenses:
            valid_licenses = list(PERMISSIVE_LICENSES.keys())
        
        return " OR ".join([f"license:{l}" for l in valid_licenses])
        
    def _detect_language(self, pr_files: list) -> Optional[str]:
        """根据文件变更检测语言"""
        extensions_count = {}
        
        for file_info in pr_files[:50]:
            filename = file_info.get("filename", "")
            
            # 先检查配置文件
            basename = os.path.basename(filename)
            for lang, lang_info in LANGUAGE_EXTENSIONS.items():
                for config in lang_info["config_files"]:
                    if config in filename or config == basename:
                        return lang
            
            # 再检查文件扩展名
            _, ext = os.path.splitext(filename)
            if ext:
                for lang, lang_info in LANGUAGE_EXTENSIONS.items():
                    if ext in lang_info["extensions"]:
                        extensions_count[lang] = extensions_count.get(lang, 0) + 1
        
        if extensions_count:
            return max(extensions_count, key=extensions_count.get)
        return None
    
    def _check_has_tests(self, pr_files: list, language: str) -> tuple[bool, list]:
        """检查 PR 是否包含测试文件变更"""
        if not language or language not in LANGUAGE_EXTENSIONS:
            return False, []
        
        test_patterns = LANGUAGE_EXTENSIONS[language]["test_patterns"]
        test_files = []
        
        for file_info in pr_files:
            filename = file_info.get("filename", "")
            
            for pattern in test_patterns:
                if pattern in filename:
                    test_files.append(filename)
                    break
            
            if file_info.get("status") == "added":
                for pattern in test_patterns:
                    if pattern in filename:
                        if filename not in test_files:
                            test_files.append(filename)
        
        return len(test_files) > 0, test_files
    
    def _extract_issue_info(self, pr_body: str) -> tuple[Optional[str], Optional[int]]:
        """从 PR 描述中提取关联的 issue"""
        import re
        
        patterns = [
            r"fixes\s+#(\d+)",
            r"closes\s+#(\d+)",
            r"resolved\s+#(\d+)",
            r"#(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pr_body.lower())
            if match:
                issue_number = int(match.group(1))
                return f"#{issue_number}", issue_number
        
        return None, None
    
    def _create_pr_from_search_result(self, item: dict) -> Optional[PullRequest]:
        """从搜索结果创建 PullRequest 对象"""
        try:
            repo_url = item.get("repository_url", "")
            parts = repo_url.rstrip("/").split("/")
            owner = parts[-2] if len(parts) >= 2 else ""
            repo = parts[-1] if parts else ""
            
            pr_data = item.get("pull_request", {})
            base_ref = pr_data.get("base", {})
            head_ref = pr_data.get("head", {})
            
            pr = PullRequest(
                repo_owner=owner,
                repo_name=repo,
                pr_number=item.get("number", 0),
                pr_title=item.get("title", ""),
                pr_body=item.get("body", "") or "",
                pr_url=item.get("html_url", ""),
                state=item.get("state", ""),
                merged_at=pr_data.get("merged_at", "") or "",
                created_at=item.get("created_at", ""),
                updated_at=item.get("updated_at", ""),
                base_branch=base_ref.get("ref", "") if base_ref else "",
                head_branch=head_ref.get("ref", "") if head_ref else "",
                author=item.get("user", {}).get("login", ""),
                additions=pr_data.get("additions", 0),
                deletions=pr_data.get("deletions", 0),
                changed_files=pr_data.get("changed_files", 0),
                labels=[l.get("name", "") for l in item.get("labels", [])],
                commits=pr_data.get("commits", 0),
            )
            
            pr.issue_url, pr.issue_number = self._extract_issue_info(pr.pr_body)
            
            return pr
            
        except Exception as e:
            print(f"  ⚠️ 解析 PR 失败: {e}")
            return None
    
    def scan(
        self,
        languages: list[str] = None,
        days: int = 365,
        min_stars: int = 10,
        max_results: int = 1000,
        has_tests: bool = None,
        min_files: int = 1,
        max_files: int = 100,
        only_merged: bool = True,
        licenses: list[str] = None,
        min_lines: int = 0,
        balanced: bool = False,
    ) -> list[PullRequest]:
        """扫描 GitHub PR
        
        参数:
            languages: 要扫描的语言列表，None 表示所有支持的语言
            days: 扫描最近多少天的 PR
            min_stars: 仓库最少 star 数
            max_results: 最大结果数
            has_tests: 是否只保留包含测试的 PR (True/False/None)
            min_files: 最少变更文件数
            max_files: 最多变更文件数
            only_merged: 是否只扫描已合并的 PR
            licenses: 协议列表，None 表示所有支持的宽泛协议
            min_lines: 最小修改行数 (additions + deletions)
            balanced: 是否保持语言分布均匀
        """
        self.scanned_prs = []
        
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        if languages:
            scan_languages = [l for l in languages if l in LANGUAGE_EXTENSIONS]
        else:
            scan_languages = list(LANGUAGE_EXTENSIONS.keys())
        
        license_query = self._build_license_query(licenses)
        
        print(f"🔍 开始扫描 PR...")
        print(f"   语言: {scan_languages if languages else '所有'}")
        print(f"   协议: {licenses if licenses else '所有支持的宽泛协议'}")
        print(f"   时间范围: 最近 {days} 天")
        print(f"   最少 star: {min_stars}")
        print(f"   最少修改行数: {min_lines}")
        print(f"   最大结果: {max_results}")
        print(f"   语言均匀分布: {'是' if balanced else '否'}")
        
        if balanced:
            results_per_lang = max(1, max_results // len(scan_languages))
            print(f"   每语言最多: {results_per_lang} 个 PR")
        
        lang_prs: Dict[str, List[PullRequest]] = {}
        for lang in scan_languages:
            lang_prs[lang] = []
        
        for lang in scan_languages:
            print(f"\n📂 扫描 {lang} 语言的 PR...")
            
            keywords = LANGUAGE_EXTENSIONS[lang]["github_query_keywords"]
            lang_query = " OR ".join(keywords)
            
            query_parts = [
                f"({lang_query})",
                "is:pr",
                f"created:>={since_date}",
                f"({license_query})",
            ]
            
            if only_merged:
                query_parts.append("is:merged")
            
            if min_lines > 0:
                query_parts.append(f"is:merged")
            
            query = " ".join(query_parts)
            
            try:
                search_results = self.client.search_issues(
                    query=query,
                    sort="updated",
                    order="desc",
                    per_page=100,
                    pages=10
                )
                
                print(f"   找到 {len(search_results)} 个候选 PR")
                
                max_per_lang = results_per_lang if balanced else max_results
                
                for item in search_results[:max_per_lang * 2]:
                    owner = item.get("repository_url", "").rstrip("/").split("/")[-2]
                    repo = item.get("repository_url", "").rstrip("/").split("/")[-1]
                    pr_number = item.get("number")
                    
                    try:
                        pr_detail = self.client.get_pull_request(owner, repo, pr_number)
                        pr_files = self.client.get_pull_request_files(owner, repo, pr_number)
                        
                        additions = pr_detail.get("additions", 0)
                        deletions = pr_detail.get("deletions", 0)
                        total_lines = additions + deletions
                        
                        if min_lines > 0 and total_lines < min_lines:
                            continue
                        
                        try:
                            repo_info = self.client.get_repo_info(owner, repo)
                            stars = repo_info.get("stargazers_count", 0)
                            if stars < min_stars:
                                continue
                        except Exception:
                            pass
                        
                        detected_lang = self._detect_language(pr_files)
                        if not detected_lang:
                            detected_lang = lang
                        
                        file_count = len(pr_files)
                        if file_count < min_files or file_count > max_files:
                            continue
                        
                        has_test_changes, test_files = self._check_has_tests(pr_files, detected_lang)
                        if has_tests is not None and has_test_changes != has_tests:
                            continue
                        
                        pr = self._create_pr_from_search_result(item)
                        if pr:
                            pr.detected_language = detected_lang
                            pr.has_tests = has_test_changes
                            pr.test_files = test_files
                            pr.instance_id = f"instance_{owner}__{repo}__{pr_number}"
                            
                            lang_prs[detected_lang].append(pr)
                            print(f"   ✅ PR #{pr_number}: {pr.pr_title[:50]}... (行: {total_lines})")
                            
                            if balanced and len(lang_prs[detected_lang]) >= max_per_lang:
                                break
                            
                    except Exception as e:
                        print(f"   ⚠️ 处理 PR #{pr_number} 失败: {e}")
                        continue
                        
            except Exception as e:
                print(f"   ❌ 搜索 {lang} PR 失败: {e}")
                continue
        
        for lang, prs in lang_prs.items():
            self.scanned_prs.extend(prs)
        
        print(f"\n✅ 扫描完成，共找到 {len(self.scanned_prs)} 个符合条件的 PR")
        return self.scanned_prs
    
    def scan_iter(
        self,
        languages: list[str] = None,
        days: int = 365,
        min_stars: int = 10,
        max_results: int = 1000,
        has_tests: bool = None,
        min_files: int = 1,
        max_files: int = 100,
        only_merged: bool = True,
        licenses: list[str] = None,
        min_lines: int = 0,
        balanced: bool = False,
    ):
        """扫描 GitHub PR 的迭代器版本 - 逐个返回 PR，支持流水线处理"""
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        if languages:
            scan_languages = [l for l in languages if l in LANGUAGE_EXTENSIONS]
        else:
            scan_languages = list(LANGUAGE_EXTENSIONS.keys())
        
        license_query = self._build_license_query(licenses)
        
        if balanced:
            results_per_lang = max(1, max_results // len(scan_languages))
        
        lang_counts: Dict[str, int] = {lang: 0 for lang in scan_languages}
        total_count = 0
        
        for lang in scan_languages:
            keywords = LANGUAGE_EXTENSIONS[lang]["github_query_keywords"]
            lang_query = " OR ".join(keywords)
            
            query_parts = [
                f"({lang_query})",
                "is:pr",
                f"created:>={since_date}",
                f"({license_query})",
            ]
            
            if only_merged:
                query_parts.append("is:merged")
            
            query = " ".join(query_parts)
            
            try:
                search_results = self.client.search_issues(
                    query=query,
                    sort="updated",
                    order="desc",
                    per_page=100,
                    pages=10
                )
                
                max_per_lang = results_per_lang if balanced else max_results
                
                for item in search_results[:max_per_lang * 2]:
                    if total_count >= max_results:
                        return
                    
                    if balanced and lang_counts[lang] >= max_per_lang:
                        break
                    
                    owner = item.get("repository_url", "").rstrip("/").split("/")[-2]
                    repo = item.get("repository_url", "").rstrip("/").split("/")[-1]
                    pr_number = item.get("number")
                    
                    try:
                        pr_detail = self.client.get_pull_request(owner, repo, pr_number)
                        pr_files = self.client.get_pull_request_files(owner, repo, pr_number)
                        
                        additions = pr_detail.get("additions", 0)
                        deletions = pr_detail.get("deletions", 0)
                        total_lines = additions + deletions
                        
                        if min_lines > 0 and total_lines < min_lines:
                            continue
                        
                        try:
                            repo_info = self.client.get_repo_info(owner, repo)
                            stars = repo_info.get("stargazers_count", 0)
                            if stars < min_stars:
                                continue
                        except Exception:
                            pass
                        
                        detected_lang = self._detect_language(pr_files) or lang
                        file_count = len(pr_files)
                        
                        if file_count < min_files or file_count > max_files:
                            continue
                        
                        has_test_changes, test_files = self._check_has_tests(pr_files, detected_lang)
                        if has_tests is not None and has_test_changes != has_tests:
                            continue
                        
                        pr = self._create_pr_from_search_result(item)
                        if pr:
                            pr.detected_language = detected_lang
                            pr.has_tests = has_test_changes
                            pr.test_files = test_files
                            pr.instance_id = f"instance_{owner}__{repo}__{pr_number}"
                            pr.additions = additions
                            pr.deletions = deletions
                            pr.total_lines = total_lines
                            
                            lang_counts[lang] += 1
                            total_count += 1
                            
                            yield asdict(pr)
                            
                    except Exception:
                        continue
                        
            except Exception:
                continue
    
    def save_to_json(self, output_path: str):
        """保存结果到 JSON 文件"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([asdict(pr) for pr in self.scanned_prs], f, ensure_ascii=False, indent=2)
        print(f"💾 已保存到 {output_path}")
    
    def save_to_jsonl(self, output_path: str):
        """保存结果到 JSONL 文件"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for pr in self.scanned_prs:
                f.write(json.dumps(asdict(pr), ensure_ascii=False) + "\n")
        print(f"💾 已保存到 {output_path}")
    
    def generate_swebench_instances(self, output_path: str, output_format: str = "jsonl"):
        """生成 SWE-Bench 格式的实例文件"""
        instances = []
        for pr in self.scanned_prs:
            instance = pr.to_swebench_instance()
            instance["instance_id"] = pr.instance_id or f"instance_{pr.full_repo_name.replace('/', '__')}__{pr.pr_number}"
            instances.append(instance)
        
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        if output_format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(instances, f, ensure_ascii=False, indent=2)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                for inst in instances:
                    f.write(json.dumps(inst, ensure_ascii=False) + "\n")
        
        print(f"💾 已生成 {len(instances)} 个 SWE-Bench 实例到 {output_path}")
        return instances


# ==================== CLI ====================

def parse_args():
    parser = argparse.ArgumentParser(
        description="扫描 GitHub 上符合 SWE-Bench 风格的多语言开源协议 PR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描所有语言的 PR（修改行数≥110，语言均匀分布）
  python scan_github_prs.py --output data/prs.jsonl --min-lines 110 --balanced

  # 指定特定协议（MIT、BSD、Apache 2.0）
  python scan_github_prs.py --output data/prs.jsonl --licenses mit bsd apache-2.0 --min-lines 110

  # 仅扫描 JavaScript/TypeScript PR
  python scan_github_prs.py --languages javascript typescript --output data/js_prs.jsonl

  # 仅扫描最近 30 天更新的 PR
  python scan_github_prs.py --days 30 --output data/recent_prs.jsonl

  # 设置 GitHub Token
  export GITHUB_TOKEN=ghp_xxxx
  python scan_github_prs.py --output data/prs.jsonl

  # 生成 SWE-Bench 实例格式
  python scan_github_prs.py --languages python --swebench-format --output data/python_instances.jsonl
        """
    )
    
    parser.add_argument("--output", "-o", default="prs.jsonl",
                        help="输出文件路径 (默认: prs.jsonl)")
    parser.add_argument("--languages", "-l", nargs="+",
                        choices=list(LANGUAGE_EXTENSIONS.keys()),
                        help="要扫描的语言")
    parser.add_argument("--licenses", nargs="+",
                        choices=list(PERMISSIVE_LICENSES.keys()),
                        help="要扫描的协议 (默认: 所有支持的宽泛协议)")
    parser.add_argument("--days", "-d", type=int, default=365,
                        help="扫描最近多少天的 PR (默认: 365)")
    parser.add_argument("--min-stars", type=int, default=10,
                        help="仓库最少 star 数 (默认: 10)")
    parser.add_argument("--min-lines", type=int, default=0,
                        help="最少修改行数 (additions + deletions, 默认: 0)")
    parser.add_argument("--max-results", type=int, default=1000,
                        help="最大结果数 (默认: 1000)")
    parser.add_argument("--has-tests", action="store_true",
                        help="只保留包含测试变更的 PR")
    parser.add_argument("--no-tests", action="store_true",
                        help="只保留不包含测试变更的 PR")
    parser.add_argument("--min-files", type=int, default=1,
                        help="最少变更文件数 (默认: 1)")
    parser.add_argument("--max-files", type=int, default=100,
                        help="最多变更文件数 (默认: 100)")
    parser.add_argument("--balanced", action="store_true",
                        help="保持语言分布均匀")
    parser.add_argument("--swebench-format", action="store_true",
                        help="生成 SWE-Bench 实例格式")
    parser.add_argument("--format", choices=["json", "jsonl"], default="jsonl",
                        help="输出格式 (默认: jsonl)")
    parser.add_argument("--token", "-t",
                        help="GitHub Token (或设置 GITHUB_TOKEN 环境变量)")
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("⚠️  警告: 未设置 GITHUB_TOKEN，API 请求可能受限流影响")
        print("   请设置环境变量: export GITHUB_TOKEN=ghp_xxxx")
    
    scanner = PRSearchScanner(token)
    
    has_tests_filter = None
    if args.has_tests:
        has_tests_filter = True
    elif args.no_tests:
        has_tests_filter = False
    
    scanner.scan(
        languages=args.languages,
        days=args.days,
        min_stars=args.min_stars,
        max_results=args.max_results,
        has_tests=has_tests_filter,
        min_files=args.min_files,
        max_files=args.max_files,
        licenses=args.licenses,
        min_lines=args.min_lines,
        balanced=args.balanced,
    )
    
    if args.swebench_format:
        scanner.generate_swebench_instances(args.output, args.format)
    else:
        if args.format == "json":
            scanner.save_to_json(args.output)
        else:
            scanner.save_to_jsonl(args.output)
    
    print("\n📊 统计信息:")
    lang_counts = {}
    for pr in scanner.scanned_prs:
        lang = pr.detected_language or "unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        print(f"   {lang}: {count}")
    
    print(f"\n总计: {len(scanner.scanned_prs)} 个 PR")


if __name__ == "__main__":
    main()
