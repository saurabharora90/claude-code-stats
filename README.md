# Claude Code Stats

A visualization dashboard for your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) usage patterns. Generates a static HTML dashboard from your local `.claude` folder data.

![Dashboard Screenshot](https://via.placeholder.com/800x400?text=Claude+Code+Stats+Dashboard)

## Quick Start

```bash
pip install git+https://github.com/saurabharora90/claude-code-stats.git
claude-stats
```

The dashboard opens automatically in your browser.

To update to the latest version:
```bash
pip install --upgrade git+https://github.com/saurabharora90/claude-code-stats.git
```

## Features

### Core Analytics
- **Activity Timeline**: Track daily messages and sessions over time
- **Date Range Filter**: Filter all charts by custom date range
- **Model Usage**: See token distribution across Sonnet, Opus, and Haiku
- **Peak Hours**: Discover when you're most productive with Claude
- **Project Breakdown**: Identify which projects get the most attention

### Cost & Efficiency
- **Cost Estimation**: Approximate API costs based on token usage
- **Cache Savings**: See how much caching saves you
- **Cache Efficiency**: Track cache hit rates

### Performance
- **Response Time**: View turn duration percentiles (p50, p95, p99)
- **API Reliability**: Track error rates and types
- **Tool Success Rate**: Monitor which tools fail most often

### Productivity
- **Task Completion**: Track todo completion rates
- **Plan Activity**: See how often you use Claude's plan mode

### Deep Dive
- **Tool Usage**: Analyze which tools (Read, Edit, Bash, etc.) you use most
- **MCP Tools**: View usage of Model Context Protocol tools and servers
- **Subagent Analysis**: Track usage of Explore, code-reviewer, Plan agents
- **Extended Thinking**: Monitor thinking token usage
- **File Edit Velocity**: Track file editing patterns
- **Conversation Depth**: Analyze conversation threading patterns

## Installation

### Option 1: pip install from GitHub (Recommended)

```bash
pip install git+https://github.com/saurabharora90/claude-code-stats.git
```

To update:
```bash
pip install --upgrade git+https://github.com/saurabharora90/claude-code-stats.git
```

### Option 2: Clone and Run Locally

```bash
git clone https://github.com/saurabharora90/claude-code-stats.git
cd claude-code-stats
pip install .
claude-stats
```

## Usage

```bash
# Generate dashboard from default ~/.claude folder (auto-opens browser)
claude-stats

# Specify a different .claude folder
claude-stats /path/to/.claude

# Save dashboard to a specific directory
claude-stats --output ./my-dashboard

# Generate only JSON stats (no HTML)
claude-stats --json-only --output ./stats

# Don't auto-open browser
claude-stats --no-open
```

## Options

| Option | Description |
|--------|-------------|
| `CLAUDE_FOLDER` | Path to .claude directory (default: `~/.claude`) |
| `--output, -o` | Output directory for dashboard (default: temp directory) |
| `--open/--no-open` | Auto-open browser after generation (default: `--open`) |
| `--json-only` | Only export stats.json, skip HTML dashboard |

## Requirements

- Python 3.9+
- `click` (installed automatically with pip)

## Privacy

All data processing happens locally. No data is sent anywhere. The generated dashboard is a static HTML file that works completely offline.

## Documentation

- [Metrics Documentation](METRICS.md) - Detailed explanation of all metrics and charts

## Data Sources

The tool reads from these files in your `.claude` folder:

| File | Data Extracted |
|------|----------------|
| `stats-cache.json` | Daily activity, model tokens, session totals, peak hours |
| `projects/*/sessions-index.json` | Per-project session counts and summaries |
| `projects/*/*.jsonl` | Tool calls, turn durations, API errors, thinking blocks |
| `todos/*.json` | Task completion statistics |
| `plans/*.md` | Plan activity |
| `file-history/` | File edit patterns |
| `settings.json` | Enabled plugins |
| `history.jsonl` | Slash command usage |

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT License. See [LICENSE](LICENSE) for details.
