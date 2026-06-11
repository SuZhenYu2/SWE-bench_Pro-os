#!/bin/bash
set -e

cd /app

if [ ! -f "Cargo.toml" ]; then
    echo "Error: Cargo.toml not found in /app"
    exit 1
fi

echo "=== Running cargo fetch ==="
cargo fetch

TEST_FILTER=""
if [ -n "$1" ]; then
    IFS=',' read -ra FILES <<< "$1"
    for FILE in "${FILES[@]}"; do
        BASENAME=$(basename "$FILE" .rs)
        TEST_FILTER="${TEST_FILTER} ${BASENAME}"
    done
    TEST_FILTER=$(echo "$TEST_FILTER" | xargs)
    echo "=== Running cargo test with filter: $TEST_FILTER ==="
    cargo test $TEST_FILTER -- --test-threads=1 2>&1
else
    echo "=== Running cargo test ==="
    cargo test -- --test-threads=1 2>&1
fi
