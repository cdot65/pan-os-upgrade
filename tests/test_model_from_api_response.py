from typing import List
from xml.etree import ElementTree as ET

import pytest
from pydantic import BaseModel

from pan_os_upgrade.utilities import model_from_api_response


# Define your model classes
class ManagedDevice(BaseModel):
    hostname: str
    serial: str
    connected: bool


class ManagedDevices(BaseModel):
    devices: List[ManagedDevice]

    @classmethod
    def from_api_response(cls, response: dict) -> "ManagedDevices":
        devices_list = response.get("result", {}).get("devices", {}).get("entry", [])
        devices = [
            ManagedDevice(
                hostname=device.get("hostname"),
                serial=device.get("serial"),
                connected=device.get("connected", "false").lower() == "true",
            )
            for device in devices_list
        ]
        return cls(devices=devices)


# Define a fixture for a sample XML API response
@pytest.fixture
def sample_xml_response():
    return ET.fromstring(
        """
        <response status="success">
            <result>
                <devices>
                    <entry>
                        <hostname>Woodlands-fw1</hostname>
                        <serial>007954000123451</serial>
                        <connected>true</connected>
                    </entry>
                    <entry>
                        <hostname>houston</hostname>
                        <serial>007954000123453</serial>
                        <connected>true</connected>
                    </entry>
                    <entry>
                        <hostname>Woodlands-fw2</hostname>
                        <serial>007954000123452</serial>
                        <connected>true</connected>
                    </entry>
                </devices>
            </result>
        </response>
    """
    )


# Define the test for model_from_api_response
def test_model_from_api_response(sample_xml_response):
    # Directly use the XML response with the model_from_api_response function
    managed_devices = model_from_api_response(sample_xml_response, ManagedDevices)

    assert isinstance(
        managed_devices, ManagedDevices
    ), "The result should be an instance of ManagedDevices"
    assert len(managed_devices.devices) == 3, "There should be 3 managed devices"

    # Verify each managed device
    for device in managed_devices.devices:
        assert isinstance(
            device, ManagedDevice
        ), "Each item should be an instance of ManagedDevice"
        assert isinstance(
            device.connected, bool
        ), "The 'connected' attribute should be a boolean"
        assert device.hostname in [
            "Woodlands-fw1",
            "houston",
            "Woodlands-fw2",
        ], "Hostname should match one of the expected values"
