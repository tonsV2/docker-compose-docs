"""Data models for Docker Compose documentation."""

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
    sourceFile: str
    services: List[ServiceDoc]
