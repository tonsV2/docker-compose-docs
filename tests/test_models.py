"""Tests for data models."""

from src.models import EnvVarDoc, ServiceDoc, ServicesDoc


class TestEnvVarDoc:
    """Test cases for EnvVarDoc model."""

    def test_env_var_doc_creation(self):
        """Test creating an EnvVarDoc instance."""
        env_var = EnvVarDoc(
            name="DATABASE_URL",
            description="Database connection string",
            default_value="postgresql://localhost/db"
        )

        assert env_var.name == "DATABASE_URL"
        assert env_var.description == "Database connection string"
        assert env_var.default_value == "postgresql://localhost/db"

    def test_env_var_doc_without_default(self):
        """Test creating an EnvVarDoc without a default value."""
        env_var = EnvVarDoc(
            name="API_KEY",
            description="API key for external service"
        )

        assert env_var.name == "API_KEY"
        assert env_var.description == "API key for external service"
        assert env_var.default_value is None

    def test_env_var_doc_equality(self):
        """Test equality comparison of EnvVarDoc instances."""
        env_var1 = EnvVarDoc("PORT", "Web server port", "8080")
        env_var2 = EnvVarDoc("PORT", "Web server port", "8080")
        env_var3 = EnvVarDoc("PORT", "Web server port", "3000")

        assert env_var1 == env_var2
        assert env_var1 != env_var3


class TestServiceDoc:
    """Test cases for ServiceDoc model."""

    def test_service_doc_creation(self):
        """Test creating a ServiceDoc instance."""
        env_vars = [
            EnvVarDoc("PORT", "Web server port", "8080"),
            EnvVarDoc("DEBUG", "Debug mode", "false")
        ]

        service = ServiceDoc(name="web", env_vars=env_vars)

        assert service.name == "web"
        assert len(service.env_vars) == 2
        assert service.env_vars[0].name == "PORT"
        assert service.env_vars[1].name == "DEBUG"

    def test_service_doc_empty_env_vars(self):
        """Test creating a ServiceDoc with no environment variables."""
        service = ServiceDoc(name="api", env_vars=[])

        assert service.name == "api"
        assert service.env_vars == []


class TestServicesDoc:
    """Test cases for ServicesDoc model."""

    def test_services_doc_creation(self):
        """Test creating a ServicesDoc instance."""
        services = [
            ServiceDoc("web", [EnvVarDoc("PORT", "Web port", "8080")]),
            ServiceDoc("api", [EnvVarDoc("API_KEY", "API key")])
        ]

        services_doc = ServicesDoc(
            source_file="../examples/docker-compose.yml",
            services=services
        )

        assert services_doc.source_file == "docker-compose.yml"
        assert len(services_doc.services) == 2
        assert services_doc.services[0].name == "web"
        assert services_doc.services[1].name == "api"

    def test_services_doc_empty_services(self):
        """Test creating a ServicesDoc with no services."""
        services_doc = ServicesDoc(
            source_file="../examples/docker-compose.yml",
            services=[]
        )

        assert services_doc.source_file == "docker-compose.yml"
        assert services_doc.services == []
