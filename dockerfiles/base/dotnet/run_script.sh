#!/bin/bash
set -e

cd "${1:-/app}"

PROJECT=""
if ls *.sln 1>/dev/null 2>&1; then
    PROJECT=$(ls *.sln | head -n 1)
    echo "Using solution: $PROJECT"
elif ls *.csproj 1>/dev/null 2>&1; then
    PROJECT=$(ls *.csproj | head -n 1)
    echo "Using project: $PROJECT"
else
    echo "No .sln or .csproj found"
    exit 0
fi

echo "Running dotnet restore..."
dotnet restore "$PROJECT"

EXTRA_ARGS=""
if [ -n "$2" ]; then
    IFS=',' read -ra FILES <<< "$2"
    FILTERS=""
    for f in "${FILES[@]}"; do
        name=$(basename "$f" .cs)
        if [ -n "$FILTERS" ]; then
            FILTERS="${FILTERS}|"
        fi
        FILTERS="${FILTERS}${name}"
    done
    EXTRA_ARGS="--filter=${FILTERS}"
fi

echo "Running dotnet test..."
dotnet test "$PROJECT" --no-restore --logger "console;verbosity=detailed" ${EXTRA_ARGS} || true
