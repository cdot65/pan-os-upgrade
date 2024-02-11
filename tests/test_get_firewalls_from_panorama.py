import os
import pytest
import re
from dotenv import load_dotenv

from panos.device import SystemSettings
from panos.panorama import Panorama
from panos.firewall import Firewall

from pan_os_upgrade.upgrade import get_firewalls_from_panorama, filter_string_to_dict


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


def test_get_firewalls_from_panorama_with_serial_filter(panorama):
    """Test getting firewalls from Panorama with optional filters."""

    # Adjust the filter to use an attribute that exists in ManagedDevice, like 'serial'
    expected_serial = "007054000254144"
    filters = {"serial": expected_serial}

    firewalls = get_firewalls_from_panorama(panorama, **filters)

    assert isinstance(firewalls, list), "Expected a list of Firewall objects."
    assert all(
        isinstance(fw, Firewall) for fw in firewalls
    ), "Each item in the list should be a Firewall object."

    # Specific checks to ensure returned firewalls match the filter criteria
    for fw in firewalls:
        assert hasattr(
            fw, "serial"
        ), "Firewall object is expected to have a 'serial' attribute."
        assert (
            fw.serial == expected_serial
        ), f"Firewall serial number should match the filter criteria: {expected_serial}"

    # Ensure that at least one firewall is returned that matches the filter
    assert (
        len(firewalls) > 0
    ), "Expected at least one firewall to match the filter criteria."


def test_get_firewalls_from_panorama_with_hostname_filter(panorama):
    """Test getting firewalls from Panorama using a hostname pattern filter."""

    # Use a hostname pattern filter
    hostname_pattern = "lab-fw*"
    filter = f"hostname={hostname_pattern}"

    # Now apply the filter and retrieve firewalls
    filtered_firewalls = get_firewalls_from_panorama(
        panorama, **filter_string_to_dict(filter)
    )

    assert isinstance(filtered_firewalls, list), "Expected a list of Firewall objects."
    assert all(
        isinstance(fw, Firewall) for fw in filtered_firewalls
    ), "Each item in the list should be a Firewall object."

    # Specific checks to ensure returned firewalls match the hostname filter criteria
    matched_firewalls = 0
    for fw in filtered_firewalls:
        fw_details = SystemSettings.refreshall(fw)[0]
        assert hasattr(
            fw_details, "hostname"
        ), "Firewall object is expected to have a 'hostname' attribute."
        if fw_details.hostname:
            assert re.match(
                hostname_pattern, fw_details.hostname
            ), f"Firewall hostname should match the filter pattern: {hostname_pattern}"
            matched_firewalls += 1

    # Ensure that at least one firewall is returned that matches the filter
    assert (
        matched_firewalls > 0
    ), "Expected at least one firewall to match the hostname filter criteria."
