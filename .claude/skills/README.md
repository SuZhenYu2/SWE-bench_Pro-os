# SWE-Bench Pro Skills

Model evaluation pipeline for long-horizon software engineering tasks.

## Skills

| Skill | Command | What it does |
|-------|---------|-------------|
| **Setup Environment** | `/setup-env` | Install deps, configure API keys, verify connectivity |
| **Find PRs** | `/find-prs` | Discover & filter GitHub PRs (blacklist, lines, files) |
| **Evaluate Models** | `/eval-model` | Run multi-model benchmarks with mini-swe-agent |
| **Verify Patches** | `/verify-patch` | Test generated patches in Docker containers |
| **Compare Models** | `/compare-models` | Aggregate results, generate comparison reports |

## Quick Start

```
/setup-env --check        # 1. Verify environment
/find-prs                 # 2. Discover PRs to evaluate
/eval-model deepseek:8 qwen:4 --parallel  # 3. Run benchmark
/compare-models           # 4. Compare results
```

## Workflow

```
setup-env → find-prs → eval-model → compare-models
                              ↓
                        verify-patch (Docker)
```

## Supported Models

| Model | Provider | Use with `/eval-model` |
|-------|----------|----------------------|
| DeepSeek v4 Pro | Anthropic-compatible | `deepseek:N` |
| Qwen 3.6 Plus | DashScope | `qwen:N` |
| Claude Opus 4.7 | Anthropic | `opus:N` |
| Claude Sonnet 4.6 | Anthropic | `sonnet:N` |
| Claude Haiku 4.5 | Anthropic | `haiku:N` |
| GPT-4 | OpenAI | `gpt4:N` |

## Key Files

- `multi_model_evaluator.py` — Core evaluation engine
- `fetch_prs.sh` — PR discovery & filtering
- `swe_bench_pro_eval.py` — Docker-based patch verification
- `pipeline_evaluator.py` — End-to-end automation
- `mini-swe-agent/` — AI agent (git submodule)
- `test_data_single/` — Test instance (login security fix)
