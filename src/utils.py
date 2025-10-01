"""Utility functions for Docker Compose documentation generation."""

import glob
import os
import sys
from typing import List


def find_compose_files(directory: str) -> List[str]:
    """Find all Docker Compose files in a directory."""
    compose_files = []

    # Common Docker Compose file patterns
    patterns = [
        "docker-compose.yml",
        "docker-compose.yaml",
        "docker-compose.*.yml",
        "docker-compose.*.yaml",
        "compose.yml",
        "compose.yaml",
    ]

    for pattern in patterns:
        full_pattern = os.path.join(directory, pattern)
        compose_files.extend(glob.glob(full_pattern))

    # Remove duplicates
    unique_files = list(set(compose_files))

    # Sort with priority: main files first, then others alphabetically
    return sort_compose_files(unique_files)


def sort_compose_files(files: List[str]) -> List[str]:
    """Sort compose files with main files first, then others alphabetically."""
    if not files:
        return files

    main_files = []
    override_files = []
    other_files = []

    for file in files:
        basename = os.path.basename(file)
        if basename in [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]:
            main_files.append(file)
        elif "override" in basename:
            override_files.append(file)
        else:
            other_files.append(file)

    # Sort each category alphabetically
    main_files.sort()
    override_files.sort()
    other_files.sort()

    # Return in priority order
    return main_files + override_files + other_files


def parse_paths_from_string(paths_str: str) -> List[str]:
    """Parse semicolon-separated paths string into list of paths."""
    if not paths_str:
        return []

    paths = [path.strip() for path in paths_str.split(";")]
    return [path for path in paths if path]  # Remove empty strings


def collect_compose_files_from_globs(globs: List[str]) -> List[str]:
    """Collect all docker compose files matching the given glob patterns."""
    all_files = []

    for glob_pattern in globs:
        files = glob.glob(glob_pattern, recursive=True)
        all_files.extend(files)

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file in all_files:
        abs_path = os.path.abspath(file)
        if abs_path not in seen:
            seen.add(abs_path)
            unique_files.append(file)

    return sort_compose_files(unique_files)


def collect_compose_files(paths: List[str]) -> List[str]:
    """Collect all docker compose files from the given paths (files and directories)."""
    all_files = []

    for path in paths:
        if os.path.isfile(path):
            all_files.append(path)
        elif os.path.isdir(path):
            directory_files = find_compose_files(path)
            all_files.extend(directory_files)
        else:
            print(f"Warning: Path not found, skipping: {path}", file=sys.stderr)

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file in all_files:
        abs_path = os.path.abspath(file)
        if abs_path not in seen:
            seen.add(abs_path)
            unique_files.append(file)

    return unique_files
