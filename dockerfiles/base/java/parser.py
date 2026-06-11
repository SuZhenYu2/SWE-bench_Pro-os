#!/usr/bin/env python3
import re
import sys
import json


def parse_java_output(output):
    tests = []

    line_by_line_tests = []

    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue

        running_match = re.search(r'Running\s+([A-Za-z0-9_.\-$]+)', line)
        if running_match:
            class_name = running_match.group(1)
            line_by_line_tests.append({
                'name': class_name,
                'status': None,
            })
            continue

        gradle_test_match = re.search(r'Test\s+([A-Za-z0-9_.\-$]+\.[A-Za-z0-9_.\-$]+)\s+(FAILED|PASSED|SKIPPED|STARTED)', line)
        if gradle_test_match:
            test_name = gradle_test_match.group(1)
            status = gradle_test_match.group(2)
            if status == 'FAILED':
                mapped = 'FAILED'
            elif status == 'SKIPPED':
                mapped = 'SKIPPED'
            elif status == 'STARTED':
                mapped = 'RUNNING'
            else:
                mapped = 'PASSED'
            tests.append({'name': test_name, 'status': mapped})
            continue

        gradle_class_match = re.search(r'(\S+)\s+>\s+(\S+)\s+(FAILED|PASSED|SKIPPED)', line)
        if gradle_class_match:
            cls = gradle_class_match.group(1)
            mth = gradle_class_match.group(2)
            status = gradle_class_match.group(3)
            if status == 'FAILED':
                mapped = 'FAILED'
            elif status == 'SKIPPED':
                mapped = 'SKIPPED'
            else:
                mapped = 'PASSED'
            tests.append({'name': f'{cls}.{mth}', 'status': mapped})
            continue

        junit_individual = re.search(r'\[\s*(PASS|FAIL|SKIP)\s*\]\s+([A-Za-z0-9_.\-$]+)', line)
        if junit_individual:
            status_tok = junit_individual.group(1)
            name = junit_individual.group(2)
            if status_tok == 'PASS':
                mapped = 'PASSED'
            elif status_tok == 'FAIL':
                mapped = 'FAILED'
            elif status_tok == 'SKIP':
                mapped = 'SKIPPED'
            else:
                mapped = status_tok
            tests.append({'name': name, 'status': mapped})
            continue

        summary_match = re.search(
            r'Tests\s+run:\s+(\d+),\s+Failures:\s+(\d+),\s+Errors:\s+(\d+)(?:,\s+Skipped:\s+(\d+))?',
            line,
        )
        if summary_match and line_by_line_tests:
            total = int(summary_match.group(1))
            failures = int(summary_match.group(2))
            errors = int(summary_match.group(3))
            skipped = int(summary_match.group(4) or 0)
            passed = total - failures - errors - skipped
            if len(line_by_line_tests) == 1:
                single = line_by_line_tests[-1]
                if failures > 0 or errors > 0:
                    single['status'] = 'FAILED'
                elif skipped > 0 and passed == 0:
                    single['status'] = 'SKIPPED'
                else:
                    single['status'] = 'PASSED'
            continue

        if 'FAILURE!' in line or 'BUILD FAILURE' in line:
            for t in line_by_line_tests:
                if t['status'] is None:
                    t['status'] = 'FAILED'
            continue
        if 'BUILD SUCCESS' in line or 'BUILD SUCCESSFUL' in line:
            for t in line_by_line_tests:
                if t['status'] is None:
                    t['status'] = 'PASSED'
            continue

    for t in line_by_line_tests:
        if t['status'] is None:
            t['status'] = 'UNKNOWN'
        tests.append(t)

    seen = set()
    unique = []
    for t in tests:
        key = (t.get('name'), t.get('status'))
        if key in seen:
            continue
        seen.add(key)
        unique.append(t)

    return {'tests': unique}


def main():
    try:
        data = sys.stdin.read()
    except Exception:
        data = ''
    result = parse_java_output(data)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
