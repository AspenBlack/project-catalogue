# AGENTS.md

This file is for coding agents, not end-user documentation.

## Purpose

Project Catalogue indexes local projects and generates MkDocs pages from scan output.

## Canonical Entry Points

- `MyCatlog.py`: main orchestrator CLI
- `scanner/cli.py`: scanner commands (`init`, `scan`, `list`)
- `scanner/project_scanner.py`: discovery, typing, metadata extraction
- `mkdocs/generate_pages.py`: docs generation from `data/projects.json`

## Data Boundaries

- Runtime/generated data:
  - `data/projects.json` (generated index)
  - `mkdocs/docs/projects/*.md` (generated detail pages)
  - `mkdocs/site/` (built site output)
- Local/private config:
  - `config/scan_config.yaml`
- Keep generated/private files out of commits.

## CLI Workflow

1. `python MyCatlog.py init`
2. `python MyCatlog.py scan`
3. `python MyCatlog.py build-docs`
4. `python MyCatlog.py serve --background`
5. `python MyCatlog.py stop`

## Command Notes

- `python MyCatlog.py serve` prebuilds docs by default.
- `python MyCatlog.py serve --no-build` skips generation.
- `python MyCatlog.py all` runs build + serve.
- `python MyCatlog.py clean` removes generated artifacts, including legacy root `projects.json`.
- `python MyCatlog.py help serve` shows command-specific help.

## Scanner Behavior

- Detects explicit project types (python/node/rust/csharp_vs/godot/zephyr/etc.).
- Empty placeholder folders map to `empty`.
- Unknown projects use majority inference:
  - `code_<lang>`
  - `data_<format>`
- VS Code `.code-workspace` files are parsed and folder entries can be ingested.

## MkDocs Generation Behavior

- Landing page: consolidated table in `mkdocs/docs/index.md`.
- Detail pages: one file per project under `mkdocs/docs/projects/`.
- Project IDs are already path-stable hashed IDs in `projects.json`; do not overwrite with name-only IDs.

## Safe Edit Guidance

- Prefer editing source generators (`scanner/*.py`, `mkdocs/generate_pages.py`) over generated docs.
- Regenerate after changes:
  - `python MyCatlog.py scan`
  - `python MyCatlog.py build-docs`
- Validate with:
  - `python -m mkdocs build` from `mkdocs/`

## Known Non-Blocking Noise

- Material for MkDocs prints an upstream notice about MkDocs 2.0. Treat as informational unless dependencies are upgraded.
