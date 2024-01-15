# models/assurance_report.py

from typing import Dict, Optional
from pydantic import BaseModel
from .arp_table import ArpTableEntry
from .content_version import ContentVersion
from .ip_sec_tunnel import IPSecTunnelEntry
from .license import LicenseFeatureEntry
from .nics import NetworkInterfaceStatus
from .routes import RouteEntry
from .session_stats import SessionStats


class AssuranceReport(BaseModel):
    hostname: str
    arp_table: Optional[Dict[str, ArpTableEntry]] = None
    content_version: Optional[ContentVersion] = None
    ip_sec_tunnels: Optional[Dict[str, IPSecTunnelEntry]] = None
    license: Optional[Dict[str, LicenseFeatureEntry]] = None
    nics: Optional[Dict[str, NetworkInterfaceStatus]] = None
    routes: Optional[Dict[str, RouteEntry]] = None
    session_stats: Optional[SessionStats] = None
