#!/usr/bin/env bash
# 构建单个语言-版本镜像
# 用法: ./dockerfiles/base/build-one.sh <language> <version> [registry-prefix] [tag]
# 示例: ./dockerfiles/base/build-one.sh python 3.11 myusername latest
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "用法: $0 <language> <version> [registry-prefix] [tag]"
    echo ""
    echo "支持的语言和版本:"
    echo "  python:     3.9, 3.10, 3.11, 3.12, 3.13"
    echo "  javascript: node16, node18, node20, node22"
    echo "  java:       jdk11, jdk17, jdk21"
    echo "  go:         1.20, 1.21, 1.22, 1.23"
    echo "  rust:       1.75, 1.80, 1.82, stable"
    echo "  ruby:       3.0, 3.1, 3.2, 3.3"
    echo "  cpp:        gcc11, gcc12, gcc13, clang16, clang17"
    echo "  php:        8.1, 8.2, 8.3"
    echo "  dotnet:     6.0, 7.0, 8.0, 9.0"
    echo "  elixir:     1.14, 1.15, 1.16, 1.17"
    exit 1
fi

LANG="$1"
VERSION="$2"
REGISTRY_PREFIX="${3:-sweap}"
TAG="${4:-latest}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/${LANG}/${VERSION}"
IMAGE_NAME="${REGISTRY_PREFIX}-${LANG}-${VERSION}:${TAG}"

if [ ! -f "${BUILD_DIR}/Dockerfile" ]; then
    echo "❌ 未找到 ${BUILD_DIR}/Dockerfile"
    echo "   请检查语言 '${LANG}' 和版本 '${VERSION}' 是否正确"
    exit 1
fi

echo "构建镜像: ${IMAGE_NAME}"
echo "上下文路径: ${BUILD_DIR}"
docker build -t "${IMAGE_NAME}" "${BUILD_DIR}"
echo "✅ 完成: ${IMAGE_NAME}"
