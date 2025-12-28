# GitHub PRD Agent Example

This example demonstrates using Sentinel to generate a PRD and Launch Plan from a GitHub milestone.

## Prerequisites

1. Set `OPENAI_API_KEY` environment variable
2. (Optional) Set `GITHUB_TOKEN` for higher GitHub API rate limits

## Example Usage

### Fetch milestone data

```bash
sentinel fetch --repo microsoft/vscode --milestone "January 2024"
```

### Run agent

```bash
sentinel run --repo microsoft/vscode --milestone "January 2024"
```

### View results

```bash
# View latest run
ls -la runs/latest/

# View report
cat runs/latest/reports/report.md

# View trace events
head -20 runs/latest/trace/events.jsonl
```

## Expected Output

After running, you should see:

- `runs/<run_id>/artifacts/PRD.md` - Generated PRD
- `runs/<run_id>/artifacts/LAUNCH_PLAN.md` - Generated launch plan
- `runs/<run_id>/reports/report.md` - Summary report
- `runs/<run_id>/trace/events.jsonl` - All trace events (≥50 events)
- `runs/<run_id>/packets/packet_0.md` - Escalation packet (if triggered)

## Understanding the Output

The report will show:
- Number of LLM calls made
- Number of tool calls executed
- Interventions issued by supervisor
- Uncovered claims (HIGH severity claims without evidence)
- Evidence bindings

## Troubleshooting

- **No artifacts generated**: Check that agent completed successfully (check trace events)
- **Many uncovered claims**: This is expected if evidence is sparse - supervisor will intervene
- **Escalation packet generated**: This means ≥3 HIGH claims are uncovered or agent made >50 tool calls with little progress
