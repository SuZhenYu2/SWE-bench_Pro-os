# eval-model

Run multi-model benchmark evaluations using mini-swe-agent.

## Usage

```
/eval-model <model:runs> [<model:runs> ...] [--parallel]
```

## Examples

```
# Single model, 5 runs
/eval-model deepseek:5

# Multi-model comparison (parallel)
/eval-model deepseek:8 qwen:4 opus:5 --parallel

# With custom input data
/eval-model deepseek:3 --input my_instances/
```

## How it works

1. Reads instances from `test_data_single/instances.csv`
2. For each model, runs mini-swe-agent to generate code patches
3. Each run is independent (files reset before each run)
4. Generates `evaluation_report.md` with pass/fail stats
5. Saves trajectories as `.jsonl` and logs as `.log`

## Supported Models

| Shortcut | Full Name | Provider |
|----------|-----------|----------|
| `deepseek` | DeepSeek v4 Pro | Anthropic-compatible |
| `qwen` | Qwen 3.6 Plus | DashScope (OpenAI-compatible) |
| `opus` | Claude Opus 4.7 | Anthropic |
| `sonnet` | Claude Sonnet 4.6 | Anthropic |
| `haiku` | Claude Haiku 4.5 | Anthropic |
| `gpt4` | GPT-4 | OpenAI |

## Output

```
output_dir/
├── evaluation_report.md     # Summary report
├── <model>/
│   ├── run_1/
│   │   ├── instance_1.jsonl # Trajectory
│   │   └── instance_1.log   # Full log
│   └── run_N/
└── ...
```

## Requirements

- Virtual env: `source venv/bin/activate`
- API keys configured in `~/.config/mini-swe-agent/.env`
- Instance CSV at `test_data_single/instances.csv`
