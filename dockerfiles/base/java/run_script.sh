#!/usr/bin/env bash

TEST_FILES="${1:-}"

cd /app || cd "$(pwd)"

run_maven_tests() {
    local files="$1"
    if [ -n "$files" ]; then
        IFS=',' read -ra FILE_ARR <<< "$files"
        local test_list=""
        for f in "${FILE_ARR[@]}"; do
            f=$(echo "$f" | xargs)
            if [ -z "$f" ]; then
                continue
            fi
            base=$(basename "$f" .java)
            base=$(basename "$base" .class)
            base=$(echo "$base" | sed 's|/|.|g; s|\\.|.|g')
            base=$(echo "$base" | sed 's|^.*src\\.|.|')
            base=$(echo "$base" | sed 's|^.*test\\.||')
            if [ -n "$test_list" ]; then
                test_list="${test_list}+${base}"
            else
                test_list="${base}"
            fi
        done
        if [ -n "$test_list" ]; then
            mvn test -Dtest="${test_list}"
        else
            mvn test
        fi
    else
        mvn test
    fi
}

run_gradle_tests() {
    local files="$1"
    if [ -n "$files" ]; then
        IFS=',' read -ra FILE_ARR <<< "$files"
        local tests=""
        for f in "${FILE_ARR[@]}"; do
            f=$(echo "$f" | xargs)
            if [ -z "$f" ]; then
                continue
            fi
            base=$(basename "$f" .java)
            base=$(basename "$base" .class)
            base=$(echo "$base" | sed 's|/|.|g; s|\\.|.|g')
            base=$(echo "$base" | sed 's|^.*src\\.test\\.java\\.||')
            base=$(echo "$base" | sed 's|^.*test\\.||')
            if [ -n "$tests" ]; then
                tests="${tests},${base}"
            else
                tests="${base}"
            fi
        done
        if [ -n "$tests" ]; then
            if [ -f ./gradlew ]; then
                ./gradlew test --tests "${tests}"
            else
                gradle test --tests "${tests}"
            fi
        else
            if [ -f ./gradlew ]; then
                ./gradlew test
            else
                gradle test
            fi
        fi
    else
        if [ -f ./gradlew ]; then
            ./gradlew test
        else
            gradle test
        fi
    fi
}

if [ -f "pom.xml" ]; then
    run_maven_tests "$TEST_FILES"
elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
    run_gradle_tests "$TEST_FILES"
else
    echo "ERROR: Neither pom.xml nor build.gradle(.kts) found in $(pwd)" >&2
    exit 1
fi
