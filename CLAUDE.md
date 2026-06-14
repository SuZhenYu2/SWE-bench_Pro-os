# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SWE-Bench Pro is a benchmark for evaluating LLMs/agents on long-horizon software engineering tasks. Given a codebase and an issue, models generate patches that are tested against real-world test suites. This repository contains the evaluation infrastructure, multi-language Docker images, and helper scripts for the complete evaluation pipeline.

## Core Evaluation Commands

### Basic Evaluation
```bash
# Evaluate patches against SWE-Bench Pro test suite
python swe_bench_pro_eval.py \
    --raw_sample_path=swe_bench_pro_full.csv \
    --patch_path=<patches>.json \
    --output_dir=<output_dir> \
    --scripts_dir=run_scripts \
    --num_workers=100 \
    --dockerhub_username=jefzda

# Use local Docker instead of Modal (beta)
python swe_bench_pro_eval.py \
    --raw_sample_path=swe_bench_pro_full.csv \
    --patch_path=<patches>.json \
    --output_dir=<output_dir> \
    --use_local_docker
```

### Gather Patches
```bash
# Collect .pred files into a single JSON for evaluation
python helper_code/gather_patches.py \
    --directory <path_to_pred_files> \
    --prefix <model_name> \
    --output <output_file>.json
```

### Extract Gold Patches
```bash
# Extract gold patches from HuggingFace dataset for testing
python helper_code/extract_gold_patches.py
```

## Full Pipeline Scripts

### Multi-Model Evaluation
```bash
# Run multiple models with multiple rounds
python multi_model_evaluator.py \
    --model qwen --runs 4 \
    --model opus --runs 8 \
    --input-dir data/eval \
    --threshold "qwen:<3,opus:>=1"
```

### Complete Evaluation Pipeline
```bash
# Scan GitHub PRs → Fetch patches → Generate instances → Evaluate
python run_evaluation.py --scan --patch --generate --eval

# Quick test with specific languages
python run_evaluation.py --quick --languages python --max-results 50
```

### Streaming Pipeline Evaluation
```bash
# Pipeline processing: scan and evaluate concurrently
python pipeline_evaluator.py \
    --languages python javascript go rust \
    --min-lines 110 --balanced \
    --max-results 100 \
    --output-dir data/eval
```

## Helper Scripts

### Scan GitHub PRs
```bash
python helper_code/scan_github_prs.py \
    --languages python javascript \
    --output prs.jsonl
```

### Fetch PR Patches
```bash
python helper_code/fetch_pr_patch.py \
    --pr-data prs.jsonl \
    --output patches.json
```

### Generate Evaluation Instances
```bash
python helper_code/generate_instances.py \
    --pr-data prs.jsonl \
    --patch-data patches.json \
    --output-dir data/eval
```

## Docker Images

### Multi-Language Support
This repository supports 10+ languages with version-specific Docker images:
- Python: 3.9, 3.10, 3.11, 3.12, 3.13
- JavaScript/TypeScript: node16, node18, node20, node22
- Java: JDK 11, 17, 21
- Go: 1.20, 1.21, 1.22, 1.23
- Rust: stable, nightly
- Ruby: 3.0, 3.1, 3.2, 3.3
- PHP: 7.4, 8.0, 8.1, 8.2, 8.3
- .NET: 6.0, 7.0, 8.0
- C++: gcc11, gcc12, clang16, clang17
- Elixir: 1.14, 1.15, 1.16

### Language Configuration
Language detection and Docker image selection is handled by `dockerfiles/base/language_config.py`, which maps repositories to languages and versions.

### Building Docker Images
```bash
# Build single language
cd dockerfiles/base
./build-one.sh python 3.11

# Build all versions of a language
./build-lang.sh javascript

# Build all languages
./build-all.sh
```

### Image Structure
Each language directory (`dockerfiles/base/{language}/`) contains:
- `Dockerfile` - Base image definition
- `run_script.sh` - Test execution script
- `parser.py` - Test output parser

All images use `debian:bookworm-slim` as the base and include git, patch, curl, and build-essential.

## Architecture

### Evaluation Flow
1. **Input**: CSV file with test instances + JSON file with patches
2. **Detection**: Automatically detect language/version from repo metadata
3. **Docker Selection**: Choose appropriate Docker image and run script
4. **Execution**: Run patch in Modal sandbox or local Docker
5. **Test Execution**: Run language-specific test commands
6. **Result Collection**: Parse test output and calculate pass/fail

### Key Components
- `swe_bench_pro_eval.py` - Main evaluation script with Modal integration
- `multi_model_evaluator.py` - Multi-model comparison framework
- `pipeline_evaluator.py` - Streaming pipeline processor
- `run_evaluation.py` - End-to-end automation script
- `dockerfiles/base/language_config.py` - Language/version configuration
- `helper_code/` - Utility scripts for PR scanning, patch extraction, instance generation

### Data Format

**Input CSV columns**:
- `instance_id` - Unique identifier
- `base_commit` - Git commit hash
- `repo` - Repository name
- `selected_test_files_to_run` - Test files to execute
- `FAIL_TO_PASS` - Tests that should pass after patch
- `PASS_TO_PASS` - Tests that should remain passing
- `before_repo_set_cmd` - Setup commands
- `dockerhub_tag` - Docker image tag (optional)
- `language` - Programming language (optional, auto-detected)

**Patch JSON format**:
```json
[
  {
    "instance_id": "unique_id",
    "patch": "git patch content",
    "prefix": "optional_prefix"
  }
]
```

## Modal vs Local Docker

### Modal (Recommended)
- Cloud-based sandboxed execution
- Parallel processing with `--num_workers`
- Requires `modal setup` with valid credentials in `~/.modal.toml`

### Local Docker (Beta)
- Local Docker execution
- Use `--use_local_docker` flag
- No additional setup beyond Docker installation

## Test Data

The `test_data/` directory contains sample instances and gold patches for testing the evaluation infrastructure. Use these to verify setup before running full evaluations.
