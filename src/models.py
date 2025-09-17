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
        """Normalize the source_file to just the basename."""
        self.source_file = os.path.basename(self.source_file)
