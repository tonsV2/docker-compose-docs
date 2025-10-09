"""Docker Compose file parser for environment variable documentation."""

import dataclasses
import re
from typing import Dict, List, Any, Optional

from ruamel.yaml import YAML

from .models import EnvVarDoc, ServiceDoc, ServicesDoc


@dataclasses.dataclass
class VariableInfo:
    """Internal representation of variable information during parsing."""

    name: str
    default: Optional[str]
    yaml_path: List[str]
    description: str = ""


class DockerComposeParser:
    """Parses Docker Compose files and extracts environment variable documentation."""

    def __init__(self, compose_file_path: str):
        self.compose_file_path = compose_file_path
        self.compose_content: Optional[Dict[str, Any]] = None
        self.raw_content: Optional[str] = None
        self.warnings: List[str] = []

    def parse(self) -> ServicesDoc:
        """Parse the Docker Compose file and return service documentation."""
        self._load_compose_file()

        if self.compose_content is None or "services" not in self.compose_content:
            return ServicesDoc(source_file=self.compose_file_path, services=[])

        all_env_vars, service_descriptions = self._scan_global_env_vars()

        services_docs: List[ServiceDoc] = []
        service_vars: Dict[str, List[EnvVarDoc]] = {}

        for env_var in all_env_vars:
            service_name = env_var.get("service_name", "unknown")
            if service_name not in service_vars:
                service_vars[service_name] = []
            service_vars[service_name].append(env_var["env_var"])

        for service_name, env_vars in service_vars.items():
            description = service_descriptions.get(service_name, "")
            services_docs.append(
                ServiceDoc(
                    name=service_name, env_vars=env_vars, description=description
                )
            )

        return ServicesDoc(self.compose_file_path, services_docs, self.warnings)

    def _load_compose_file(self) -> None:
        """Load and parse the Docker Compose file."""
        try:
            yaml_parser = YAML()
            with open(self.compose_file_path, "r", encoding="utf-8") as f:
                self.raw_content = f.read()
                self.compose_content = yaml_parser.load(self.raw_content)
        except FileNotFoundError:
            raise FileNotFoundError(f"Docker Compose file not found: {self.compose_file_path}")
        except Exception as e:
            raise ValueError(f"Invalid YAML in Docker Compose file: {e}")

    def _scan_global_env_vars(self) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Scan entire file for documented environment variables using ruamel.yaml."""
        if not self.compose_content or not self.raw_content:
            return [], {}

        documented_vars = self._find_variables_with_metadata()
        service_descriptions = self._extract_service_descriptions()

        # Group by service
        env_vars = []
        for var_info in documented_vars:
            service_name = self._extract_service_from_path(var_info.yaml_path)
            parent_property = self._extract_property_from_path(var_info.yaml_path)
            env_var = EnvVarDoc(var_info.name, var_info.description, var_info.default, parent_property)
            env_vars.append({"service_name": service_name, "env_var": env_var})

        return env_vars, service_descriptions

    def _find_variables_with_metadata(self) -> List[VariableInfo]:
        """Find all variables and associate comments."""
        variables: List[VariableInfo] = []

        if (
                self.compose_content is not None
                and hasattr(self.compose_content, "get")
                and "services" in self.compose_content
        ):
            services = self.compose_content["services"]

            for service_name, service_config in services.items():
                if hasattr(service_config, "items"):
                    for prop_name, prop_value in service_config.items():
                        if isinstance(prop_value, str) and "${" in prop_value:
                            vars_in_value = self._extract_vars_from_string(prop_value)
                            for var_info in vars_in_value:
                                name = var_info["name"]
                                default = var_info.get("default")
                                yaml_path = ["services", service_name, prop_name]
                                variables.append(self._create_variable_info(name, default, yaml_path))
                        elif isinstance(prop_value, list):
                            for i, item in enumerate(prop_value):
                                if isinstance(item, str) and "${" in item:
                                    vars_in_value = self._extract_vars_from_string(item)
                                    for var_info in vars_in_value:
                                        name = var_info["name"]
                                        default = var_info.get("default")
                                        yaml_path = ["services", service_name, prop_name, str(i)]
                                        variables.append(self._create_variable_info(name, default, yaml_path))
                        elif isinstance(prop_value, dict):
                            # Handle nested mappings like environment
                            self._process_nested_mapping(
                                prop_value,
                                ["services", service_name, prop_name],
                                variables,
                            )

        self._associate_comments_with_variables_text(variables)

        return variables

    def _create_variable_info(self, name: str, default: Optional[str], yaml_path: List[str]) -> VariableInfo:
        """Create a VariableInfo object."""
        return VariableInfo(
            name=name, default=default, yaml_path=yaml_path, description=""
        )

    def _associate_comments_with_variables_text(self, variables: List[VariableInfo]) -> None:
        """Associate comments with variables using text analysis."""
        if not self.raw_content:
            return

        lines = self.raw_content.split("\n")
        line_to_vars: Dict[int, List[VariableInfo]] = {}

        # Build map of line numbers to variables
        for var_info in variables:
            var_line = self._find_variable_line(var_info, lines)
            if var_line is not None:
                if var_line not in line_to_vars:
                    line_to_vars[var_line] = []
                line_to_vars[var_line].append(var_info)

        # Associate comments with variables
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("# --"):
                comments = []
                start_comment_line = i
                while i < len(lines) and lines[i].strip().startswith("# --"):
                    comment_text = lines[i].strip()[4:].strip()
                    if comment_text:
                        comments.append(comment_text)
                    i += 1

                # Associate with the immediate next line
                if i < len(lines):
                    next_line = lines[i]
                    if next_line.strip() and not next_line.strip().startswith("#"):
                        if (
                                next_line.startswith("  ")
                                and ":" in next_line.strip()
                                and not next_line.startswith("   ")
                        ):
                            # Service definition (indented with 2 spaces), comment is for service
                            pass
                        elif i in line_to_vars:
                            for var_info in line_to_vars[i]:
                                var_info.description = " ".join(comments)
                        else:
                            self.warnings.append(f"Line {start_comment_line + 1}: Comment without associated variable")
            else:
                i += 1

        # Check for variables without comments
        for var_info in variables:
            if not var_info.description:
                var_line = self._find_variable_line(var_info, lines)
                if var_line is not None:
                    self.warnings.append(f"Line {var_line + 1}: Variable '{var_info.name}' without comment")

    def _process_nested_mapping(self, mapping: Any, current_path: List[str], variables: List[VariableInfo]) -> None:
        """Process nested mappings like environment sections."""
        if hasattr(mapping, "items"):
            for key, value in mapping.items():
                if isinstance(value, str) and "${" in value:
                    vars_in_value = self._extract_vars_from_string(value)
                    for var_info in vars_in_value:
                        variable_info = VariableInfo(
                            var_info["name"],
                            var_info.get("default"),
                            current_path + [key],
                            "",
                        )
                        variables.append(variable_info)

    def _find_variable_line(self, var_info: VariableInfo, lines: List[str]) -> Optional[int]:
        """Find which line contains this variable using text search."""
        var_name = var_info.name
        for i, line in enumerate(lines):
            if f"${{{var_name}" in line or f"${var_name}" in line:
                return i
        return None

    def _extract_service_level_comments(self, mapping: Any) -> str:
        """Extract service-level comments (appear before first key)."""
        comments = []

        if hasattr(mapping, "ca") and hasattr(mapping.ca, "comment"):
            comment_tokens = mapping.ca.comment
            if comment_tokens:
                for token_list in comment_tokens:
                    if token_list:
                        for token in token_list:
                            if hasattr(token, "value"):
                                comment_text = token.value.strip()
                                if comment_text.startswith("# --"):
                                    comments.append(comment_text[4:].strip())

        return " ".join(comments)

    def _extract_service_descriptions(self) -> Dict[str, str]:
        """Extract descriptions for all services using text analysis."""
        descriptions = {}
        if not self.raw_content:
            return descriptions

        lines = self.raw_content.split("\n")
        services_section_start = None

        for i, line in enumerate(lines):
            if line.strip() == "services:":
                services_section_start = i
                break

        if services_section_start is None:
            return descriptions

        i = services_section_start + 1
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("# --"):
                # Collect comment lines
                comments = []
                while i < len(lines) and lines[i].strip().startswith("# --"):
                    comment_text = lines[i].strip()[4:].strip()
                    if comment_text:
                        comments.append(comment_text)
                    i += 1
                # Next non-comment line should be a service name
                if i < len(lines):
                    next_line = lines[i].strip()
                    if ":" in next_line and not next_line.startswith(" "):
                        service_name = next_line.split(":")[0].strip()
                        descriptions[service_name] = " ".join(comments)
            elif line and not line.startswith("#") and ":" in line and not line.startswith(" "):
                # Service definition without comment
                pass
            i += 1

        return descriptions

    def _extract_comments_for_key(self, mapping: Any, key: str) -> str:
        """Extract comments associated with a key in a YAML mapping."""
        comments = []

        if hasattr(mapping, "ca") and hasattr(mapping.ca, "items") and key in mapping.ca.items:
            comment_tokens = mapping.ca.items[key]
            if comment_tokens:
                # comment_tokens is a list where each element can be a CommentToken or a list
                for token_or_list in comment_tokens:
                    if token_or_list:
                        # Handle both single tokens and lists of tokens
                        if hasattr(token_or_list, "value"):
                            # Single CommentToken
                            tokens = [token_or_list]
                        else:
                            # List of CommentTokens
                            tokens = token_or_list

                        for token in tokens:
                            if hasattr(token, "value"):
                                comment_text = token.value.strip()
                                if comment_text.startswith("# --"):
                                    comments.append(comment_text[4:].strip())

        return " ".join(comments)

    def _extract_service_from_path(self, yaml_path: List[str]) -> str:
        """Extract service name from YAML path."""
        # For well-formed Docker Compose files, path is always ["services", service_name, ...]
        return yaml_path[1] if len(yaml_path) > 1 else "unknown"

    def _extract_property_from_path(self, yaml_path: List[str]) -> str:
        """Extract the immediate parent property from YAML path."""
        # For well-formed files, path is ["services", service_name, property_name, ...]
        # The property is always at index 2
        return yaml_path[2] if len(yaml_path) > 2 else "unknown"

    def _extract_vars_from_string(self, text: str) -> List[Dict[str, str]]:
        """Extract all ${VAR} patterns from a line."""
        import re

        vars_found = []
        # Find all ${...} patterns
        var_pattern = r"\$\{([^}]+)\}"
        matches = re.findall(var_pattern, text)

        for match in matches:
            parts = match.split("-", 1)
            if len(parts) == 2:
                var = {
                    "name": parts[0].rstrip(":").strip(),
                    "default": parts[1].strip(),
                }
            else:
                var = {"name": match.strip(), "default": None}
            vars_found.append(var)
        return vars_found

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
