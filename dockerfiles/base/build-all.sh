#!/usr/bin/env bash
# ============================================================
# 构建所有多版本语言的 SWE-Bench Pro 基础镜像
# 用法: ./dockerfiles/base/build-all.sh [registry-prefix] [tag]
# 示例: ./dockerfiles/base/build-all.sh myusername latest
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY_PREFIX="${1:-sweap}"
TAG="${2:-latest}"

# 定义所有语言及其版本
# 格式: "语言:版本1,版本2,..."
LANGUAGE_VERSIONS=(
    "python:3.9,3.10,3.11,3.12,3.13"
    "javascript:node16,node18,node20,node22"
    "java:jdk11,jdk17,jdk21"
    "go:1.20,1.21,1.22,1.23"
    "rust:1.75,1.80,1.82,stable"
    "ruby:3.0,3.1,3.2,3.3"
    "cpp:gcc11,gcc12,gcc13,clang16,clang17"
    "php:8.1,8.2,8.3"
    "dotnet:6.0,7.0,8.0,9.0"
    "elixir:1.14,1.15,1.16,1.17"
)

echo "=========================================="
echo " 开始构建多版本 SWE-Bench Pro 镜像"
echo " Registry 前缀: ${REGISTRY_PREFIX}"
echo " Tag:          ${TAG}"
echo "=========================================="

TOTAL_BUILDS=0
CURRENT=0
FAILED=()

# 计算总构建数
for entry in "${LANGUAGE_VERSIONS[@]}"; do
    versions="${entry#*:}"
    IFS=',' read -ra VERS <<< "$versions"
    TOTAL_BUILDS=$((TOTAL_BUILDS + ${#VERS[@]}))
done

echo " 总计: ${TOTAL_BUILDS} 个镜像需要构建"
echo "=========================================="

for entry in "${LANGUAGE_VERSIONS[@]}"; do
    lang="${entry%%:*}"
    versions="${entry#*:}"
    IFS=',' read -ra VERS <<< "$versions"

    echo ""
    echo "┌───────────────────────────────────────"
    echo "│ 语言: ${lang}"
    echo "│ 版本: ${versions}"
    echo "└───────────────────────────────────────"

    for ver in "${VERS[@]}"; do
        CURRENT=$((CURRENT + 1))
        IMAGE_NAME="${REGISTRY_PREFIX}-${lang}-${ver}:${TAG}"
        BUILD_DIR="${SCRIPT_DIR}/${lang}/${ver}"

        echo ""
        echo "  [${CURRENT}/${TOTAL_BUILDS}] 构建: ${IMAGE_NAME}"

        if [ ! -f "${BUILD_DIR}/Dockerfile" ]; then
            echo "    ❌ 缺少 Dockerfile: ${BUILD_DIR}/Dockerfile"
            FAILED+=("${lang}-${ver}(missing Dockerfile)")
            continue
        fi

        set +e
        docker build -t "${IMAGE_NAME}" "${BUILD_DIR}"
        BUILD_EXIT=$?
        set -e

        if [ ${BUILD_EXIT} -ne 0 ]; then
            echo "    ❌ 构建失败: ${lang}-${ver}"
            FAILED+=("${lang}-${ver}")
        else
            echo "    ✅ 构建成功: ${IMAGE_NAME}"
        fi
    done
done

echo ""
echo "=========================================="
echo " 构建完成"
echo " 成功: $((TOTAL_BUILDS - ${#FAILED[@]})) / ${TOTAL_BUILDS}"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo " 失败: $(IFS=, ; echo "${FAILED[*]}")"
    exit 1
else
    echo " 全部成功 🎉"
fi
echo "=========================================="
