# Metrics Documentation

This document explains all the metrics and charts displayed in the Claude Code Stats dashboard.

## Overview Stats Cards

### Sessions
The total number of Claude Code sessions you've started. A session begins when you start a new conversation with Claude Code and ends when you close the terminal or start a new conversation.

### Messages
The total number of messages exchanged with Claude (both your prompts and Claude's responses).

### Tool Calls
The total number of tool invocations Claude made (Read, Edit, Bash, Glob, Grep, etc.).

### Projects
The number of unique directories/projects where you've used Claude Code.

### Est. Cost
An estimate of your total API costs based on token usage. This is calculated using Anthropic's published API pricing (not actual billing data). See the Cost & Efficiency section for pricing details.

### Cache Savings
An estimate of how much money caching has saved you. When Claude re-reads context it has seen before, it uses cached tokens at a 90% discount.

---

## Core Analytics Section

### Daily Activity Chart
A line chart showing your usage patterns over time:
- **Messages** (orange line, left axis): Number of messages exchanged per day
- **Sessions** (purple line, right axis): Number of sessions started per day

Use the date range filter at the top to focus on specific time periods.

### Model Usage Chart
A doughnut chart showing the distribution of output tokens across different Claude models:
- **Opus**: Most capable model, highest cost
- **Sonnet**: Balanced capability and cost (default)
- **Haiku**: Fastest and most economical

### Peak Hours Chart
A bar chart showing when you typically start sessions, broken down by hour of day (0-23). Helps identify your most productive coding hours with Claude.

### Token Usage Over Time
A stacked area chart showing daily token consumption by model. Useful for tracking usage trends and identifying spikes.

### Top Projects
A horizontal bar chart of your most active projects ranked by message count. Project names are derived from directory paths.

### Subagent Usage
A doughnut chart showing the distribution of subagent types used:
- **Explore**: Quick codebase exploration
- **Plan**: Architecture and implementation planning
- **code-reviewer**: Code review tasks
- **Bash**: Command execution
- And other specialized agents

### Top Tools
A horizontal bar chart of the most frequently used built-in tools:
- **Read**: Reading file contents
- **Edit**: Modifying existing files
- **Write**: Creating new files
- **Bash**: Running shell commands
- **Glob**: Finding files by pattern
- **Grep**: Searching file contents
- **Task**: Spawning subagents
- And others

### MCP Tools
A horizontal bar chart of Model Context Protocol tool usage. MCP tools are external integrations (like Linear, Xcode Build, etc.) that extend Claude's capabilities.

### MCP Servers
A doughnut chart showing the distribution of calls across different MCP servers.

### Slash Commands
A horizontal bar chart of your most-used slash commands:
- `/commit`: Git commit workflow
- `/review`: Code review
- `/help`: Getting help
- And custom commands

### User Installed Plugins
A list of plugins you've installed, with enabled plugins highlighted in green.

---

## Cost & Efficiency Section

### Pricing Note
Costs are estimated using Anthropic's API pricing (per 1 million tokens):

| Model | Input | Output | Cache Read | Cache Write |
|-------|-------|--------|------------|-------------|
| Sonnet | $3.00 | $15.00 | $0.30 | $3.75 |
| Opus | $15.00 | $75.00 | $1.50 | $18.75 |
| Haiku | $0.25 | $1.25 | $0.03 | $0.30 |

These are estimates based on token counts, not actual billing data.

### Cost by Model Chart
A doughnut chart showing how your estimated costs break down by model. Opus is significantly more expensive than Sonnet.

### Cache Efficiency Chart
A doughnut chart showing the ratio of cache hits (tokens read from cache) vs cache misses (tokens that needed to be processed fresh). Higher cache hit rates mean better efficiency and lower costs.

---

## Performance Section

### Response Time (Turn Duration) Chart
A line chart showing Claude's response times over time:
- **Average**: Mean response time per day
- **P50**: Median response time (50th percentile)
- **P95**: 95th percentile response time

Higher percentiles help identify occasional slow responses that might not show up in averages.

### API Reliability Chart
A bar chart showing API errors by type:
- **overloaded_error**: Anthropic's servers were busy
- **rate_limit_error**: You hit rate limits
- **Other errors**: Network issues, timeouts, etc.

Fewer errors = more reliable experience. Some errors are expected during peak usage.

### Tool Success Rate Chart
A stacked bar chart showing success vs error rates for tools that have failed at least once. Tools with 100% success rates are not shown (they're working fine).

Common failure reasons:
- **Bash**: Command returned non-zero exit code
- **Read**: File not found
- **Edit**: Failed to match text for replacement

---

## Productivity Section

### Task Completion Chart
A doughnut chart showing the status of all tasks Claude has tracked for you:
- **Completed** (green): Tasks marked as done
- **In Progress** (orange): Currently being worked on
- **Pending** (purple): Not yet started

The completion rate percentage is shown in the chart title.

Note: Tasks persist across sessions, so you may see old "in progress" tasks from abandoned conversations.

### Plan Activity Chart
A bar chart showing when you've used Claude's plan mode (`/plan` or entering plan mode). Each bar represents plans created on that day.

The chart title shows the total number of plans and average lines per plan.

---

## Deep Dive Section

### File Edit Velocity
Statistics about Claude's file editing activity:
- **Files Edited**: Unique files that Claude has modified
- **Total Versions**: Total number of file snapshots saved (file-history backups)
- **Sessions with Edits**: How many sessions involved file modifications

### Extended Thinking
Statistics about Claude's extended thinking feature (when Claude shows its reasoning):
- **Sessions with Thinking**: Number of sessions that used thinking
- **Total Thinking Blocks**: Number of thinking blocks generated
- **Est. Thinking Tokens**: Estimated tokens used for thinking (rough approximation)

Extended thinking is typically used for complex reasoning tasks.

### Conversation Depth
Statistics about conversation threading:
- **Max Conversation Depth**: Deepest conversation thread (messages in a single chain)
- **Average Depth**: Typical conversation length
- **Sessions with Branching**: Sessions where the conversation branched

Higher depth usually indicates more complex, back-and-forth problem solving.

---

## Date Range Filtering

Use the date inputs at the top of the dashboard to filter all time-based metrics. The filter affects:
- Daily activity charts
- Token usage charts
- Project stats (based on session dates)
- Recalculated totals

Click "Reset" to return to the full date range.

---

## Data Freshness

The dashboard is generated from your local `.claude` folder at a specific point in time. To see updated stats, regenerate the dashboard:

```bash
python -m claude_code_stats
```

The "Generated" timestamp at the bottom shows when the dashboard was created.
