# models/devices.py

from pydantic import BaseModel
from pan_os_upgrade.models.mixins import FromAPIResponseMixin


class ManagedDevice(BaseModel):
    """Single device from output of `show devices all` on panorama"""

    hostname: str
    serial: str
    connected: bool


class ManagedDevices(BaseModel, FromAPIResponseMixin):
    """Output of `show devices all`"""

    devices: list[ManagedDevice]

    @classmethod
    def from_api_response(cls, response: dict):
        fixed_dict = {"devices": response.get("result").get("devices").get("entry")}
        return cls(**fixed_dict)
