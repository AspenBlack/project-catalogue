# Quick Start

## Install

```bash
pip install -r requirements.txt
```

## First Run

```bash
python MyCatlog.py init
python MyCatlog.py scan
python MyCatlog.py build-docs
python MyCatlog.py serve --background
```

Open the local site at `http://127.0.0.1:8000`.

Stop the server cleanly:

```bash
python MyCatlog.py stop
```

## Common Commands

```bash
python MyCatlog.py help
python MyCatlog.py help serve
python MyCatlog.py list
python MyCatlog.py clean
```

## Data Locations

- Generated project index: `data/projects.json`
- Local config: `config/scan_config.yaml`
- Generated project pages: `mkdocs/docs/projects/`
- Built static site: `mkdocs/site/`

## Typical Update Cycle

```bash
python MyCatlog.py scan
python MyCatlog.py build-docs
```

## Notes

- `serve` prebuilds docs by default.
- `serve --no-build` skips regeneration.
- `build-docs` reads from `data/projects.json`.
- `clean` removes generated docs, site output, and generated data.
