"""Tests for output generators."""

from src.generators import MarkdownGenerator
from src.models import EnvVarDoc, ServiceDoc, ServicesDoc


class TestMarkdownGenerator:
    """Test cases for MarkdownGenerator."""

    def test_generate_empty_services_doc(self):
        """Test generating markdown for empty services documentation."""
        services_doc = ServicesDoc(source_file="../examples/docker-compose.yml", services=[])
        generator = MarkdownGenerator()

        result = generator.generate([services_doc])

        # When there are no services, the generator just produces the header
        expected = "# Environment Variables Documentation"
        assert result == expected

    def test_generate_single_service_single_env_var(self):
        """Test generating markdown for a single service with one environment variable."""
        env_var = EnvVarDoc(
            name="PORT",
            description="Web server port",
            default_value="8080"
        )

        service = ServiceDoc(name="web", env_vars=[env_var])
        services_doc = ServicesDoc(source_file="../examples/docker-compose.yml", services=[service])

        generator = MarkdownGenerator()
        result = generator.generate([services_doc])

        assert "# Environment Variables Documentation" in result
        assert "## File: `../examples/docker-compose.yml`" in result
        assert "### Service: web" in result
        assert "| Variable | Description | Default Value |" in result
        assert "| `PORT` | Web server port | `8080` |" in result

    def test_generate_multiple_services(self):
        """Test generating markdown for multiple services."""
        env_vars_web = [
            EnvVarDoc("PORT", "Web server port", "8080"),
            EnvVarDoc("DEBUG", "Debug mode", "false")
        ]

        env_vars_api = [
            EnvVarDoc("API_KEY", "API key for external service"),
            EnvVarDoc("DATABASE_URL", "Database connection string", "postgresql://localhost/db")
        ]

        services = [
            ServiceDoc("web", env_vars_web),
            ServiceDoc("api", env_vars_api)
        ]

        services_doc = ServicesDoc(source_file="../examples/docker-compose.yml", services=services)

        generator = MarkdownGenerator()
        result = generator.generate([services_doc])

        # Check that both services are included
        assert "### Service: web" in result
        assert "### Service: api" in result

        # Check that all environment variables are included
        assert "`PORT`" in result
        assert "`DEBUG`" in result
        assert "`API_KEY`" in result
        assert "`DATABASE_URL`" in result

    def test_generate_multiple_files(self):
        """Test generating markdown for multiple compose files."""
        # First file
        env_var1 = EnvVarDoc("PORT", "Web port", "8080")
        service1 = ServiceDoc("web", [env_var1])
        services_doc1 = ServicesDoc(source_file="../examples/docker-compose.yml", services=[service1])

        # Second file
        env_var2 = EnvVarDoc("API_KEY", "API key")
        service2 = ServiceDoc("api", [env_var2])
        services_doc2 = ServicesDoc(source_file="docker-compose.prod.yml", services=[service2])

        generator = MarkdownGenerator()
        result = generator.generate([services_doc1, services_doc2])

        # Check that both files are included
        assert "## File: `../examples/docker-compose.yml`" in result
        assert "## File: `./docker-compose.prod.yml`" in result

        # Check that services from both files are included
        assert "### Service: web" in result
        assert "### Service: api" in result

    def test_generate_service_without_env_vars(self):
        """Test generating markdown for a service with no documented environment variables."""
        service = ServiceDoc("database", env_vars=[])
        services_doc = ServicesDoc(source_file="../examples/docker-compose.yml", services=[service])

        generator = MarkdownGenerator()
        result = generator.generate([services_doc])

        assert "### Service: database" in result
        assert "No documented environment variables." in result

    def test_generate_env_var_without_default(self):
        """Test generating markdown for environment variable without default value."""
        env_var = EnvVarDoc("API_KEY", "API key for external service")
        service = ServiceDoc("api", [env_var])
        services_doc = ServicesDoc(source_file="../examples/docker-compose.yml", services=[service])

        generator = MarkdownGenerator()
        result = generator.generate([services_doc])

        assert "`API_KEY`" in result
        assert "`-`" in result  # Should show "-" for missing default value

    def test_escape_markdown_characters(self):
        """Test that markdown characters in content are properly escaped."""
        env_var = EnvVarDoc(
            name="VAR|NAME",
            description="Description with | pipe",
            default_value="default|value"
        )

        service = ServiceDoc("test", [env_var])
        services_doc = ServicesDoc(source_file="../examples/docker-compose.yml", services=[service])

        generator = MarkdownGenerator()
        result = generator.generate([services_doc])

        # Check that pipe characters are escaped
        assert "`VAR\\|NAME`" in result
        assert "Description with \\| pipe" in result
        assert "`default\\|value`" in result
