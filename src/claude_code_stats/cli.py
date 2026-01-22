"""CLI entry point for Claude Code Stats."""

from __future__ import annotations

import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

import click

from .exporters import export_html
from .parser import parse_claude_folder


@click.command()
@click.argument(
    "claude_folder",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.home() / ".claude",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Output directory for the dashboard. Defaults to a temp directory.",
)
@click.option(
    "--open/--no-open",
    "open_browser",
    default=True,
    help="Open the dashboard in a browser after generation.",
)
@click.option(
    "--json-only",
    is_flag=True,
    default=False,
    help="Only export JSON stats, skip HTML dashboard.",
)
def main(
    claude_folder: Path,
    output: Optional[Path],
    open_browser: bool,
    json_only: bool,
) -> None:
    """Generate a visualization dashboard for your Claude Code usage.

    CLAUDE_FOLDER is the path to your .claude directory.
    Defaults to ~/.claude
    """
    claude_folder = Path(claude_folder).expanduser()

    if not claude_folder.exists():
        click.echo(f"Error: Claude folder not found at {claude_folder}", err=True)
        sys.exit(1)

    click.echo(f"Parsing Claude Code data from {claude_folder}...")

    stats = parse_claude_folder(claude_folder)

    click.echo(f"Found {stats.total_sessions} sessions with {stats.total_messages} messages")
    click.echo(f"Across {stats.total_projects} projects")

    if output is None:
        output = Path(tempfile.mkdtemp(prefix="claude-stats-"))

    output = Path(output)

    if json_only:
        from .exporters import export_json

        json_file = export_json(stats, output)
        click.echo(f"Stats exported to {json_file}")
    else:
        html_file = export_html(stats, output)
        click.echo(f"Dashboard generated at {html_file}")

        if open_browser:
            click.echo("Opening in browser...")
            webbrowser.open(f"file://{html_file}")


if __name__ == "__main__":
    main()
