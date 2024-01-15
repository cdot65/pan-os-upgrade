class AssuranceOptions:
    """
    Configuration options for panos-upgrade-assurance.

    This class contains various configurations used in the upgrade assurance process
    for PAN-OS appliances, including definitions for readiness checks, state snapshots,
    and reports.
    """

    READINESS_CHECKS = [
        "active_support",
        "arp_entry_exist",
        "candidate_config",
        "content_version",
        "free_disk_space",
        "expired_licenses",
        "ha",
        "ip_sec_tunnel_status",
        "ntp_sync",
        "panorama",
        "planes_clock_sync",
        "session_exist",
    ]

    STATE_SNAPSHOTS = [
        "arp_table",
        "content_version",
        "ip_sec_tunnels",
        "license",
        "nics",
        "routes",
        "session_stats",
    ]

    REPORTS = [
        "arp_table",
        "content_version",
        "ip_sec_tunnels",
        "license",
        "nics",
        "routes",
        "session_stats",
    ]
