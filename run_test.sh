#!/bin/bash
set -e

# Run specific test fixture for lifecycle-pagehide
cd /workspace/marko-repo/packages/runtime-tags

# Run the specific test
npm test -- --grep "lifecycle-pagehide" 2>&1 || true

# Also run all lifecycle tests to ensure no regression
npm test -- --grep "lifecycle-tag" 2>&1 || true
