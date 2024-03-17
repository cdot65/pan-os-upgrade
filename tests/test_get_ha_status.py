import os
import pytest
from dotenv import load_dotenv
from pan_os_upgrade.components.device import connect_to_host, get_ha_status

# Loading environment variables from .env file for credentials
load_dotenv(".dev.env")

# Updated test cases with corrected HA modes based on test results
test_cases = [
    ("panorama1.cdot.io", "primary-active", None),
    ("panorama2.cdot.io", "secondary-passive", None),
    ("austin-fw1.cdot.io", "active-primary", None),
    ("austin-fw2.cdot.io", "active-secondary", None),
    ("austin-fw3.cdot.io", "disabled", None),
    ("dallas-fw1.cdot.io", "active", None),
    ("dallas-fw2.cdot.io", "passive", None),
    ("houston-fw1.cdot.io", "active", None),
    ("houston-fw2.cdot.io", "passive", None),
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
    target_device = connect_to_host(
        hostname=hostname,
        password=password,
        username=username,
    )

    # Call the get_ha_status function
    ha_mode, ha_config = get_ha_status(
        hostname=hostname,
        target_device=target_device,
    )

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
