import os
import pytest
from pan_os_upgrade.upgrade import connect_to_host
from panos.base import PanDevice
from unittest.mock import patch
from dotenv import load_dotenv


@pytest.fixture
def mock_pan_device():
    with patch("panos.base.PanDevice.create_from_device") as mock_create:
        # Setup the normal mock device
        mock_device = PanDevice(hostname="mock_device")
        mock_create.return_value = mock_device

        # Simulate an authentication failure
        mock_create.side_effect = lambda hostname, api_username, api_password: (
            PanDevice(hostname="failed_device")
            if api_username == "bad_user"
            else mock_device
        )

        # Simulate a network issue
        mock_create.side_effect = lambda hostname, api_username, api_password: (
            PanDevice(hostname="network_error_device")
            if hostname == "bad_network"
            else mock_device
        )

        yield mock_create


@pytest.mark.integration
def test_connect_to_host_valid(mock_pan_device):
    """Test connection with valid credentials."""
    connected_device = connect_to_host("mock_hostname", "valid_user", "valid_password")
    assert isinstance(
        connected_device, PanDevice
    ), "Should return a PanDevice instance."
    assert (
        connected_device.hostname == "mock_device"
    ), "Should match the mock device's hostname."


@pytest.mark.integration
def test_connect_to_host(mock_pan_device):
    """Validate connection to a device, either mock or real based on environment setup."""
    load_dotenv(".dev.env")

    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")
    hostname = os.getenv("PANORAMA")

    if not all([username, password, hostname]):
        pytest.skip(
            "Integration test skipped - no device credentials provided in environment"
        )

    # Use the mock device if testing in a mock environment, otherwise connect to the real device
    if os.getenv("USE_MOCK_DEVICE", "true").lower() == "true":
        connected_device = connect_to_host(
            "mock_hostname", "mock_user", "mock_password"
        )
        expected_hostname = "mock_device"
    else:
        connected_device = connect_to_host(hostname, username, password)
        expected_hostname = hostname

    assert isinstance(
        connected_device, PanDevice
    ), "Should return a PanDevice instance."
    assert (
        connected_device.hostname == expected_hostname
    ), "Should match the expected device's hostname."
