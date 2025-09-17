#!/usr/bin/env python3
"""
Docker Compose Environment Variable Documentation Generator

Parses Docker Compose files and generates documentation for environment variables
that are commented with '# -- <description>' format.
"""

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

import sys
import yaml


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


class DockerComposeParser:
    """Parses Docker Compose files and extracts environment variable documentation."""

    def __init__(self, compose_file_path: str):
        self.compose_file_path = compose_file_path
        self.compose_content = None
        self.raw_content = None

    def parse(self) -> List[ServiceDoc]:
        """Parse the Docker Compose file and return service documentation."""
        self._load_compose_file()
        services_docs = []

        if 'services' not in self.compose_content:
            return services_docs

        for service_name, service_config in self.compose_content['services'].items():
            env_vars = self._extract_env_vars_with_docs(service_name, service_config)
            if env_vars:
                services_docs.append(ServiceDoc(name=service_name, env_vars=env_vars))

        return services_docs

    def _load_compose_file(self) -> None:
        """Load and parse the Docker Compose file."""
        try:
            with open(self.compose_file_path, 'r', encoding='utf-8') as f:
                self.raw_content = f.read()
                self.compose_content = yaml.safe_load(self.raw_content)
        except FileNotFoundError:
            raise FileNotFoundError(f"Docker Compose file not found: {self.compose_file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in Docker Compose file: {e}")

    def _extract_env_vars_with_docs(self, service_name: str, service_config: Dict[str, Any]) -> List[EnvVarDoc]:
        """Extract environment variables with documentation comments for a service."""
        env_vars = []

        if 'environment' not in service_config:
            return env_vars

        service_lines = self._get_service_raw_lines(service_name)

        env_section_start = None
        for i, line in enumerate(service_lines):
            if re.match(r'\s*environment:\s*$', line):
                env_section_start = i + 1
                break

        if env_section_start is None:
            return env_vars

        env_config = service_config['environment']

        if isinstance(env_config, dict):
            env_vars.extend(self._parse_dict_environment(env_config, service_lines, env_section_start))
        elif isinstance(env_config, list):
            env_vars.extend(self._parse_list_environment(env_config, service_lines, env_section_start))

        return env_vars

    def _get_service_raw_lines(self, service_name: str) -> List[str]:
        """Get raw lines for a specific service from the Docker Compose file."""
        lines = self.raw_content.split('\n')
        service_lines = []
        in_service = False
        service_indent = None

        for line in lines:
            if re.match(rf'\s*{re.escape(service_name)}:\s*$', line):
                in_service = True
                service_indent = len(line) - len(line.lstrip())
                service_lines.append(line)
                continue

            if in_service:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else float('inf')

                # Check if we've moved to another service at the same level
                if line.strip() and current_indent <= service_indent and ':' in line:
                    break

                service_lines.append(line)

        return service_lines

    def _parse_dict_environment(self, env_config: Dict[str, Any], service_lines: List[str], start_line: int) -> List[
        EnvVarDoc]:
        """Parse dictionary-style environment configuration."""
        env_vars = []

        if not env_config:
            return env_vars

        for var_name, var_value in env_config.items():
            comment = self._find_comment_for_var(var_name, service_lines, start_line)
            if comment:
                default_value = str(var_value) if var_value is not None else None
                env_vars.append(EnvVarDoc(
                    name=var_name,
                    description=comment,
                    default_value=default_value
                ))

        return env_vars

    def _parse_list_environment(self, env_config: List[str], service_lines: List[str], start_line: int) -> List[
        EnvVarDoc]:
        """Parse list-style environment configuration."""
        env_vars = []

        if not env_config:
            return env_vars

        for env_entry in env_config:
            if not env_entry:
                continue

            if env_entry is None:
                continue

            env_entry_str = str(env_entry)

            if '=' in env_entry_str:
                var_name, var_value = env_entry_str.split('=', 1)
            else:
                var_name, var_value = env_entry_str, None

            var_name = var_name.strip()

            comment = self._find_comment_for_var(var_name, service_lines, start_line)

            if comment:
                env_vars.append(EnvVarDoc(var_name, comment, var_value))

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
            if ':' in line_stripped and not line_stripped.startswith('-'):
                var_in_line = line_stripped.split(':')[0].strip()
                var_found = (var_in_line == var_name)
            elif line_stripped.startswith('- ') and '=' in line_stripped:
                list_content = line_stripped[2:].strip()  # Remove "- "
                var_in_line = list_content.split('=')[0].strip()
                var_found = (var_in_line == var_name)

            if var_found:
                # Look backward for a comment
                for j in range(i - 1, max(start_line - 1, -1), -1):
                    if j < 0:
                        break
                    prev_line = service_lines[j].strip()

                    if not prev_line:
                        continue

                    # Check for regular comment: # -- description
                    if prev_line.startswith('# --'):
                        return prev_line[4:].strip()

                    # Check for list comment: - # -- description
                    if prev_line.startswith('- # --'):
                        return prev_line[6:].strip()

                    # Stop if we hit a non-comment line
                    if not prev_line.startswith('#') and not prev_line.startswith('- #'):
                        break

        return None


class OutputGenerator(ABC):
    """Abstract base class for output generators."""

    @abstractmethod
    def generate(self, services_docs: List[ServiceDoc]) -> str:
        """Generate output from service documentation."""
        pass


class MarkdownGenerator(OutputGenerator):
    """Generates Markdown documentation from service documentation."""

    def generate(self, services_docs: List[ServiceDoc]) -> str:
        """Generate Markdown documentation."""
        if not services_docs:
            return "# Environment Variables Documentation\n\nNo documented environment variables found.\n"

        output = ["# Environment Variables Documentation\n"]

        for service_doc in services_docs:
            output.append(f"## Service: {service_doc.name}\n")

            if not service_doc.env_vars:
                output.append("No documented environment variables.\n")
                continue

            output.append("| Variable | Description | Default Value |")
            output.append("|----------|-------------|---------------|")

            for env_var in service_doc.env_vars:
                default_val = env_var.default_value if env_var.default_value is not None else ""
                # Escape pipe characters in content
                name = env_var.name.replace("|", "\\|") if env_var.name else ""
                desc = env_var.description.replace("|", "\\|") if env_var.description else ""
                default = default_val.replace("|", "\\|") if default_val else ""

                output.append(f"| `{name}` | {desc} | `{default}` |")

            output.append("")  # Empty line between services

        return "\n".join(output)


def main():
    """Main function."""
    compose_file = None

    # 1. File was provided as an argument
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        compose_file = sys.argv[1]

    # 2. File was provided by environment variables
    if compose_file is None:
        docker_compose_path = os.environ.get('DOCKER_COMPOSE_FILE_PATH')
        docker_compose_name = os.environ.get('DOCKER_COMPOSE_FILE_NAME')

        if docker_compose_path:
            if docker_compose_name:
                # Check for a specific file name in the path
                candidate_file = os.path.join(docker_compose_path, docker_compose_name)
                if os.path.isfile(candidate_file):
                    compose_file = candidate_file
            else:
                # Check for default docker-compose files in env path
                for filename in ['docker-compose.yml', 'docker-compose.yaml']:
                    candidate_file = os.path.join(docker_compose_path, filename)
                    if os.path.isfile(candidate_file):
                        compose_file = candidate_file
                        break

    # 3. File was provided through default paths
    if compose_file is None:
        default_paths = [
            '/data/docker-compose.yml',
            '/data/docker-compose.yaml',
            '/src/docker-compose.yml',
            '/src/docker-compose.yaml'
        ]

        for path in default_paths:
            if os.path.isfile(path):
                compose_file = path
                break

    # If no file is found, show usage
    if compose_file is None:
        print("Usage: python docker_compose_docs.py <docker-compose.yml>")
        print("Or set DOCKER_COMPOSE_FILE_PATH environment variable")
        print("Optionally set DOCKER_COMPOSE_FILE_NAME for specific filename")
        print("Default paths checked: /data/, /src/ (docker-compose.yml, docker-compose.yaml)")
        sys.exit(1)

    try:
        parser = DockerComposeParser(compose_file)
        services_docs = parser.parse()

        generator = MarkdownGenerator()
        output = generator.generate(services_docs)

        print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
