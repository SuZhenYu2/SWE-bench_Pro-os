#!/bin/bash
set -euo pipefail

TEST_FILES="${1:-}"

if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found" >&2
    exit 1
fi

if [ -f "yarn.lock" ]; then
    PKG_MANAGER="yarn"
elif [ -f "pnpm-lock.yaml" ]; then
    PKG_MANAGER="pnpm"
elif [ -f "package-lock.json" ]; then
    PKG_MANAGER="npm"
else
    PKG_MANAGER="npm"
fi

echo "Using package manager: ${PKG_MANAGER}"

case "${PKG_MANAGER}" in
    yarn)
        yarn install --frozen-lockfile 2>&1 || yarn install 2>&1
        ;;
    pnpm)
        pnpm install --frozen-lockfile 2>&1 || pnpm install 2>&1
        ;;
    npm)
        npm ci 2>&1 || npm install 2>&1
        ;;
esac

TEST_ARGS=""
if [ -n "${TEST_FILES}" ]; then
    IFS=',' read -r -a TEST_ARRAY <<< "${TEST_FILES}"
    TEST_ARGS="${TEST_ARRAY[*]}"
fi

HAS_TEST_SCRIPT=false
if node -e "const pkg=require('./package.json'); if(pkg.scripts && pkg.scripts.test) process.exit(0); else process.exit(1)" 2>/dev/null; then
    HAS_TEST_SCRIPT=true
fi

TEST_EXTRA_ARGS=""
if [ -n "${TEST_ARGS}" ]; then
    TEST_EXTRA_ARGS=" -- ${TEST_ARGS}"
fi

if [ "${HAS_TEST_SCRIPT}" = "true" ]; then
    echo "Running: ${PKG_MANAGER} test${TEST_EXTRA_ARGS}"
    eval "${PKG_MANAGER} test${TEST_EXTRA_ARGS}" 2>&1 || true
elif command -v vitest >/dev/null 2>&1 || [ -x "./node_modules/.bin/vitest" ]; then
    echo "Running: vitest run ${TEST_ARGS}"
    if [ -x "./node_modules/.bin/vitest" ]; then
        ./node_modules/.bin/vitest run ${TEST_ARGS} 2>&1 || true
    else
        vitest run ${TEST_ARGS} 2>&1 || true
    fi
elif command -v jest >/dev/null 2>&1 || [ -x "./node_modules/.bin/jest" ]; then
    echo "Running: jest ${TEST_ARGS}"
    if [ -x "./node_modules/.bin/jest" ]; then
        ./node_modules/.bin/jest ${TEST_ARGS} 2>&1 || true
    else
        jest ${TEST_ARGS} 2>&1 || true
    fi
else
    echo "Running: ${PKG_MANAGER} test${TEST_EXTRA_ARGS}"
    eval "${PKG_MANAGER} test${TEST_EXTRA_ARGS}" 2>&1 || true
fi
