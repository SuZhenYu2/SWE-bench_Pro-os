#!/usr/bin/env bash
# 构建单个语言镜像
# 用法: ./dockerfiles/base/build-one.sh <language> [registry-prefix] [tag]
# 示例: ./dockerfiles/base/build-one.sh python myusername latest
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "用法: $0 <language> [registry-prefix] [tag]"
    echo "支持的语言: python, javascript, java, go, rust, ruby, cpp, php, dotnet, elixir"
    exit 1
fi

LANG="$1"
REGISTRY_PREFIX="${2:-sweap}"
TAG="${3:-latest}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/${LANG}"
IMAGE_NAME="${REGISTRY_PREFIX}-${LANG}:${TAG}"

if [ ! -f "${BUILD_DIR}/Dockerfile" ]; then
    echo "❌ 未找到 ${BUILD_DIR}/Dockerfile"
    exit 1
fi

echo "构建镜像: ${IMAGE_NAME}"
echo "上下文路径: ${BUILD_DIR}"
docker build -t "${IMAGE_NAME}" "${BUILD_DIR}"
echo "✅ 完成: ${IMAGE_NAME}"
