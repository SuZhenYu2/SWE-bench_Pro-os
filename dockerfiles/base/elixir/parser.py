#!/usr/bin/env python3
import json
import re
import sys


def parse_exunit_output(text):
    tests = []
    current_describe = None

    lines = text.splitlines()

    pending_name = None

    for idx, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("describe ") and stripped.endswith(":"):
            current_describe = stripped[len("describe "):-1].strip()
            continue

        m = re.match(r"^  (.+?) \((\d+\.\d+)s\)$", line)
        if m:
            pending_name = m.group(1).strip()
            continue

        m = re.match(r"^  (.+)$", line)
        if m and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            nm = re.match(r"^    (.+?) \((\d+\.\d+)s\)$", next_line)
            if not nm:
                pass

        if stripped.startswith("*"):
            m = re.match(r"^\*\s+\*\*(.+?)\*\*\s*:\s*(.+)$", stripped)
            if m:
                name = m.group(2).strip()
                if pending_name:
                    name = pending_name
                full_name = f"{current_describe}: {name}" if current_describe else name
                tests.append({"name": full_name, "status": "FAILED"})
                pending_name = None
            continue

        if re.match(r"^\.{2,}$", stripped) and " " not in stripped:
            for ch in stripped:
                status = char_to_status(ch)
                tests.append({"name": f"test_{len(tests)+1}", "status": status})
            pending_name = None
            continue

        if len(stripped) == 1 and stripped in ".1?HST":
            status = char_to_status(stripped)
            name = pending_name or f"test_{len(tests)+1}"
            full_name = f"{current_describe}: {name}" if current_describe else name
            tests.append({"name": full_name, "status": status})
            pending_name = None
            continue

        m = re.match(r"^\s*\d+\) (.+?)$", stripped)
        if m:
            name = m.group(1).strip()
            full_name = f"{current_describe}: {name}" if current_describe else name
            tests.append({"name": full_name, "status": "FAILED"})
            pending_name = None
            continue

    return tests


def char_to_status(ch):
    if ch == ".":
        return "PASSED"
    if ch == "1":
        return "FAILED"
    if ch == "?":
        return "INVALID"
    if ch == "H":
        return "EXCLUDED"
    if ch == "S":
        return "SKIPPED"
    if ch == "T":
        return "TIMEOUT"
    return "UNKNOWN"


def _read_file_as_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _parse_fallback(text, tests):
    for line in text.splitlines():
        s = line.strip()
        m = re.match(
            r"^Finished in [\d.]+ seconds?\s*\((\d+) tests?, (\d+) failures?(?:, (\d+) skipped?)?\)$", s
        )
        if not m:
            m = re.match(r"^(\d+) tests?, (\d+) failures?(?:, (\d+) skipped?)?$", s)
        if m:
            total = int(m.group(1))
            failures = int(m.group(2))
            skipped = int(m.group(3) or 0)
            passed = total - failures - skipped
            idx = 1
            for _ in range(passed):
                tests.append({"name": f"test_{idx}", "status": "PASSED"})
                idx += 1
            for _ in range(failures):
                tests.append({"name": f"test_{idx}", "status": "FAILED"})
                idx += 1
            for _ in range(skipped):
                tests.append({"name": f"test_{idx}", "status": "SKIPPED"})
                idx += 1
            break


def main():
    # 统一接口: parser.py <stdout_log_path> <stderr_log_path> <output_json_path>
    # 兼容模式: 未提供参数时回退到 stdin
    if len(sys.argv) >= 4:
        stdout_path = sys.argv[1]
        stderr_path = sys.argv[2]
        output_path = sys.argv[3]
        text = _read_file_as_text(stdout_path) + "\n" + _read_file_as_text(stderr_path)
        tests = parse_exunit_output(text)
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
        tests = parse_exunit_output(text)
        if not tests:
            _parse_fallback(text, tests)
        print(json.dumps({"tests": tests}, ensure_ascii=False))


if __name__ == "__main__":
    main()
