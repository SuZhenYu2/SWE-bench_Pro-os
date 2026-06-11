#!/bin/bash
set -e

cd "${1:-/app}"

if [ ! -f "mix.exs" ]; then
    echo "No mix.exs found"
    exit 0
fi

echo "Setting up mix dependencies..."
mix local.rebar --force
mix local.hex --force
mix deps.get

if [ -n "$2" ]; then
    IFS=',' read -ra FILES <<< "$2"
    echo "Running mix test for specific files: $2"
    for f in "${FILES[@]}"; do
        if [ -f "$f" ]; then
            mix test --trace "$f" || true
        fi
    done
else
    echo "Running mix test..."
    mix test --trace || true
fi
