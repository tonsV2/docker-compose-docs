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
    parent_property: Optional[str] = None


@dataclass
class ServiceDoc:
    """Represents documentation for a service and its environment variables."""
    name: str
    env_vars: List[EnvVarDoc]
    description: str = ""


@dataclass
class ServicesDoc:
    """Represents documentation for a list of services."""
    source_file: str
    services: List[ServiceDoc]

    def __post_init__(self):
        """Normalize source_file to show appropriate directory context for clarity."""
        self.source_file = self._get_display_path(self.source_file)

    def _get_display_path(self, file_path: str) -> str:
        """Get display path - map container paths to host paths for Docker."""
        try:
            # Map Docker container paths back to host paths
            if file_path.startswith("/src/"): # TODO: Shouldn't be hardcoded, get from a environment variable
                host_path = "." + file_path[4:]  # /src -> .
                return host_path

            # For non-mounted paths, use the relative path from the current directory
            rel_path = os.path.relpath(file_path, os.getcwd())

            # Add ./ prefix for files in the current directory for clarity
            if "/" not in rel_path and "\\" not in rel_path:
                return f"./{rel_path}"

            return rel_path

        except (ValueError, OSError):
            # Fallback to basename if path operations fail
            return os.path.basename(file_path)
