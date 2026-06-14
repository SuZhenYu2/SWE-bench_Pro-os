# compare-models

Compare evaluation results across multiple models and generate reports.

## Usage

```
/compare-models --results <dir> [--threshold <conditions>]
```

## Examples

```
# Compare DeepSeek vs Qwen
/compare-models \
  --results benchmark_final_v3/ \
  --threshold "deepseek:>=5,qwen:>=2"

# Report only (no re-evaluation)
/compare-models --results benchmark_final_v3/ --report-only
```

## How it works

1. Reads all evaluation results from output directory
2. Aggregates per-model statistics:
   - Total runs, passed runs, pass rate
   - API calls per instance, cost per instance
   - Trajectory sizes, completion patterns
3. Checks threshold conditions (e.g., `deepseek:>=5` = deepseek must pass >=5)
4. Generates comparison report in Markdown

## Report Contents

```markdown
| Model | Runs | Passed | Rate | Status |
|-------|------|--------|------|--------|
| deepseek | 8 | 7 | 87.5% | ✅ |
| qwen | 4 | 3 | 75.0% | ❌ threshold not met |
```

## Supported Threshold Operators

- `>=` : greater than or equal
- `>`  : greater than
- `<=` : less than or equal
- `<`  : less than
- `=`  : equal to

## Requirements

- Completed evaluation runs in output directory
- Trajectory files (*.jsonl) with exit_status info
- Log files (*.log) for detailed analysis
