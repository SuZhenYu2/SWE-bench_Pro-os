#!/usr/bin/env python3
"""
Parse test output for marko-js/marko test fixtures.
"""

import sys
import re

def parse_test_output(output: str) -> dict:
    """Parse test output and return results."""
    results = {
        "passed": [],
        "failed": [],
        "errors": []
    }

    # Look for passing tests
    for match in re.finditer(r'✓\s+(\S+)', output):
        results["passed"].append(match.group(1))

    # Look for failing tests
    for match in re.finditer(r'✗\s+(\S+)', output):
        results["failed"].append(match.group(1))

    # Look for errors
    for match in re.finditer(r'Error:\s*(.+)', output):
        results["errors"].append(match.group(1).strip())

    return results

if __name__ == "__main__":
    output = sys.stdin.read()
    results = parse_test_output(output)

    print("=== Test Results ===")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Errors: {len(results['errors'])}")

    if results['failed']:
        print("\nFailed tests:")
        for test in results['failed']:
            print(f"  - {test}")

    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")

    # Exit with error if any tests failed
    if results['failed'] or results['errors']:
        sys.exit(1)
    sys.exit(0)
