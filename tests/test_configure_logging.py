import logging
from logging.handlers import RotatingFileHandler
import pytest
from pan_os_upgrade.components.utilities import configure_logging
from dynaconf import LazySettings


@pytest.fixture
def reset_logging():
    # Fixture to reset logging to default state after each test case
    yield
    logging.getLogger().handlers = []


def test_configure_logging_debug_level(reset_logging, tmp_path):
    # Create a temporary YAML settings file with the desired log file path in the temp directory
    settings_file = tmp_path / "settings.yaml"
    log_file_path = tmp_path / "test.log"  # Use the temp path for the log file
    settings_content = f"""
    logging:
      level: DEBUG
      file_path: {log_file_path}  # Use the temp log file path here
      max_size: 10
      upgrade_log_count: 3
    """
    settings_file.write_text(settings_content)

    # Load settings from the YAML file
    settings = LazySettings(SETTINGS_FILE=str(settings_file))

    configure_logging(
        encoding="utf-8",
        settings_file=settings,
        settings_file_path=settings_file,
    )

    logger = logging.getLogger()
    assert logger.level == logging.DEBUG, "Logging level should be set to DEBUG."

    assert any(
        isinstance(h, logging.StreamHandler) for h in logger.handlers
    ), "Console handler should be added."
    assert any(
        isinstance(h, RotatingFileHandler) for h in logger.handlers
    ), "File handler should be added."

    file_handler = next(
        h for h in logger.handlers if isinstance(h, RotatingFileHandler)
    )
    assert file_handler.baseFilename == str(
        log_file_path
    ), "File handler should use the specified log file path."
