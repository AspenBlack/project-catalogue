# Implementation Summary

## Current State

Project Catalogue is now a Python-first local indexing tool with MkDocs output.

### Canonical Entrypoint

```bash
python MyCatlog.py
```

### Core Workflow

```bash
python MyCatlog.py init
python MyCatlog.py scan
python MyCatlog.py build-docs
python MyCatlog.py serve --background
python MyCatlog.py stop
```

## Code vs Data Split

- Code lives in the repository root, `scanner/`, and `mkdocs/`.
- Generated runtime data is stored in `data/projects.json`.
- Local/private configuration is stored in `config/scan_config.yaml`.
- Generated detail pages are stored in `mkdocs/docs/projects/`.
- Built site output is stored in `mkdocs/site/`.

## Scanner Behavior

- Detects explicit project types including Python, Node.js, Rust, C#, Godot, and Zephyr.
- Reads VS Code `.code-workspace` files and can ingest referenced folders.
- Marks empty placeholder folders as `empty`.
- Infers unknown projects using majority file families:
  - `code_<lang>`
  - `data_<format>`

## MkDocs Behavior

- Landing page is consolidated into `mkdocs/docs/index.md`.
- Each project gets its own detail page in `mkdocs/docs/projects/`.
- Project detail pages include metadata and sanitized README summary text.
- Local folder path appears as the last column on the landing page.

## Operational Notes

- `serve` regenerates docs by default before starting MkDocs.
- `stop` shuts down a background MkDocs server using the stored PID file.
- `clean` removes generated docs, built site output, and generated data files.

## Validation Commands

```bash
python MyCatlog.py help
python MyCatlog.py list
python -m mkdocs build -f mkdocs/mkdocs.yml
```
