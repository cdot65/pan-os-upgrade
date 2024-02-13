import os
import pytest
import re
from dotenv import load_dotenv

from panos.device import SystemSettings
from panos.panorama import Panorama
from panos.firewall import Firewall

from pan_os_upgrade.upgrade import get_firewalls_from_panorama


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
def test_get_firewalls_from_panorama_with_hostname_filter(panorama):
    """Test getting firewalls from Panorama."""

    # Retrieve firewalls
    firewalls = get_firewalls_from_panorama(panorama)

    assert isinstance(firewalls, list), "Expected a list of Firewall objects."
    assert all(
        isinstance(fw, Firewall) for fw in firewalls
    ), "Each item in the list should be a Firewall object."
