"""Integration tests for the complete application."""

import subprocess
import tempfile
from pathlib import Path


class TestCLIIntegration:
    """Integration tests for the CLI application."""

    def create_test_compose_file(self, content: str) -> str:
        """Create a temporary Docker Compose file with given content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            return f.name

    def run_cli(self, args, cwd=None):
        """Run the CLI application with given arguments."""
        cmd = ["python", "-m", "src.cli"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or Path(__file__).parent.parent
        )
        return result

    def test_cli_with_single_file(self):
        """Test CLI with a single Docker Compose file."""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    environment:
      # -- Port number for the web server
      PORT: ${PORT:-8080}
"""

        file_path = self.create_test_compose_file(compose_content)
        try:
            result = self.run_cli([file_path])

            assert result.returncode == 0
            assert "# Environment Variables Documentation" in result.stdout
            assert "## File:" in result.stdout
            assert "### Service: web" in result.stdout
            assert "`PORT`" in result.stdout
            assert "Port number for the web server" in result.stdout

        finally:
            Path(file_path).unlink()

    def test_cli_with_directory(self):
        """Test CLI with a directory containing compose files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a compose file in the directory
            compose_file = Path(temp_dir) / "docker-compose.yml"
            compose_file.write_text("""
version: '3.8'
services:
  app:
    environment:
      # -- Application port
      PORT: 3000
""")

            result = self.run_cli([temp_dir])

            assert result.returncode == 0
            assert "# Environment Variables Documentation" in result.stdout
            assert "`PORT`" in result.stdout

    def test_cli_with_no_files(self):
        """Test CLI when compose files are found but have no documented variables."""
        # Create a compose file with no documented environment variables
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    environment:
      PORT: 8080  # No # -- comment, so not documented
"""
        file_path = self.create_test_compose_file(compose_content)
        try:
            result = self.run_cli([file_path])

            # CLI returns 0 and shows message when files have no documented variables
            assert result.returncode == 0
            assert "No documented environment variables found" in result.stdout
        finally:
            Path(file_path).unlink()

    def test_cli_with_invalid_file(self):
        """Test CLI with an invalid YAML file."""
        # Create a file with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: [\n")
            file_path = f.name

        try:
            result = self.run_cli([file_path])

            # CLI continues processing even with invalid files
            assert result.returncode == 0
            assert "Warning: Failed to parse" in result.stderr

        finally:
            Path(file_path).unlink()

    def test_cli_with_multiple_files(self):
        """Test CLI with multiple Docker Compose files."""
        compose_content1 = """
version: '3.8'
services:
  web:
    environment:
      # -- Web port
      PORT: 8080
"""

        compose_content2 = """
version: '3.8'
services:
  api:
    environment:
      # -- API port
      PORT: 3000
"""

        file1 = self.create_test_compose_file(compose_content1)
        file2 = self.create_test_compose_file(compose_content2)

        try:
            result = self.run_cli([file1, file2])

            assert result.returncode == 0
            assert "# Environment Variables Documentation" in result.stdout
            # Should contain both services
            assert "### Service: web" in result.stdout
            assert "### Service: api" in result.stdout

        finally:
            Path(file1).unlink()
            Path(file2).unlink()

    def test_cli_output_format(self):
        """Test that CLI output is properly formatted markdown."""
        compose_content = """
version: '3.8'
services:
  test:
    environment:
      # -- Test variable
      TEST_VAR: value
"""

        file_path = self.create_test_compose_file(compose_content)
        try:
            result = self.run_cli([file_path])

            assert result.returncode == 0

            lines = result.stdout.strip().split('\n')

            # Check markdown table format
            assert "| Variable | Description | Default Value |" in lines
            assert "|----------|-------------|---------------|" in lines
            assert "| `TEST_VAR` | Test variable | `value` |" in lines

        finally:
            Path(file_path).unlink()

    def test_cli_with_environment_variable_paths(self):
        """Test CLI using DOCKER_COMPOSE_FILE_PATHS environment variable."""
        compose_content = """
version: '3.8'
services:
  envtest:
    environment:
      # -- Environment test variable
      ENV_VAR: test
"""

        file_path = self.create_test_compose_file(compose_content)
        try:
            # Set environment variable and run CLI without arguments
            env = {"DOCKER_COMPOSE_FILE_PATHS": file_path}
            cmd = ["python", "-m", "src.cli"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                env={**env, **{"PATH": "/usr/local/bin:/usr/bin:/bin"}}
            )

            assert result.returncode == 0
            assert "ENV_VAR" in result.stdout
            assert "Environment test variable" in result.stdout

        finally:
            Path(file_path).unlink()
