import os
import pytest
from dotenv import load_dotenv

from panos.panorama import Panorama
from pan_os_upgrade.device import get_managed_devices

# project imports
from pan_os_upgrade.models import (
    ManagedDevice,
)


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
def test_get_managed_devices(panorama):
    """Test getting firewalls from Panorama."""

    # Retrieve firewalls
    firewalls = get_managed_devices(panorama)

    assert isinstance(firewalls, list), "Expected a list of Firewall objects."
    assert all(
        isinstance(fw, ManagedDevice) for fw in firewalls
    ), "Each item in the list should be a Firewall object."
