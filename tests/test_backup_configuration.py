import os
import pytest
import tempfile
from pan_os_upgrade.device import connect_to_host
from pan_os_upgrade.upgrade import backup_configuration
from dotenv import load_dotenv


@pytest.mark.integration
def test_backup_configuration():
    load_dotenv(".dev.env")

    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")
    hostname = os.getenv("PANORAMA")

    if not all([username, password, hostname]):
        pytest.skip(
            "Integration test skipped - no device credentials provided in environment"
        )

    # Connect to the device
    target_device = connect_to_host(hostname, username, password)

    # Create a temporary file for the backup in the current working directory
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        test_backup_path = tmp_file.name

    # Ensure the temporary file is deleted if it exists from a previous test run
    if os.path.exists(test_backup_path):
        os.remove(test_backup_path)

    # Call the backup_configuration function
    backup_success = backup_configuration(
        file_path=test_backup_path,
        hostname=hostname,
        target_device=target_device,
    )

    assert backup_success, "Backup should succeed"

    # Check the backup file exists and has content
    assert os.path.exists(test_backup_path), "Backup file should exist"
    assert os.path.getsize(test_backup_path) > 0, "Backup file should not be empty"

    # Cleanup: remove the test backup file
    os.remove(test_backup_path)
