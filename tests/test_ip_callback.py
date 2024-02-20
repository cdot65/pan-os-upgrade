import os
import pytest
from typer.testing import CliRunner

from pan_os_upgrade.main import ip_callback

runner = CliRunner()


# Helper function to determine if .dev.env file exists
def skip_if_no_dev_env():
    if not os.path.exists(".dev.env"):
        pytest.skip("Skipping integration test - .dev.env file not found")


def test_ip_callback_with_valid_ip():
    skip_if_no_dev_env()
    assert ip_callback("192.168.1.1") == "192.168.1.1"
    assert ip_callback("::1") == "::1"


@pytest.mark.integration
def test_ip_callback_with_valid_hostname(mocker):
    skip_if_no_dev_env()
    mocker.patch("pan_os_upgrade.upgrade.resolve_hostname", return_value=True)
    assert ip_callback("example.com") == "example.com"


def test_ip_callback_with_invalid_ip():
    skip_if_no_dev_env()
    with pytest.raises(Exception) as exc_info:
        ip_callback("999.999.999.999")
    assert "neither a valid DNS hostname nor IP address" in str(exc_info.value)


@pytest.mark.integration
def test_ip_callback_with_unresolvable_hostname(mocker):
    skip_if_no_dev_env()
    mocker.patch("pan_os_upgrade.upgrade.resolve_hostname", return_value=False)
    with pytest.raises(Exception) as exc_info:
        ip_callback("nonexistent.example.com")
    assert "neither a valid DNS hostname nor IP address" in str(exc_info.value)
