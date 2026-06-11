#!/usr/bin/env python3
import re
import sys
import json


def parse_go_output(output):
    tests = []
    current_test = None
    current_package = None

    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue

        run_match = re.match(r'^={3}\s*RUN\s+(.+)$', line)
        if run_match:
            name = run_match.group(1).strip()
            current_test = {'name': name, 'status': 'RUNNING'}
            tests.append(current_test)
            continue

        status_match = re.match(r'^-{3}\s*(PASS|FAIL|SKIP):\s+(.+?)(?:\s+\([0-9.]+s\))?\s*$', line)
        if status_match:
            status_tok = status_match.group(1)
            name = status_match.group(2).strip()
            if status_tok == 'PASS':
                mapped = 'PASSED'
            elif status_tok == 'FAIL':
                mapped = 'FAILED'
            elif status_tok == 'SKIP':
                mapped = 'SKIPPED'
            else:
                mapped = status_tok
            found = False
            for t in tests:
                if t['name'] == name:
                    t['status'] = mapped
                    found = True
                    break
            if not found:
                tests.append({'name': name, 'status': mapped})
            if current_test and current_test['name'] == name:
                current_test = None
            continue

        pkg_ok = re.match(r'^(ok|FAIL)\s+(\S+)', line)
        if pkg_ok:
            continue

        if line.strip() in ('PASS', 'FAIL'):
            continue

        cont_match = re.match(r'^={3}\s+(CONT|PAUSE)\s+(.+)$', line)
        if cont_match:
            continue

    for t in tests:
        if t.get('status') in (None, 'RUNNING'):
            t['status'] = 'UNKNOWN'

    seen = set()
    unique = []
    for t in tests:
        key = (t.get('name'), t.get('status'))
        if key in seen:
            continue
        seen.add(key)
        unique.append(t)

    return {'tests': unique}


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
        data = _read_file_as_text(stdout_path) + "\n" + _read_file_as_text(stderr_path)
        result = parse_go_output(data)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    else:
        try:
            data = sys.stdin.read()
        except Exception:
            data = ''
        result = parse_go_output(data)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
