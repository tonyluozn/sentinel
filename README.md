# sentinel

Runtime supervision for long-running AI agents. Decision boundaries, evidence binding, and minimal human escalation.

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

**Required: OpenAI API Key**
```bash
export OPENAI_API_KEY="sk-your-openai-api-key-here"
```
Get it from: https://platform.openai.com/api-keys

**Optional: GitHub Token** (recommended for higher rate limits)
```bash
export GITHUB_TOKEN="ghp_your-github-token-here"
```
Get it from: https://github.com/settings/tokens (select `public_repo` scope)

**To make keys persistent**, add the `export` commands to your shell profile:
- `~/.zshrc` (macOS/Linux with zsh)
- `~/.bashrc` (Linux with bash)
- `~/.config/fish/config.fish` (Fish shell)

Then reload: `source ~/.zshrc`

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
