"""
Project Scanner: Discovers Git repos and VS Code projects, extracts metadata.
Outputs a structured projects.json file for indexing and documentation generation.
"""

import json
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
from collections import Counter
import re
import yaml

# Configure encoding for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


class ProjectScanner:
    """Scans directories for projects and extracts metadata."""

    def __init__(self, config_path: Path):
        """Initialize scanner with config file."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.projects: List[Dict] = []
        self._project_paths: Set[str] = set()

    def _load_config(self) -> Dict:
        """Load configuration from YAML."""
        if not self.config_path.exists():
            return {"scan_paths": [], "categories": {}, "exclusions": [], "max_depth": 8}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return {"scan_paths": [], "categories": {}, "exclusions": [], "max_depth": 8}

    def _save_config(self) -> None:
        """Save configuration to YAML."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        print(f"✓ Config saved to {self.config_path}")

    @staticmethod
    def _should_skip(path: Path, exclusions: List[str]) -> bool:
        """Check if a path matches exclusion patterns."""
        path_str = str(path).lower()
        skip_patterns = exclusions + [
            'node_modules', '.venv', 'venv', '__pycache__', '.git/objects',
            '.vs', '.vscode/extensions', 'dist', 'build', '.pytest_cache'
        ]
        for pattern in skip_patterns:
            if pattern.lower() in path_str:
                return True
        return False

    def _is_git_repo(self, path: Path) -> bool:
        """Check if directory is a Git repository."""
        return (path / '.git').exists()

    def _is_vs_code_workspace(self, path: Path) -> bool:
        """Check if directory contains VS Code workspace files."""
        return any(path.glob('*.code-workspace')) or (path / '.vscode').exists()

    def _is_placeholder_folder(self, path: Path) -> bool:
        """Return True when folder is empty or only contains placeholder files."""
        placeholder_files = {'.gitkeep', '.keep', '.placeholder'}
        try:
            entries = [entry for entry in path.iterdir()]
        except Exception:
            return False

        if not entries:
            return True

        return all(entry.is_file() and entry.name.lower() in placeholder_files for entry in entries)

    def _has_lightweight_project_markers(self, path: Path) -> bool:
        """Detect lightweight/script-style repositories with minimal structure."""
        has_repo_layout = (path / '.github').exists() or (path / 'scripts').exists() or (path / 'docs').exists()
        has_source_files = any(path.glob('*.py')) or any(path.glob('*.sh')) or any(path.glob('*.ps1'))
        has_readme_like = any(path.glob('README*')) or (path / 'Notes.md').exists()
        has_build_files = (path / 'Dockerfile').exists() or (path / 'docker-compose.yml').exists()
        return (has_repo_layout and has_source_files and has_readme_like) or has_build_files

    def _is_project_dir(self, path: Path) -> bool:
        """Check if directory should be treated as a project."""
        if self._is_git_repo(path) or self._is_vs_code_workspace(path):
            return True

        if any(path.glob('*.sln')) or any(path.glob('*.csproj')):
            return True

        if (path / 'project.godot').exists():
            return True

        marker_files = [
            'package.json',
            'pyproject.toml',
            'setup.py',
            'requirements.txt',
            'Pipfile',
            'Cargo.toml',
            'CMakeLists.txt',
            'prj.conf',
        ]
        if any((path / marker).exists() for marker in marker_files):
            return True

        # Script-style Python projects often have .py files and dependency files,
        # but no pyproject.toml/setup.py.
        has_python_files = any(path.glob('*.py'))
        has_python_deps = (path / 'requirements.txt').exists() or (path / 'Pipfile').exists()
        if has_python_files and has_python_deps:
            return True

        return self._has_lightweight_project_markers(path)

    def _detect_project_type(self, path: Path) -> str:
        """Detect project type based on key files."""
        if self._is_placeholder_folder(path):
            return 'empty'

        if (path / 'prj.conf').exists() and (path / 'CMakeLists.txt').exists():
            return 'zephyr'
        if (path / 'micro:bit').exists() or (path / 'makefile').exists() and (path / 'main.cpp').exists():
            return 'microbit'
        if (path / 'package.json').exists():
            return 'nodejs'
        if (path / 'setup.py').exists() or (path / 'pyproject.toml').exists():
            return 'python'
        if (path / 'requirements.txt').exists() and any(path.glob('*.py')):
            return 'python'
        if (path / 'Cargo.toml').exists():
            return 'rust'
        if any(path.glob('*.sln')) or any(path.glob('*.csproj')):
            return 'csharp_vs'
        if (path / 'project.godot').exists():
            return 'godot'
        if self._has_lightweight_project_markers(path):
            return 'script_repo'
        return self._infer_unknown_type(path)

    def _infer_unknown_type(self, path: Path) -> str:
        """Infer unknown project type by majority file family and dominant subtype.

        Returns values like:
        - code_python
        - code_csharp
        - data_json
        - data_csv
        - unknown_mixed
        - unknown
        """
        code_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.cs': 'csharp',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.c': 'c',
            '.h': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.hpp': 'cpp',
            '.m': 'objc',
            '.swift': 'swift',
            '.php': 'php',
            '.rb': 'ruby',
            '.kt': 'kotlin',
            '.sh': 'shell',
            '.ps1': 'powershell',
            '.bat': 'batch',
            '.cmd': 'batch',
            '.sql': 'sql',
        }

        data_map = {
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.csv': 'csv',
            '.tsv': 'csv',
            '.parquet': 'parquet',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.sqlite': 'sqlite',
            '.db': 'sqlite',
            '.txt': 'text',
            '.md': 'markdown',
            '.log': 'log',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'ini',
            '.zip': 'archive',
            '.7z': 'archive',
            '.rar': 'archive',
            '.tar': 'archive',
            '.gz': 'archive',
            '.vsix': 'package',
            '.str': 'text',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.bmp': 'image',
            '.svg': 'image',
            '.mp3': 'audio',
            '.wav': 'audio',
            '.flac': 'audio',
            '.ogg': 'audio',
            '.mp4': 'video',
            '.mkv': 'video',
            '.avi': 'video',
        }

        code_counts: Counter = Counter()
        data_counts: Counter = Counter()

        max_depth = 3
        max_files = 1500
        scanned = 0

        stack = [(path, 0)]
        while stack and scanned < max_files:
            current, depth = stack.pop()
            if depth > max_depth:
                continue

            if self._should_skip(current, self.config.get('exclusions', [])):
                continue

            try:
                for entry in current.iterdir():
                    if entry.is_symlink():
                        continue
                    if entry.is_dir():
                        stack.append((entry, depth + 1))
                        continue

                    scanned += 1
                    suffix = entry.suffix.lower()
                    if suffix in code_map:
                        code_counts[code_map[suffix]] += 1
                    elif suffix in data_map:
                        data_counts[data_map[suffix]] += 1

                    if scanned >= max_files:
                        break
            except Exception:
                continue

        code_total = sum(code_counts.values())
        data_total = sum(data_counts.values())

        if code_total == 0 and data_total == 0:
            return 'unknown'

        if code_total > data_total:
            dominant = code_counts.most_common(1)[0][0]
            return f'code_{dominant}'

        if data_total > code_total:
            dominant = data_counts.most_common(1)[0][0]
            return f'data_{dominant}'

        return 'unknown_mixed'

    def _add_project(self, path: Path, force: bool = False) -> None:
        """Add project if not already indexed.

        When force=True, add path even if normal project markers are absent.
        This is used for folders explicitly listed in VS Code workspace files.
        """
        if not path.exists() or not path.is_dir():
            return

        if not force and not self._is_project_dir(path):
            return

        path_key = str(path.resolve()).lower()
        if path_key in self._project_paths:
            return

        project = self._extract_metadata(path)
        if force and 'workspace' not in project['tags']:
            project['tags'].append('workspace')

        self.projects.append(project)
        self._project_paths.add(path_key)

    def _ingest_workspace_file(self, workspace_file: Path, exclusions: List[str]) -> None:
        """Read a VS Code .code-workspace file and index its folder entries."""
        if self._should_skip(workspace_file, exclusions):
            return

        try:
            with open(workspace_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return

        folders = data.get('folders', [])
        for folder in folders:
            if not isinstance(folder, dict):
                continue
            raw_path = folder.get('path')
            if not raw_path:
                continue

            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = (workspace_file.parent / candidate).resolve()

            if self._should_skip(candidate, exclusions):
                continue

            # Avoid indexing technical metadata folders as standalone projects.
            if candidate.name in {'.github', '.vscode', '.idea'}:
                continue

            self._add_project(candidate, force=True)

    def _get_last_modified(self, path: Path) -> str:
        """Get last modified date of directory."""
        try:
            git_path = path / '.git' / 'HEAD'
            if git_path.exists():
                timestamp = git_path.stat().st_mtime
            else:
                timestamp = path.stat().st_mtime
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        except Exception:
            return datetime.now().strftime('%Y-%m-%d')

    def _read_readme_excerpt(self, readme_path: Path, max_chars: int = 700) -> str:
        """Read a concise README excerpt for summary display."""
        try:
            raw = readme_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return ''

        cleaned_lines = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('#'):
                continue
            if stripped.startswith('![') or stripped.startswith('['):
                # Skip badges and link-only lines.
                continue
            cleaned_lines.append(stripped)

            if sum(len(x) for x in cleaned_lines) >= max_chars:
                break

        excerpt = ' '.join(cleaned_lines)
        if len(excerpt) > max_chars:
            excerpt = excerpt[: max_chars - 3].rstrip() + '...'
        return excerpt

    def _extract_metadata(self, path: Path) -> Dict:
        """Extract metadata from a project directory."""
        project_name = path.name
        project_id = self._make_project_id(path, project_name)
        
        # Read README
        readme_path = None
        for readme_name in ['README.md', 'README.txt', 'readme.md']:
            candidate = path / readme_name
            if candidate.exists():
                readme_path = candidate
                break

        readme_excerpt = self._read_readme_excerpt(readme_path) if readme_path else ''
        readme_file = str(readme_path.relative_to(path)) if readme_path else ''

        # Detect diagrams
        diagrams = []
        for dot_file in path.rglob('*.dot'):
            if not self._should_skip(dot_file, []):
                diagrams.append(str(dot_file.relative_to(path)))

        # Detect project type
        project_type = self._detect_project_type(path)

        # Get tags from metadata if available
        tags = [project_type] if project_type not in {'unknown', 'empty'} else []
        
        # Try to read metadata from a .metadata.json file if it exists
        metadata_file = path / '.metadata.json'
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    tags.extend(metadata.get('tags', []))
            except Exception:
                pass

        # Determine category based on path patterns
        category = self._determine_category(path)

        return {
            'id': project_id,
            'name': project_name,
            'path': str(path),
            'category': category,
            'type': project_type,
            'tags': list(set(tags)),  # Remove duplicates
            'has_readme': readme_path is not None,
            'readme_file': readme_file,
            'readme_excerpt': readme_excerpt,
            'diagrams': diagrams,
            'last_modified': self._get_last_modified(path)
        }

    def _make_project_id(self, path: Path, project_name: str) -> str:
        """Create a stable, unique ID for project pages and links."""
        slug = re.sub(r'[^a-z0-9_-]+', '-', project_name.lower()).strip('-')
        if not slug:
            slug = 'project'

        path_key = str(path.resolve()).lower().encode('utf-8', errors='ignore')
        suffix = hashlib.sha1(path_key).hexdigest()[:8]
        return f"{slug}-{suffix}"

    def _determine_category(self, path: Path) -> str:
        """Determine if project is work or personal based on path patterns."""
        path_str = str(path).lower()
        
        # Check against defined categories
        for category, patterns in self.config.get('categories', {}).items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                # Simple glob matching
                if '*' in pattern_lower:
                    pattern_regex = pattern_lower.replace('*', '.*')
                    if re.match(pattern_regex, path_str):
                        return category
                elif pattern_lower in path_str:
                    return category
        
        # Default heuristic
        if 'work' in path_str or 'company' in path_str or 'client' in path_str:
            return 'work'
        return 'personal'

    def prompt_for_scan_paths(self) -> None:
        """Interactively prompt user for directories to scan."""
        print("\n" + "="*60)
        print("PROJECT CATALOGUE SETUP")
        print("="*60)
        print("\nEnter top-level directories to scan for projects.")
        print("(Leave blank when done)\n")

        scan_paths = []
        index = 1

        while True:
            user_input = input(f"Path {index}: ").strip()
            
            if not user_input:
                if scan_paths:
                    break
                else:
                    print("Please enter at least one path.")
                    continue

            path = Path(user_input).expanduser().resolve()
            
            if not path.exists():
                print(f"  ✗ Path does not exist: {path}")
                continue
            
            if not path.is_dir():
                print(f"  ✗ Not a directory: {path}")
                continue

            if path in [Path(p) for p in scan_paths]:
                print(f"  ✗ Already added: {path}")
                continue

            scan_paths.append(str(path))
            print(f"  ✓ Added: {path}")
            index += 1

        self.config['scan_paths'] = scan_paths
        self._save_config()

        print(f"\n✓ Configuration saved with {len(scan_paths)} path(s)")

    def scan(self) -> List[Dict]:
        """Scan configured directories for projects."""
        self.projects = []
        self._project_paths = set()
        scan_paths = self.config.get('scan_paths', [])
        exclusions = self.config.get('exclusions', [])
        max_depth = int(self.config.get('max_depth', 8))

        if not scan_paths:
            print("No scan paths configured. Run 'init' first.")
            return []

        print(f"\nScanning {len(scan_paths)} path(s)...\n")

        for scan_path in scan_paths:
            scan_root = Path(scan_path)
            if not scan_root.exists():
                print(f"⚠ Skipping non-existent path: {scan_root}")
                continue

            print(f"Scanning: {scan_root}")
            self._scan_directory(scan_root, exclusions, max_depth=max_depth, keep_descending=True)

        print(f"\n✓ Found {len(self.projects)} project(s)")
        return self.projects

    def _scan_directory(
        self,
        root: Path,
        exclusions: List[str],
        depth: int = 0,
        max_depth: int = 8,
        keep_descending: bool = False,
    ) -> None:
        """Recursively scan directory for projects."""
        if depth > max_depth:
            return

        if self._should_skip(root, exclusions):
            return

        try:
            # Index folders referenced in workspace files at this level.
            for workspace_file in root.glob('*.code-workspace'):
                self._ingest_workspace_file(workspace_file, exclusions)

            # Check if this directory is a project
            if self._is_project_dir(root):
                self._add_project(root)

                # For configured scan roots we continue descending to find nested projects.
                if not keep_descending:
                    return

            # Recurse into subdirectories
            for entry in root.iterdir():
                if entry.is_dir() and not entry.is_symlink():
                    self._scan_directory(
                        entry,
                        exclusions,
                        depth + 1,
                        max_depth=max_depth,
                        keep_descending=False,
                    )
        except PermissionError:
            pass
        except Exception as e:
            print(f"Warning: Error scanning {root}: {e}")

    def export_json(self, output_path: Path) -> None:
        """Export projects to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sort by name
        sorted_projects = sorted(self.projects, key=lambda p: p['name'].lower())
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_projects, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Exported {len(sorted_projects)} project(s) to {output_path}")

    def list_projects(self) -> None:
        """Display all discovered projects."""
        if not self.projects:
            print("No projects found.")
            return

        print(f"\n{'Project':<28} {'Type':<18} {'Category':<10} {'Modified':<12} {'Path'}")
        print("-" * 140)
        
        for proj in sorted(self.projects, key=lambda p: p['name'].lower()):
            print(
                f"{proj['name']:<28} {proj['type']:<18} {proj['category']:<10} "
                f"{proj['last_modified']:<12} {proj['path']}"
            )
        
        print(f"\nTotal: {len(self.projects)} project(s)")


if __name__ == '__main__':
    print("Use cli.py to run this scanner.")
