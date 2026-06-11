#!/usr/bin/env python3
import sys
import re
import json


def parse_cpp_test_output(text):
    tests = []
    lines = text.split("\n")

    gtest_run_pattern = re.compile(r"^\[\s*RUN\s*\]\s+(.+?)\s*$")
    gtest_ok_pattern = re.compile(r"^\[\s*OK\s*\]\s+(.+?)\s*\(\d+\s*ms\)\s*$")
    gtest_failed_pattern = re.compile(r"^\[\s*FAILED\s*\]\s+(.+?)\s*\(\d+\s*ms\)\s*$")
    gtest_summary_pattern = re.compile(r"\[\s*PASSED\s*\]\s+(\d+)\s+tests?\.")
    ctest_pass_pattern = re.compile(r"^\s*\d+/\d+\s+Test\s+#\d+:\s+(.+?)\s+\.{3,}\s+Passed\s+\d+\.\d+\s+sec")
    ctest_fail_pattern = re.compile(r"^\s*\d+/\d+\s+Test\s+#\d+:\s+(.+?)\s+\.{3,}\s+\*{0,}Failed\s+\*{0,}\s+\d+\.\d+\s+sec")
    ctest_summary_pattern = re.compile(r"(\d+)%\s+tests?\s+passed,\s+(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)")

    current_test = None

    for line in lines:
        stripped = line.strip()

        run_match = gtest_run_pattern.match(stripped)
        if run_match:
            current_test = run_match.group(1).strip()
            continue

        ok_match = gtest_ok_pattern.match(stripped)
        if ok_match:
            test_name = ok_match.group(1).strip()
            tests.append({"name": test_name, "status": "PASSED"})
            if current_test == test_name:
                current_test = None
            continue

        failed_match = gtest_failed_pattern.match(stripped)
        if failed_match:
            test_name = failed_match.group(1).strip()
            tests.append({"name": test_name, "status": "FAILED"})
            if current_test == test_name:
                current_test = None
            continue

        ctest_pass_match = ctest_pass_pattern.match(stripped)
        if ctest_pass_match:
            tests.append({"name": ctest_pass_match.group(1).strip(), "status": "PASSED"})
            continue

        ctest_fail_match = ctest_fail_pattern.match(stripped)
        if ctest_fail_match:
            tests.append({"name": ctest_fail_match.group(1).strip(), "status": "FAILED"})
            continue

    if current_test:
        tests.append({"name": current_test, "status": "UNKNOWN"})

    return {"tests": tests}


def _read_file_as_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def main():
    # 统一接口: parser.py <stdout_log_path> <stderr_log_path> <output_json_path>
    # 兼容模式: 未提供参数时回退到 stdin
    if len(sys.argv) >= 4:
        stdout_path = sys.argv[1]
        stderr_path = sys.argv[2]
        output_path = sys.argv[3]
        text = _read_file_as_text(stdout_path) + "\n" + _read_file_as_text(stderr_path)
        result = parse_cpp_test_output(text)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    else:
        text = sys.stdin.read()
        result = parse_cpp_test_output(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
