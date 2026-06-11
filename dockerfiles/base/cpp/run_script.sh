#!/bin/bash
set -e

cd /app

if [ ! -f "CMakeLists.txt" ]; then
    echo "Error: CMakeLists.txt not found in /app"
    exit 1
fi

echo "=== Running cmake build ==="
cmake -B build
cmake --build build --parallel

TEST_FILTER=""
if [ -n "$1" ]; then
    IFS=',' read -ra FILES <<< "$1"
    for FILE in "${FILES[@]}"; do
        BASENAME=$(basename "$FILE" .cpp)
        BASENAME=$(basename "$BASENAME" .cc)
        BASENAME=$(basename "$BASENAME" .cxx)
        if [ -z "$TEST_FILTER" ]; then
            TEST_FILTER="${BASENAME}"
        else
            TEST_FILTER="${TEST_FILTER}|${BASENAME}"
        fi
    done
fi

if [ -d "build" ]; then
    echo "=== Running ctest ==="
    if [ -n "$TEST_FILTER" ]; then
        echo "=== Test filter: $TEST_FILTER ==="
        ctest --test-dir build --output-on-failure -R "$TEST_FILTER" 2>&1 || true
    else
        ctest --test-dir build --output-on-failure 2>&1 || true
    fi

    if [ -x "./build/tests" ]; then
        echo "=== Running ./build/tests ==="
        ./build/tests 2>&1 || true
    fi
fi
