#!/usr/bin/env python3
import sys
import re
import json


def parse_ruby_test_output(text):
    tests = []
    lines = text.split("\n")

    rspec_example_pattern = re.compile(r"^(\w+.*?)\s+\(FAILED\s+\d+\)$")
    rspec_pattern = re.compile(r"(\d+)\s+examples?,\s+(\d+)\s+failures?(?:,\s+(\d+)\s+pendings?)?")
    minitest_pattern = re.compile(
        r"Finished\s+in\s+[\d.]+\s+seconds[,\s]+(\d+)\s+runs[,\s]+(\d+)\s+assertions[,\s]+(\d+)\s+failures[,\s]+(\d+)\s+errors(?:[,\s]+(\d+)\s+skips)?"
    )

    in_rspec_failures = False

    for line in lines:
        stripped = line.strip()

        if "Failures:" in stripped:
            in_rspec_failures = True
            continue

        if in_rspec_failures:
            if rspec_pattern.search(stripped):
                in_rspec_failures = False
                continue
            if stripped.startswith("  "):
                if ")" in stripped and stripped.count(")") >= 1:
                    match = re.match(r"^\s*\d+\)\s+(.+?)\s*$", stripped)
                    if match:
                        test_name = match.group(1).strip()
                        test_name = re.sub(r"\s*\(FAILED\s+\d+\)\s*$", "", test_name)
                        tests.append({"name": test_name, "status": "FAILED"})
                        continue

        if "PASS" in stripped and "[" in stripped:
            match = re.search(r"\[PASS\]\s+(.+?)\s*$", stripped)
            if match:
                tests.append({"name": match.group(1).strip(), "status": "PASSED"})
                continue

        if "FAIL" in stripped and "[" in stripped:
            match = re.search(r"\[FAIL\]\s+(.+?)\s*$", stripped)
            if match:
                tests.append({"name": match.group(1).strip(), "status": "FAILED"})
                continue

        if "ERROR" in stripped and "[" in stripped:
            match = re.search(r"\[ERROR\]\s+(.+?)\s*$", stripped)
            if match:
                tests.append({"name": match.group(1).strip(), "status": "ERROR"})
                continue

        if "SKIP" in stripped and "[" in stripped:
            match = re.search(r"\[SKIP\]\s+(.+?)\s*$", stripped)
            if match:
                tests.append({"name": match.group(1).strip(), "status": "SKIPPED"})
                continue

    return {"tests": tests}


def main():
    text = sys.stdin.read()
    result = parse_ruby_test_output(text)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
