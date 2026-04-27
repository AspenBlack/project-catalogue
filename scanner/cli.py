#!/usr/bin/env python3
"""
CLI for the Project Catalogue Scanner.

Usage:
    python cli.py init      - First-time setup (configure scan paths)
    python cli.py scan      - Run project discovery
    python cli.py list      - Show discovered projects
"""

import sys
import argparse
from pathlib import Path
from project_scanner import ProjectScanner


def get_config_path() -> Path:
    """Get the config file path."""
    return Path(__file__).parent.parent / 'config' / 'scan_config.yaml'


def get_projects_json_path() -> Path:
    """Get the projects.json output path."""
    return Path(__file__).parent.parent / 'data' / 'projects.json'


def cmd_init(args):
    """Initialize the scanner with user configuration."""
    config_path = get_config_path()
    scanner = ProjectScanner(config_path)
    scanner.prompt_for_scan_paths()


def cmd_scan(args):
    """Scan configured directories for projects."""
    config_path = get_config_path()
    
    if not config_path.exists():
        print("Error: Not initialized. Run 'python cli.py init' first.")
        sys.exit(1)
    
    scanner = ProjectScanner(config_path)
    projects = scanner.scan()
    
    if projects:
        output_path = get_projects_json_path()
        scanner.export_json(output_path)
        print(f"\n✓ Ready to build documentation with MkDocs")
    else:
        print("\n⚠ No projects found. Check your scan paths with 'python cli.py list'")


def cmd_list(args):
    """List discovered projects."""
    config_path = get_config_path()
    
    if not config_path.exists():
        print("Error: Not initialized. Run 'python cli.py init' first.")
        sys.exit(1)
    
    scanner = ProjectScanner(config_path)
    
    # Try to load from projects.json if available
    projects_json_path = get_projects_json_path()
    if projects_json_path.exists():
        import json
        with open(projects_json_path, 'r', encoding='utf-8') as f:
            scanner.projects = json.load(f)
        print(f"Loaded from {projects_json_path}")
    else:
        scanner.scan()
    
    scanner.list_projects()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Project Catalogue Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py init   - Configure which directories to scan
  python cli.py scan   - Discover projects and generate projects.json
  python cli.py list   - Show all discovered projects
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Init command
    subparsers.add_parser('init', help='Initialize and configure scan paths')

    # Scan command
    subparsers.add_parser('scan', help='Run project discovery scan')

    # List command
    subparsers.add_parser('list', help='List discovered projects')

    args = parser.parse_args()

    if args.command == 'init':
        cmd_init(args)
    elif args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'list':
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
