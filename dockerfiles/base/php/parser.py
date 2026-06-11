#!/usr/bin/env python3
import json
import re
import sys


def parse_phpunit_output(text):
    tests = []
    current_method = None
    current_class = None
    summary_line = None
    summary_detected = False

    lines = text.splitlines()

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^Time:.*[0-9].*Memory:.*$", stripped) or re.match(r"^OK \(.+\)$", stripped) or stripped.startswith("FAILURES!") or stripped.startswith("ERRORS!"):
            summary_detected = True
        if re.match(r"^(OK|FAILURES!|ERRORS!)\b", stripped):
            summary_line = stripped
            continue

        class_match = re.match(r"^(.+?)$", stripped)
        if stripped.endswith(":") and idx + 1 < len(lines):
            potential_class = stripped[:-1]
            if re.match(r"^[A-Z][A-Za-z0-9_]*(::[A-Za-z0-9_]+)?$", potential_class) or " " in potential_class:
                current_class = potential_class
                current_method = None
                continue

        m = re.match(r"^\[x\] (.+?)$", stripped)
        if m:
            name = m.group(1).strip()
            tests.append({"name": name, "status": "FAILED"})
            continue
        m = re.match(r"^\[\] (.+?)$", stripped)
        if m:
            name = m.group(1).strip()
            tests.append({"name": name, "status": "PASSED"})
            continue

        if re.match(r"^ ✓ ", stripped):
            name = stripped[2:].strip()
            tests.append({"name": f"{current_class}: {name}" if current_class else name, "status": "PASSED"})
            continue
        if re.match(r"^ ✗ ", stripped):
            name = stripped[2:].strip()
            tests.append({"name": f"{current_class}: {name}" if current_class else name, "status": "FAILED"})
            continue

        if re.match(r"^\d+\) ", stripped):
            current_method = stripped
            continue

    if not tests:
        dots_line = None
        single_chars_line = None
        for line in lines:
            s = line.strip()
            if re.match(r"^[\.EFISRW]+$", s) and len(s) >= 3:
                single_chars_line = s
                break
            if re.match(r"^[0-9]+ / [0-9]+ \(100%\)", s):
                dots_line = line
        if single_chars_line:
            for i, ch in enumerate(single_chars_line):
                status = "PASSED"
                if ch == ".":
                    status = "PASSED"
                elif ch == "F" or ch == "X":
                    status = "FAILED"
                elif ch == "E":
                    status = "ERROR"
                elif ch == "S":
                    status = "SKIPPED"
                elif ch == "I":
                    status = "INCOMPLETE"
                elif ch == "R":
                    status = "RISKY"
                elif ch == "W":
                    status = "WARNING"
                tests.append({"name": f"test_{i+1}", "status": status})

    return tests


def main():
    try:
        text = sys.stdin.read()
    except Exception:
        text = ""

    tests = parse_phpunit_output(text)
    if not tests:
        for line in text.splitlines():
            s = line.strip()
            m = re.match(r"^OK \((\d+) tests?, (\d+) assertions?\)$", s)
            if m:
                total = int(m.group(1))
                for i in range(total):
                    tests.append({"name": f"test_{i+1}", "status": "PASSED"})
                break
            m = re.match(r"^Tests:\s+(\d+),", s)
            if m:
                total = int(m.group(1))
                for i in range(total):
                    tests.append({"name": f"test_{i+1}", "status": "PASSED"})
                break

    print(json.dumps({"tests": tests}, ensure_ascii=False))


if __name__ == "__main__":
    main()
