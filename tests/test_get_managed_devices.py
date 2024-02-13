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
