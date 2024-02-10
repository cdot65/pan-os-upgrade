import logging
from logging.handlers import RotatingFileHandler
import pytest
from pan_os_upgrade.upgrade import configure_logging


@pytest.fixture
def reset_logging():
    # Fixture to reset logging to default state after each test case
    yield
    logging.getLogger().handlers = []


def test_configure_logging_debug_level(reset_logging, tmp_path):
    log_file_path = tmp_path / "test.log"
    log_max_size = 5 * 1024 * 1024  # 5 MB for testing
    configure_logging(
        "DEBUG",
        encoding="utf-8",
        log_file_path=str(log_file_path),
        log_max_size=log_max_size,
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
    assert (
        file_handler.encoding == "utf-8"
    ), "File handler should use the specified encoding."
    assert (
        file_handler.maxBytes == log_max_size
    ), "File handler should respect the specified max log size."


def test_configure_logging_invalid_level(reset_logging):
    with pytest.raises(ValueError):
        configure_logging("INVALID_LEVEL")
