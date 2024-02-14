import os
import pytest
from dotenv import load_dotenv
from pan_os_upgrade.upgrade import (
    connect_to_host,
    get_firewalls_from_panorama,
    get_firewalls_info,
    create_firewall_mapping,
)
from panos.firewall import Firewall


# Load environment variables from .dev.env for integration tests
@pytest.fixture(scope="session", autouse=True)
def load_env():
    load_dotenv(".dev.env")


@pytest.fixture
def sample_firewalls():
    return [
        Firewall(serial="001"),
        Firewall(serial="002"),
        Firewall(serial="003"),
    ]


@pytest.fixture
def sample_firewalls_info():
    # Sample firewall information corresponding to the Firewall objects in sample_firewalls
    return [
        {
            "hostname": "fw1",
            "serial": "001",
            "ip-address": "10.0.0.1",
            "model": "PA-VM",
            "sw-version": "9.1.0",
            "app-version": "1234",
        },
        {
            "hostname": "fw2",
            "serial": "002",
            "ip-address": "10.0.0.2",
            "model": "PA-VM",
            "sw-version": "9.1.0",
            "app-version": "1234",
        },
        {
            "hostname": "fw3",
            "serial": "003",
            "ip-address": "10.0.0.3",
            "model": "PA-VM",
            "sw-version": "9.1.0",
            "app-version": "1234",
        },
    ]


@pytest.mark.integration
def test_create_firewall_mapping_integration():
    # Load required environment variables
    hostname = os.getenv("PANORAMA")
    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")

    # Skip the test if any required environment variable is missing
    if not all([hostname, username, password]):
        pytest.skip(
            "Integration test skipped - required environment variables are not set"
        )

    # Connect to Panorama
    panorama = connect_to_host(hostname, username, password)

    # Get firewalls managed by Panorama
    all_firewalls = get_firewalls_from_panorama(panorama)

    # Ensure that firewalls are retrieved
    assert all_firewalls, "No firewalls retrieved from Panorama"

    # Fetch detailed information for each firewall
    firewalls_info = get_firewalls_info(all_firewalls)

    # Ensure that information is retrieved for each firewall
    assert firewalls_info, "Failed to retrieve firewall information"

    # Create the firewall mapping
    firewall_mapping = create_firewall_mapping(all_firewalls, firewalls_info)

    # check that the mapping includes all expected firewalls and their details
    for fw_info in firewalls_info:
        hostname = fw_info["hostname"]
        serial = fw_info["serial"]
        assert hostname in firewall_mapping, f"Hostname {hostname} not found in mapping"
        assert (
            firewall_mapping[hostname]["serial"] == serial
        ), f"Serial number for {hostname} does not match"


def test_invalid_firewall_entry_does_not_get_mapped(
    sample_firewalls, sample_firewalls_info
):
    # Add an invalid firewall info entry
    invalid_firewall_info = {
        "hostname": "invalid-fw",
        "serial": "invalid-serial",
        "ip-address": "10.0.0.255",
    }
    sample_firewalls_info.append(invalid_firewall_info)

    # Create the mapping
    firewall_mapping = create_firewall_mapping(sample_firewalls, sample_firewalls_info)

    # Check that the invalid entry is not in the mapping
    assert (
        "invalid-fw" not in firewall_mapping
    ), "Invalid firewall entry should not be mapped"
