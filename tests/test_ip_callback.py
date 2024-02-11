import pytest
from typer.testing import CliRunner

from pan_os_upgrade.upgrade import ip_callback

runner = CliRunner()


def test_ip_callback_with_valid_ip():
    assert ip_callback("192.168.1.1") == "192.168.1.1"
    assert ip_callback("::1") == "::1"


def test_ip_callback_with_valid_hostname(mocker):
    # Mock the resolve_hostname function to return True for the test
    mocker.patch("pan_os_upgrade.upgrade.resolve_hostname", return_value=True)
    assert ip_callback("example.com") == "example.com"


def test_ip_callback_with_invalid_ip():
    with pytest.raises(
        Exception
    ) as exc_info:  # Replace 'Exception' with the specific exception type thrown by typer.BadParameter
        ip_callback("999.999.999.999")
    assert "neither a valid DNS hostname nor IP address" in str(exc_info.value)


def test_ip_callback_with_unresolvable_hostname(mocker):
    # Mock the resolve_hostname function to return False for the test
    mocker.patch("pan_os_upgrade.upgrade.resolve_hostname", return_value=False)
    with pytest.raises(
        Exception
    ) as exc_info:  # Replace 'Exception' with the specific exception type thrown by typer.BadParameter
        ip_callback("nonexistent.example.com")
    assert "neither a valid DNS hostname nor IP address" in str(exc_info.value)
