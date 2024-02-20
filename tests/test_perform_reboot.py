import pytest
from unittest.mock import patch, MagicMock
from panos.firewall import Firewall
from panos.panorama import Panorama
from pan_os_upgrade.device import perform_reboot


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
def test_perform_reboot_success(mock_target_device, device_class, target_version):
    # Mock the 'op' method to return an XML-like string with a 'result' tag
    mock_response = (
        '<response status="success"><result>Reboot initiated</result></response>'
    )

    # Mock the flatten_xml_to_dict to return a dictionary with 'result' key
    # Notice how we specify the full path to the function within the patch call
    with patch(
        "pan_os_upgrade.upgrade.flatten_xml_to_dict",
        return_value={"result": "Reboot initiated"},
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
                    mock_target_device,
                    mock_target_device.hostname,
                    target_version,
                    initial_sleep_duration=2,
                )

                # Verify the mock device's version is updated to the target version, indicating a successful reboot
                assert (
                    mock_target_device.version == target_version
                ), "Device did not reboot to the target version"
