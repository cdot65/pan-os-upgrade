import os
import pytest
import tempfile
import json
from pan_os_upgrade.upgrade import connect_to_host, perform_readiness_checks
from dotenv import load_dotenv
from panos.firewall import Firewall

# Load environment variables from .env file
load_dotenv(".dev.env")

# Define test cases for different firewalls
test_cases = [
    "houston.cdot.io",  # Standalone firewall
    "woodlands-fw1.cdot.io",  # HA firewall 1
    "woodlands-fw2.cdot.io",  # HA firewall 2
]


@pytest.mark.integration
@pytest.mark.parametrize("hostname", test_cases)
def test_perform_readiness_checks(hostname):
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

    # Create a temporary file for the readiness report in the current working directory
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".json", mode="w+"
    ) as tmp_file:
        test_readiness_path = tmp_file.name

    # Perform readiness checks and save to the temporary file
    perform_readiness_checks(target_device, hostname, test_readiness_path)

    # Verify the readiness report file is created
    assert os.path.exists(test_readiness_path), "Readiness report file was not created"
    with open(test_readiness_path, "r") as report_file:
        try:
            # Load and validate JSON content
            report_content = json.load(report_file)

            # Define expected keys in the readiness report
            expected_keys = [
                "active_support",
                "arp_entry_exist",
                "candidate_config",
                "certificates_requirements",
                "content_version",
                "dynamic_updates",
                "expired_licenses",
                "free_disk_space",
                "ha",
                "ip_sec_tunnel_status",
                "jobs",
                "ntp_sync",
                "panorama",
                "planes_clock_sync",
                "session_exist",
            ]

            # Check if all expected keys are in the report
            missing_keys = [key for key in expected_keys if key not in report_content]
            assert not missing_keys, f"Missing keys in the report: {missing_keys}"

        except json.JSONDecodeError:
            pytest.fail("Readiness report file is not valid JSON")

    # Cleanup: remove the test readiness report file
    os.remove(test_readiness_path)
