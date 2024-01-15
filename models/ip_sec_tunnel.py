# models/ip_sec_tunnel.py

from pydantic import BaseModel, Field


class IPSecTunnelEntry(BaseModel):
    peerip: str
    name: str
    outer_if: str = Field(..., alias="outer-if")
    gwid: str
    localip: str
    state: str
    inner_if: str = Field(..., alias="inner-if")
    mon: str
    owner: str
    id: str
