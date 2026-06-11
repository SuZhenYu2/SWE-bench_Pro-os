#!/bin/bash
set -e

cd /app

if [ ! -f "Gemfile" ]; then
    echo "Error: Gemfile not found in /app"
    exit 1
fi

echo "=== Running bundle install ==="
bundle install

TEST_FILES=""
if [ -n "$1" ]; then
    IFS=',' read -ra FILES <<< "$1"
    for FILE in "${FILES[@]}"; do
        TEST_FILES="${TEST_FILES} ${FILE}"
    done
    TEST_FILES=$(echo "$TEST_FILES" | xargs)
fi

if [ -d "spec" ] || ls *_spec.rb 1>/dev/null 2>&1; then
    echo "=== Running RSpec ==="
    if [ -n "$TEST_FILES" ]; then
        bundle exec rspec $TEST_FILES 2>&1
    else
        bundle exec rspec spec/ 2>&1
    fi
elif [ -d "test" ] || ls *_test.rb 1>/dev/null 2>&1; then
    echo "=== Running Minitest ==="
    if [ -f "Rakefile" ]; then
        bundle exec rake test 2>&1
    else
        if [ -n "$TEST_FILES" ]; then
            ruby -Ilib:test $TEST_FILES 2>&1
        else
            ruby -Ilib:test test/**/*_test.rb 2>&1
        fi
    fi
else
    echo "Error: No spec/ or test/ directories found"
    exit 1
fi
