import os
import pytest
import threading
from dotenv import load_dotenv
from panos.firewall import Firewall
from pan_os_upgrade.components.device import connect_to_host
from pan_os_upgrade.components.ha import handle_firewall_ha
from dynaconf import LazySettings

# Load environment variables from .env file
load_dotenv(".dev.env")

# Define test cases with different HA configurations
test_cases = [
    (
        "austin-fw1.cdot.io",
        "active-primary",
    ),  # HA and is active-primary, might be added to revisit list, check proceed accordingly
    (
        "austin-fw2.cdot.io",
        "active",
    ),  # HA and is active, might be added to revisit list, check proceed accordingly
    ("austin-fw3.cdot.io", None),  # Standalone, expecting no HA peer and proceed
    (
        "dallas-fw1.cdot.io",
        "active",
    ),  # HA and is active, might be added to revisit list, check proceed accordingly
    (
        "dallas-fw2.cdot.io",
        "passive",
    ),  # HA and is passive, expecting HA peer status and proceed
]


@pytest.fixture(scope="module")
def settings_file(tmp_path_factory):
    # Create a temporary YAML settings file
    settings_content = """
    concurrency:
      threads: 99
    # Add other settings as needed
    """
    settings_file = tmp_path_factory.mktemp("data") / "settings.yaml"
    settings_file.write_text(settings_content)
    return settings_file


@pytest.mark.integration
@pytest.mark.parametrize("hostname, expected_ha_status", test_cases)
def test_handle_firewall_ha(hostname, expected_ha_status, settings_file):
    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")

    # Skip test if any necessary environment variable is missing
    if not all([username, password, hostname]):
        pytest.skip("Skipping test due to missing environment variables.")

    # Load settings from the YAML file
    settings = LazySettings(SETTINGS_FILE=str(settings_file))

    # Connect to the target device
    target_device = connect_to_host(
        hostname=hostname,
        password=password,
        username=username,
    )

    # Ensure the target device is a Firewall instance
    assert isinstance(
        target_device, Firewall
    ), "Target device is not a Firewall instance."

    # Prepare for handling HA devices
    target_devices_to_revisit = []
    target_devices_to_revisit_lock = threading.Lock()

    # Run the handle_firewall_ha function in dry_run mode to avoid making changes
    proceed_with_upgrade, peer_firewall = handle_firewall_ha(
        dry_run=True,
        hostname=hostname,
        settings_file=settings,
        settings_file_path=settings_file,
        target_device=target_device,
        target_devices_to_revisit=target_devices_to_revisit,
        target_devices_to_revisit_lock=target_devices_to_revisit_lock,
    )

    # Assert that the function suggests proceeding with the upgrade for standalone devices
    if expected_ha_status is None:
        assert (
            proceed_with_upgrade
        ), f"Expected to proceed with upgrade for standalone device {hostname}, but did not."

    # For 'active' HA devices, check if they are added to the revisit list and not proceeding with the upgrade
    elif expected_ha_status == "active":
        with target_devices_to_revisit_lock:
            assert (
                target_device in target_devices_to_revisit
            ), f"Expected active HA device {hostname} to be added to the revisit list."
            assert (
                not proceed_with_upgrade
            ), f"Did not expect to proceed with upgrade for active HA device {hostname}."

    # For 'passive' HA devices, the function should typically suggest proceeding with the upgrade
    elif expected_ha_status == "passive":
        assert (
            proceed_with_upgrade
        ), f"Expected to proceed with upgrade for passive HA device {hostname}, but did not."
        with target_devices_to_revisit_lock:
            assert (
                target_device not in target_devices_to_revisit
            ), f"Did not expect passive HA device {hostname} to be added to the revisit list."

    # Assert no HA peer for standalone configurations
    if expected_ha_status is None:
        assert (
            peer_firewall is None
        ), f"Did not expect an HA peer for standalone device {hostname}, but found one."
