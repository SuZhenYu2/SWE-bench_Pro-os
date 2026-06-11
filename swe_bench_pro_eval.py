"""
The script is used to evaluate the performance of the SWEAP Pro agent with Modal.
支持多语言多版本的 SWE-Bench Pro 评估脚本。

This evaluation script:
1. Takes a CSV file containing test cases and a JSON file containing patches
2. Detects language and version from repo metadata or project files
3. Selects appropriate Docker image, run_script, and parser for the language
4. Runs each patch in a Modal sandbox environment using Docker Hub images
5. Executes the tests using language-specific run scripts and collects results
6. Calculates overall accuracy based on test pass/fail status

Usage:
python swe_bench_pro_eval.py \
    --raw_sample_path=data.csv \
    --patch_path={OUTPUT}/gold_patches.json \
    --output_dir={OUTPUT}/ \
    --num_workers=100 \
    --dockerhub_username=your-username

It expects:
- Multi-language base images in dockerfiles/base/{language}/{version}/
- Language-specific run scripts in dockerfiles/base/{language}/run_script.sh
- Language-specific parser scripts in dockerfiles/base/{language}/parser.py
- CSV file with columns: instance_id, before_repo_set_cmd, selected_test_files_to_run,
  base_commit, base_dockerfile, instance_dockerfile, FAIL_TO_PASS, PASS_TO_PASS, repo, language (optional)

And the generated patch file (gold_patches.json) should have the following format:
[
    {
        "instance_id": "unique_id",
        "patch": "git patch content",
        "prefix": "optional_prefix"
    },
    ...
]
"""

import argparse
import concurrent.futures
import json
import os
import platform as py_platform
import re
import sys

try:
    import modal  # Lazy/optional: only required when not using --use_local_docker
except Exception:
    modal = None
try:
    import docker  # Optional: used when --use_local_docker is set
except Exception:
    docker = None
import pandas as pd
from tqdm import tqdm

# Import multi-language configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "dockerfiles", "base"))
try:
    from language_config import (
        get_language_config,
        get_all_languages,
        get_all_versions,
        get_default_version,
        detect_language_by_config,
        detect_version_from_files,
        resolve_image_tag,
    )
    MULTILANG_AVAILABLE = True
except ImportError:
    MULTILANG_AVAILABLE = False
    get_language_config = None
    get_all_languages = lambda: []
    resolve_image_tag = lambda lang, ver=None: None


def load_base_docker(iid):
    with open(f"dockerfiles/base_dockerfile/{iid}/Dockerfile") as fp:
        return fp.read()

def instance_docker(iid):
    with open(f"dockerfiles/instance_dockerfile/{iid}/Dockerfile") as fp:
        return fp.read()


def detect_language_from_repo(repo_name):
    """
    根据仓库名称推断语言。支持从 repo_name (如 'django/django', 'marko-js/marko') 推断。
    """
    if not repo_name:
        return "python", "3.11"

    repo_lower = repo_name.lower()

    # Known repo -> language mappings (simplified)
    REPO_LANGUAGE_MAP = {
        # JavaScript/TypeScript
        "marko-js": ("javascript", "node20"),
        "publint": ("javascript", "node20"),
        "facebook/react": ("javascript", "node18"),
        "vuejs": ("javascript", "node18"),
        "angular": ("javascript", "node18"),
        "sveltejs": ("javascript", "node18"),
        "preactjs": ("javascript", "node18"),
        "expressjs": ("javascript", "node18"),
        "koa": ("javascript", "node18"),
        "fastify": ("javascript", "node18"),
        "nestjs": ("javascript", "node18"),
        "nextjs": ("javascript", "node18"),
        "nuxt": ("javascript", "node18"),
        "gatsbyjs": ("javascript", "node18"),
        "astro": ("javascript", "node18"),
        "remix-run": ("javascript", "node18"),
        "vercel": ("javascript", "node18"),
        "vitejs": ("javascript", "node18"),
        "rollup": ("javascript", "node18"),
        "parcel-bundler": ("javascript", "node18"),
        "esbuild": ("javascript", "node18"),
        "swc-project": ("javascript", "node18"),
        "babel": ("javascript", "node18"),
        "webpack": ("javascript", "node18"),
        "typescript": ("typescript", "node20"),
        "denoland": ("javascript", "node22"),
        "bun": ("javascript", "node22"),
        # Java
        "spring-projects": ("java", "jdk17"),
        "apache/maven": ("java", "jdk17"),
        "gradle": ("java", "jdk17"),
        "junit-team": ("java", "jdk17"),
        "mockito": ("java", "jdk17"),
        "assertj": ("java", "jdk17"),
        "hibernate": ("java", "jdk17"),
        "mybatis": ("java", "jdk17"),
        "netty": ("java", "jdk17"),
        "vert-x3": ("java", "jdk17"),
        "quarkusio": ("java", "jdk21"),
        "micronaut-projects": ("java", "jdk21"),
        "eclipse-vertx": ("java", "jdk17"),
        # Go
        "golang": ("go", "1.22"),
        "kubernetes": ("go", "1.22"),
        "docker": ("go", "1.22"),
        "moby": ("go", "1.22"),
        "etcd-io": ("go", "1.22"),
        "cockroachdb": ("go", "1.22"),
        "influxdata": ("go", "1.22"),
        "prometheus": ("go", "1.22"),
        "grafana": ("go", "1.22"),
        "hashicorp": ("go", "1.22"),
        "terraform": ("go", "1.22"),
        "consul": ("go", "1.22"),
        "vault": ("go", "1.22"),
        "nomad": ("go", "1.22"),
        "hugo": ("go", "1.22"),
        "caddyserver": ("go", "1.22"),
        "traefik": ("go", "1.22"),
        "gin-gonic": ("go", "1.22"),
        "labstack": ("go", "1.22"),
        "go-kit": ("go", "1.22"),
        "micro": ("go", "1.22"),
        "grpc": ("go", "1.22"),
        # Rust
        "rust-lang": ("rust", "stable"),
        "tokio-rs": ("rust", "stable"),
        "hyperium": ("rust", "stable"),
        "actix": ("rust", "stable"),
        "rocket": ("rust", "stable"),
        "serde-rs": ("rust", "stable"),
        "diesel-rs": ("rust", "stable"),
        "sea-orm": ("rust", "stable"),
        "sqlx": ("rust", "stable"),
        "tantivy-search": ("rust", "stable"),
        "meilisearch": ("rust", "stable"),
        "paritytech": ("rust", "stable"),
        "solana-labs": ("rust", "stable"),
        "near": ("rust", "stable"),
        # Ruby
        "rails": ("ruby", "3.2"),
        "sinatra": ("ruby", "3.2"),
        "puma": ("ruby", "3.2"),
        "sidekiq": ("ruby", "3.2"),
        "jekyll": ("ruby", "3.2"),
        "middleman": ("ruby", "3.2"),
        "octopress": ("ruby", "3.2"),
        "fastlane": ("ruby", "3.2"),
        "cocoapods": ("ruby", "3.2"),
        "bundler": ("ruby", "3.2"),
        # PHP
        "laravel": ("php", "8.2"),
        "symfony": ("php", "8.2"),
        "composer": ("php", "8.2"),
        "phpunit": ("php", "8.2"),
        "wordpress": ("php", "8.2"),
        "drupal": ("php", "8.2"),
        "magento": ("php", "8.2"),
        "prestashop": ("php", "8.2"),
        "joomla": ("php", "8.2"),
        "cakephp": ("php", "8.2"),
        "zendframework": ("php", "8.2"),
        "laminas": ("php", "8.2"),
        "phalcon": ("php", "8.2"),
        "yii": ("php", "8.2"),
        "codeigniter": ("php", "8.2"),
        # .NET
        "dotnet": ("dotnet", "8.0"),
        "aspnet": ("dotnet", "8.0"),
        "mono": ("dotnet", "8.0"),
        "unity": ("dotnet", "8.0"),
        "nunit": ("dotnet", "8.0"),
        "xunit": ("dotnet", "8.0"),
        # Elixir
        "elixir-lang": ("elixir", "1.16"),
        "phoenixframework": ("elixir", "1.16"),
        "nerves-project": ("elixir", "1.16"),
        # C++
        "opencv": ("cpp", "gcc12"),
        "llvm": ("cpp", "clang17"),
        "grpc/grpc": ("cpp", "gcc12"),
        "abseil": ("cpp", "gcc12"),
        "protobuf": ("cpp", "gcc12"),
        "fmtlib": ("cpp", "gcc12"),
        "spdlog": ("cpp", "gcc12"),
        "catchorg": ("cpp", "gcc12"),
        "boostorg": ("cpp", "gcc12"),
        "google/googletest": ("cpp", "gcc12"),
    }

    for prefix, (lang, ver) in REPO_LANGUAGE_MAP.items():
        if prefix in repo_lower:
            return lang, ver

    # Fallback: detect by file extensions in repo name
    if any(x in repo_lower for x in [".js", "node", "npm", "yarn", "vite", "webpack", "babel", "rollup"]):
        return "javascript", "node20"
    if any(x in repo_lower for x in [".ts", "typescript"]):
        return "typescript", "node20"
    if any(x in repo_lower for x in [".go", "golang"]):
        return "go", "1.22"
    if any(x in repo_lower for x in [".rs", "rust"]):
        return "rust", "stable"
    if any(x in repo_lower for x in [".rb", "ruby", "rails", "sinatra"]):
        return "ruby", "3.2"
    if any(x in repo_lower for x in [".java", "maven", "gradle", "spring"]):
        return "java", "jdk17"
    if any(x in repo_lower for x in [".php", "composer", "laravel", "symfony"]):
        return "php", "8.2"
    if any(x in repo_lower for x in [".cs", ".net", "dotnet", "aspnet"]):
        return "dotnet", "8.0"
    if any(x in repo_lower for x in [".ex", "elixir", "phoenix"]):
        return "elixir", "1.16"
    if any(x in repo_lower for x in [".cpp", ".cc", ".cxx", "cmake", "gcc", "clang"]):
        return "cpp", "gcc12"

    # Default to python for unknown repos
    return "python", "3.11"


def get_instance_language_version(sample):
    """
    从 sample 数据中推断语言和版本。
    优先使用 sample 中显式指定的 language 字段，否则从 repo 推断。
    """
    # Check if language is explicitly specified in the sample
    explicit_lang = sample.get("language", "")
    explicit_ver = sample.get("version", "")
    if explicit_lang:
        return explicit_lang, explicit_ver or None

    # Detect from repo name
    repo = sample.get("repo", "")
    return detect_language_from_repo(repo)


def load_language_script(lang, script_name):
    """
    从 dockerfiles/base/{language}/ 加载共用脚本。
    """
    script_path = os.path.join(SCRIPT_DIR, "dockerfiles", "base", lang, script_name)
    if not os.path.exists(script_path):
        # Fallback to python scripts
        script_path = os.path.join(SCRIPT_DIR, "dockerfiles", "base", "python", script_name)
    with open(script_path, 'r') as f:
        return f.read()


def strip_binary_hunks(patch: str) -> str:
    """Remove binary diff sections from a git patch."""
    if not patch:
        return patch

    sections = re.split(r'(?=^diff --git )', patch, flags=re.MULTILINE)

    kept: list[str] = []
    for section in sections:
        if not section.strip():
            continue
        if re.search(r'^Binary files .* differ$', section, re.MULTILINE):
            continue
        if re.search(r'^GIT binary patch$', section, re.MULTILINE):
            continue
        kept.append(section)

    return "".join(kept)


def create_entryscript(sample, lang="python"):
    """
    生成 entryscript.sh，根据语言选择 parser 执行方式。
    """
    before_repo_set_cmd = sample["before_repo_set_cmd"].strip().split("\n")[-1]
    selected_test_files_to_run = ",".join(eval(sample["selected_test_files_to_run"]))
    base_commit = sample["base_commit"]
    base_dockerfile = load_base_docker(sample["instance_id"])
    instance_dockerfile = instance_docker(sample["instance_id"])

    # Extract ENV commands from dockerfiles
    env_cmds = []
    for dockerfile_content in [base_dockerfile, instance_dockerfile]:
        for line in dockerfile_content.split("\n"):
            line = line.strip()
            if line.startswith("ENV"):
                env_cmd = line.replace("ENV", "export", 1)
                env_cmds.append(env_cmd)

    env_cmds = "\n".join(env_cmds)

    # Determine parser interpreter based on language
    # Most parsers are Python scripts, but some languages might use their own runtime
    parser_cmd = "python /workspace/parser.py"

    entry_script = f"""
{env_cmds}
# apply patch
cd /app
git reset --hard {base_commit}
git checkout {base_commit}
git apply -v /workspace/patch.diff
{before_repo_set_cmd}
# run test and save stdout and stderr to separate files
bash /workspace/run_script.sh {selected_test_files_to_run} > /workspace/stdout.log 2> /workspace/stderr.log
# run parsing script
{parser_cmd} /workspace/stdout.log /workspace/stderr.log /workspace/output.json
"""
    return entry_script


def create_dockerhub_tag(uid, repo_name=""):
    """
    Convert instance_id and repo name to Docker Hub compatible tag format.
    """
    if repo_name:
        repo_base, repo_name_only = repo_name.lower().split("/")
        hsh = uid.replace("instance_", "")
        return f"{repo_base}.{repo_name_only}-{hsh}"
    else:
        image_name = "default"

    if "__" in uid and len(uid) > 9:
        tag_part = uid[9:]
    else:
        tag_part = uid

    return f"{image_name}-{tag_part}"


def get_multilang_image_uri(sample, dockerhub_username):
    """
    获取多语言镜像 URI。优先使用语言配置索引，回退到旧版逻辑。
    """
    if not MULTILANG_AVAILABLE or not get_language_config:
        # Fallback to old logic
        from helper_code.image_uri import get_dockerhub_image_uri
        return get_dockerhub_image_uri(
            sample["instance_id"],
            dockerhub_username,
            sample.get("repo", "")
        )

    lang, version = get_instance_language_version(sample)
    image_tag = resolve_image_tag(lang, version)

    if image_tag:
        return f"{dockerhub_username}/{image_tag}"

    # Fallback to old logic if no multi-lang image found
    from helper_code.image_uri import get_dockerhub_image_uri
    return get_dockerhub_image_uri(
        sample["instance_id"],
        dockerhub_username,
        sample.get("repo", "")
    )


def prepare_run(uid, output_dir, prefix, redo):
    uid_dir = os.path.join(output_dir, uid)
    os.makedirs(uid_dir, exist_ok=True)
    output_path = os.path.join(uid_dir, f"{prefix}_output.json")
    if not redo and os.path.exists(output_path):
        print(f"Skipping {uid} - output already exists")
        with open(output_path, "r") as f:
            return json.load(f), output_path, os.path.join(uid_dir, "workspace")
    workspace_dir = os.path.join(uid_dir, "workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    return None, output_path, workspace_dir


def write_patch_snapshot(output_dir, uid, prefix, patch):
    with open(os.path.join(output_dir, uid, f"{prefix}_patch.diff"), "w") as f:
        f.write(patch)


def assemble_workspace_files(uid, scripts_dir, patch, sample, use_multilang=True):
    """
    组装工作区文件。支持多语言模式（从 dockerfiles/base/ 加载）或旧模式（从 scripts_dir 加载）。
    """
    lang, version = get_instance_language_version(sample)

    if use_multilang and MULTILANG_AVAILABLE:
        # Load from dockerfiles/base/{language}/
        try:
            run_script = load_language_script(lang, "run_script.sh")
            parser_script = load_language_script(lang, "parser.py")
        except FileNotFoundError:
            # Fallback to old scripts_dir
            run_script = load_local_script(scripts_dir, uid, "run_script.sh")
            parser_script = load_local_script(scripts_dir, uid, "parser.py")
    else:
        # Old mode: load from scripts_dir/{instance_id}/
        run_script = load_local_script(scripts_dir, uid, "run_script.sh")
        parser_script = load_local_script(scripts_dir, uid, "parser.py")

    entryscript_content = create_entryscript(sample, lang)

    cleaned_patch = strip_binary_hunks(patch)
    if cleaned_patch != patch:
        print(f"Stripped binary diff hunks from patch for {uid}")

    files = {
        "patch.diff": cleaned_patch,
        "run_script.sh": run_script,
        "parser.py": parser_script,
        "entryscript.sh": entryscript_content,
    }
    return files, entryscript_content, lang, version


def load_local_script(scripts_dir, instance_id, script_name):
    """Load a script file from local scripts directory."""
    script_path = os.path.join(scripts_dir, instance_id, script_name)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")
    with open(script_path, 'r') as f:
        return f.read()


def write_files_modal(sandbox, files):
    for rel_path, content in files.items():
        with sandbox.open(f"/workspace/{rel_path}", "w") as f:
            f.write(content)


def write_files_local(workspace_dir, files):
    for rel_path, content in files.items():
        dst = os.path.join(workspace_dir, rel_path)
        with open(dst, "w") as f:
            f.write(content)


def save_entryscript_copy(output_dir, uid, prefix, entryscript_content):
    with open(os.path.join(output_dir, uid, f"{prefix}_entryscript.sh"), "w") as f:
        f.write(entryscript_content if entryscript_content is not None else "")


def collect_outputs_modal(sandbox, output_dir, uid, prefix):
    try:
        with sandbox.open("/workspace/stdout.log", "r") as f_in:
            with open(os.path.join(output_dir, uid, f"{prefix}_stdout.log"), "w") as f:
                stdout_content = f_in.read()
                f.write(stdout_content if stdout_content is not None else "")
    except FileNotFoundError:
        pass
    try:
        with sandbox.open("/workspace/stderr.log", "r") as f_in:
            with open(os.path.join(output_dir, uid, f"{prefix}_stderr.log"), "w") as f:
                stderr_content = f_in.read()
                f.write(stderr_content if stderr_content is not None else "")
    except FileNotFoundError:
        pass

    try:
        with sandbox.open("/workspace/output.json", "r") as f_in:
            output = json.load(f_in)
            with open(os.path.join(output_dir, uid, f"{prefix}_output.json"), "w") as f:
                json.dump(output, f)
            return output
    except FileNotFoundError:
        print(
            f"Warning: output.json not found for {uid}. Check {prefix}_stdout.log and {prefix}_stderr.log for details"
        )
        return None


def collect_outputs_local(workspace_dir, output_dir, uid, prefix):
    def _copy_safe(src_name, dest_name):
        src_path = os.path.join(workspace_dir, src_name)
        dest_path = os.path.join(output_dir, uid, dest_name)
        try:
            with open(src_path, "r") as f_in:
                content = f_in.read()
        except FileNotFoundError:
            content = ""
        with open(dest_path, "w") as f_out:
            f_out.write(content if content is not None else "")

    _copy_safe("stdout.log", f"{prefix}_stdout.log")
    _copy_safe("stderr.log", f"{prefix}_stderr.log")

    try:
        with open(os.path.join(workspace_dir, "output.json"), "r") as f_in:
            output = json.load(f_in)
            with open(os.path.join(output_dir, uid, f"{prefix}_output.json"), "w") as f:
                json.dump(output, f)
            return output
    except FileNotFoundError:
        print(
            f"Warning: output.json not found for {uid}. Check {prefix}_stdout.log and {prefix}_stderr.log for details"
        )
        return None


def eval_with_modal(patch, sample, output_dir, dockerhub_username, scripts_dir, prefix="", redo=False, block_network=False, docker_platform=None, use_multilang=True):
    if modal is None:
        raise RuntimeError("modal is not installed. Install it or run with --use_local_docker")
    uid = sample["instance_id"]
    existing_output, output_path, workspace_dir = prepare_run(uid, output_dir, prefix, redo)
    if existing_output is not None:
        return existing_output

    sandbox = None

    print(f"Running evaluation for {uid}")
    try:
        write_patch_snapshot(output_dir, uid, prefix, patch)

        try:
            files, entryscript_content, lang, version = assemble_workspace_files(uid, scripts_dir, patch, sample, use_multilang)
            print(f"  Language: {lang}, Version: {version or 'default'}")
        except FileNotFoundError as e:
            print(f"Error loading scripts for {uid}: {e}")
            return None

        app = modal.App.lookup(name="swe-bench-pro-eval", create_if_missing=True)

        # Use multi-language image or fallback to old logic
        dockerhub_image_uri = get_multilang_image_uri(sample, dockerhub_username)
        print(f"Using Docker Hub image: {dockerhub_image_uri}")

        image = modal.Image.from_registry(dockerhub_image_uri)

        sandbox = modal.Sandbox.create(
            image=image,
            app=app,
            timeout=60 * 60,
            cpu=(1, 4),
            memory=(5 * 1024, 30 * 1024),
            block_network=block_network,
        )

        process = sandbox.exec("mkdir", "-p", "/workspace")
        process.wait()

        write_files_modal(sandbox, files)

        process = sandbox.exec("bash", "/workspace/entryscript.sh")
        process.wait()

        if process.returncode != 0:
            print(f"Entryscript failed for {uid} with return code: {process.returncode}")
            try:
                stderr_content = getattr(process, 'stderr', None)
                if stderr_content and hasattr(stderr_content, 'read'):
                    error_details = stderr_content.read()
                    if error_details:
                        print(f"Error details for {uid}:")
                        print(error_details[:1000])
            except Exception as e:
                print(f"Failed to read stderr for {uid}: {e}")

        output = collect_outputs_modal(sandbox, output_dir, uid, prefix)
        if output is None:
            return None
        save_entryscript_copy(output_dir, uid, prefix, entryscript_content)

        return output
    except Exception as e:
        print(f"Error in eval_with_modal for {uid}: {repr(e)}")
        print(f"Error type: {type(e)}")
        return None
    finally:
        if sandbox:
            try:
                sandbox.terminate()
            except Exception:
                pass


def eval_with_docker(patch, sample, output_dir, dockerhub_username, scripts_dir, prefix="", redo=False, block_network=False, docker_platform=None, use_multilang=True):
    if docker is None:
        raise RuntimeError("docker SDK is not installed. Install via 'pip install docker' or run without --use_local_docker")
    uid = sample["instance_id"]
    existing_output, output_path, workspace_dir = prepare_run(uid, output_dir, prefix, redo)
    if existing_output is not None:
        return existing_output

    print(f"Running local-docker evaluation for {uid}")

    try:
        try:
            files, entryscript_content, lang, version = assemble_workspace_files(uid, scripts_dir, patch, sample, use_multilang)
            print(f"  Language: {lang}, Version: {version or 'default'}")
        except FileNotFoundError as e:
            print(f"Error loading scripts for {uid}: {e}")
            return None
        write_files_local(workspace_dir, files)
        write_patch_snapshot(output_dir, uid, prefix, patch)

        dockerhub_image_uri = get_multilang_image_uri(sample, dockerhub_username)
        print(f"Using Docker Hub image: {dockerhub_image_uri}")

        client = docker.from_env()
        try:
            if docker_platform:
                client.images.pull(dockerhub_image_uri, platform=docker_platform)
            else:
                client.images.pull(dockerhub_image_uri)
        except Exception as pull_err:
            try:
                client.images.get(dockerhub_image_uri)
                print(f"Using locally available image: {dockerhub_image_uri}")
            except Exception:
                print(f"Failed to pull or find image locally for {uid}: {pull_err}")
                return None

        abs_workspace_dir = os.path.abspath(workspace_dir)
        volumes = {abs_workspace_dir: {"bind": "/workspace", "mode": "rw"}}
        run_kwargs = {
            "volumes": volumes,
            "detach": True,
            "remove": True,
            "entrypoint": "/bin/bash",
            "command": ["-c", "bash /workspace/entryscript.sh"],
        }
        if block_network:
            run_kwargs["network_mode"] = "none"
        if docker_platform:
            run_kwargs["platform"] = docker_platform

        container = client.containers.run(dockerhub_image_uri, **run_kwargs)

        result = container.wait()
        status_code = result.get("StatusCode", 1) if isinstance(result, dict) else 1
        if status_code != 0:
            print(f"Entryscript failed for {uid} with return code: {status_code}")

        output = collect_outputs_local(workspace_dir, output_dir, uid, prefix)
        if output is None:
            return None
        save_entryscript_copy(output_dir, uid, prefix, entryscript_content)

        return output
    except Exception as e:
        print(f"Error in eval_with_docker for {uid}: {repr(e)}")
        print(f"Error type: {type(e)}")
        return None


def parse_args():
    parser = argparse.ArgumentParser(description="Run SWEAP Pro evaluations using Modal or local Docker with multi-language support")
    parser.add_argument("--raw_sample_path", required=True, help="Path to the raw sample CSV file")
    parser.add_argument("--patch_path", required=True, help="Path to the JSON file containing patches")
    parser.add_argument("--output_dir", required=True, help="Directory to store evaluation outputs")
    parser.add_argument("--dockerhub_username", required=True, help="Docker Hub username where sweap-images repository is located")
    parser.add_argument("--scripts_dir", default="run_scripts", help="Directory containing local run scripts (fallback for non-multilang mode)")
    parser.add_argument("--use_local_docker", action="store_true", help="Run locally with Docker instead of Modal")
    parser.add_argument("--docker_platform", default=None, help="Docker platform override, e.g., linux/amd64")
    parser.add_argument("--redo", action="store_true", help="Redo evaluations even if output exists")
    parser.add_argument("--num_workers", type=int, default=50, help="Number of workers to run evaluations in parallel")
    parser.add_argument("--block_network", action="store_true", help="Block network access inside container")
    parser.add_argument("--no_multilang", action="store_true", help="Disable multi-language mode, use old scripts_dir logic only")
    return parser.parse_args()


def main():
    args = parse_args()
    use_multilang = not args.no_multilang

    if use_multilang and not MULTILANG_AVAILABLE:
        print("Warning: Multi-language config not available, falling back to old mode")
        use_multilang = False

    if args.raw_sample_path.endswith(".jsonl"):
        raw_sample_df = pd.read_json(args.raw_sample_path, lines=True)
    else:
        raw_sample_df = pd.read_csv(args.raw_sample_path)

    raw_sample_df = raw_sample_df.fillna("")
    raw_sample_df = raw_sample_df.set_index("instance_id", drop=False)

    with open(args.patch_path, "r") as f:
        patches_to_run = json.load(f)
    eval_results = {}

    valid_patches = []
    missing_instances = []
    for patch_sample in patches_to_run:
        instance_id = patch_sample["instance_id"]
        if instance_id in raw_sample_df.index:
            valid_patches.append(patch_sample)
        else:
            missing_instances.append(instance_id)

    if missing_instances:
        print(f"Warning: Found {len(missing_instances)} patch instances not in raw sample data:")
        for missing_id in missing_instances[:5]:
            print(f"  - {missing_id}")
        if len(missing_instances) > 5:
            print(f"  ... and {len(missing_instances) - 5} more")
        print(f"Proceeding with {len(valid_patches)} valid patches out of {len(patches_to_run)} total patches")

    detected_platform = None
    if args.use_local_docker and args.docker_platform is None:
        try:
            if py_platform.machine().lower() in {"arm64", "aarch64"}:
                detected_platform = "linux/amd64"
        except Exception:
            detected_platform = None

    eval_fn = eval_with_docker if args.use_local_docker else eval_with_modal

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        future_to_patch = {
            executor.submit(
                eval_fn,
                patch_sample.get("model_patch", patch_sample.get("patch", "")),
                raw_sample_df.loc[patch_sample["instance_id"]],
                args.output_dir,
                args.dockerhub_username,
                args.scripts_dir,
                prefix=patch_sample.get("prefix", ""),
                redo=args.redo,
                block_network=args.block_network,
                docker_platform=(args.docker_platform or detected_platform) if args.use_local_docker else None,
                use_multilang=use_multilang,
            ): patch_sample
            for patch_sample in valid_patches
        }

        pbar = tqdm(concurrent.futures.as_completed(future_to_patch), total=len(valid_patches))
        for future in pbar:
            patch_sample = future_to_patch[future]
            try:
                output = future.result()
                if output is None:
                    print(f'Evaluation for {patch_sample["instance_id"]} returned None')
                    eval_results[patch_sample["instance_id"]] = False
                else:
                    instance_id = patch_sample["instance_id"]
                    if instance_id not in raw_sample_df.index:
                        print(f'Warning: Instance {instance_id} not found in raw sample data, skipping')
                        eval_results[instance_id] = False
                    else:
                        raw_sample = raw_sample_df.loc[instance_id]
                        passed_tests = {x["name"] for x in output["tests"] if x["status"] == "PASSED"}
                        f2p = set(eval(raw_sample["fail_to_pass"]))
                        p2p = set(eval(raw_sample["pass_to_pass"]))
                        result = (f2p | p2p) <= passed_tests
                        eval_results[instance_id] = result

                current_accuracy = sum(eval_results.values()) / len(eval_results)
                pbar.set_description(f"Accuracy: {current_accuracy:.2%}")
            except Exception as exc:
                print(f'Evaluation for {patch_sample["instance_id"]} generated an exception: {exc}')
                eval_results[patch_sample["instance_id"]] = False
                current_accuracy = sum(eval_results.values()) / len(eval_results)
                pbar.set_description(f"Accuracy: {current_accuracy:.2%}")

    with open(os.path.join(args.output_dir, "eval_results.json"), "w") as f:
        json.dump(eval_results, f)
    print("Overall accuracy: ", sum(eval_results.values()) / len(eval_results))


if __name__ == "__main__":
    main()
