#!/usr/bin/env bash
set -e

TEST_FILES_COMMA="$1"
TEST_FILES_SPACE=$(echo "$TEST_FILES_COMMA" | tr ',' ' ')

cd /app

echo "=== Detecting project type ==="
HAS_SETUP_PY=0
HAS_PYPROJECT=0
HAS_REQUIREMENTS=0

if [ -f setup.py ]; then
    HAS_SETUP_PY=1
    echo "Found: setup.py"
fi
if [ -f pyproject.toml ]; then
    HAS_PYPROJECT=1
    echo "Found: pyproject.toml"
fi
if [ -f requirements.txt ]; then
    HAS_REQUIREMENTS=1
    echo "Found: requirements.txt"
fi

echo "=== Installing dependencies ==="
if [ "$HAS_SETUP_PY" -eq 1 ]; then
    echo "Running: pip install -e ."
    pip install -e . || echo "pip install -e . failed, continuing..."
elif [ "$HAS_PYPROJECT" -eq 1 ]; then
    echo "Running: pip install -e ."
    pip install -e . || echo "pip install -e . failed, continuing..."
fi

if [ "$HAS_REQUIREMENTS" -eq 1 ]; then
    echo "Running: pip install -r requirements.txt"
    pip install -r requirements.txt || echo "pip install -r requirements.txt failed, continuing..."
fi

echo "=== Running tests ==="
if [ -n "$TEST_FILES_SPACE" ]; then
    TARGETS="$TEST_FILES_SPACE"
else
    TARGETS=""
fi

set +e
if command -v pytest >/dev/null 2>&1; then
    echo "Using pytest: pytest $TARGETS"
    pytest $TARGETS
    EXIT_CODE=$?
else
    echo "Using unittest: python -m unittest $TARGETS"
    python -m unittest $TARGETS
    EXIT_CODE=$?
fi
set -e

echo "=== Tests finished with exit code: $EXIT_CODE ==="
exit $EXIT_CODE
