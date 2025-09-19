"""Docker Compose file parser for environment variable documentation."""

import re
from typing import Dict, List, Any, Optional

import yaml

from .models import EnvVarDoc, ServiceDoc, ServicesDoc


class DockerComposeParser:
    """Parses Docker Compose files and extracts environment variable documentation."""

    def __init__(self, compose_file_path: str):
        self.compose_file_path = compose_file_path
        self.compose_content: Optional[Dict[str, Any]] = None
        self.raw_content: Optional[str] = None

    def parse(self) -> ServicesDoc:
        """Parse the Docker Compose file and return service documentation."""
        self._load_compose_file()
        services_docs: List[ServiceDoc] = []

        if self.compose_content is None or "services" not in self.compose_content:
            return ServicesDoc(source_file=self.compose_file_path, services=[])

        for service_name, service_config in self.compose_content["services"].items():
            env_vars = self._extract_env_vars_with_docs(service_name, service_config)
            if env_vars:
                services_docs.append(ServiceDoc(name=service_name, env_vars=env_vars))

        return ServicesDoc(source_file=self.compose_file_path, services=services_docs)

    def _load_compose_file(self) -> None:
        """Load and parse the Docker Compose file."""
        try:
            with open(self.compose_file_path, "r", encoding="utf-8") as f:
                self.raw_content = f.read()
                self.compose_content = yaml.safe_load(self.raw_content)
        except FileNotFoundError:
            raise FileNotFoundError(f"Docker Compose file not found: {self.compose_file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in Docker Compose file: {e}")

    def _parse_default_value(self, value: Optional[str]) -> Optional[str]:
        """
        Parse Docker Compose variable substitution syntax to extract default values.

        Docker Compose supports these patterns:
        - ${VAR:-default} -> "default" (if VAR is unset or empty)
        - ${VAR-default} -> "default" (if VAR is unset)
        - ${VAR} or $VAR -> None (no default provided)
        - regular_value -> "regular_value" (literal value)
        """
        if value is None:
            return None

        # Pattern for Docker Compose variable substitution with defaults
        # Only matches: ${VAR:-default} and ${VAR-default}
        default_pattern = r"\$\{[^}]+(-|:-)([^}]*)\}"
        match = re.search(default_pattern, value)

        if match:
            return match.group(2)

        # Check if it's a variable reference without default: ${VAR} or $VAR
        if re.match(r"^\$\{[^}]+}$|^\$[A-Za-z_][A-Za-z0-9_]*$", value):
            return None

        # If it's not a variable substitution, return the value as-is
        return value

    def _extract_env_vars_with_docs(self, service_name: str, service_config: Dict[str, Any]) -> List[EnvVarDoc]:
        """Extract environment variables with documentation comments for a service."""
        env_vars: List[EnvVarDoc] = []

        if "environment" not in service_config:
            return env_vars

        service_lines = self._get_service_raw_lines(service_name)

        env_section_start = None
        for i, line in enumerate(service_lines):
            if re.match(r"\s*environment:\s*$", line):
                env_section_start = i + 1
                break

        if env_section_start is None:
            return env_vars

        env_config = service_config["environment"]

        if isinstance(env_config, dict):
            env_vars.extend(self._parse_dict_environment(env_config, service_lines, env_section_start))
        elif isinstance(env_config, list):
            env_vars.extend(self._parse_list_environment(env_config, service_lines, env_section_start))

        return env_vars

    def _get_service_raw_lines(self, service_name: str) -> List[str]:
        """Get raw lines for a specific service from the Docker Compose file."""
        if self.raw_content is None:
            return []
        lines = self.raw_content.split("\n")
        service_lines = []
        in_service = False
        service_indent = None

        for line in lines:
            # Only match service definitions at the proper indentation level (typically 2 spaces)
            # This avoids matching dependency references that have the same service name
            if re.match(rf"^\s{{2}}{re.escape(service_name)}:\s*$", line):
                in_service = True
                service_indent = len(line) - len(line.lstrip())
                service_lines.append(line)
                continue

            if in_service:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else float("inf")

                # Check if we've moved to another service at the same level
                if line.strip() and service_indent is not None and current_indent <= service_indent and ":" in line:
                    break

                service_lines.append(line)

        return service_lines

    def _parse_dict_environment(self, env_config: Dict[str, Any], service_lines: List[str], start_line: int) -> List[
        EnvVarDoc]:
        """Parse dictionary-style environment configuration."""
        env_vars: List[EnvVarDoc] = []

        if not env_config:
            return env_vars

        for var_name, var_value in env_config.items():
            comment = DockerComposeParser._find_comment_for_var(var_name, service_lines, start_line)
            if comment:
                parsed_default = self._parse_default_value(str(var_value)) if var_value is not None else None
                env_vars.append(EnvVarDoc(var_name, comment, parsed_default))

        return env_vars

    def _parse_list_environment(self, env_config: List[str], service_lines: List[str], start_line: int) -> List[
        EnvVarDoc]:
        """Parse list-style environment configuration."""
        env_vars: List[EnvVarDoc] = []

        if not env_config:
            return env_vars

        for env_entry in env_config:
            if not env_entry:
                continue

            if env_entry is None:
                continue

            env_entry_str = str(env_entry)

            if "=" in env_entry_str:
                var_name, var_value = env_entry_str.split("=", 1)
            else:
                var_name, var_value = env_entry_str, None

            var_name = var_name.strip()

            comment = DockerComposeParser._find_comment_for_var(var_name, service_lines, start_line)

            if comment:
                parsed_default = self._parse_default_value(var_value) if var_value is not None else None
                env_vars.append(EnvVarDoc(var_name, comment, parsed_default))

        return env_vars

    @staticmethod
    def _find_comment_for_var(var_name: str, service_lines: List[str], start_line: int) -> Optional[str]:
        """Find the documentation comment for a specific environment variable."""
        if not service_lines or start_line >= len(service_lines):
            return None

        # Look for the variable in the service lines
        for i in range(start_line, len(service_lines)):
            line = service_lines[i]

            if not line:
                continue

            line_stripped = line.strip()
            var_found = False

            # Handle both list and dictionary environment formats:
            # - VAR_NAME: value
            # - - VAR_NAME=value
            if ":" in line_stripped and not line_stripped.startswith("-"):
                var_in_line = line_stripped.split(":")[0].strip()
                var_found = var_in_line == var_name
            elif line_stripped.startswith("- ") and "=" in line_stripped:
                list_content = line_stripped[2:].strip()  # Remove "- "
                var_in_line = list_content.split("=")[0].strip()
                var_found = var_in_line == var_name

            if var_found:
                # Look backward for a comment, skipping YAML anchor lines
                for j in range(i - 1, max(start_line - 1, -1), -1):
                    if j < 0:
                        break
                    prev_line = service_lines[j].strip()

                    if not prev_line:
                        continue

                    # Skip YAML anchor/merge lines: <<: *anchor_name
                    if prev_line.startswith("<<:") or "<<:" in prev_line:
                        continue

                    # Check for regular comment: # -- description
                    if prev_line.startswith("# --"):
                        return prev_line[4:].strip()

                    # Check for list comment: - # -- description
                    if prev_line.startswith("- # --"):
                        return prev_line[6:].strip()

                    # Stop if we hit a non-comment line
                    if not prev_line.startswith("#") and not prev_line.startswith("- #"):
                        break

        return None
