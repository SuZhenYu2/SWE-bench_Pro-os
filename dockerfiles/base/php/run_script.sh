#!/bin/bash
set -e

cd "${1:-/app}"

if [ -f "composer.json" ]; then
    echo "Detected composer.json, installing dependencies..."
    composer install --no-interaction
else
    echo "No composer.json found, skipping install."
fi

EXTRA_ARGS=""
if [ -n "$2" ]; then
    IFS=',' read -ra FILES <<< "$2"
    FILTERS=""
    for f in "${FILES[@]}"; do
        name=$(basename "$f" .php)
        if [ -n "$FILTERS" ]; then
            FILTERS="${FILTERS}|"
        fi
        FILTERS="${FILTERS}${name}"
    done
    EXTRA_ARGS="--filter=${FILTERS}"
fi

if [ -f "bin/phpunit" ]; then
    PHPUNIT_CMD="php bin/phpunit"
elif [ -f "vendor/bin/phpunit" ]; then
    PHPUNIT_CMD="./vendor/bin/phpunit"
elif command -v phpunit >/dev/null 2>&1; then
    PHPUNIT_CMD="phpunit"
else
    echo "PHPUnit not found"
    exit 1
fi

if [ -f "phpunit.xml" ] || [ -f "phpunit.xml.dist" ] || [ -d "tests" ]; then
    echo "Running PHPUnit..."
    ${PHPUNIT_CMD} --testdox ${EXTRA_ARGS} || true
else
    echo "No phpunit configuration or tests/ directory found"
    exit 0
fi
