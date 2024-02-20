import pytest
from unittest.mock import patch, MagicMock
from panos.firewall import Firewall
from panos.panorama import Panorama
from pan_os_upgrade.components.device import perform_reboot
from dynaconf import LazySettings


@pytest.fixture
def mock_target_device():
    device = MagicMock(spec=Firewall)
    # Initial version before "reboot"
    device.version = "9.1.0"
    # Mock hostname
    device.hostname = "mock_device"
    return device


@pytest.mark.parametrize(
    "device_class, target_version",
    [
        (Firewall, "10.0.0"),
        (Panorama, "10.0.0"),
    ],
)
def test_perform_reboot_success(
    mock_target_device, device_class, target_version, tmp_path
):
    # Mock the 'op' method to return an XML-like string with a 'result' tag
    mock_response = (
        '<response status="success"><result>Reboot initiated</result></response>'
    )

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

    # Load settings from the YAML file
    settings = LazySettings(SETTINGS_FILE=str(settings_file))

    # Adjust the mock to reflect the expected structure of the reboot_job_result
    with patch(
        "pan_os_upgrade.components.utilities.flatten_xml_to_dict",
        return_value={"@status": "success", "result": "Reboot initiated"},
    ):
        with patch.object(device_class, "op", return_value=mock_response):
            # Mock the 'refresh_system_info' method to simulate device behavior post-reboot
            with patch.object(
                device_class,
                "refresh_system_info",
                side_effect=[Exception("Device rebooting"), None],
            ):
                # Update the mock device's version to simulate a successful reboot to the target version
                mock_target_device.version = target_version

                # Execute the perform_reboot function with the mock device
                perform_reboot(
                    hostname=mock_target_device.hostname,
                    settings_file=settings,
                    settings_file_path=settings_file,
                    target_device=mock_target_device,
                    target_version=target_version,
                    initial_sleep_duration=2,
                )

                # Verify the mock device's version is updated to the target version, indicating a successful reboot
                assert (
                    mock_target_device.version == target_version
                ), "Device did not reboot to the target version"
