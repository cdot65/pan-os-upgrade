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


@pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_configure_logging_levels(reset_logging, tmp_path, log_level):
    log_file_path = tmp_path / f"{log_level.lower()}_test.log"
    configure_logging(
        log_level,
        encoding="utf-8",
        log_file_path=str(log_file_path),
    )

    logger = logging.getLogger()
    assert logger.level == getattr(
        logging, log_level
    ), f"Logging level should be set to {log_level}."

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


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
def test_configure_logging_encodings(reset_logging, tmp_path, encoding):
    log_file_path = tmp_path / f"encoding_{encoding}_test.log"
    configure_logging(
        "INFO",
        encoding=encoding,
        log_file_path=str(log_file_path),
    )

    logger = logging.getLogger()  # Define logger here
    file_handler = next(
        h for h in logger.handlers if isinstance(h, RotatingFileHandler)
    )
    assert (
        file_handler.encoding == encoding
    ), f"File handler should use the specified encoding {encoding}."


@pytest.mark.parametrize("invalid_level", ["INVALID", "LOG", "TRACE"])
def test_configure_logging_invalid_levels(reset_logging, invalid_level):
    with pytest.raises(ValueError):
        configure_logging(invalid_level)


# Test default parameters are used correctly
def test_configure_logging_default_parameters(reset_logging, tmp_path):
    log_file_path = tmp_path / "upgrade.log"  # Use a temporary directory
    configure_logging("INFO", log_file_path=str(log_file_path))

    logger = logging.getLogger()
    assert logger.level == logging.INFO, "Logging level should be set to INFO."

    file_handler = next(
        h for h in logger.handlers if isinstance(h, RotatingFileHandler)
    )
    assert file_handler.baseFilename == str(
        log_file_path
    ), "File handler should use the specified log file path."
