# setup-env

Setup or verify the evaluation environment for SWE-bench Pro.

## Usage

```
/setup-env [--check] [--install] [--config]
```

## Examples

```
# Check current setup
/setup-env --check

# Full setup
/setup-env --install --config

# Quick verify API connectivity
/setup-env --check --api
```

## What it does

### --check
- Verify virtual environment exists and is active
- Check all Python dependencies
- Verify mini-swe-agent installation
- Test API connectivity (DeepSeek, DashScope, Anthropic)
- Check GitHub token validity

### --install
- Create virtual environment if missing
- Install all dependencies from `requirements.txt`
- Install mini-swe-agent from submodule
- Install `modal` and `docker` packages

### --config
- Verify `~/.config/mini-swe-agent/.env` exists
- Check API keys are set:
  - `ANTHROPIC_API_KEY` (for DeepSeek/Claude)
  - `DASHSCOPE_API_KEY` (for Qwen)
- Validate API key formats
- Test each API endpoint

## Environment Variables

```
ANTHROPIC_API_KEY=sk-...        # DeepSeek/Claude API key
DASHSCOPE_API_KEY=sk-...        # Qwen API key (DashScope)
ANTHROPIC_BASE_URL=https://...  # Optional: API proxy/base URL
```

## Requirements

- Python 3.10+
- Git (for submodules)
- pip (for package installation)
