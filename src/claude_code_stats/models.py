"""Data models for Claude Code statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DailyActivity:
    """Activity metrics for a single day."""

    date: str
    message_count: int
    session_count: int
    tool_call_count: int


@dataclass
class DailyModelTokens:
    """Token usage by model for a single day."""

    date: str
    tokens_by_model: dict


@dataclass
class ModelUsage:
    """Aggregate token usage for a single model."""

    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int


@dataclass
class LongestSession:
    """Details about the longest session."""

    session_id: str
    duration_ms: int
    message_count: int
    timestamp: str


@dataclass
class ProjectStats:
    """Statistics for a single project."""

    path: str
    name: str
    session_count: int
    message_count: int
    first_session: Optional[str]
    last_session: Optional[str]


@dataclass
class SessionEntry:
    """A single session from the sessions-index."""

    session_id: str
    project_path: str
    first_prompt: str
    summary: str
    message_count: int
    created: str
    modified: str
    git_branch: Optional[str]


@dataclass
class ToolUsage:
    """Usage count for a specific tool."""

    name: str
    count: int
    category: str  # "builtin", "mcp", "subagent"


@dataclass
class SlashCommandUsage:
    """Usage count for a slash command from history.jsonl."""

    command: str
    count: int


@dataclass
class CostEstimate:
    """Estimated API costs based on token usage."""

    total_cost_usd: float
    cost_by_model: dict  # {model: cost_usd}
    cost_by_day: list  # [{date, cost}]
    cache_savings_usd: float


@dataclass
class CacheMetrics:
    """Cache efficiency metrics."""

    total_cache_read_tokens: int
    total_cache_write_tokens: int
    cache_hit_ratio: float
    tokens_saved: int


@dataclass
class TurnDuration:
    """Turn duration metrics for a single day."""

    date: str
    avg_duration_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    count: int


@dataclass
class ApiError:
    """API error metrics."""

    date: str
    error_type: str
    count: int
    avg_retry_ms: float


@dataclass
class TaskStats:
    """Task (todo) completion statistics."""

    total_created: int
    total_completed: int
    completion_rate: float
    by_status: dict  # {status: count}


@dataclass
class FileEditStats:
    """File editing statistics from file-history."""

    total_files_edited: int
    total_versions: int
    by_session: dict  # {session_id: count}


@dataclass
class ThinkingUsage:
    """Extended thinking usage statistics."""

    sessions_with_thinking: int
    total_thinking_blocks: int
    total_thinking_tokens: int


@dataclass
class PlanStats:
    """Plan creation statistics."""

    total_plans: int
    by_date: list  # [{date, count}]
    avg_plan_lines: float


@dataclass
class SessionDepth:
    """Session threading depth statistics."""

    max_depth: int
    avg_depth: float
    sessions_with_children: int


@dataclass
class ToolSuccessRate:
    """Tool success/failure rate statistics."""

    tool_name: str
    total_calls: int
    success_count: int
    error_count: int
    success_rate: float


@dataclass
class ClaudeStats:
    """Aggregate statistics from the .claude folder."""

    # Metadata
    generated_at: str
    claude_folder_path: str
    first_session_date: Optional[str]
    last_computed_date: Optional[str]

    # Totals
    total_sessions: int
    total_messages: int
    total_tool_calls: int
    total_projects: int

    # Daily data
    daily_activity: list
    daily_model_tokens: list

    # Model usage
    model_usage: list

    # Session stats
    longest_session: Optional[LongestSession]
    hour_counts: dict

    # Project stats
    project_stats: list

    # Tool usage
    tool_usage: list

    # Slash commands
    slash_command_usage: list

    # Plugins
    enabled_plugins: list
    installed_plugins: list

    # New analytics (v2)
    cost_estimate: Optional[CostEstimate]
    cache_metrics: Optional[CacheMetrics]
    turn_durations: list  # list[TurnDuration]
    api_errors: list  # list[ApiError]
    task_stats: Optional[TaskStats]
    file_edit_stats: Optional[FileEditStats]
    thinking_usage: Optional[ThinkingUsage]
    plan_stats: Optional[PlanStats]
    session_depth: Optional[SessionDepth]
    tool_success_rates: list  # list[ToolSuccessRate]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "generatedAt": self.generated_at,
            "claudeFolderPath": self.claude_folder_path,
            "firstSessionDate": self.first_session_date,
            "lastComputedDate": self.last_computed_date,
            "totalSessions": self.total_sessions,
            "totalMessages": self.total_messages,
            "totalToolCalls": self.total_tool_calls,
            "totalProjects": self.total_projects,
            "dailyActivity": [
                {
                    "date": d.date,
                    "messageCount": d.message_count,
                    "sessionCount": d.session_count,
                    "toolCallCount": d.tool_call_count,
                }
                for d in self.daily_activity
            ],
            "dailyModelTokens": [
                {"date": d.date, "tokensByModel": d.tokens_by_model}
                for d in self.daily_model_tokens
            ],
            "modelUsage": [
                {
                    "model": m.model,
                    "inputTokens": m.input_tokens,
                    "outputTokens": m.output_tokens,
                    "cacheReadTokens": m.cache_read_tokens,
                    "cacheCreationTokens": m.cache_creation_tokens,
                }
                for m in self.model_usage
            ],
            "longestSession": (
                {
                    "sessionId": self.longest_session.session_id,
                    "durationMs": self.longest_session.duration_ms,
                    "messageCount": self.longest_session.message_count,
                    "timestamp": self.longest_session.timestamp,
                }
                if self.longest_session
                else None
            ),
            "hourCounts": self.hour_counts,
            "projectStats": [
                {
                    "path": p.path,
                    "name": p.name,
                    "sessionCount": p.session_count,
                    "messageCount": p.message_count,
                    "firstSession": p.first_session,
                    "lastSession": p.last_session,
                }
                for p in self.project_stats
            ],
            "toolUsage": [
                {"name": t.name, "count": t.count, "category": t.category}
                for t in self.tool_usage
            ],
            "slashCommandUsage": [
                {"command": s.command, "count": s.count} for s in self.slash_command_usage
            ],
            "enabledPlugins": self.enabled_plugins,
            "installedPlugins": self.installed_plugins,
            # New analytics (v2)
            "costEstimate": (
                {
                    "totalCostUsd": self.cost_estimate.total_cost_usd,
                    "costByModel": self.cost_estimate.cost_by_model,
                    "costByDay": self.cost_estimate.cost_by_day,
                    "cacheSavingsUsd": self.cost_estimate.cache_savings_usd,
                }
                if self.cost_estimate
                else None
            ),
            "cacheMetrics": (
                {
                    "totalCacheReadTokens": self.cache_metrics.total_cache_read_tokens,
                    "totalCacheWriteTokens": self.cache_metrics.total_cache_write_tokens,
                    "cacheHitRatio": self.cache_metrics.cache_hit_ratio,
                    "tokensSaved": self.cache_metrics.tokens_saved,
                }
                if self.cache_metrics
                else None
            ),
            "turnDurations": [
                {
                    "date": t.date,
                    "avgDurationMs": t.avg_duration_ms,
                    "p50Ms": t.p50_ms,
                    "p95Ms": t.p95_ms,
                    "p99Ms": t.p99_ms,
                    "count": t.count,
                }
                for t in self.turn_durations
            ],
            "apiErrors": [
                {
                    "date": e.date,
                    "errorType": e.error_type,
                    "count": e.count,
                    "avgRetryMs": e.avg_retry_ms,
                }
                for e in self.api_errors
            ],
            "taskStats": (
                {
                    "totalCreated": self.task_stats.total_created,
                    "totalCompleted": self.task_stats.total_completed,
                    "completionRate": self.task_stats.completion_rate,
                    "byStatus": self.task_stats.by_status,
                }
                if self.task_stats
                else None
            ),
            "fileEditStats": (
                {
                    "totalFilesEdited": self.file_edit_stats.total_files_edited,
                    "totalVersions": self.file_edit_stats.total_versions,
                    "bySession": self.file_edit_stats.by_session,
                }
                if self.file_edit_stats
                else None
            ),
            "thinkingUsage": (
                {
                    "sessionsWithThinking": self.thinking_usage.sessions_with_thinking,
                    "totalThinkingBlocks": self.thinking_usage.total_thinking_blocks,
                    "totalThinkingTokens": self.thinking_usage.total_thinking_tokens,
                }
                if self.thinking_usage
                else None
            ),
            "planStats": (
                {
                    "totalPlans": self.plan_stats.total_plans,
                    "byDate": self.plan_stats.by_date,
                    "avgPlanLines": self.plan_stats.avg_plan_lines,
                }
                if self.plan_stats
                else None
            ),
            "sessionDepth": (
                {
                    "maxDepth": self.session_depth.max_depth,
                    "avgDepth": self.session_depth.avg_depth,
                    "sessionsWithChildren": self.session_depth.sessions_with_children,
                }
                if self.session_depth
                else None
            ),
            "toolSuccessRates": [
                {
                    "toolName": t.tool_name,
                    "totalCalls": t.total_calls,
                    "successCount": t.success_count,
                    "errorCount": t.error_count,
                    "successRate": t.success_rate,
                }
                for t in self.tool_success_rates
            ],
        }
