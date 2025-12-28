# Quick Start Guide

Get Sentinel running in 3 steps:

## 1. Install Dependencies

```bash
cd /Users/zeningluo/github/sentinel
pip install -e .
```

This installs:
- `requests` - GitHub API client
- `openai` - LLM API client  
- `pydantic` - Data validation
- `python-dateutil` - Date parsing

## 2. Set API Keys

**Easiest: Use .env file**

```bash
# Copy example file
cp .env.example .env

# Edit .env and add your keys:
# OPENAI_API_KEY=sk-your-actual-key-here
# GITHUB_TOKEN=ghp_your-actual-token-here
```

**Or use environment variables:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
export GITHUB_TOKEN="ghp_your-token-here"
```

## 3. Run Your First Command

```bash
# Test the CLI
sentinel --help

# Fetch milestone data (no API key needed)
sentinel fetch --repo microsoft/vscode --milestone "On Deck"

# Run full pipeline (requires OPENAI_API_KEY)
sentinel run --repo microsoft/vscode --milestone "On Deck"
```

## Verify Installation

```bash
# Check imports work
python3 -c "import sentinel; print('✓ Sentinel installed')"

# Check CLI works
sentinel --help
```

## Expected Output

After running `sentinel run`, you should see:

```
✓ Run completed: 20250115_143022
  Artifacts: 2
  Events: 50+
  Interventions: 0-3
  Uncovered claims: 0-5

  Report: runs/20250115_143022/reports/report.md
  Trace: runs/20250115_143022/trace/events.jsonl
```

Check the results:
```bash
# View report
cat runs/latest/reports/report.md

# View artifacts
ls -la runs/latest/artifacts/

# View trace (first 10 events)
head -10 runs/latest/trace/events.jsonl | jq .
```

## Troubleshooting

**"No module named 'pydantic'"**
→ Run `pip install -e .` to install dependencies

**"OPENAI_API_KEY environment variable not set"**
→ Set it: `export OPENAI_API_KEY="sk-your-key"`

**"Rate limit exceeded" (GitHub)**
→ Set `GITHUB_TOKEN` for higher rate limits

**Import errors**
→ Make sure you're in the project directory and ran `pip install -e .`

## Next Steps

- Read [SETUP.md](SETUP.md) for detailed setup
- Read [README.md](README.md) for usage examples
- Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for architecture details


