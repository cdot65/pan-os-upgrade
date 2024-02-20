import os
import pytest
import tempfile
import json
from dotenv import load_dotenv
from pan_os_upgrade.components.device import connect_to_host
from pan_os_upgrade.components.assurance import perform_readiness_checks
from panos.firewall import Firewall

# Load environment variables from .env file
load_dotenv(".dev.env")

# Define test cases for different firewalls
test_cases = [
    "lab-fw1.cdot.io",  # Standalone firewall
    "lab-fw6.cdot.io",  # HA firewall 1
    "lab-fw7.cdot.io",  # HA firewall 2
]


@pytest.mark.integration
@pytest.mark.parametrize("hostname", test_cases)
def test_perform_readiness_checks(hostname, tmp_path):
    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")

    # Skip test if any necessary environment variable is missing
    if not all([username, password, hostname]):
        pytest.skip("Skipping test due to missing environment variables.")

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

    # Create a temporary file for the readiness report in the current working directory
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".json", mode="w+"
    ) as tmp_file:
        test_readiness_path = tmp_file.name

    # Create a temporary YAML settings file with the desired log file path in the temp directory
    settings_file = tmp_path / "settings.yaml"
    log_file_path = tmp_path / "test.log"  # Use the temp path for the log file
    settings_content = f"""
    logging:
      level: DEBUG
      file_path: {log_file_path}  # Use the temp log file path here
      max_size: 10
      upgrade_log_count: 3
    """
    settings_file.write_text(settings_content)

    # Perform readiness checks and save to the temporary file
    perform_readiness_checks(
        file_path=test_readiness_path,
        firewall=target_device,
        hostname=hostname,
        settings_file_path=settings_file,
    )

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
