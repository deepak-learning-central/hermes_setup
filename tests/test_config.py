"""Test configuration management."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from hermes_setup.config import HermesConfig


class TestHermesConfig:
    """Test HermesConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HermesConfig()
        assert config.docker_image == "nousresearch/hermes-agent:latest"
        assert config.host_port == 8000
        assert config.container_port == 8000
        assert config.memory_limit == "4g"
        assert config.cpus_limit == 2.0
        assert config.model_name == "NousResearch/Hermes-3-Llama-3.1-8B"
        assert config.context_size == 8192
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.max_tokens == 2048
        assert config.log_level == "INFO"

    def test_log_level_validation(self):
        """Test log level validation."""
        config = HermesConfig(log_level="debug")
        assert config.log_level == "DEBUG"

        config = HermesConfig(log_level="WARNING")
        assert config.log_level == "WARNING"

        with pytest.raises(ValidationError):
            HermesConfig(log_level="INVALID")

    def test_port_validation(self):
        """Test port validation."""
        config = HermesConfig(host_port=8080)
        assert config.host_port == 8080

        with pytest.raises(ValidationError):
            HermesConfig(host_port=0)

        with pytest.raises(ValidationError):
            HermesConfig(host_port=65536)

    def test_context_size_validation(self):
        """Test context size validation."""
        config = HermesConfig(context_size=4096)
        assert config.context_size == 4096

        with pytest.raises(ValidationError):
            HermesConfig(context_size=256)

        with pytest.raises(ValidationError):
            HermesConfig(context_size=65536)

    def test_temperature_validation(self):
        """Test temperature validation."""
        config = HermesConfig(temperature=0.5)
        assert config.temperature == 0.5

        with pytest.raises(ValidationError):
            HermesConfig(temperature=-0.1)

        with pytest.raises(ValidationError):
            HermesConfig(temperature=2.1)

    def test_top_p_validation(self):
        """Test top_p validation."""
        config = HermesConfig(top_p=0.8)
        assert config.top_p == 0.8

        with pytest.raises(ValidationError):
            HermesConfig(top_p=-0.1)

        with pytest.raises(ValidationError):
            HermesConfig(top_p=1.1)

    def test_path_expansion(self):
        """Test path expansion."""
        config = HermesConfig(data_dir="~/mydata")
        assert config.get_data_path() == Path("~/mydata").expanduser().resolve()

    def test_ensure_directories(self, tmp_path):
        """Test directory creation."""
        config = HermesConfig(
            data_dir=str(tmp_path / "data"),
            models_dir=str(tmp_path / "models"),
        )
        config.ensure_directories()
        assert config.get_data_path().exists()
        assert config.get_models_path().exists()

    def test_env_template_generation(self):
        """Test .env.example template generation."""
        template = HermesConfig.get_default_env_template()
        assert "HERMES_DOCKER_IMAGE" in template
        assert "HERMES_HOST_PORT" in template
        assert "HERMES_MEMORY_LIMIT" in template
        assert "HERMES_HF_TOKEN" in template
        assert "# NEVER commit .env" in template
