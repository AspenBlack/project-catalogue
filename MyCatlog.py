#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCANNER_DIR = ROOT / "scanner"
MKDOCS_DIR = ROOT / "mkdocs"
PID_FILE = ROOT / ".mkdocs-serve.pid"
PROJECTS_JSON = ROOT / "data" / "projects.json"

STANDARD_WORKFLOW = """Standard workflow:
    1) python MyCatlog.py init
    2) python MyCatlog.py scan
    3) python MyCatlog.py build-docs
    4) python MyCatlog.py serve --background
    5) python MyCatlog.py stop

Command-specific help:
    python MyCatlog.py help serve
    python MyCatlog.py help build-docs
"""


def run_cmd(cmd: list[str], cwd: Path | None = None) -> int:
    print(">", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None).returncode


def ensure_ok(code: int, step: str) -> None:
    if code != 0:
        raise SystemExit(f"[ERROR] {step} failed with exit code {code}")


def _write_pid(pid: int) -> None:
    PID_FILE.write_text(str(pid), encoding="utf-8")


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _clear_pid() -> None:
    if PID_FILE.exists():
        PID_FILE.unlink()


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cmd_init(_: argparse.Namespace) -> None:
    ensure_ok(run_cmd([sys.executable, "cli.py", "init"], cwd=SCANNER_DIR), "init")


def cmd_scan(_: argparse.Namespace) -> None:
    ensure_ok(run_cmd([sys.executable, "cli.py", "scan"], cwd=SCANNER_DIR), "scan")


def cmd_list(_: argparse.Namespace) -> None:
    ensure_ok(run_cmd([sys.executable, "cli.py", "list"], cwd=SCANNER_DIR), "list")


def cmd_build_docs(args: argparse.Namespace) -> None:
    if not args.no_scan:
        cmd_scan(args)
    ensure_ok(run_cmd([sys.executable, "generate_pages.py"], cwd=MKDOCS_DIR), "build-docs")
    print("[OK] Documentation built successfully.")
    print("     View it with: python MyCatlog.py serve")


def cmd_serve(args: argparse.Namespace) -> None:
    if not args.no_build:
        ensure_ok(run_cmd([sys.executable, "generate_pages.py"], cwd=MKDOCS_DIR), "build-docs")

    existing_pid = _read_pid()
    if existing_pid and _is_process_running(existing_pid):
        print(f"[WARN] MkDocs server already running with PID {existing_pid}")
        print(f"       Open http://{args.host}:{args.port} in your browser")
        return

    serve_cmd = [
        sys.executable,
        "-m",
        "mkdocs",
        "serve",
        "--dev-addr",
        f"{args.host}:{args.port}",
    ]

    print("Starting local server...")
    print(f"Open http://{args.host}:{args.port} in your browser")

    if args.background:
        popen_kwargs = {
            "cwd": str(MKDOCS_DIR),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            popen_kwargs["start_new_session"] = True

        proc = subprocess.Popen(serve_cmd, **popen_kwargs)
        _write_pid(proc.pid)
        print(f"[OK] MkDocs server started in background (PID {proc.pid})")
        print("     Stop it with: python MyCatlog.py stop")
        return

    proc = subprocess.Popen(serve_cmd, cwd=str(MKDOCS_DIR))
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Stopping MkDocs server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[OK] Server stopped cleanly.")


def cmd_stop(_: argparse.Namespace) -> None:
    pid = _read_pid()
    if not pid:
        print("[INFO] No background MkDocs server PID file found.")
        return

    if not _is_process_running(pid):
        _clear_pid()
        print("[INFO] No running server found for recorded PID. Cleaned up stale PID file.")
        return

    print(f"Stopping MkDocs server PID {pid}...")
    if os.name == "nt":
        forced = False
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            forced = True
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    else:
        import signal

        os.kill(pid, signal.SIGTERM)
        forced = False

    time.sleep(0.3)
    _clear_pid()
    if forced:
        print("[OK] Server stopped (force-terminated by OS).")
    else:
        print("[OK] Server stopped.")


def cmd_all(args: argparse.Namespace) -> None:
    cmd_build_docs(args)
    args.no_build = True
    cmd_serve(args)


def cmd_clean(_: argparse.Namespace) -> None:
    site_dir = MKDOCS_DIR / "site"
    if site_dir.exists():
        shutil.rmtree(site_dir)
        print(f"[OK] Removed {site_dir}")

    if PROJECTS_JSON.exists():
        PROJECTS_JSON.unlink()
        print(f"[OK] Removed {PROJECTS_JSON}")

    legacy_projects_json = ROOT / "projects.json"
    if legacy_projects_json.exists():
        legacy_projects_json.unlink()
        print(f"[OK] Removed legacy file {legacy_projects_json}")

    projects_dir = MKDOCS_DIR / "docs" / "projects"
    if projects_dir.exists():
        for md in projects_dir.glob("*.md"):
            if md.name != "index.md":
                md.unlink()
        print("[OK] Removed generated project markdown files")

    print("Clean complete.")


def cmd_setup(args: argparse.Namespace) -> None:
    ensure_ok(run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=ROOT), "pip install")
    cmd_init(args)
    cmd_scan(args)
    cmd_build_docs(args)


def cmd_help(args: argparse.Namespace) -> None:
    parser = args._parser
    command = args.command_name
    if command:
        try:
            parser.parse_args([command, "-h"])
        except SystemExit:
            pass
        return

    parser.print_help()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="MyCatlog.py",
        description="Project Catalogue main CLI",
        epilog=STANDARD_WORKFLOW,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    help_parser = sub.add_parser("help", help="Show help, workflow, and command-specific help examples")
    help_parser.add_argument("command_name", nargs="?", help="Optional command name")
    help_parser.set_defaults(func=cmd_help)

    sub.add_parser("init", help="Configure scan paths").set_defaults(func=cmd_init)
    sub.add_parser("scan", help="Discover projects and generate projects.json").set_defaults(func=cmd_scan)
    sub.add_parser("list", help="Show discovered projects").set_defaults(func=cmd_list)

    build_docs = sub.add_parser("build-docs", help="Generate documentation pages")
    build_docs.add_argument("--no-scan", action="store_true", help="Skip scan step")
    build_docs.set_defaults(func=cmd_build_docs)

    serve = sub.add_parser("serve", help="Serve MkDocs locally")
    serve.add_argument("--host", default="127.0.0.1", help="Host for MkDocs dev server")
    serve.add_argument("--port", type=int, default=8000, help="Port for MkDocs dev server")
    serve.add_argument("--no-build", action="store_true", help="Skip docs generation before serving")
    serve.add_argument("--background", action="store_true", help="Run server in background")
    serve.set_defaults(func=cmd_serve)

    sub.add_parser("stop", help="Stop background MkDocs server").set_defaults(func=cmd_stop)

    all_cmd = sub.add_parser("all", help="build-docs + serve")
    all_cmd.add_argument("--no-scan", action="store_true", help="Skip scan step")
    all_cmd.add_argument("--host", default="127.0.0.1", help="Host for MkDocs dev server")
    all_cmd.add_argument("--port", type=int, default=8000, help="Port for MkDocs dev server")
    all_cmd.add_argument("--no-build", action="store_true", help="Skip docs generation before serving")
    all_cmd.add_argument("--background", action="store_true", help="Run server in background")
    all_cmd.set_defaults(func=cmd_all)

    sub.add_parser("clean", help="Remove generated files").set_defaults(func=cmd_clean)

    setup = sub.add_parser("setup", help="Install deps + init + scan + build-docs")
    setup.add_argument("--no-scan", action="store_true", help="Skip scan during build-docs")
    setup.set_defaults(func=cmd_setup)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args._parser = parser
    args.func(args)


if __name__ == "__main__":
    main()