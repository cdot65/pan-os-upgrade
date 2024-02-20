import os
import pytest
from dotenv import load_dotenv
from pan_os_upgrade.device import connect_to_host
from pan_os_upgrade.utilities import determine_upgrade
from panos.firewall import Firewall
from panos.panorama import Panorama

# Loading environment variables from .env file
load_dotenv(".dev.env")


@pytest.mark.integration
def test_determine_upgrade():
    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")
    hostname = os.getenv("PANORAMA")

    # Ensure all required environment variables are set
    if not all([username, password, hostname]):
        pytest.skip(
            "Integration test skipped - missing required environment variables."
        )

    # Connect to the device
    target_device = connect_to_host(hostname, username, password)

    # Ensure the connection was successful and the device is either a Firewall or Panorama instance
    assert isinstance(
        target_device, (Firewall, Panorama)
    ), "Failed to connect to the device or device type is unsupported."

    # Define the target PAN-OS version for the upgrade check
    target_major = 11  # For example, target PAN-OS 11.x.x
    target_minor = 0  # For example, target PAN-OS x.0.x
    target_maintenance = "1-h1"  # For example, target PAN-OS x.x.1-h1

    # Use a try-except block to capture the SystemExit raised by the determine_upgrade function when no upgrade is needed or a downgrade is attempted
    try:
        determine_upgrade(
            target_device, hostname, target_major, target_minor, target_maintenance
        )
    except SystemExit as e:
        assert (
            str(e) == "1"
        ), "The script halted as expected due to no upgrade requirement or a downgrade attempt."
