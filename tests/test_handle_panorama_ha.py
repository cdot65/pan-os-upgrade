import os
import pytest
from dotenv import load_dotenv
from panos.panorama import Panorama
from pan_os_upgrade.upgrade import connect_to_host, handle_panorama_ha

# Load environment variables from .env file
load_dotenv(".dev.env")

# Define test cases with different HA configurations and expected outcomes
test_cases = [
    (
        "panorama.cdot.io",
        "standalone",
        True,
    ),  # Standalone Panorama, should proceed with upgrade
    (
        "panorama1.cdot.io",
        "primary-active",
        False,
    ),  # Primary-active Panorama in HA, might not proceed if versions match
    (
        "panorama2.cdot.io",
        "secondary-passive",
        True,
    ),  # Secondary-passive Panorama in HA, should proceed with upgrade
]


@pytest.mark.integration
@pytest.mark.parametrize("hostname, expected_ha_role, expected_proceed", test_cases)
def test_handle_panorama_ha(hostname, expected_ha_role, expected_proceed):
    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")

    # Skip test if any necessary environment variable is missing
    if not all([username, password, hostname]):
        pytest.skip("Skipping test due to missing environment variables.")

    # Connect to the target device
    target_device = connect_to_host(hostname, username, password)

    # Ensure the target device is a Panorama instance
    assert isinstance(
        target_device, Panorama
    ), "Target device is not a Panorama instance."

    # Run the handle_panorama_ha function in dry_run mode to avoid making changes
    proceed, _ = handle_panorama_ha(target_device, hostname, dry_run=True)

    # Assert that the function's suggestion to proceed matches the expected outcome
    assert (
        proceed == expected_proceed
    ), f"Function's suggestion to proceed ({proceed}) does not match expected outcome ({expected_proceed}) for {hostname} with role {expected_ha_role}."

    # Additional checks can be added here based on the expected HA role and specific behaviors
