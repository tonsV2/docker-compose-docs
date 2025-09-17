#!/usr/bin/env python3
"""
Docker Compose Environment Variable Documentation Generator

Parses Docker Compose files and generates documentation for environment variables
that are commented with '# -- <description>' format.
"""

import os
import re
import glob
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


@dataclass
class ServicesDoc:
    """Represents documentation for a list of services."""
    sourceFile: str
    services: List[ServiceDoc]


class DockerComposeParser:
    """Parses Docker Compose files and extracts environment variable documentation."""

    def __init__(self, compose_file_path: str):
        self.compose_file_path = compose_file_path
        self.compose_content = None
        self.raw_content = None

    def parse(self) -> ServicesDoc:
        """Parse the Docker Compose file and return service documentation."""
        self._load_compose_file()
        services_docs = []

        if self.compose_content is None or 'services' not in self.compose_content:
            return ServicesDoc(sourceFile=self.compose_file_path, services=[])

        for service_name, service_config in self.compose_content['services'].items():
            env_vars = self._extract_env_vars_with_docs(service_name, service_config)
            if env_vars:
                services_docs.append(ServiceDoc(name=service_name, env_vars=env_vars))

        return ServicesDoc(sourceFile=self.compose_file_path, services=services_docs)

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
        default_pattern = r'\$\{[^}]+(-|:-)([^}]*)\}'
        match = re.search(default_pattern, value)

        if match:
            return match.group(2)

        # Check if it's a variable reference without default: ${VAR} or $VAR
        if re.match(r'^\$\{[^}]+}$|^\$[A-Za-z_][A-Za-z0-9_]*$', value):
            return None

        # If it's not a variable substitution, return the value as-is
        return value

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
        if self.raw_content is None:
            return []
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
                if line.strip() and service_indent is not None and current_indent <= service_indent and ':' in line:
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
                parsed_default = self._parse_default_value(str(var_value)) if var_value is not None else None
                env_vars.append(EnvVarDoc(var_name, comment, parsed_default))

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
    def generate(self, services_docs: List[ServicesDoc]) -> str:
        """Generate output from a list of service documentation objects."""
        pass


class MarkdownGenerator(OutputGenerator):
    """Generates Markdown documentation from service documentation."""

    def generate(self, services_docs: List[ServicesDoc]) -> str:
        """Generate Markdown documentation."""
        if not services_docs:
            return "# Environment Variables Documentation\n\nNo documented environment variables found.\n"

        output = ["# Environment Variables Documentation\n"]

        for services_doc in services_docs:
            if not services_doc.services:
                continue

            output.append(f"## File: `{services_doc.sourceFile}`\n")

            for service_doc in services_doc.services:
                output.append(f"### Service: {service_doc.name}\n")

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
                    default = default_val.replace("|", "\\|") if default_val else "-"

                    output.append(f"| `{name}` | {desc} | `{default}` |")

                output.append("")  # Empty line between services

            output.append("")  # Empty line between files

        return "\n".join(output).rstrip('\n')


def find_compose_files(directory: str) -> List[str]:
    """Find all Docker Compose files in a directory."""
    compose_files = []

    # Common Docker Compose file patterns
    patterns = [
        'docker-compose.yml',
        'docker-compose.yaml',
        'docker-compose.*.yml',
        'docker-compose.*.yaml',
        'compose.yml',
        'compose.yaml'
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
        if basename in ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']:
            main_files.append(file)
        elif 'override' in basename:
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

    paths = [path.strip() for path in paths_str.split(';')]
    return [path for path in paths if path]  # Remove empty strings


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


def main():
    """Main function."""
    compose_files = []

    # 1. Command line arguments take the highest precedence (support multiple paths)
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
        compose_files = collect_compose_files(paths)

    # 2. Environment variables take precedence over default paths
    elif os.environ.get('DOCKER_COMPOSE_FILE_PATHS'):
        docker_compose_paths = os.environ.get('DOCKER_COMPOSE_FILE_PATHS')
        if docker_compose_paths is not None:
            paths = parse_paths_from_string(docker_compose_paths)
        else:
            paths = []

        if paths:
            compose_files = collect_compose_files(paths)
        else:
            print("Error: DOCKER_COMPOSE_FILE_PATHS is set but empty")
            sys.exit(1)

    # 3. Fall back to default paths
    if not compose_files:
        default_paths = ['/data', '/src', '.']
        compose_files = collect_compose_files(default_paths)

    # If no files are found, show usage
    if not compose_files:
        print("Usage: python docker_compose_docs.py <files-and-directories...>")
        print("Or set DOCKER_COMPOSE_FILE_PATHS environment variable (semicolon-separated)")
        print("Default paths checked: /data/, /src/, .")
        print("Files are automatically excluded if they contain no documented environment variables.")
        sys.exit(1)

    try:
        doc_models = []

        for compose_file in compose_files:
            try:
                parser = DockerComposeParser(compose_file)
                doc_model = parser.parse()

                # Only add if there are documented services (automatic filtering)
                if doc_model.services:
                    doc_models.append(doc_model)
            except Exception as e:
                print(f"Warning: Failed to parse {compose_file}: {e}", file=sys.stderr)
                continue

        if not doc_models:
            print("# Environment Variables Documentation\n\nNo documented environment variables found in any files.\n")
            return

        generator = MarkdownGenerator()
        output = generator.generate(doc_models)

        print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
