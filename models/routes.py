# models/route.py

from pydantic import BaseModel, Field
from typing import Optional


class RouteEntry(BaseModel):
    virtual_router: str = Field(..., alias="virtual-router")
    destination: str
    nexthop: str
    metric: str
    flags: str
    age: Optional[str]
    interface: Optional[str]
    route_table: str = Field(..., alias="route-table")
