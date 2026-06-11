#!/usr/bin/env python3
import json
import re
import sys


def parse_dotnet_output(text):
    tests = []
    seen = set()

    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()

        m = re.match(r"^Passed!\s*(.+)$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "PASSED"})
            continue
        m = re.match(r"^Failed!\s*(.+)$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "FAILED"})
            continue
        m = re.match(r"^Skipped\s*(.+)$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "SKIPPED"})
            continue

        m = re.match(r"^! (.+)$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "FAILED"})
            continue

        m = re.match(r"^\s*✓\s+(.+)$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "PASSED"})
            continue
        m = re.match(r"^\s*✗\s+(.+)$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "FAILED"})
            continue

        m = re.match(r"^\s*(.+)\s+\[PASSED\]$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "PASSED"})
            continue
        m = re.match(r"^\s*(.+)\s+\[FAILED\]$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "FAILED"})
            continue
        m = re.match(r"^\s*(.+)\s+\[SKIPPED\]$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "SKIPPED"})
            continue

        m = re.match(r"^(.+)\s+Passed$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "PASSED"})
            continue
        m = re.match(r"^(.+)\s+Failed$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "FAILED"})
            continue
        m = re.match(r"^(.+)\s+Skipped$", stripped)
        if m:
            name = m.group(1).strip()
            if name not in seen:
                seen.add(name)
                tests.append({"name": name, "status": "SKIPPED"})
            continue

    return tests


def _read_file_as_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _parse_fallback(text, tests):
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^(\d+) Passed,\s+(\d+) Failed(?:,\s+(\d+) Skipped)?$", s)
        if m:
            passed = int(m.group(1))
            failed = int(m.group(2))
            skipped = int(m.group(3) or 0)
            idx = 1
            for _ in range(passed):
                tests.append({"name": f"test_{idx}", "status": "PASSED"})
                idx += 1
            for _ in range(failed):
                tests.append({"name": f"test_{idx}", "status": "FAILED"})
                idx += 1
            for _ in range(skipped):
                tests.append({"name": f"test_{idx}", "status": "SKIPPED"})
                idx += 1
            break
        m = re.match(r"^Test Run Successful\b", s)
        if m and not tests:
            tests.append({"name": "test_suite", "status": "PASSED"})
            break
        m = re.match(r"^Test Run Failed\b", s)
        if m and not tests:
            tests.append({"name": "test_suite", "status": "FAILED"})
            break


def main():
    # 统一接口: parser.py <stdout_log_path> <stderr_log_path> <output_json_path>
    # 兼容模式: 未提供参数时回退到 stdin
    if len(sys.argv) >= 4:
        stdout_path = sys.argv[1]
        stderr_path = sys.argv[2]
        output_path = sys.argv[3]
        text = _read_file_as_text(stdout_path) + "\n" + _read_file_as_text(stderr_path)
        tests = parse_dotnet_output(text)
        if not tests:
            _parse_fallback(text, tests)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"tests": tests}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    else:
        try:
            text = sys.stdin.read()
        except Exception:
            text = ""
        tests = parse_dotnet_output(text)
        if not tests:
            _parse_fallback(text, tests)
        print(json.dumps({"tests": tests}, ensure_ascii=False))


if __name__ == "__main__":
    main()
