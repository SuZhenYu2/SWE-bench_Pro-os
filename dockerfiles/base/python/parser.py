#!/usr/bin/env python3
import json
import re
import sys


def parse_pytest_output(stdout_path, stderr_path):
    tests = []

    def add_tests_from_text(text):
        for line in text.splitlines():
            line = line.strip()
            m = re.match(r'^([A-Za-z0-9_\-\./]+::[A-Za-z0-9_]+(?:\s*\[[^\]]+\])?)\s+(PASSED|FAILED|ERROR|SKIPPED)', line)
            if m:
                tests.append({"name": m.group(1), "status": m.group(2)})

    try:
        with open(stdout_path, "r", encoding="utf-8", errors="replace") as f:
            add_tests_from_text(f.read())
    except Exception:
        pass

    if not tests:
        try:
            with open(stderr_path, "r", encoding="utf-8", errors="replace") as f:
                add_tests_from_text(f.read())
        except Exception:
            pass

    if not tests:
        try:
            with open(stdout_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for line in content.splitlines():
                line = line.strip()
                if re.match(r'^[A-Za-z0-9_\-\./]+::[A-Za-z0-9_]+', line):
                    status_match = re.search(r'(PASSED|FAILED|ERROR|SKIPPED)', line)
                    name_match = re.match(r'^([A-Za-z0-9_\-\./]+::[A-Za-z0-9_]+(?:\s*\[[^\]]+\])?)', line)
                    if status_match and name_match:
                        tests.append({"name": name_match.group(1), "status": status_match.group(1)})
        except Exception:
            pass

    return tests


def main():
    if len(sys.argv) < 4:
        print("Usage: parser.py <stdout_log_path> <stderr_log_path> <output_json_path>", file=sys.stderr)
        json.dump({"tests": []}, sys.stdout)
        sys.exit(0)

    stdout_path = sys.argv[1]
    stderr_path = sys.argv[2]
    output_path = sys.argv[3]

    try:
        tests = parse_pytest_output(stdout_path, stderr_path)
        result = {"tests": tests}
    except Exception:
        result = {"tests": []}

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


if __name__ == "__main__":
    main()
