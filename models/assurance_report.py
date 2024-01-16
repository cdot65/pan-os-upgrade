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


class SnapshotReport(BaseModel):
    hostname: str
    arp_table: Optional[Dict[str, ArpTableEntry]] = None
    content_version: Optional[ContentVersion] = None
    ip_sec_tunnels: Optional[Dict[str, IPSecTunnelEntry]] = None
    license: Optional[Dict[str, LicenseFeatureEntry]] = None
    nics: Optional[Dict[str, NetworkInterfaceStatus]] = None
    routes: Optional[Dict[str, RouteEntry]] = None
    session_stats: Optional[SessionStats] = None


class ReadinessCheckResult(BaseModel):
    state: bool
    reason: str


class ReadinessCheckReport(BaseModel):
    active_support: Optional[ReadinessCheckResult] = None
    arp_entry_exist: Optional[ReadinessCheckResult] = None
    candidate_config: Optional[ReadinessCheckResult] = None
    certificates_requirements: Optional[ReadinessCheckResult] = None
    content_version: Optional[ReadinessCheckResult] = None
    dynamic_updates: Optional[ReadinessCheckResult] = None
    expired_licenses: Optional[ReadinessCheckResult] = None
    free_disk_space: Optional[ReadinessCheckResult] = None
    ha: Optional[ReadinessCheckResult] = None
    ip_sec_tunnel_status: Optional[ReadinessCheckResult] = None
    jobs: Optional[ReadinessCheckResult] = None
    ntp_sync: Optional[ReadinessCheckResult] = None
    panorama: Optional[ReadinessCheckResult] = None
    planes_clock_sync: Optional[ReadinessCheckResult] = None
    session_exist: Optional[ReadinessCheckResult] = None
