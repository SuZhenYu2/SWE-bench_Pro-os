# 多语言镜像配置索引
# 供 swe_bench_pro_eval.py 和 generate_sweagent_instances.py 根据语言+版本自动选择镜像

# 版本矩阵定义
LANGUAGE_VERSIONS = {
    "python": {
        "display_name": "Python",
        "default_version": "3.11",
        "versions": {
            "3.9": {
                "image_tag": "sweap-python-3.9:latest",
                "dockerfile_path": "dockerfiles/base/python/3.9/Dockerfile",
            },
            "3.10": {
                "image_tag": "sweap-python-3.10:latest",
                "dockerfile_path": "dockerfiles/base/python/3.10/Dockerfile",
            },
            "3.11": {
                "image_tag": "sweap-python-3.11:latest",
                "dockerfile_path": "dockerfiles/base/python/3.11/Dockerfile",
            },
            "3.12": {
                "image_tag": "sweap-python-3.12:latest",
                "dockerfile_path": "dockerfiles/base/python/3.12/Dockerfile",
            },
            "3.13": {
                "image_tag": "sweap-python-3.13:latest",
                "dockerfile_path": "dockerfiles/base/python/3.13/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/python/run_script.sh",
        "parser_path": "dockerfiles/base/python/parser.py",
        "test_frameworks": ["pytest", "unittest", "tox"],
        "file_extensions": [".py"],
        "config_files": [
            "setup.py", "setup.cfg", "pyproject.toml",
            "requirements.txt", "Pipfile", "tox.ini",
        ],
    },
    "javascript": {
        "display_name": "JavaScript / TypeScript",
        "default_version": "node20",
        "versions": {
            "node16": {
                "image_tag": "sweap-javascript-node16:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node16/Dockerfile",
            },
            "node18": {
                "image_tag": "sweap-javascript-node18:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node18/Dockerfile",
            },
            "node20": {
                "image_tag": "sweap-javascript-node20:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node20/Dockerfile",
            },
            "node22": {
                "image_tag": "sweap-javascript-node22:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node22/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/javascript/run_script.sh",
        "parser_path": "dockerfiles/base/javascript/parser.py",
        "test_frameworks": ["vitest", "jest", "mocha", "tap", "ava"],
        "file_extensions": [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
        "config_files": [
            "package.json", "package-lock.json",
            "yarn.lock", "pnpm-lock.yaml",
            "tsconfig.json", "vitest.config.ts", "jest.config.js",
        ],
    },
    "typescript": {
        "display_name": "TypeScript",
        "default_version": "node20",
        "versions": {
            "node16": {
                "image_tag": "sweap-javascript-node16:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node16/Dockerfile",
            },
            "node18": {
                "image_tag": "sweap-javascript-node18:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node18/Dockerfile",
            },
            "node20": {
                "image_tag": "sweap-javascript-node20:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node20/Dockerfile",
            },
            "node22": {
                "image_tag": "sweap-javascript-node22:latest",
                "dockerfile_path": "dockerfiles/base/javascript/node22/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/javascript/run_script.sh",
        "parser_path": "dockerfiles/base/javascript/parser.py",
        "test_frameworks": ["vitest", "jest", "mocha"],
        "file_extensions": [".ts", ".tsx"],
        "config_files": [
            "package.json", "tsconfig.json",
            "vitest.config.ts", "jest.config.ts",
        ],
    },
    "java": {
        "display_name": "Java",
        "default_version": "jdk17",
        "versions": {
            "jdk11": {
                "image_tag": "sweap-java-jdk11:latest",
                "dockerfile_path": "dockerfiles/base/java/jdk11/Dockerfile",
            },
            "jdk17": {
                "image_tag": "sweap-java-jdk17:latest",
                "dockerfile_path": "dockerfiles/base/java/jdk17/Dockerfile",
            },
            "jdk21": {
                "image_tag": "sweap-java-jdk21:latest",
                "dockerfile_path": "dockerfiles/base/java/jdk21/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/java/run_script.sh",
        "parser_path": "dockerfiles/base/java/parser.py",
        "test_frameworks": ["junit5", "junit4", "testng"],
        "file_extensions": [".java"],
        "config_files": [
            "pom.xml", "build.gradle", "build.gradle.kts",
            "settings.gradle", "settings.gradle.kts",
        ],
    },
    "go": {
        "display_name": "Go",
        "default_version": "1.22",
        "versions": {
            "1.20": {
                "image_tag": "sweap-go-1.20:latest",
                "dockerfile_path": "dockerfiles/base/go/1.20/Dockerfile",
            },
            "1.21": {
                "image_tag": "sweap-go-1.21:latest",
                "dockerfile_path": "dockerfiles/base/go/1.21/Dockerfile",
            },
            "1.22": {
                "image_tag": "sweap-go-1.22:latest",
                "dockerfile_path": "dockerfiles/base/go/1.22/Dockerfile",
            },
            "1.23": {
                "image_tag": "sweap-go-1.23:latest",
                "dockerfile_path": "dockerfiles/base/go/1.23/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/go/run_script.sh",
        "parser_path": "dockerfiles/base/go/parser.py",
        "test_frameworks": ["go test"],
        "file_extensions": [".go"],
        "config_files": ["go.mod", "go.sum"],
    },
    "rust": {
        "display_name": "Rust",
        "default_version": "stable",
        "versions": {
            "1.75": {
                "image_tag": "sweap-rust-1.75:latest",
                "dockerfile_path": "dockerfiles/base/rust/1.75/Dockerfile",
            },
            "1.80": {
                "image_tag": "sweap-rust-1.80:latest",
                "dockerfile_path": "dockerfiles/base/rust/1.80/Dockerfile",
            },
            "1.82": {
                "image_tag": "sweap-rust-1.82:latest",
                "dockerfile_path": "dockerfiles/base/rust/1.82/Dockerfile",
            },
            "stable": {
                "image_tag": "sweap-rust-stable:latest",
                "dockerfile_path": "dockerfiles/base/rust/stable/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/rust/run_script.sh",
        "parser_path": "dockerfiles/base/rust/parser.py",
        "test_frameworks": ["cargo test"],
        "file_extensions": [".rs"],
        "config_files": ["Cargo.toml", "Cargo.lock"],
    },
    "ruby": {
        "display_name": "Ruby",
        "default_version": "3.2",
        "versions": {
            "3.0": {
                "image_tag": "sweap-ruby-3.0:latest",
                "dockerfile_path": "dockerfiles/base/ruby/3.0/Dockerfile",
            },
            "3.1": {
                "image_tag": "sweap-ruby-3.1:latest",
                "dockerfile_path": "dockerfiles/base/ruby/3.1/Dockerfile",
            },
            "3.2": {
                "image_tag": "sweap-ruby-3.2:latest",
                "dockerfile_path": "dockerfiles/base/ruby/3.2/Dockerfile",
            },
            "3.3": {
                "image_tag": "sweap-ruby-3.3:latest",
                "dockerfile_path": "dockerfiles/base/ruby/3.3/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/ruby/run_script.sh",
        "parser_path": "dockerfiles/base/ruby/parser.py",
        "test_frameworks": ["rspec", "minitest"],
        "file_extensions": [".rb"],
        "config_files": [
            "Gemfile", "Gemfile.lock",
            ".rspec", "spec/", "test/",
        ],
    },
    "cpp": {
        "display_name": "C / C++",
        "default_version": "gcc12",
        "versions": {
            "gcc11": {
                "image_tag": "sweap-cpp-gcc11:latest",
                "dockerfile_path": "dockerfiles/base/cpp/gcc11/Dockerfile",
            },
            "gcc12": {
                "image_tag": "sweap-cpp-gcc12:latest",
                "dockerfile_path": "dockerfiles/base/cpp/gcc12/Dockerfile",
            },
            "gcc13": {
                "image_tag": "sweap-cpp-gcc13:latest",
                "dockerfile_path": "dockerfiles/base/cpp/gcc13/Dockerfile",
            },
            "clang16": {
                "image_tag": "sweap-cpp-clang16:latest",
                "dockerfile_path": "dockerfiles/base/cpp/clang16/Dockerfile",
            },
            "clang17": {
                "image_tag": "sweap-cpp-clang17:latest",
                "dockerfile_path": "dockerfiles/base/cpp/clang17/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/cpp/run_script.sh",
        "parser_path": "dockerfiles/base/cpp/parser.py",
        "test_frameworks": ["gtest", "catch2", "boost.test", "ctest"],
        "file_extensions": [".cpp", ".cc", ".cxx", ".c++", ".c", ".h", ".hpp"],
        "config_files": [
            "CMakeLists.txt", "Makefile",
            "configure.ac", "meson.build",
        ],
    },
    "php": {
        "display_name": "PHP",
        "default_version": "8.2",
        "versions": {
            "8.1": {
                "image_tag": "sweap-php-8.1:latest",
                "dockerfile_path": "dockerfiles/base/php/8.1/Dockerfile",
            },
            "8.2": {
                "image_tag": "sweap-php-8.2:latest",
                "dockerfile_path": "dockerfiles/base/php/8.2/Dockerfile",
            },
            "8.3": {
                "image_tag": "sweap-php-8.3:latest",
                "dockerfile_path": "dockerfiles/base/php/8.3/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/php/run_script.sh",
        "parser_path": "dockerfiles/base/php/parser.py",
        "test_frameworks": ["phpunit"],
        "file_extensions": [".php"],
        "config_files": [
            "composer.json", "composer.lock",
            "phpunit.xml", "phpunit.xml.dist",
        ],
    },
    "dotnet": {
        "display_name": ".NET (C# / F# / VB)",
        "default_version": "8.0",
        "versions": {
            "6.0": {
                "image_tag": "sweap-dotnet-6.0:latest",
                "dockerfile_path": "dockerfiles/base/dotnet/6.0/Dockerfile",
            },
            "7.0": {
                "image_tag": "sweap-dotnet-7.0:latest",
                "dockerfile_path": "dockerfiles/base/dotnet/7.0/Dockerfile",
            },
            "8.0": {
                "image_tag": "sweap-dotnet-8.0:latest",
                "dockerfile_path": "dockerfiles/base/dotnet/8.0/Dockerfile",
            },
            "9.0": {
                "image_tag": "sweap-dotnet-9.0:latest",
                "dockerfile_path": "dockerfiles/base/dotnet/9.0/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/dotnet/run_script.sh",
        "parser_path": "dockerfiles/base/dotnet/parser.py",
        "test_frameworks": ["xunit", "nunit", "mstest"],
        "file_extensions": [".cs", ".fs", ".vb"],
        "config_files": [
            "*.sln", "*.csproj", "*.fsproj", "*.vbproj",
        ],
    },
    "elixir": {
        "display_name": "Elixir",
        "default_version": "1.16",
        "versions": {
            "1.14": {
                "image_tag": "sweap-elixir-1.14:latest",
                "dockerfile_path": "dockerfiles/base/elixir/1.14/Dockerfile",
            },
            "1.15": {
                "image_tag": "sweap-elixir-1.15:latest",
                "dockerfile_path": "dockerfiles/base/elixir/1.15/Dockerfile",
            },
            "1.16": {
                "image_tag": "sweap-elixir-1.16:latest",
                "dockerfile_path": "dockerfiles/base/elixir/1.16/Dockerfile",
            },
            "1.17": {
                "image_tag": "sweap-elixir-1.17:latest",
                "dockerfile_path": "dockerfiles/base/elixir/1.17/Dockerfile",
            },
        },
        "run_script_path": "dockerfiles/base/elixir/run_script.sh",
        "parser_path": "dockerfiles/base/elixir/parser.py",
        "test_frameworks": ["exunit"],
        "file_extensions": [".ex", ".exs"],
        "config_files": ["mix.exs", "mix.lock"],
    },
}


def get_language_config(lang, version=None):
    """
    获取语言配置。
    
    Args:
        lang: 语言代码 (如 'python', 'go')
        version: 版本号 (如 '3.11', '1.22')，为 None 时使用默认版本
    
    Returns:
        dict: 包含 image_tag, dockerfile_path, run_script_path, parser_path 等的配置
    """
    lang_cfg = LANGUAGE_VERSIONS.get(lang)
    if not lang_cfg:
        return None
    
    ver = version or lang_cfg.get("default_version")
    ver_cfg = lang_cfg.get("versions", {}).get(ver)
    if not ver_cfg:
        # 如果指定版本不存在，回退到默认版本
        ver = lang_cfg.get("default_version")
        ver_cfg = lang_cfg.get("versions", {}).get(ver, {})
    
    result = {
        "language": lang,
        "version": ver,
        "display_name": lang_cfg.get("display_name"),
        "image_tag": ver_cfg.get("image_tag"),
        "dockerfile_path": ver_cfg.get("dockerfile_path"),
        "run_script_path": lang_cfg.get("run_script_path"),
        "parser_path": lang_cfg.get("parser_path"),
        "test_frameworks": lang_cfg.get("test_frameworks", []),
        "file_extensions": lang_cfg.get("file_extensions", []),
        "config_files": lang_cfg.get("config_files", []),
    }
    return result


def get_all_versions(lang):
    """获取某语言的所有可用版本列表。"""
    lang_cfg = LANGUAGE_VERSIONS.get(lang)
    if not lang_cfg:
        return []
    return list(lang_cfg.get("versions", {}).keys())


def get_default_version(lang):
    """获取某语言的默认版本。"""
    lang_cfg = LANGUAGE_VERSIONS.get(lang)
    if not lang_cfg:
        return None
    return lang_cfg.get("default_version")


def get_all_languages():
    """获取所有支持的语言代码列表。"""
    return list(LANGUAGE_VERSIONS.keys())


def detect_language_by_config(config_files_found):
    """根据发现的配置文件猜测主语言。"""
    priority_order = [
        "rust", "elixir", "go", "dotnet", "java",
        "php", "ruby", "cpp", "javascript", "typescript", "python",
    ]
    for lang in priority_order:
        confs = LANGUAGE_VERSIONS[lang]["config_files"]
        for conf in confs:
            for found in config_files_found:
                if conf.endswith("*"):
                    if found.endswith(conf.replace("*", "").split("/")[-1]):
                        return lang
                elif conf.endswith("/"):
                    if conf in found:
                        return lang
                elif conf in found:
                    return lang
    return None


def detect_version_from_files(lang, file_contents):
    """
    从项目文件中检测语言版本。
    
    Args:
        lang: 语言代码
        file_contents: dict，文件名 -> 文件内容
    
    Returns:
        str: 检测到的版本号，或 None
    """
    if lang == "python":
        # 从 pyproject.toml 或 setup.py 检测 Python 版本要求
        for fname, content in file_contents.items():
            if "pyproject.toml" in fname:
                import re
                m = re.search(r'requires-python\s*=\s*["\']([\d.]+)', content)
                if m:
                    ver = m.group(1)
                    # 映射到最接近的版本
                    for v in ["3.13", "3.12", "3.11", "3.10", "3.9"]:
                        if ver.startswith(v):
                            return v
    elif lang == "javascript" or lang == "typescript":
        for fname, content in file_contents.items():
            if "package.json" in fname:
                import re
                m = re.search(r'"engines"\s*:\s*\{[^}]*"node"\s*:\s*["\']?([\d.]+)', content)
                if m:
                    ver = m.group(1)
                    for v in ["22", "20", "18", "16"]:
                        if ver.startswith(v):
                            return f"node{v}"
    elif lang == "go":
        for fname, content in file_contents.items():
            if "go.mod" in fname:
                import re
                m = re.search(r'^go\s+([\d.]+)', content, re.MULTILINE)
                if m:
                    ver = m.group(1)
                    for v in ["1.23", "1.22", "1.21", "1.20"]:
                        if ver.startswith(v):
                            return v
    elif lang == "rust":
        for fname, content in file_contents.items():
            if "Cargo.toml" in fname:
                import re
                m = re.search(r'^rust-version\s*=\s*["\']([\d.]+)', content, re.MULTILINE)
                if m:
                    ver = m.group(1)
                    for v in ["1.82", "1.80", "1.75"]:
                        if ver.startswith(v):
                            return v
    elif lang == "java":
        for fname, content in file_contents.items():
            if "pom.xml" in fname:
                import re
                m = re.search(r'<java\.version>([\d.]+)</java\.version>', content)
                if m:
                    ver = m.group(1)
                    for v in ["21", "17", "11"]:
                        if ver.startswith(v):
                            return f"jdk{v}"
            if "build.gradle" in fname:
                import re
                m = re.search(r'sourceCompatibility\s*=\s*["\']?([\d.]+)', content)
                if m:
                    ver = m.group(1)
                    for v in ["21", "17", "11"]:
                        if ver.startswith(v):
                            return f"jdk{v}"
    elif lang == "ruby":
        for fname, content in file_contents.items():
            if "Gemfile" in fname:
                import re
                m = re.search(r'ruby\s*["\']([\d.]+)', content)
                if m:
                    ver = m.group(1)
                    for v in ["3.3", "3.2", "3.1", "3.0"]:
                        if ver.startswith(v):
                            return v
    elif lang == "php":
        for fname, content in file_contents.items():
            if "composer.json" in fname:
                import re
                m = re.search(r'"php"\s*:\s*["\']?([\d.]+)', content)
                if m:
                    ver = m.group(1)
                    for v in ["8.3", "8.2", "8.1"]:
                        if ver.startswith(v):
                            return v
    elif lang == "dotnet":
        for fname, content in file_contents.items():
            if fname.endswith(".csproj"):
                import re
                m = re.search(r'<TargetFramework>(net[\d.]+)</TargetFramework>', content)
                if m:
                    tf = m.group(1)
                    for v in ["9.0", "8.0", "7.0", "6.0"]:
                        if tf.endswith(v):
                            return v
    elif lang == "elixir":
        for fname, content in file_contents.items():
            if "mix.exs" in fname:
                import re
                m = re.search(r'elixir:\s*["\']~>\s*([\d.]+)', content)
                if m:
                    ver = m.group(1)
                    for v in ["1.17", "1.16", "1.15", "1.14"]:
                        if ver.startswith(v):
                            return v
    
    return None


def resolve_image_tag(lang, version=None):
    """
    解析语言+版本对应的 Docker 镜像 tag。
    
    Args:
        lang: 语言代码
        version: 版本号，为 None 时使用默认版本
    
    Returns:
        str: Docker 镜像 tag，如 "sweap-python-3.11:latest"
    """
    cfg = get_language_config(lang, version)
    if cfg:
        return cfg.get("image_tag")
    return None
