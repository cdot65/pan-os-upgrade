# models/license.py

from pydantic import BaseModel, Field
from typing import Optional
from collections import OrderedDict


class LicenseFeatureEntry(BaseModel):
    feature: str
    description: str
    serial: str
    issued: str
    expires: str
    expired: str
    base_license_name: Optional[str] = Field(None, alias="base-license-name")
    authcode: Optional[str]
    custom: Optional[OrderedDict] = None
