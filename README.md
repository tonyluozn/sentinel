# sentinel

Runtime supervision for long-running AI agents. Decision boundaries, evidence binding, and minimal human escalation.

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Set API key
export OPENAI_API_KEY="sk-your-key-here"

# 3. Run
sentinel run --repo owner/repo --milestone "v1.0.0"
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

## Overview

Sentinel provides runtime supervision for AI agents that make tool calls and run for extended periods. It monitors agent behavior in real-time, detects decision boundaries, extracts claims from generated artifacts, binds evidence, and generates interventions when needed.

## Features

- **Trace-first event logging**: All agent actions are logged as structured events
- **Decision boundary detection**: Identifies critical decision points during agent execution
- **Claim extraction + evidence binding**: Extracts claims from artifacts and binds supporting evidence
- **Surgical interventions**: Generates actionable "next steps" when issues are detected
- **Optional escalation packets**: Creates minimal human review packets when escalation is needed

## Installation

```bash
# Install in development mode
pip install -e .

# Or install dependencies directly
pip install requests openai pydantic python-dateutil
```

## Setup

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Set API Keys

**Option A: Use .env file (Recommended)**

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your keys:
   ```bash
   OPENAI_API_KEY=sk-your-actual-key-here
   GITHUB_TOKEN=ghp_your-actual-token-here
   ```

The `.env` file is automatically loaded when you import sentinel.

**Option B: Environment variables**

```bash
export OPENAI_API_KEY="sk-your-openai-api-key-here"
export GITHUB_TOKEN="ghp_your-github-token-here"
```

**Getting Your Keys:**
- OpenAI API Key: https://platform.openai.com/api-keys (Required)
- GitHub Token: https://github.com/settings/tokens (Optional, select `public_repo` scope)

See [SETUP.md](SETUP.md) for detailed setup instructions and troubleshooting.

## Usage

### Fetch GitHub milestone data

```bash
sentinel fetch --repo owner/repo --milestone "v1.0.0"
```

### Run agent with supervisor

```bash
sentinel run --repo owner/repo --milestone "v1.0.0"
```

This will:
1. Fetch milestone data from GitHub (or use cache)
2. Run LLM-based agent to generate PRD and Launch Plan
3. Monitor agent with supervisor (detects boundaries, extracts claims, binds evidence)
4. Generate interventions if needed
5. Create escalation packets if thresholds are exceeded
6. Generate final report

### Generate report

```bash
sentinel report --run-id 20250115_143022
```

## Output Structure

```
runs/
  <run_id>/
    trace/
      events.jsonl          # All trace events
    artifacts/
      PRD.md                # Generated PRD
      LAUNCH_PLAN.md        # Generated launch plan
    reports/
      report.md             # Summary report
    packets/
      packet_0.md           # Escalation packet (if generated)
  latest -> <run_id>/       # Symlink to latest run
```

## Testing

```bash
# Run smoke test
pytest tests/test_smoke.py -v
```

## Architecture

See `docs/ARCHITECTURE.md` for detailed architecture documentation.

## License

MIT
