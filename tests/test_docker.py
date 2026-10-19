"""Test Docker orchestration."""

from unittest.mock import patch

import pytest

from hermes_setup.config import HermesConfig
from hermes_setup.docker import DockerOrchestrator


class TestDockerOrchestrator:
    """Test DockerOrchestrator class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return HermesConfig(
            host_port=8080,
            container_port=8080,
            data_dir="./test_data",
            models_dir="./test_models",
        )

    @pytest.fixture
    def orchestrator(self, config):
        """Create test orchestrator."""
        return DockerOrchestrator(config)

    def test_initialization(self, orchestrator, config):
        """Test orchestrator initialization."""
        assert orchestrator.config == config
        assert orchestrator.compose_file.name == "compose.yml"
        assert orchestrator.compose_prod_file.name == "compose.prod.yml"

    @patch("hermes_setup.docker.subprocess.run")
    def test_check_docker_available(self, mock_run, orchestrator):
        """Test Docker availability check."""
        mock_run.return_value.returncode = 0
        assert orchestrator.check_docker() is True
        mock_run.assert_called_once_with(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    @patch("hermes_setup.docker.subprocess.run")
    def test_check_docker_unavailable(self, mock_run, orchestrator):
        """Test Docker unavailable check."""
        mock_run.side_effect = FileNotFoundError()
        assert orchestrator.check_docker() is False

    @patch("hermes_setup.docker.subprocess.run")
    def test_check_compose_available(self, mock_run, orchestrator):
        """Test Docker Compose availability check."""
        mock_run.return_value.returncode = 0
        assert orchestrator.check_compose() is True
        mock_run.assert_called_once_with(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_validate_environment(self, orchestrator):
        """Test environment validation."""
        with patch.object(orchestrator, "check_docker", return_value=True), \
             patch.object(orchestrator, "check_compose", return_value=True), \
             patch.object(orchestrator.compose_file, "exists", return_value=True):
            issues = orchestrator.validate_environment()
            assert len(issues) == 0

    def test_generate_compose_file(self, orchestrator):
        """Test compose file generation."""
        content = orchestrator.generate_compose_file()
        assert "version: '3.8'" in content
        assert "hermes:" in content
        assert "nousresearch/hermes:latest" in content
        assert "8080:8080" in content  # test ports
        assert "./test_data:/app/data" in content
        assert "./test_models:/app/models" in content
        assert "MEMORY_LIMIT" in content
        assert "CPUS_LIMIT" in content

    def test_generate_compose_file_production(self, orchestrator):
        """Test production compose file generation."""
        content = orchestrator.generate_compose_file(production=True)
        assert "networks:" in content
        assert "hermes-network" in content

    @patch("hermes_setup.docker.subprocess.run")
    def test_pull_image_success(self, mock_run, orchestrator):
        """Test successful image pull."""
        mock_run.return_value.returncode = 0
        assert orchestrator.pull_image() is True
        mock_run.assert_called_once_with(
            ["docker", "pull", "nousresearch/hermes:latest"],
            capture_output=True,
            text=True,
            timeout=300,
        )

    @patch("hermes_setup.docker.subprocess.run")
    def test_pull_image_failure(self, mock_run, orchestrator):
        """Test failed image pull."""
        mock_run.return_value.returncode = 1
        assert orchestrator.pull_image() is False

    @patch("hermes_setup.docker.subprocess.run")
    def test_start_container(self, mock_run, orchestrator):
        """Test starting container."""
        mock_run.return_value.returncode = 0
        assert orchestrator.start() is True
        mock_run.assert_called_once_with(
            ["up"],
            check=False,
            capture_output=True,
            text=True,
        )

    @patch("hermes_setup.docker.subprocess.run")
    def test_stop_container(self, mock_run, orchestrator):
        """Test stopping container."""
        mock_run.return_value.returncode = 0
        assert orchestrator.stop() is True
        mock_run.assert_called_once_with(
            ["down"],
            check=False,
            capture_output=True,
            text=True,
        )

    @patch("hermes_setup.docker.subprocess.run")
    def test_status_parsing(self, mock_run, orchestrator):
        """Test status parsing."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """{"State": "running", "Service": "hermes", "Health": "healthy"}
{"State": "exited", "Service": "other", "Health": "none"}"""
        status = orchestrator.status()
        assert status["running"] is True
        assert len(status["containers"]) == 2
        assert status["containers"][0]["State"] == "running"
        assert status["containers"][0]["Service"] == "hermes"
        assert status["containers"][0]["Health"] == "healthy"

    def test_generate_env_example(self, orchestrator, tmp_path):
        """Test .env.example generation."""
        test_file = tmp_path / ".env.example"
        orchestrator.generate_env_example(test_file)
        assert test_file.exists()
        content = test_file.read_text()
        assert "HERMES_DOCKER_IMAGE" in content
        assert "# NEVER commit .env" in content

    def test_generate_gitignore(self, orchestrator, tmp_path):
        """Test .gitignore generation."""
        test_file = tmp_path / ".gitignore"
        orchestrator.generate_gitignore(test_file)
        assert test_file.exists()
        content = test_file.read_text()
        assert ".env" in content
        assert "__pycache__/" in content

    def test_generate_pre_commit_config(self, orchestrator, tmp_path):
        """Test pre-commit config generation."""
        test_file = tmp_path / ".pre-commit-config.yaml"
        orchestrator.generate_pre_commit_config(test_file)
        assert test_file.exists()
        content = test_file.read_text()
        assert "gitleaks" in content
        assert "ruff" in content
        assert "mypy" in content

    def test_init_project(self, orchestrator, tmp_path, monkeypatch):
        """Test project initialization."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Mock file system operations
        with patch.object(orchestrator, "write_compose_files"), \
             patch.object(orchestrator, "generate_env_example"), \
             patch.object(orchestrator, "generate_gitignore"), \
             patch.object(orchestrator, "generate_pre_commit_config"), \
             patch.object(orchestrator.config, "ensure_directories"):
            orchestrator.init_project()
            # Verify all methods were called
            assert orchestrator.write_compose_files.called
            assert orchestrator.generate_env_example.called
            assert orchestrator.generate_gitignore.called
            assert orchestrator.generate_pre_commit_config.called
            assert orchestrator.config.ensure_directories.called


if __name__ == "__main__":
    pytest.main([__file__])
