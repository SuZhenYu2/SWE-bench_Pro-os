#!/usr/bin/env bash
# ============================================================
# 构建所有 10 种语言的 SWE-Bench Pro 基础镜像
# 用法: ./dockerfiles/base/build-all.sh [registry-prefix] [tag]
# 示例: ./dockerfiles/base/build-all.sh myusername latest
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

REGISTRY_PREFIX="${1:-sweap}"
TAG="${2:-latest}"

LANGUAGES=(
    "python"
    "javascript"
    "java"
    "go"
    "rust"
    "ruby"
    "cpp"
    "php"
    "dotnet"
    "elixir"
)

echo "=========================================="
echo " 开始构建 10 种语言的 SWE-Bench Pro 镜像"
echo "  Registry 前缀: ${REGISTRY_PREFIX}"
echo "  Tag:          ${TAG}"
echo "=========================================="

TOTAL=${#LANGUAGES[@]}
CURRENT=0
FAILED=()

for lang in "${LANGUAGES[@]}"; do
    CURRENT=$((CURRENT + 1))
    IMAGE_NAME="${REGISTRY_PREFIX}-${lang}:${TAG}"
    BUILD_DIR="${SCRIPT_DIR}/${lang}"

    echo ""
    echo "┌───────────────────────────────────────"
    echo "│ [${CURRENT}/${TOTAL}] 正在构建: ${IMAGE_NAME}"
    echo "│ 路径: ${BUILD_DIR}"
    echo "└───────────────────────────────────────"

    if [ ! -f "${BUILD_DIR}/Dockerfile" ]; then
        echo "  ❌ 缺少 Dockerfile，跳过"
        FAILED+=("${lang}(missing Dockerfile)")
        continue
    fi

    set +e
    docker build -t "${IMAGE_NAME}" "${BUILD_DIR}"
    BUILD_EXIT=$?
    set -e

    if [ ${BUILD_EXIT} -ne 0 ]; then
        echo "  ❌ 构建失败: ${lang}"
        FAILED+=("${lang}")
    else
        echo "  ✅ 构建成功: ${IMAGE_NAME}"
    fi
done

echo ""
echo "=========================================="
echo " 构建完成"
echo " 成功: $((TOTAL - ${#FAILED[@]})) / ${TOTAL}"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo " 失败: $(IFS=, ; echo "${FAILED[*]}")"
    exit 1
else
    echo " 全部成功 🎉"
fi
echo "=========================================="
