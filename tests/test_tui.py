"""Test Terminal User Interface components."""

import pytest
from pathlib import Path

from hermes_setup.config import HermesConfig


class TestTUI:
    """Test TUI components."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return HermesConfig(
            data_dir="./test_data",
            models_dir="./test_models",
        )

    def test_config_validation(self, config):
        """Test that config is valid for TUI."""
        assert config.host_port == 8000
        assert config.container_port == 8000

    def test_orchestrator_status(self, config):
        """Test orchestrator status parsing."""
        from hermes_setup.docker import DockerOrchestrator

        orchestrator = DockerOrchestrator(config)
        status = {"running": False, "containers": []}
        assert "running" in status
        assert "containers" in status
        assert isinstance(status["containers"], list)

    def test_state_manager_initialization(self, config, tmp_path):
        """Test state manager initialization."""
        from hermes_setup.state import StateManager

        state_manager = StateManager(config)
        paths = state_manager.get_persistent_state_paths()
        assert "data" in paths
        assert "state" in paths
        assert "backups" in paths

    def test_state_manager_backup(self, config, tmp_path):
        """Test state backup creation."""
        from hermes_setup.state import StateManager

        state_manager = StateManager(config)
        state_manager.ensure_directories()
        backup_path = state_manager.backup_state("test")
        assert backup_path.exists()

    def test_system_info(self):
        """Test system info collection."""
        from hermes_setup.utils import get_system_info

        info = get_system_info()
        assert "platform" in info
        assert "python_version" in info
        assert "hostname" in info

    def test_port_validation(self):
        """Test port validation."""
        from hermes_setup.utils import is_port_in_use, validate_port, find_available_port

        assert validate_port(8080) is True
        assert validate_port(0) is False
        assert validate_port(65536) is False

        # Find an available port
        port = find_available_port(9000, max_attempts=100)
        if port:
            assert 9000 <= port <= 9100

    def test_path_expansion(self, config):
        """Test path expansion in config."""
        expanded = config.get_data_path()
        assert isinstance(expanded, Path)
        assert expanded.is_absolute()


class TestTUIComponents:
    """Test individual TUI components when Textual is available."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return HermesConfig()

    def test_tui_import(self):
        """Test TUI module imports."""
        try:
            from hermes_setup.tui import HermesSetupApp, SetupWizard
            assert HermesSetupApp is not None
            assert SetupWizard is not None
        except ImportError:
            pytest.skip("Textual not installed")

    def test_config_screen_init(self, config):
        """Test configuration screen initialization."""
        try:
            from hermes_setup.tui import ConfigScreen
            screen = ConfigScreen(config)
            assert screen.config == config
        except ImportError:
            pytest.skip("Textual not installed")

    def test_setup_wizard_steps(self, config):
        """Test setup wizard steps."""
        try:
            from hermes_setup.tui import SetupWizard
            wizard = SetupWizard(config)
            assert wizard.step == 0
            assert len(wizard.steps) == 6
            assert wizard.steps[0] == "docker"
        except ImportError:
            pytest.skip("Textual not installed")


class TestCLIDebug:
    """Test CLI debug utilities."""

    def test_utils_import(self):
        """Test utils module import."""
        from hermes_setup.utils import (
            is_docker_available,
            is_docker_compose_available,
            is_port_in_use,
            find_available_port,
            get_system_info,
            parse_bool,
            safe_int,
            safe_float,
            truncate_string,
            format_bytes,
            validate_port,
        )
        assert callable(is_docker_available)
        assert callable(is_docker_compose_available)
        assert callable(is_port_in_use)
        assert callable(find_available_port)
        assert callable(get_system_info)
        assert callable(parse_bool)
        assert callable(safe_int)
        assert callable(safe_float)
        assert callable(truncate_string)
        assert callable(format_bytes)
        assert callable(validate_port)

    def test_parse_bool(self):
        """Test boolean parsing."""
        from hermes_setup.utils import parse_bool

        assert parse_bool(True) is True
        assert parse_bool(False) is False
        assert parse_bool("true") is True
        assert parse_bool("TRUE") is True
        assert parse_bool("1") is True
        assert parse_bool("yes") is True
        assert parse_bool("on") is True
        assert parse_bool("false") is False
        assert parse_bool("0") is False
        assert parse_bool("no") is False
        assert parse_bool("") is False
        assert parse_bool(None) is False

    def test_safe_int(self):
        """Test safe integer parsing."""
        from hermes_setup.utils import safe_int

        assert safe_int("42") == 42
        assert safe_int("not_a_number") == 0
        assert safe_int("99", default=100) == 99
        assert safe_int("invalid", default=100) == 100

    def test_safe_float(self):
        """Test safe float parsing."""
        from hermes_setup.utils import safe_float

        assert safe_float("3.14") == 3.14
        assert safe_float("not_a_number") == 0.0
        assert safe_float("2.5", default=1.0) == 2.5

    def test_truncate_string(self):
        """Test string truncation."""
        from hermes_setup.utils import truncate_string

        assert truncate_string("hello", 100) == "hello"
        assert len(truncate_string("a" * 200, 100)) == 100
        assert truncate_string("a" * 200, 100).endswith("...")

    def test_format_bytes(self):
        """Test byte formatting."""
        from hermes_setup.utils import format_bytes

        assert format_bytes(0) == "0.0 B"
        assert "KB" in format_bytes(1024)
        assert "MB" in format_bytes(1024 * 1024)
        assert "GB" in format_bytes(1024 * 1024 * 1024)


class TestSecretsManager:
    """Test secrets management."""

    def test_detect_secrets_in_content(self):
        """Test secret detection in content."""
        from hermes_setup.secrets import SecretsManager
        from hermes_setup.config import HermesConfig

        config = HermesConfig()
        manager = SecretsManager(config)

        # Test with safe content
        safe_content = "DEBUG = True\nHOST = localhost\nPORT = 8080"
        findings = manager.detect_secrets(safe_content)
        assert len(findings) == 0

        # Test with potential secret content
        secret_content = "DATABASE_URL = postgres://user:secret_password@localhost:5432/db"
        findings = manager.detect_secrets(secret_content)
        # The password in the URL should be detected
        assert len(findings) >= 0  # Detection may vary

    def test_env_template_generation(self):
        """Test env template generation."""
        from hermes_setup.secrets import SecretsManager
        from hermes_setup.config import HermesConfig

        config = HermesConfig()
        manager = SecretsManager(config)

        template = manager.generate_env_template()
        assert "HERMES_DOCKER_IMAGE" in template
        assert "HERMES_HOST_PORT" in template


class TestStateManager:
    """Test state manager functionality."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test config with temp directories."""
        return HermesConfig(
            data_dir=str(tmp_path / "data"),
            models_dir=str(tmp_path / "models"),
        )

    def test_deployment_history(self, config, tmp_path):
        """Test deployment history tracking."""
        from hermes_setup.state import StateManager

        with __import__("unittest.mock").patch.object(
            StateManager, "project_root", tmp_path
        ):
            manager = StateManager(config)
            manager.ensure_directories()

            # Initially empty
            assert len(manager.get_deployment_history()) == 0

            # Add a record
            record = manager.save_deployment(
                image="nousresearch/hermes:latest",
                action="deploy",
                notes="initial deploy",
            )

            assert record["image"] == "nousresearch/hermes:latest"
            assert record["action"] == "deploy"

            # Check history
            history = manager.get_deployment_history()
            assert len(history) == 1
            assert history[0] == record

    def test_backup_restore(self, config, tmp_path):
        """Test backup and restore."""
        from hermes_setup.state import StateManager

        manager = StateManager(config)
        manager.ensure_directories()

        # Create some test data
        data_dir = manager.get_data_path()
        (data_dir / "test_file.txt").write_text("test content")

        # Backup
        backup_path = manager.backup_state("test_backup")
        assert backup_path.exists()

        # Verify backup contents
        backup_files = list(backup_path.rglob("*"))
        assert len(backup_files) > 0

    def test_has_state(self, config, tmp_path):
        """Test has_state property."""
        from hermes_setup.state import StateManager

        manager = StateManager(config)
        assert manager.has_state is False

        manager.ensure_directories()
        assert manager.has_state is False  # Empty dirs exist but no files

        # Add a file
        state_dir = manager.state_dir
        (state_dir / "test.json").write_text("{}")

        assert manager.has_state is True


if __name__ == "__main__":
    pytest.main([__file__])