"""Data models for Docker Compose documentation."""

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EnvVarDoc:
    """Represents a documented environment variable."""
    name: str
    description: str
    default_value: Optional[str] = None


@dataclass
class ServiceDoc:
    """Represents documentation for a service and its environment variables."""
    name: str
    env_vars: List[EnvVarDoc]


@dataclass
class ServicesDoc:
    """Represents documentation for a list of services."""
    source_file: str
    services: List[ServiceDoc]

    def __post_init__(self):
        """Normalize source_file to show appropriate directory context for clarity."""
        self.source_file = self._get_display_path(self.source_file)

    def _get_display_path(self, file_path: str) -> str:
        """Get display path - just use the full relative path."""
        try:
            # Get relative path from current working directory
            rel_path = os.path.relpath(file_path, os.getcwd())

            # Add ./ prefix for files in current directory for clarity
            if '/' not in rel_path and '\\' not in rel_path:
                return f"./{rel_path}"

            return rel_path

        except (ValueError, OSError):
            # Fallback to basename if path operations fail
            return os.path.basename(file_path)
