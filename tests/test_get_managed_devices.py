import os
import pytest
import re
from dotenv import load_dotenv

from panos.panorama import Panorama
from pan_os_upgrade.upgrade import get_managed_devices


@pytest.fixture
def panorama():
    """A real Panorama host for use in integration testing."""
    load_dotenv(".dev.env")  # Load environment variables from a .env file

    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")
    hostname = os.getenv("PANORAMA")

    if not all([username, password, hostname]):
        pytest.skip("Integration test skipped - no Panorama available")

    return Panorama(hostname=hostname, api_username=username, api_password=password)


@pytest.mark.integration
def test_get_managed_devices_with_serial_filter(panorama):
    """Test getting managed devices from Panorama with a serial number filter."""

    # Use a known serial number for filtering
    expected_serial = "007054000254144"
    filters = {"serial": expected_serial}

    managed_devices = get_managed_devices(panorama, **filters)

    assert isinstance(
        managed_devices, list
    ), "Expected a list of ManagedDevice objects."
    assert all(
        device.serial == expected_serial for device in managed_devices
    ), "All returned devices should match the filter criteria."


@pytest.mark.integration
def test_get_managed_devices_with_hostname_pattern_filter(panorama):
    """Test getting managed devices from Panorama using a hostname pattern filter."""

    # Use a hostname pattern filter
    hostname_pattern = r"lab-fw.*"  # Adjust the pattern as needed
    filters = {"hostname": hostname_pattern}

    managed_devices = get_managed_devices(panorama, **filters)

    assert isinstance(
        managed_devices, list
    ), "Expected a list of ManagedDevice objects."

    # Specific checks to ensure returned devices match the hostname filter criteria
    matched_devices = 0
    for device in managed_devices:
        if re.match(hostname_pattern, device.hostname):
            matched_devices += 1

    # Ensure that at least one device is returned that matches the filter
    assert (
        matched_devices > 0
    ), "Expected at least one device to match the hostname filter criteria."
