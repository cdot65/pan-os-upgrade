import os
import pytest
from dotenv import load_dotenv
from panos.firewall import Firewall
from pan_os_upgrade.upgrade import (
    connect_to_host,
    get_ha_status,
    handle_firewall_ha,
    target_devices_to_revisit,
)

# Load environment variables from .env file
load_dotenv(".dev.env")

# Define test cases with different HA configurations
test_cases = [
    ("houston.cdot.io", None),  # Standalone, expecting no HA peer and proceed
    (
        "woodlands-fw1.cdot.io",
        "passive",
    ),  # HA and is passive, expecting HA peer status and proceed
    (
        "woodlands-fw2.cdot.io",
        "active",
    ),  # HA and is active, might be added to revisit list, check proceed accordingly
]


@pytest.mark.integration
@pytest.mark.parametrize("hostname, expected_ha_status", test_cases)
def test_handle_firewall_ha(hostname, expected_ha_status):
    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")

    # Skip test if any necessary environment variable is missing
    if not all([username, password, hostname]):
        pytest.skip("Skipping test due to missing environment variables.")

    # Connect to the target device
    target_device = connect_to_host(hostname, username, password)

    # Ensure the target device is a Firewall instance
    assert isinstance(
        target_device, Firewall
    ), "Target device is not a Firewall instance."

    # Clear the revisit list before the test
    target_devices_to_revisit.clear()

    # Run the handle_firewall_ha function in dry_run mode to avoid making changes
    proceed, ha_peer = handle_firewall_ha(target_device, hostname, dry_run=True)

    # For 'active' devices that might be added to the revisit list, check the list instead of proceed flag
    if expected_ha_status == "active":
        assert (
            target_device in target_devices_to_revisit
        ), "Active HA device should be added to the revisit list."
    else:
        # Assert that the function suggests proceeding with the upgrade for other cases
        assert proceed, "Function should suggest proceeding with the upgrade."

    # Check if the HA status matches the expected status for HA peers
    if expected_ha_status:
        deploy_info, ha_details = get_ha_status(target_device, hostname)
        actual_ha_status = (
            ha_details["result"]["group"]["local-info"]["state"] if ha_details else None
        )
        assert (
            actual_ha_status == expected_ha_status
        ), f"Expected HA status '{expected_ha_status}', but got '{actual_ha_status}'."
    else:
        assert ha_peer is None, "Did not expect an HA peer but one was found."
