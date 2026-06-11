# 多语言 SWE-Bench Pro Docker 镜像模板

## 目录结构

```
dockerfiles/base/
├── common/
│   └── base-utils.Dockerfile       # 通用工具层（所有语言镜像的基础）
├── python/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── javascript/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── java/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── go/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── rust/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── ruby/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── cpp/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── php/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
├── dotnet/
│   ├── Dockerfile
│   ├── run_script.sh
│   └── parser.py
└── elixir/
    ├── Dockerfile
    ├── run_script.sh
    └── parser.py
```

## 通用约定

所有镜像统一使用 `debian:bookworm-slim` 作为底层（兼容性最好），预装：

- `git` / `patch` / `diffutils` —— 用于 git apply 和补丁操作
- `curl` / `wget` / `ca-certificates` —— 网络工具
- `build-essential` —— C/C++ 编译链（某些语言项目需要）
- `bash` —— 统一 shell

工作目录统一为 `/app`，评估脚本目录为 `/workspace`。

## 构建命令示例

```bash
# 构建单个语言镜像
docker build -t sweap-python:latest dockerfiles/base/python
docker build -t sweap-javascript:latest dockerfiles/base/javascript
docker build -t sweap-java:latest dockerfiles/base/java
docker build -t sweap-go:latest dockerfiles/base/go
docker build -t sweap-rust:latest dockerfiles/base/rust
docker build -t sweap-ruby:latest dockerfiles/base/ruby
docker build -t sweap-cpp:latest dockerfiles/base/cpp
docker build -t sweap-php:latest dockerfiles/base/php
docker build -t sweap-dotnet:latest dockerfiles/base/dotnet
docker build -t sweap-elixir:latest dockerfiles/base/elixir

# 一键构建所有
./dockerfiles/base/build-all.sh
```
