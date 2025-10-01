"""Command-line interface for Docker Compose documentation generator."""

import os
import sys

from .parser import DockerComposeParser
from .generators import MarkdownGenerator
from .utils import (
    collect_compose_files,
    parse_paths_from_string,
    collect_compose_files_from_globs,
)


def main():
    """Main function."""
    compose_files = []

    # 1. Command line arguments take the highest precedence (support multiple paths)
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
        compose_files = collect_compose_files(paths)

    # 2. Environment variables take precedence over default paths
    else:
        env_paths_set = bool(os.environ.get("DOCKER_COMPOSE_FILE_PATHS"))
        env_globs_set = bool(os.environ.get("DOCKER_COMPOSE_FILE_GLOBS"))

        if env_paths_set or env_globs_set:
            if env_paths_set:
                docker_compose_paths = os.environ.get("DOCKER_COMPOSE_FILE_PATHS")
                if docker_compose_paths:
                    paths = parse_paths_from_string(docker_compose_paths)
                    compose_files.extend(collect_compose_files(paths))
                else:
                    print("Error: DOCKER_COMPOSE_FILE_PATHS is set but empty")
                    sys.exit(1)

            if env_globs_set:
                globs_str = os.environ.get("DOCKER_COMPOSE_FILE_GLOBS")
                if globs_str:
                    globs = parse_paths_from_string(globs_str)
                    compose_files.extend(collect_compose_files_from_globs(globs))
                else:
                    print("Error: DOCKER_COMPOSE_FILE_GLOBS is set but empty")
                    sys.exit(1)

            # Remove duplicates while preserving order
            seen = set()
            unique_files = []
            for file in compose_files:
                abs_path = os.path.abspath(file)
                if abs_path not in seen:
                    seen.add(abs_path)
                    unique_files.append(file)
            compose_files = unique_files

        # 3. Fall back to default paths
        else:
            default_paths = ["/data", "/src", "."]
            compose_files = collect_compose_files(default_paths)

    # If no files are found, show usage
    if not compose_files:
        print("Usage: python -m src.cli <files-and-directories...>")
        print("Or set DOCKER_COMPOSE_FILE_PATHS or DOCKER_COMPOSE_FILE_GLOBS environment variable (semicolon-separated)")
        print("Or use Docker: docker compose -f config/docker-compose.yml run --rm app <files>")
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
            print(
                "# Environment Variables Documentation\n\nNo documented environment variables found in any files.\n"
            )
            return

        generator = MarkdownGenerator()
        output = generator.generate(doc_models)

        print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
