"""Parser for .claude folder data."""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from .models import (
    ApiError,
    CacheMetrics,
    ClaudeStats,
    CostEstimate,
    DailyActivity,
    DailyModelTokens,
    FileEditStats,
    LongestSession,
    ModelUsage,
    PlanStats,
    ProjectStats,
    SessionDepth,
    SessionEntry,
    SlashCommandUsage,
    TaskStats,
    ThinkingUsage,
    ToolSuccessRate,
    ToolUsage,
    TurnDuration,
)

logger = logging.getLogger(__name__)


def validate_stats_cache(data: dict) -> bool:
    """Validate the structure of stats-cache.json."""
    if not isinstance(data, dict):
        return False
    expected_keys = {"dailyActivity", "modelUsage", "totalSessions", "totalMessages"}
    return bool(expected_keys & set(data.keys()))


def parse_stats_cache(claude_path: Path) -> dict:
    """Parse stats-cache.json for daily activity and model usage."""
    stats_file = claude_path / "stats-cache.json"
    if not stats_file.exists():
        return {}

    try:
        with open(stats_file, encoding="utf-8") as f:
            data = json.load(f)
        if not validate_stats_cache(data):
            logger.warning("stats-cache.json has unexpected structure")
        return data
    except json.JSONDecodeError as e:
        logger.error("Failed to parse stats-cache.json: %s", e)
        return {}
    except OSError as e:
        logger.error("Failed to read stats-cache.json: %s", e)
        return {}


def parse_sessions_index(project_path: Path) -> list[SessionEntry]:
    """Parse sessions-index.json from a project folder."""
    index_file = project_path / "sessions-index.json"
    if not index_file.exists():
        return []

    try:
        with open(index_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse %s: %s", index_file, e)
        return []

    entries = []
    for entry in data.get("entries", []):
        entries.append(
            SessionEntry(
                session_id=entry.get("sessionId", ""),
                project_path=entry.get("projectPath", ""),
                first_prompt=entry.get("firstPrompt", ""),
                summary=entry.get("summary", ""),
                message_count=entry.get("messageCount", 0),
                created=entry.get("created", ""),
                modified=entry.get("modified", ""),
                git_branch=entry.get("gitBranch"),
            )
        )
    return entries


def parse_project_folder_name(folder_name: str) -> str:
    """Convert folder name like -Users-foo-bar to /Users/foo/bar."""
    if folder_name.startswith("-"):
        return "/" + folder_name[1:].replace("-", "/")
    return folder_name


def extract_project_name(path: str) -> str:
    """Extract a readable project name from the path.

    Uses meaningful segments to create a unique identifier.
    """
    parts = [p for p in path.rstrip("/").split("/") if p]
    if not parts:
        return path

    # Skip common prefixes like Users, home, workspace
    skip_prefixes = {"Users", "home"}

    # Find where meaningful path starts
    start_idx = 0
    for i, part in enumerate(parts):
        if part in skip_prefixes:
            start_idx = i + 1
        elif part in ("workspace", "Documents", "Personal", "Projects", "Downloads"):
            start_idx = i + 1

    meaningful = parts[start_idx:]
    if not meaningful:
        return parts[-1]

    # Return last 2 segments joined, or all if short
    if len(meaningful) <= 2:
        return "/".join(meaningful)
    return "/".join(meaningful[-2:])


def extract_cwd_from_jsonl(jsonl_path: Path) -> str:
    """Extract the cwd (working directory) from the first user message in a JSONL file."""
    if not jsonl_path.exists():
        return ""

    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    cwd = data.get("cwd")
                    if cwd and data.get("type") in ("user", "assistant"):
                        return cwd
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        logger.warning("Failed to read %s: %s", jsonl_path, e)

    return ""


def parse_tool_calls_from_jsonl(jsonl_path: Path) -> Counter:
    """Extract tool call names from a session JSONL file."""
    tool_counts: Counter = Counter()

    if not jsonl_path.exists():
        return tool_counts

    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    message = data.get("message", {})
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "tool_use":
                                tool_name = item.get("name", "")
                                if tool_name:
                                    tool_counts[tool_name] += 1
                                # Check for subagent_type in input
                                tool_input = item.get("input", {})
                                if isinstance(tool_input, dict):
                                    subagent = tool_input.get("subagent_type")
                                    if subagent:
                                        tool_counts[f"subagent:{subagent}"] += 1
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        logger.warning("Failed to read %s: %s", jsonl_path, e)

    return tool_counts


def parse_history_jsonl(claude_path: Path) -> list[SlashCommandUsage]:
    """Parse history.jsonl for slash command usage."""
    history_file = claude_path / "history.jsonl"
    if not history_file.exists():
        return []

    command_counts: Counter = Counter()

    try:
        with open(history_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    display = data.get("display", "")
                    if display.startswith("/"):
                        # Extract command name (first word after /)
                        match = re.match(r"^(/\w+)", display)
                        if match:
                            command_counts[match.group(1)] += 1
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        logger.warning("Failed to read %s: %s", history_file, e)

    return [
        SlashCommandUsage(command=cmd, count=count)
        for cmd, count in command_counts.most_common()
    ]


def parse_settings(claude_path: Path) -> dict:
    """Parse settings.json for enabled plugins and MCPs."""
    settings_file = claude_path / "settings.json"
    if not settings_file.exists():
        return {}

    try:
        with open(settings_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse settings.json: %s", e)
        return {}


def parse_installed_plugins(claude_path: Path) -> list[str]:
    """Parse installed_plugins.json for list of installed plugins."""
    plugins_file = claude_path / "plugins" / "installed_plugins.json"
    if not plugins_file.exists():
        return []

    try:
        with open(plugins_file, encoding="utf-8") as f:
            data = json.load(f)
            return list(data.get("plugins", {}).keys())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse installed_plugins.json: %s", e)
        return []


def categorize_tool(tool_name: str) -> str:
    """Categorize a tool as builtin, mcp, or subagent."""
    if tool_name.startswith("mcp__"):
        return "mcp"
    if tool_name.startswith("subagent:"):
        return "subagent"
    return "builtin"


# Pricing per million tokens (Jan 2026 estimates)
PRICING = {
    "sonnet": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "opus": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "haiku": {"input": 0.25, "output": 1.25, "cache_read": 0.03, "cache_write": 0.30},
}


def get_model_pricing_key(model: str) -> str:
    """Map full model name to pricing key."""
    model_lower = model.lower()
    if "opus" in model_lower:
        return "opus"
    if "haiku" in model_lower:
        return "haiku"
    return "sonnet"  # Default to sonnet


def parse_cost_and_cache(
    model_usage: list[ModelUsage], daily_model_tokens: list[DailyModelTokens]
) -> tuple[CostEstimate, CacheMetrics]:
    """Calculate costs and cache metrics from model usage data."""
    total_cost = 0.0
    cost_by_model = {}
    total_cache_read = 0
    total_cache_write = 0
    total_input_without_cache = 0

    for usage in model_usage:
        pricing_key = get_model_pricing_key(usage.model)
        pricing = PRICING.get(pricing_key, PRICING["sonnet"])

        # Calculate cost for this model
        input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
        cache_read_cost = (usage.cache_read_tokens / 1_000_000) * pricing["cache_read"]
        cache_write_cost = (usage.cache_creation_tokens / 1_000_000) * pricing["cache_write"]

        model_cost = input_cost + output_cost + cache_read_cost + cache_write_cost
        total_cost += model_cost
        cost_by_model[usage.model] = model_cost

        total_cache_read += usage.cache_read_tokens
        total_cache_write += usage.cache_creation_tokens
        total_input_without_cache += usage.input_tokens

    # Calculate cache savings (what we would have paid without cache)
    cache_savings = 0.0
    for usage in model_usage:
        pricing_key = get_model_pricing_key(usage.model)
        pricing = PRICING.get(pricing_key, PRICING["sonnet"])
        # Cache read tokens would have cost full input price
        savings = (usage.cache_read_tokens / 1_000_000) * (pricing["input"] - pricing["cache_read"])
        cache_savings += savings

    # Calculate cache hit ratio (reads vs total cache operations)
    # This shows how much of the cached content is being reused vs newly created
    total_cache_ops = total_cache_read + total_cache_write
    cache_hit_ratio = total_cache_read / total_cache_ops if total_cache_ops > 0 else 0.0

    # Calculate daily costs from daily_model_tokens
    cost_by_day = []
    for daily in daily_model_tokens:
        day_cost = 0.0
        day_cost_by_model = {}
        for model, tokens in daily.tokens_by_model.items():
            pricing_key = get_model_pricing_key(model)
            pricing = PRICING.get(pricing_key, PRICING["sonnet"])
            # Use output price as approximation (most expensive, conservative estimate)
            # We don't have input/output/cache breakdown per day, only total tokens
            model_day_cost = (tokens / 1_000_000) * pricing["output"]
            day_cost += model_day_cost
            day_cost_by_model[model] = round(model_day_cost, 4)
        cost_by_day.append({
            "date": daily.date,
            "cost": round(day_cost, 4),
            "costByModel": day_cost_by_model,
        })

    cost_estimate = CostEstimate(
        total_cost_usd=round(total_cost, 2),
        cost_by_model={k: round(v, 2) for k, v in cost_by_model.items()},
        cost_by_day=cost_by_day,
        cache_savings_usd=round(cache_savings, 2),
    )

    cache_metrics = CacheMetrics(
        total_cache_read_tokens=total_cache_read,
        total_cache_write_tokens=total_cache_write,
        cache_hit_ratio=round(cache_hit_ratio, 4),
        tokens_saved=total_cache_read,
    )

    return cost_estimate, cache_metrics


def parse_turn_durations_from_jsonl(jsonl_files: list[Path]) -> list[TurnDuration]:
    """Extract turn_duration entries from JSONL files and aggregate by day."""
    durations_by_day: dict[str, list[float]] = {}

    for jsonl_path in jsonl_files:
        if not jsonl_path.exists():
            continue
        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("subtype") == "turn_duration":
                            duration_ms = data.get("durationMs", 0)
                            timestamp = data.get("timestamp", "")
                            if duration_ms > 0 and timestamp:
                                date = timestamp[:10]  # YYYY-MM-DD
                                if date not in durations_by_day:
                                    durations_by_day[date] = []
                                durations_by_day[date].append(duration_ms)
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.warning("Failed to read %s: %s", jsonl_path, e)

    result = []
    for date in sorted(durations_by_day.keys()):
        durations = sorted(durations_by_day[date])
        n = len(durations)
        if n == 0:
            continue

        avg = sum(durations) / n
        p50_idx = int(n * 0.5)
        p95_idx = min(int(n * 0.95), n - 1)
        p99_idx = min(int(n * 0.99), n - 1)

        result.append(
            TurnDuration(
                date=date,
                avg_duration_ms=round(avg, 2),
                p50_ms=durations[p50_idx],
                p95_ms=durations[p95_idx],
                p99_ms=durations[p99_idx],
                count=n,
            )
        )

    return result


def parse_api_errors_from_jsonl(jsonl_files: list[Path]) -> list[ApiError]:
    """Extract api_error entries from JSONL files."""
    errors_by_day_type: dict[tuple[str, str], list[float]] = {}

    for jsonl_path in jsonl_files:
        if not jsonl_path.exists():
            continue
        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("subtype") == "api_error":
                            # Extract error type from nested structure
                            error_obj = data.get("error", {})
                            nested_error = error_obj.get("error", {})
                            inner_error = nested_error.get("error", {})
                            error_type = inner_error.get("type", "unknown")
                            if error_type == "unknown":
                                # Try alternative paths
                                error_type = nested_error.get("type", "unknown")
                            timestamp = data.get("timestamp", "")
                            retry_ms = data.get("retryInMs", 0)
                            if timestamp:
                                date = timestamp[:10]
                                key = (date, error_type)
                                if key not in errors_by_day_type:
                                    errors_by_day_type[key] = []
                                errors_by_day_type[key].append(retry_ms)
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.warning("Failed to read %s: %s", jsonl_path, e)

    result = []
    for (date, error_type), retry_times in sorted(errors_by_day_type.items()):
        avg_retry = sum(retry_times) / len(retry_times) if retry_times else 0
        result.append(
            ApiError(
                date=date,
                error_type=error_type,
                count=len(retry_times),
                avg_retry_ms=round(avg_retry, 2),
            )
        )

    return result


def parse_todos(claude_path: Path) -> TaskStats:
    """Parse todos/*.json for task completion metrics."""
    todos_dir = claude_path / "todos"
    if not todos_dir.exists():
        return TaskStats(total_created=0, total_completed=0, completion_rate=0.0, by_status={})

    status_counts: Counter = Counter()
    total_created = 0

    for todo_file in todos_dir.glob("*.json"):
        try:
            with open(todo_file, encoding="utf-8") as f:
                data = json.load(f)
            todos = data if isinstance(data, list) else data.get("todos", [])
            for todo in todos:
                if isinstance(todo, dict):
                    status = todo.get("status", "unknown")
                    status_counts[status] += 1
                    total_created += 1
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to parse %s: %s", todo_file, e)

    total_completed = status_counts.get("completed", 0)
    completion_rate = total_completed / total_created if total_created > 0 else 0.0

    return TaskStats(
        total_created=total_created,
        total_completed=total_completed,
        completion_rate=round(completion_rate, 4),
        by_status=dict(status_counts),
    )


def parse_file_history(claude_path: Path) -> FileEditStats:
    """Analyze file-history directory structure.

    Structure: file-history/{session_id}/{file_hash}@v{version}
    Files are named with hash and version suffix, e.g., "57239a817f9be6be@v2"
    """
    file_history_dir = claude_path / "file-history"
    if not file_history_dir.exists():
        return FileEditStats(total_files_edited=0, total_versions=0, by_session={})

    total_versions = 0
    by_session: dict[str, int] = {}
    unique_files: set[str] = set()

    for session_dir in file_history_dir.iterdir():
        if not session_dir.is_dir():
            continue
        session_id = session_dir.name
        session_count = 0

        for file_entry in session_dir.iterdir():
            if file_entry.is_file():
                # Parse filename like "57239a817f9be6be@v2"
                name = file_entry.name
                if "@v" in name:
                    file_hash = name.split("@v")[0]
                    unique_files.add(f"{session_id}/{file_hash}")
                    total_versions += 1
                    session_count += 1

        if session_count > 0:
            by_session[session_id] = session_count

    return FileEditStats(
        total_files_edited=len(unique_files),
        total_versions=total_versions,
        by_session=by_session,
    )


def parse_thinking_usage_from_jsonl(jsonl_files: list[Path]) -> ThinkingUsage:
    """Count messages with thinking blocks."""
    sessions_with_thinking = set()
    total_thinking_blocks = 0
    total_thinking_tokens = 0

    for jsonl_path in jsonl_files:
        if not jsonl_path.exists():
            continue
        session_id = jsonl_path.stem
        has_thinking = False

        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        message = data.get("message", {})
                        content = message.get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "thinking":
                                    has_thinking = True
                                    total_thinking_blocks += 1
                                    # Estimate tokens from thinking text length
                                    thinking_text = item.get("thinking", "")
                                    total_thinking_tokens += len(thinking_text) // 4
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.warning("Failed to read %s: %s", jsonl_path, e)

        if has_thinking:
            sessions_with_thinking.add(session_id)

    return ThinkingUsage(
        sessions_with_thinking=len(sessions_with_thinking),
        total_thinking_blocks=total_thinking_blocks,
        total_thinking_tokens=total_thinking_tokens,
    )


def parse_plans(claude_path: Path) -> PlanStats:
    """Analyze plans directory for markdown plan files."""
    plans_dir = claude_path / "plans"
    if not plans_dir.exists():
        return PlanStats(total_plans=0, by_date=[], avg_plan_lines=0.0)

    total_plans = 0
    total_lines = 0
    by_date: dict[str, int] = {}

    for plan_file in plans_dir.glob("*.md"):
        try:
            stat = plan_file.stat()
            date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
            by_date[date] = by_date.get(date, 0) + 1
            total_plans += 1

            with open(plan_file, encoding="utf-8") as f:
                lines = len(f.readlines())
                total_lines += lines
        except OSError as e:
            logger.warning("Failed to read %s: %s", plan_file, e)

    avg_lines = total_lines / total_plans if total_plans > 0 else 0.0

    return PlanStats(
        total_plans=total_plans,
        by_date=[{"date": d, "count": c} for d, c in sorted(by_date.items())],
        avg_plan_lines=round(avg_lines, 1),
    )


def parse_session_depth_from_jsonl(jsonl_files: list[Path]) -> SessionDepth:
    """Analyze conversation threading via uuid/parentUuid."""
    uuid_to_parent: dict[str, str] = {}
    root_uuids = set()

    for jsonl_path in jsonl_files:
        if not jsonl_path.exists():
            continue
        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        uuid = data.get("uuid")
                        parent_uuid = data.get("parentUuid")
                        if uuid:
                            if parent_uuid:
                                uuid_to_parent[uuid] = parent_uuid
                            else:
                                root_uuids.add(uuid)
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.warning("Failed to read %s: %s", jsonl_path, e)

    # Calculate depth for each message
    def get_depth(uuid: str, memo: dict) -> int:
        if uuid in memo:
            return memo[uuid]
        parent = uuid_to_parent.get(uuid)
        if not parent:
            memo[uuid] = 1
            return 1
        depth = 1 + get_depth(parent, memo)
        memo[uuid] = depth
        return depth

    depths: list[int] = []
    memo: dict[str, int] = {}
    for uuid in list(uuid_to_parent.keys()) + list(root_uuids):
        depths.append(get_depth(uuid, memo))

    if not depths:
        return SessionDepth(max_depth=0, avg_depth=0.0, sessions_with_children=0)

    sessions_with_children = len([d for d in depths if d > 1])

    return SessionDepth(
        max_depth=max(depths) if depths else 0,
        avg_depth=round(sum(depths) / len(depths), 2) if depths else 0.0,
        sessions_with_children=sessions_with_children,
    )


def parse_tool_success_rates_from_jsonl(jsonl_files: list[Path]) -> list[ToolSuccessRate]:
    """Track tool_result success/failure patterns."""
    tool_stats: dict[str, dict] = {}
    pending_tool_calls: dict[str, str] = {}  # tool_use_id -> tool_name

    for jsonl_path in jsonl_files:
        if not jsonl_path.exists():
            continue
        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        message = data.get("message", {})
                        content = message.get("content", [])

                        if isinstance(content, list):
                            for item in content:
                                if not isinstance(item, dict):
                                    continue

                                # Track tool_use calls
                                if item.get("type") == "tool_use":
                                    tool_id = item.get("id", "")
                                    tool_name = item.get("name", "")
                                    if tool_id and tool_name:
                                        pending_tool_calls[tool_id] = tool_name

                                # Track tool_result responses
                                if item.get("type") == "tool_result":
                                    tool_id = item.get("tool_use_id", "")
                                    is_error = item.get("is_error", False)
                                    tool_name = pending_tool_calls.get(tool_id, "unknown")

                                    if tool_name not in tool_stats:
                                        tool_stats[tool_name] = {"success": 0, "error": 0}

                                    if is_error:
                                        tool_stats[tool_name]["error"] += 1
                                    else:
                                        tool_stats[tool_name]["success"] += 1
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.warning("Failed to read %s: %s", jsonl_path, e)

    result = []
    for tool_name, stats in tool_stats.items():
        total = stats["success"] + stats["error"]
        if total > 0:
            result.append(
                ToolSuccessRate(
                    tool_name=tool_name,
                    total_calls=total,
                    success_count=stats["success"],
                    error_count=stats["error"],
                    success_rate=round(stats["success"] / total, 4),
                )
            )

    result.sort(key=lambda x: x.total_calls, reverse=True)
    return result


def parse_claude_folder(claude_path: Path) -> ClaudeStats:
    """Parse the entire .claude folder and return aggregate statistics."""
    claude_path = Path(claude_path).expanduser()

    # Parse stats-cache.json
    stats_cache = parse_stats_cache(claude_path)

    # Parse daily activity
    daily_activity = [
        DailyActivity(
            date=d["date"],
            message_count=d.get("messageCount", 0),
            session_count=d.get("sessionCount", 0),
            tool_call_count=d.get("toolCallCount", 0),
        )
        for d in stats_cache.get("dailyActivity", [])
    ]

    # Parse daily model tokens
    daily_model_tokens = [
        DailyModelTokens(date=d["date"], tokens_by_model=d.get("tokensByModel", {}))
        for d in stats_cache.get("dailyModelTokens", [])
    ]

    # Parse model usage
    model_usage_raw = stats_cache.get("modelUsage", {})
    model_usage = [
        ModelUsage(
            model=model,
            input_tokens=data.get("inputTokens", 0),
            output_tokens=data.get("outputTokens", 0),
            cache_read_tokens=data.get("cacheReadInputTokens", 0),
            cache_creation_tokens=data.get("cacheCreationInputTokens", 0),
        )
        for model, data in model_usage_raw.items()
    ]

    # Parse longest session
    longest_raw = stats_cache.get("longestSession")
    longest_session = None
    if longest_raw:
        longest_session = LongestSession(
            session_id=longest_raw.get("sessionId", ""),
            duration_ms=longest_raw.get("duration", 0),
            message_count=longest_raw.get("messageCount", 0),
            timestamp=longest_raw.get("timestamp", ""),
        )

    # Parse hour counts
    hour_counts = stats_cache.get("hourCounts", {})

    # Parse projects
    projects_dir = claude_path / "projects"
    project_stats = []
    all_tool_counts: Counter = Counter()
    all_jsonl_files: list[Path] = []
    all_sessions: list[SessionEntry] = []

    if projects_dir.exists():
        for project_folder in projects_dir.iterdir():
            if not project_folder.is_dir() or project_folder.name.startswith("."):
                continue

            sessions = parse_sessions_index(project_folder)
            all_sessions.extend(sessions)
            jsonl_files = list(project_folder.glob("*.jsonl"))
            all_jsonl_files.extend(jsonl_files)

            # Get project path from sessions if available, else try JSONL cwd, else reconstruct
            project_path = ""
            if sessions and sessions[0].project_path:
                project_path = sessions[0].project_path
            elif jsonl_files:
                for jf in jsonl_files:
                    project_path = extract_cwd_from_jsonl(jf)
                    if project_path:
                        break
            if not project_path:
                project_path = parse_project_folder_name(project_folder.name)
            session_count = len(sessions) if sessions else len(jsonl_files)

            if session_count == 0:
                continue

            if sessions:
                total_messages = sum(s.message_count for s in sessions)
                created_dates = [s.created for s in sessions if s.created]
                modified_dates = [s.modified for s in sessions if s.modified]
                first_session = min(created_dates) if created_dates else None
                last_session = max(modified_dates) if modified_dates else None
            else:
                # Estimate from JSONL files
                total_messages = 0
                first_session = None
                last_session = None
                for jf in jsonl_files:
                    try:
                        with open(jf, encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    data = json.loads(line)
                                    if data.get("type") in ("user", "assistant"):
                                        total_messages += 1
                                except json.JSONDecodeError:
                                    continue
                    except OSError as e:
                        logger.warning("Failed to read %s: %s", jf, e)

            project_stats.append(
                ProjectStats(
                    path=project_path,
                    name=extract_project_name(project_path),
                    session_count=session_count,
                    message_count=total_messages,
                    first_session=first_session,
                    last_session=last_session,
                )
            )

            # Parse tool calls from session JSONL files
            for jsonl_file in jsonl_files:
                tool_counts = parse_tool_calls_from_jsonl(jsonl_file)
                all_tool_counts.update(tool_counts)

    # Sort projects by message count
    project_stats.sort(key=lambda p: p.message_count, reverse=True)

    # Convert tool counts to ToolUsage list
    tool_usage = [
        ToolUsage(name=name, count=count, category=categorize_tool(name))
        for name, count in all_tool_counts.most_common()
    ]

    # Parse slash commands from history
    slash_command_usage = parse_history_jsonl(claude_path)

    # Parse settings
    settings = parse_settings(claude_path)
    enabled_plugins = list(settings.get("enabledPlugins", {}).keys())

    # Parse installed plugins
    installed_plugins = parse_installed_plugins(claude_path)

    # Calculate totals - prefer stats-cache value as source of truth
    # Fall back to sum from daily activity or parsed tool usage
    total_tool_calls = stats_cache.get("totalToolCalls")
    if total_tool_calls is None:
        daily_sum = sum(d.tool_call_count for d in daily_activity)
        parsed_sum = sum(t.count for t in tool_usage if t.category == "builtin")
        total_tool_calls = daily_sum if daily_sum > 0 else parsed_sum

    # Parse new v2 analytics
    cost_estimate, cache_metrics = parse_cost_and_cache(model_usage, daily_model_tokens)
    turn_durations = parse_turn_durations_from_jsonl(all_jsonl_files)
    api_errors = parse_api_errors_from_jsonl(all_jsonl_files)
    task_stats = parse_todos(claude_path)
    file_edit_stats = parse_file_history(claude_path)
    thinking_usage = parse_thinking_usage_from_jsonl(all_jsonl_files)
    plan_stats = parse_plans(claude_path)
    session_depth = parse_session_depth_from_jsonl(all_jsonl_files)
    tool_success_rates = parse_tool_success_rates_from_jsonl(all_jsonl_files)

    return ClaudeStats(
        generated_at=datetime.now().isoformat(),
        claude_folder_path=str(claude_path),
        first_session_date=stats_cache.get("firstSessionDate"),
        last_computed_date=stats_cache.get("lastComputedDate"),
        total_sessions=stats_cache.get("totalSessions", 0),
        total_messages=stats_cache.get("totalMessages", 0),
        total_tool_calls=total_tool_calls,
        total_projects=len(project_stats),
        daily_activity=daily_activity,
        daily_model_tokens=daily_model_tokens,
        model_usage=model_usage,
        longest_session=longest_session,
        hour_counts=hour_counts,
        project_stats=project_stats,
        tool_usage=tool_usage,
        slash_command_usage=slash_command_usage,
        enabled_plugins=enabled_plugins,
        installed_plugins=installed_plugins,
        # New v2 analytics
        cost_estimate=cost_estimate,
        cache_metrics=cache_metrics,
        turn_durations=turn_durations,
        api_errors=api_errors,
        task_stats=task_stats,
        file_edit_stats=file_edit_stats,
        thinking_usage=thinking_usage,
        plan_stats=plan_stats,
        session_depth=session_depth,
        tool_success_rates=tool_success_rates,
    )
