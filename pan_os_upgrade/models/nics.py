#  models/nics.py

from pydantic import BaseModel, validator, root_validator


class NetworkInterfaceStatus(BaseModel):
    status: str

    @root_validator(pre=True)
    def parse_root(cls, values):
        if isinstance(values, str):
            return {"status": values}
        raise ValueError("Invalid input for network interface status")

    @validator("status")
    def check_status(cls, v):
        if v not in ("up", "down"):
            raise ValueError('Status must be "up" or "down"')
        return v
