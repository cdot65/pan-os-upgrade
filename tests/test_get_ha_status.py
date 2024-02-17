import os
import pytest
from dotenv import load_dotenv
from pan_os_upgrade.upgrade import connect_to_host, get_ha_status

# Loading environment variables from .env file for credentials
load_dotenv(".dev.env")

# Updated test cases with corrected HA modes based on test results
test_cases = [
    ("panorama.cdot.io", "disabled", None),
    ("panorama1.cdot.io", "primary-active", None),
    ("panorama2.cdot.io", "secondary-passive", None),
    ("lab-fw1.cdot.io", "disabled", None),
    ("lab-fw6.cdot.io", "active", None),
    ("lab-fw7.cdot.io", "passive", None),
]


@pytest.mark.parametrize("hostname, expected_mode, expected_status", test_cases)
def test_get_ha_status(hostname, expected_mode, expected_status):
    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")

    # Ensure all required environment variables are set
    if not all([username, password]):
        pytest.skip(
            "Integration test skipped - missing required environment variables."
        )

    # Connect to the device
    target_device = connect_to_host(hostname, username, password)

    # Call the get_ha_status function
    ha_mode, ha_config = get_ha_status(target_device, hostname)

    # Assert the HA mode is as expected
    assert (
        ha_mode == expected_mode
    ), f"Unexpected HA mode for {hostname}. Expected: {expected_mode}, Got: {ha_mode}"

    # Since standalone devices are expected to have 'disabled' mode without ha_config, we skip ha_config checks for them
    if expected_mode != "disabled":
        # For HA devices, ha_config should not be None and should reflect the expected status if provided
        assert (
            ha_config is not None
        ), f"Expected HA configuration details for {hostname} in {expected_mode} mode"
        if expected_status:
            assert expected_status in str(
                ha_config
            ), f"Expected HA status '{expected_status}' not found in HA configuration for {hostname}"

    # Log or print HA status for informational purposes
    print(f"{hostname} - HA Mode: {ha_mode}")
    if ha_config:
        print(f"{hostname} - HA Configuration Details: {ha_config}")
