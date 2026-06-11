#!/usr/bin/env python3
import json
import re
import sys


def parse_logs(stdout_path, stderr_path):
    tests = []

    content_parts = []
    for path in [stdout_path, stderr_path]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content_parts.append(f.read())
        except Exception:
            continue

    content = "\n".join(content_parts)

    pass_patterns = [
        re.compile(r"^\s*✓\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*✔\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*√\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*PASS\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*passing\s+(.+)$", re.MULTILINE),
    ]

    fail_patterns = [
        re.compile(r"^\s*✗\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*✘\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*✕\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*FAIL\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*failing\s+(.+)$", re.MULTILINE),
    ]

    skip_patterns = [
        re.compile(r"^\s*○\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*⊘\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*SKIP\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*skipped\s+(.+)$", re.MULTILINE),
    ]

    found = set()

    for pat in pass_patterns:
        for m in pat.finditer(content):
            name = m.group(1).strip()
            if name and name not in found:
                found.add(name)
                tests.append({"name": name, "status": "PASSED"})

    for pat in fail_patterns:
        for m in pat.finditer(content):
            name = m.group(1).strip()
            if name and name not in found:
                found.add(name)
                tests.append({"name": name, "status": "FAILED"})

    for pat in skip_patterns:
        for m in pat.finditer(content):
            name = m.group(1).strip()
            if name and name not in found:
                found.add(name)
                tests.append({"name": name, "status": "SKIPPED"})

    if not tests:
        error_pattern = re.compile(r"^\s*(?:Error|error|FAILED|fail):\s+(.+)$", re.MULTILINE | re.IGNORECASE)
        for m in error_pattern.finditer(content):
            name = m.group(1).strip()
            if name:
                tests.append({"name": name, "status": "ERROR"})

    return tests


def main():
    if len(sys.argv) < 4:
        print("Usage: parser.py <stdout_log_path> <stderr_log_path> <output_json_path>", file=sys.stderr)
        sys.exit(1)

    stdout_path = sys.argv[1]
    stderr_path = sys.argv[2]
    output_path = sys.argv[3]

    try:
        tests = parse_logs(stdout_path, stderr_path)
    except Exception:
        tests = []

    result = {"tests": tests}

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


if __name__ == "__main__":
    main()
