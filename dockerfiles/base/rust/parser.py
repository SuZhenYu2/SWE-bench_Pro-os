#!/usr/bin/env python3
import sys
import re
import json


def parse_rust_test_output(text):
    tests = []
    lines = text.split("\n")

    test_pattern = re.compile(r"^test\s+(.+?)\s+\.\.\.\s+(ok|FAILED|ignored)$")

    for line in lines:
        match = test_pattern.match(line.strip())
        if match:
            name = match.group(1)
            status_raw = match.group(2)
            if status_raw == "ok":
                status = "PASSED"
            elif status_raw == "FAILED":
                status = "FAILED"
            elif status_raw == "ignored":
                status = "SKIPPED"
            else:
                status = "UNKNOWN"
            tests.append({"name": name, "status": status})

    return {"tests": tests}


def main():
    text = sys.stdin.read()
    result = parse_rust_test_output(text)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
