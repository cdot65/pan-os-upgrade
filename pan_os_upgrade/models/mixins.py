# models/mixins.py

from abc import abstractmethod
from typing import Self


class FromAPIResponseMixin:
    """Mixin class to identify models that can be parsed directly from the XML returned by a given API response."""

    pass

    @classmethod
    @abstractmethod
    def from_api_response(cls, response: dict) -> Self:
        pass
