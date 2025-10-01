"""Output generators for Docker Compose documentation."""

from abc import ABC, abstractmethod
from typing import Dict, List

from .models import EnvVarDoc, ServicesDoc


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

            output.append(f"## File: `{services_doc.source_file}`\n")

            for service_doc in services_doc.services:
                output.append(f"### Service: {service_doc.name}\n")

                if not service_doc.env_vars:
                    output.append("No documented environment variables.\n")
                    continue

                parent_property_groups: Dict[str, List[EnvVarDoc]] = {}
                for env_var in service_doc.env_vars:
                    prop = env_var.parent_property or "other"
                    if prop not in parent_property_groups:
                        parent_property_groups[prop] = []
                    parent_property_groups[prop].append(env_var)

                property_names = list(parent_property_groups.keys())
                for i, prop_name in enumerate(property_names):
                    if prop_name != "other":
                        output.append(f"#### {prop_name.title()}\n")
                    else:
                        output.append("#### Other\n")

                    output.append("| Variable | Description | Default Value |")
                    output.append("|----------|-------------|---------------|")

                    vars_in_prop = parent_property_groups[prop_name]
                    for env_var in vars_in_prop:
                        default_val = (
                            env_var.default_value
                            if env_var.default_value is not None
                            else ""
                        )
                        # Escape pipe characters in content
                        name = env_var.name.replace("|", "\\|") if env_var.name else ""
                        desc = (
                            env_var.description.replace("|", "\\|")
                            if env_var.description
                            else ""
                        )
                        default = (
                            default_val.replace("|", "\\|") if default_val else "-"
                        )

                        output.append(f"| `{name}` | {desc} | `{default}` |")

                    if i < len(property_names) - 1:
                        output.append("")

                if service_doc != services_doc.services[-1]:
                    output.append("")

            if services_doc != services_docs[-1]:
                output.append("")

        return "\n".join(output).rstrip("\n")
