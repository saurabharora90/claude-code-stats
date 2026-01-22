"""Exporters for generating JSON and HTML output."""

import json
import shutil
from pathlib import Path

from .models import ClaudeStats


def _find_web_dir() -> Path:
    """Find the web directory, checking both dev and installed locations."""
    # Development: web/ is sibling to src/
    dev_path = Path(__file__).parent.parent.parent / "web"
    if dev_path.exists():
        return dev_path

    # Installed: web/ is copied into the package
    pkg_path = Path(__file__).parent / "web"
    if pkg_path.exists():
        return pkg_path

    raise FileNotFoundError(
        "Web directory not found. Expected at:\n"
        f"  - {dev_path} (development)\n"
        f"  - {pkg_path} (installed package)"
    )


WEB_DIR = _find_web_dir()


def export_json(stats: ClaudeStats, output_path: Path) -> Path:
    """Export statistics to JSON file."""
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    json_file = output_path / "stats.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(stats.to_dict(), f, indent=2)

    return json_file


def export_html(stats: ClaudeStats, output_path: Path) -> Path:
    """Export HTML dashboard with embedded statistics.

    Embeds stats directly into HTML to avoid CORS issues when opening as file://.
    """
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Copy CSS and JS
    for file_name in ["style.css", "app.js"]:
        src = WEB_DIR / file_name
        if src.exists():
            shutil.copy(src, output_path / file_name)

    # Read HTML template and inject stats
    html_src = WEB_DIR / "index.html"
    with open(html_src, encoding="utf-8") as f:
        html_content = f.read()

    # Inject stats as a script tag before app.js
    stats_json = json.dumps(stats.to_dict())
    stats_script = f'<script>window.CLAUDE_STATS = {stats_json};</script>'
    html_content = html_content.replace(
        '<script src="app.js"></script>',
        f'{stats_script}\n    <script src="app.js"></script>'
    )

    # Write modified HTML
    html_file = output_path / "index.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Also write stats.json for reference
    export_json(stats, output_path)

    return html_file
