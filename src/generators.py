"""Output generators for Docker Compose documentation."""

from abc import ABC, abstractmethod
from typing import List

from .models import ServicesDoc


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
