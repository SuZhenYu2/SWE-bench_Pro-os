#!/usr/bin/env bash

TEST_FILES="${1:-}"

cd /app || cd "$(pwd)"

if [ ! -f "go.mod" ]; then
    echo "ERROR: go.mod not found in $(pwd)" >&2
    exit 1
fi

go mod download || go mod tidy

if [ -n "$TEST_FILES" ]; then
    IFS=',' read -ra FILE_ARR <<< "$TEST_FILES"
    declare -a DIRS=()
    for f in "${FILE_ARR[@]}"; do
        f=$(echo "$f" | xargs)
        if [ -z "$f" ]; then
            continue
        fi
        dir=$(dirname "$f")
        dir=$(echo "$dir" | sed 's|^\./||; s|^/app/||; s|^app/||')
        if [ -z "$dir" ] || [ "$dir" = "." ]; then
            pattern="./..."
        else
            pattern="./${dir}/..."
        fi
        already=0
        for d in "${DIRS[@]}"; do
            if [ "$d" = "$pattern" ]; then
                already=1
                break
            fi
        done
        if [ "$already" -eq 0 ]; then
            DIRS+=("$pattern")
        fi
    done
    if [ "${#DIRS[@]}" -eq 0 ]; then
        go test -v ./...
    else
        go test -v "${DIRS[@]}"
    fi
else
    go test -v ./...
fi
