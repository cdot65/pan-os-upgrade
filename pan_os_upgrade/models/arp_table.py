# models/arp_table.py
from pydantic import BaseModel


class ArpTableEntry(BaseModel):
    interface: str
    ip: str
    mac: str
    port: str
    status: str
    ttl: int
