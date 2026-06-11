# 多语言镜像配置索引
# 供 swe_bench_pro_eval.py 和 generate_sweagent_instances.py 根据语言自动选择镜像

LANGUAGES = {
    "python": {
        "display_name": "Python",
        "image_tag": "sweap-python:latest",
        "dockerfile_path": "dockerfiles/base/python/Dockerfile",
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
        "image_tag": "sweap-javascript:latest",
        "dockerfile_path": "dockerfiles/base/javascript/Dockerfile",
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
        "image_tag": "sweap-javascript:latest",
        "dockerfile_path": "dockerfiles/base/javascript/Dockerfile",
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
        "image_tag": "sweap-java:latest",
        "dockerfile_path": "dockerfiles/base/java/Dockerfile",
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
        "image_tag": "sweap-go:latest",
        "dockerfile_path": "dockerfiles/base/go/Dockerfile",
        "run_script_path": "dockerfiles/base/go/run_script.sh",
        "parser_path": "dockerfiles/base/go/parser.py",
        "test_frameworks": ["go test"],
        "file_extensions": [".go"],
        "config_files": ["go.mod", "go.sum"],
    },
    "rust": {
        "display_name": "Rust",
        "image_tag": "sweap-rust:latest",
        "dockerfile_path": "dockerfiles/base/rust/Dockerfile",
        "run_script_path": "dockerfiles/base/rust/run_script.sh",
        "parser_path": "dockerfiles/base/rust/parser.py",
        "test_frameworks": ["cargo test"],
        "file_extensions": [".rs"],
        "config_files": ["Cargo.toml", "Cargo.lock"],
    },
    "ruby": {
        "display_name": "Ruby",
        "image_tag": "sweap-ruby:latest",
        "dockerfile_path": "dockerfiles/base/ruby/Dockerfile",
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
        "image_tag": "sweap-cpp:latest",
        "dockerfile_path": "dockerfiles/base/cpp/Dockerfile",
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
        "image_tag": "sweap-php:latest",
        "dockerfile_path": "dockerfiles/base/php/Dockerfile",
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
        "image_tag": "sweap-dotnet:latest",
        "dockerfile_path": "dockerfiles/base/dotnet/Dockerfile",
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
        "image_tag": "sweap-elixir:latest",
        "dockerfile_path": "dockerfiles/base/elixir/Dockerfile",
        "run_script_path": "dockerfiles/base/elixir/run_script.sh",
        "parser_path": "dockerfiles/base/elixir/parser.py",
        "test_frameworks": ["exunit"],
        "file_extensions": [".ex", ".exs"],
        "config_files": ["mix.exs", "mix.lock"],
    },
}


def detect_language_by_config(config_files_found):
    """根据发现的配置文件猜测主语言。"""
    priority_order = [
        "rust", "elixir", "go", "dotnet", "java",
        "php", "ruby", "cpp", "javascript", "typescript", "python",
    ]
    for lang in priority_order:
        confs = LANGUAGES[lang]["config_files"]
        for conf in confs:
            # 简单前缀/精确匹配
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


def get_all_language_codes():
    return list(LANGUAGES.keys())


def get_language_config(lang):
    return LANGUAGES.get(lang)
