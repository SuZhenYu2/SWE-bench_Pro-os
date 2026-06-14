# verify-patch

Verify that generated patches actually fix the issues by running tests in Docker.

## Usage

```
/verify-patch --patches <patches.json> --instances <instances.csv>
```

## Examples

```
# Verify a single model's patches
/verify-patch \
  --patches benchmark_final_v3/deepseek \
  --instances test_data_single/instances.csv

# Full evaluation with Docker
/verify-patch \
  --patches deepseek_patches.json \
  --instances real_instances.csv \
  --use-docker
```

## How it works

1. Collects generated `.jsonl` trajectory files
2. Extracts code patches from model output
3. Uses `swe_bench_pro_eval.py` to:
   - Apply patches in Docker containers
   - Run test suites (FAIL_TO_PASS + PASS_TO_PASS)
   - Report actual pass/fail per instance
4. Generates evaluation results

## Pipeline

```
Model Patches → gather_patches.py → patches.json
                                      ↓
Instances CSV → swe_bench_pro_eval.py → eval_results.json
                                      ↓
                              evaluation_report.md
```

## Requirements

- Docker installed
- `docker` Python package: `pip install docker`
- Real instances with test configurations
- Valid Docker images for each language/version
