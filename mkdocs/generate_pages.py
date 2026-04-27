#!/usr/bin/env python3
"""Generate MkDocs pages from projects.json.

- Landing page: consolidated table with links to project detail pages.
- Detail page: metadata + README summary + diagrams.
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path


def load_projects_json(projects_json_path: Path) -> list:
    """Load projects from projects.json."""
    if not projects_json_path.exists():
        print(f"Error: {projects_json_path} not found.")
        print("Run: python ../scanner/cli.py scan")
        sys.exit(1)

    with open(projects_json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _escape_md_table_cell(text: str) -> str:
    return text.replace('|', '\\|').replace('\n', ' ').strip()


def _shorten(text: str, max_chars: int = 120) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + '...'


def _sanitize_summary_text(text: str) -> str:
    """Convert markdown-heavy README excerpts into plain text.

    This avoids MkDocs warning on unresolved relative links/anchors from snippets.
    """
    if not text:
        return ""

    cleaned = text
    # markdown links/images: [label](target) -> label
    cleaned = re.sub(r'!?\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
    # autolinks: <https://...> -> https://...
    cleaned = re.sub(r'<(https?://[^>]+)>', r'\1', cleaned)
    # strip simple HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    # normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _path_to_file_uri(path_text: str) -> str:
    """Convert a local path into a file:// URI when possible."""
    try:
        return Path(path_text).resolve().as_uri()
    except Exception:
        return ""


def generate_project_page(project: dict) -> str:
    """Generate Markdown content for a single project."""
    lines = [
        f"# {project['name']}",
        "",
        f"**Type:** `{project['type']}`  ",
        f"**Category:** `{project['category']}`  ",
        f"**Path:** `{project['path']}`  ",
        f"**Last Modified:** {project['last_modified']}",
        "",
        "## Tags",
        "",
    ]

    if project.get('tags'):
        for tag in sorted(project['tags']):
            lines.append(f"- `{tag}`")
    else:
        lines.append("- (no tags)")

    lines.extend(["", "## README Summary", ""])
    if project.get('has_readme'):
        readme_file = project.get('readme_file', 'README')
        lines.append(f"- README file: `{readme_file}`")
        excerpt = _sanitize_summary_text(project.get('readme_excerpt', ''))
        if excerpt:
            lines.extend(["", excerpt])
        else:
            lines.extend(["", "README exists but no summary text could be extracted."])
    else:
        lines.append("No README file detected.")

    if project.get('diagrams'):
        lines.extend(["", "## Diagrams", ""])
        for diagram in project['diagrams']:
            lines.append(f"- `{diagram}`")

    lines.extend(
        [
            "",
            "## Metadata",
            "",
            f"- **ID:** `{project['id']}`",
            f"- **Type:** `{project['type']}`",
            f"- **Full Path:** `{project['path']}`",
            "",
            "---",
            "",
            "*Auto-generated page. For updates, re-run the scanner.*",
            "",
        ]
    )
    return "\n".join(lines)


def generate_landing_page(projects: list, docs_path: Path, data_path: Path) -> None:
    """Generate single consolidated landing page with linked project rows."""
    categories = defaultdict(int)
    types = defaultdict(int)
    for proj in projects:
        categories[proj['category']] += 1
        types[proj['type']] += 1

    lines = [
        "# Project Catalogue",
        "",
        "Single-page overview of all indexed projects. Click a project name for details.",
        "",
        "## Summary",
        "",
        f"- Total projects: **{len(projects)}**",
        f"- Categories: **{len(categories)}**",
        f"- Types: **{len(types)}**",
        "",
        "### Category Counts",
        "",
        "| Category | Count |",
        "|----------|-------|",
    ]

    for category in sorted(categories.keys()):
        lines.append(f"| {category} | {categories[category]} |")

    lines.extend(
        [
            "",
            "## All Projects",
            "",
            "<table>",
            "  <thead>",
            "    <tr>",
            "      <th>Project</th>",
            "      <th>Type</th>",
            "      <th>Category</th>",
            "      <th>Modified</th>",
            "      <th>Folder</th>",
            "    </tr>",
            "  </thead>",
            "  <tbody>",
        ]
    )

    for proj in sorted(projects, key=lambda p: p['name'].lower()):
        name = escape(proj['name'])
        ptype = escape(proj['type'])
        category = escape(proj['category'])
        modified = escape(proj['last_modified'])
        path = escape(proj['path'])
        folder_uri = _path_to_file_uri(proj['path'])
        summary = _shorten(escape(proj.get('readme_excerpt', '')))
        if not summary:
            summary = "-"

        lines.extend(
            [
                "    <tr>",
                f"      <td><a href=\"projects/{proj['id']}.md\">{name}</a></td>",
                f"      <td><code>{ptype}</code></td>",
                f"      <td>{category}</td>",
                f"      <td>{modified}</td>",
                (
                    f"      <td style=\"white-space: nowrap;\"><a href=\"{folder_uri}\">{path}</a></td>"
                    if folder_uri
                    else f"      <td style=\"white-space: nowrap;\">{path}</td>"
                ),
                "    </tr>",
                "    <tr>",
                f"      <td colspan=\"5\"><strong>Summary:</strong> {summary}</td>",
                "    </tr>",
            ]
        )

    lines.extend(["  </tbody>", "</table>"])

    lines.extend(["", "---", "", f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*", ""])

    landing_content = "\n".join(lines)

    data_path.mkdir(parents=True, exist_ok=True)
    data_index_path = data_path / 'index.md'
    with open(data_index_path, 'w', encoding='utf-8') as f:
        f.write(landing_content)

    index_path = docs_path / 'index.md'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(landing_content)
    print("  ✓ docs/index.md")


def generate_projects_index(projects: list, projects_dir: Path, data_path: Path) -> None:
    """Generate projects/index.md grouped by category."""
    content = ["# All Projects", ""]

    by_category = defaultdict(list)
    for proj in sorted(projects, key=lambda p: p['name'].lower()):
        by_category[proj['category']].append(proj)

    for category in sorted(by_category.keys()):
        content.append(f"## {category.capitalize()} Projects")
        content.append("")
        for proj in by_category[category]:
            content.append(f"- [{proj['name']}]({proj['id']}.md) - `{proj['type']}`")
        content.append("")

    projects_index_content = "\n".join(content) + "\n"

    data_path.mkdir(parents=True, exist_ok=True)
    with open(data_path / 'projects-index.md', 'w', encoding='utf-8') as f:
        f.write(projects_index_content)

    with open(projects_dir / 'index.md', 'w', encoding='utf-8') as f:
        f.write(projects_index_content)
    print("  ✓ projects/index.md")


def main(projects_json_path: Path = None, docs_path: Path = None, data_path: Path = None):
    """Generate all docs pages."""
    if projects_json_path is None:
        projects_json_path = Path(__file__).parent.parent / 'data' / 'projects.json'
    if docs_path is None:
        docs_path = Path(__file__).parent / 'docs'
    if data_path is None:
        data_path = Path(__file__).parent.parent / 'data'

    projects = load_projects_json(projects_json_path)

    if not projects:
        print("No projects to generate.")
        return

    projects_dir = docs_path / 'projects'
    projects_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(projects)} project page(s)...\n")

    for project in projects:
        page_name = f"{project['id']}.md"
        page_path = projects_dir / page_name
        content = generate_project_page(project)
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ {page_name}")

    generate_projects_index(projects, projects_dir, data_path)
    generate_landing_page(projects, docs_path, data_path)

    print(f"\n✓ Generated documentation for {len(projects)} project(s)")


if __name__ == '__main__':
    main()
