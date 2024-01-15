# models/content_version.py

from pydantic import BaseModel


class ContentVersion(BaseModel):
    version: str
