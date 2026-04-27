# Project Catalogue
Local project index + docs generator for private and public codebases.

## Quick Start

```bash
pip install -r requirements.txt
python MyCatlog.py init
python MyCatlog.py scan
python MyCatlog.py build-docs
python MyCatlog.py serve --background
```

Stop server cleanly:

```bash
python MyCatlog.py stop
```

## Main Commands

```bash
python MyCatlog.py init         # configure scan roots
python MyCatlog.py scan         # build data/projects.json
python MyCatlog.py list         # terminal table (includes path)
python MyCatlog.py build-docs   # generate mkdocs/docs pages
python MyCatlog.py serve        # run mkdocs server (foreground)
python MyCatlog.py serve --background
python MyCatlog.py stop         # graceful stop for background server
python MyCatlog.py clean        # remove generated data/docs artifacts
python MyCatlog.py help         # help + standard workflow
python MyCatlog.py help serve   # help for one command
```

## Classification Rules

Scanner type order:
1. explicit frameworks (`zephyr`, `godot`, `csharp_vs`, `python`, `nodejs`, etc.)
2. `empty` for empty/placeholder project folders
3. inferred types for unknowns by majority files:
   - `code_<lang>`
   - `data_<format>`

Examples:
- `code_python`
- `data_image`
- `empty`

## MkDocs Output

Landing page is consolidated into one page with:
- project link
- type/category/date
- folder link (last column)
- summary row below each item

Detail pages include metadata + README summary.

## Sharing Safely

Before pushing to a public Git remote:
1. run `python MyCatlog.py clean`
2. confirm `data/projects.json` is not staged
3. confirm `config/scan_config.yaml` is not staged
4. review `git status` and push only code/docs templates
