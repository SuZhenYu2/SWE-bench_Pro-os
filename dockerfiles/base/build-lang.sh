#!/usr/bin/env bash
# 构建某个语言的所有版本镜像
# 用法: ./dockerfiles/base/build-lang.sh <language> [registry-prefix] [tag]
# 示例: ./dockerfiles/base/build-lang.sh python myusername latest
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
LANG_DIR="${SCRIPT_DIR}/${LANG}"

if [ ! -d "${LANG_DIR}" ]; then
    echo "❌ 未找到语言目录: ${LANG_DIR}"
    exit 1
fi

# 获取该语言的所有版本目录
VERSIONS=()
for dir in "${LANG_DIR}"/*/; do
    if [ -f "${dir}/Dockerfile" ]; then
        ver=$(basename "$dir")
        VERSIONS+=("$ver")
    fi
done

if [ ${#VERSIONS[@]} -eq 0 ]; then
    echo "❌ 语言 '${LANG}' 下没有找到任何版本目录"
    exit 1
fi

echo "=========================================="
echo " 构建语言: ${LANG}"
echo " 版本: $(IFS=,; echo "${VERSIONS[*]}")"
echo " Registry 前缀: ${REGISTRY_PREFIX}"
echo " Tag: ${TAG}"
echo "=========================================="

TOTAL=${#VERSIONS[@]}
CURRENT=0
FAILED=()

for ver in "${VERSIONS[@]}"; do
    CURRENT=$((CURRENT + 1))
    IMAGE_NAME="${REGISTRY_PREFIX}-${LANG}-${ver}:${TAG}"
    BUILD_DIR="${LANG_DIR}/${ver}"

    echo ""
    echo "  [${CURRENT}/${TOTAL}] 构建: ${IMAGE_NAME}"

    set +e
    docker build -t "${IMAGE_NAME}" "${BUILD_DIR}"
    BUILD_EXIT=$?
    set -e

    if [ ${BUILD_EXIT} -ne 0 ]; then
        echo "    ❌ 构建失败: ${LANG}-${ver}"
        FAILED+=("${LANG}-${ver}")
    else
        echo "    ✅ 构建成功: ${IMAGE_NAME}"
    fi
done

echo ""
echo "=========================================="
echo " ${LANG} 构建完成"
echo " 成功: $((TOTAL - ${#FAILED[@]})) / ${TOTAL}"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo " 失败: $(IFS=, ; echo "${FAILED[*]}")"
    exit 1
else
    echo " 全部成功 🎉"
fi
echo "=========================================="
