from typing import Dict, Optional, List, Union
from panos.firewall import Firewall
from pan_os_upgrade.models import (
    SnapshotReport,
    ReadinessCheckReport,
    # ManagedDevice,
    # ManagedDevices,
    # FromAPIResponseMixin,
)
import logging

# project imports
from pan_os_upgrade.models import (
    SnapshotReport,
    ReadinessCheckReport,
    ManagedDevice,
    ManagedDevices,
    FromAPIResponseMixin,
)

# Palo Alto Networks panos-upgrade-assurance imports
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare


# Define panos-upgrade-assurance options
class AssuranceOptions:
    """
    Centralizes configuration options for readiness checks, reports, and state snapshots in the upgrade assurance process.

    This class provides a structured approach to define and access various configuration options related to the upgrade
    assurance process for Palo Alto Networks devices. It outlines available readiness checks, types of reports, and
    categories of state snapshots that can be utilized during the device upgrade process. These configurations are
    designed to be flexible, allowing customization through an external `settings.yaml` file to cater to specific
    operational needs and preferences.

    Attributes
    ----------
    READINESS_CHECKS : dict
        A dictionary mapping the names of readiness checks to their attributes, which include descriptions, associated
        log levels, and flags to indicate whether to exit the process upon check failure. These checks are designed to
        ensure a device's readiness for an upgrade by validating its operational and configuration status.
    REPORTS : dict
        A dictionary enumerating the types of reports that can be generated to offer insights into the device's state
        before and after an upgrade. These reports encompass aspects like ARP tables, content versions, IPsec tunnels,
        licenses, network interfaces, routing tables, and session statistics.
    STATE_SNAPSHOTS : dict
        A dictionary listing the categories of state snapshots that can be captured to document essential data about
        the device's current state. These snapshots are crucial for diagnostics and verifying the device's operational
        status before proceeding with the upgrade.

    Examples
    --------
    Accessing the log level for the 'active_support' readiness check:
        >>> log_level = AssuranceOptions.READINESS_CHECKS['active_support']['log_level']
        >>> print(log_level)
        'warning'

    Iterating through all available report types:
        >>> for report_type in AssuranceOptions.REPORTS:
        ...     print(report_type)
        'arp_table'
        'content_version'
        ...

    Notes
    -----
    - The configurations for readiness checks, report types, and state snapshots provided in this class can be selectively
      enabled or customized through the `settings.yaml` file. This allows users to adapt the upgrade assurance process
      to their specific requirements and scenarios.
    - Default settings are predefined within this class; however, they can be overridden by specifying custom configurations
      in the `settings.yaml` file, thus enhancing the script's flexibility and adaptability to different upgrade contexts.
    """

    READINESS_CHECKS = {
        "active_support": {
            "description": "Check if active support is available",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "arp_entry_exist": {
            "description": "Check if a given ARP entry is available in the ARP table",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "candidate_config": {
            "description": "Check if there are pending changes on device",
            "log_level": "error",
            "exit_on_failure": True,
            "enabled_by_default": True,
        },
        "certificates_requirements": {
            "description": "Check if the certificates' keys meet minimum size requirements",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "content_version": {
            "description": "Running Latest Content Version",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "dynamic_updates": {
            "description": "Check if any Dynamic Update job is scheduled to run within the specified time window",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "expired_licenses": {
            "description": "No Expired Licenses",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "free_disk_space": {
            "description": "Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "ha": {
            "description": "Checks HA pair status from the perspective of the current device",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "ip_sec_tunnel_status": {
            "description": "Check if a given IPsec tunnel is in active state",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "jobs": {
            "description": "Check for any job with status different than FIN",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "ntp_sync": {
            "description": "Check if NTP is synchronized",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "planes_clock_sync": {
            "description": "Check if the clock is synchronized between dataplane and management plane",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "panorama": {
            "description": "Check connectivity with the Panorama appliance",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "session_exist": {
            "description": "Check if a critical session is present in the sessions table",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
    }

    # This is a placeholder for the report types, currently no reports are executed
    REPORTS = {
        "arp_table": {
            "enabled_by_default": True,
            "description": "ARP Table",
        },
        "content_version": {
            "enabled_by_default": True,
            "description": "App Content Version",
        },
        "ip_sec_tunnels": {
            "enabled_by_default": True,
            "description": "IPsec VPN tunnels",
        },
        "license": {
            "enabled_by_default": True,
            "description": "License Information",
        },
        "nics": {
            "enabled_by_default": True,
            "description": "Network Interfaces",
        },
        "routes": {
            "enabled_by_default": False,
            "description": "Route Table",
        },
        "session_stats": {
            "enabled_by_default": True,
            "description": "Session Stats",
        },
    }

    STATE_SNAPSHOTS = {
        "arp_table": {
            "enabled_by_default": False,
            "description": "Snapshot of the ARP Table",
        },
        "content_version": {
            "enabled_by_default": True,
            "description": "Snapshot of the Content Version",
        },
        "ip_sec_tunnels": {
            "enabled_by_default": False,
            "description": "Snapshot of the IPsec Tunnels",
        },
        "license": {
            "enabled_by_default": True,
            "description": "Snapshot of the License Information",
        },
        "nics": {
            "enabled_by_default": True,
            "description": "Snapshot of the Network Interfaces",
        },
        "routes": {
            "enabled_by_default": False,
            "description": "Snapshot of the Routing Table",
        },
        "session_stats": {
            "enabled_by_default": False,
            "description": "Snapshot of the Session Statistics",
        },
    }


# class UpgradeAssurance:
#     def __init__(self, device, hostname):
#         self.device = device
#         self.hostname = hostname
#         self.proxy_device = FirewallProxy(self.device)
#         self.checks_device = CheckFirewall(self.proxy_device)

#     def check_readiness_and_log(self, result, test_name, test_info):
#         """
#         Analyzes and logs the outcomes of readiness checks for a firewall or Panorama device,
#         emphasizing failures that could impact the upgrade process.
#         """
#         test_result = result.get(
#             test_name, {"state": False, "reason": "Skipped Readiness Check"}
#         )
#         reason = test_result.get("reason", "No reason provided")
#         log_message = f'{reason}: {test_info["description"]}'

#         if test_result["state"]:
#             logging.info(
#                 f"{get_emoji('success')} {self.hostname}: Passed Readiness Check: {test_info['description']}"
#             )
#         else:
#             if test_info["log_level"] == "error":
#                 logging.error(f"{get_emoji('error')} {self.hostname}: {log_message}")
#                 if test_info["exit_on_failure"]:
#                     logging.error(
#                         f"{get_emoji('stop')} {self.hostname}: Halting script."
#                     )
#                     sys.exit(1)
#             elif test_info["log_level"] == "warning":
#                 logging.info(
#                     f"{get_emoji('skipped')} {self.hostname}: Skipped Readiness Check: {test_info['description']}"
#                 )
#             else:
#                 logging.info(
#                     f"{get_emoji('report')} {self.hostname}: Log Message {log_message}"
#                 )

#     def perform_readiness_checks(self, hostname: str, file_path: str) -> None:
#         """
#         Executes readiness checks to verify the device's preparedness for an upgrade.

#         Parameters
#         ----------
#         hostname : str
#             The hostname or IP address of the device, used for identification and logging.
#         file_path : str
#             The path where the readiness report will be saved.

#         Example
#         -------
#         >>> assurance_manager = Assurance(firewall)
#         >>> assurance_manager.perform_readiness_checks('192.168.1.1', '/path/to/readiness_report.json')
#         """
#         # Implementation of the readiness checks and report generation logic...
#         pass

#     def perform_snapshot(
#         self, hostname: str, file_path: str, actions: Optional[List[str]] = None
#     ) -> SnapshotReport:
#         """
#         Captures a detailed snapshot of the device's current state for upgrade assurance purposes.

#         Parameters
#         ----------
#         hostname : str
#             The hostname or IP address of the device, used for identification and logging.
#         file_path : str
#             The path where the snapshot report will be saved.
#         actions : Optional[List[str]]
#             Custom actions or data points to include in the snapshot.

#         Returns
#         -------
#         SnapshotReport
#             The snapshot report object containing detailed state information.

#         Example
#         -------
#         >>> assurance_manager = AssuranceManager(firewall)
#         >>> snapshot_report = assurance_manager.perform_snapshot('192.168.1.1', '/path/to/snapshot.json')
#         """
#         # Implementation of the snapshot capture and saving logic...
#         pass

#     def run_assurance(self, operation_type, actions, config):
#         """
#         Executes specified operational tasks, such as readiness checks or state snapshots, on a firewall
#         based on the given operation type.
#         """
#         results = None
#         if operation_type == "readiness_check":
#             for action in actions:
#                 if action not in AssuranceOptions.READINESS_CHECKS.keys():
#                     logging.error(
#                         f"{get_emoji('error')} {self.hostname}: Invalid action for readiness check: {action}"
#                     )
#                     sys.exit(1)
#             try:
#                 logging.info(
#                     f"{get_emoji('start')} {self.hostname}: Performing readiness checks to determine if firewall is ready for upgrade."
#                 )
#                 result = self.checks_device.run_readiness_checks(actions)
#                 for test_name, test_info in AssuranceOptions.READINESS_CHECKS.items():
#                     self.check_readiness_and_log(result, test_name, test_info)
#                 return ReadinessCheckReport(**result)
#             except Exception as e:
#                 logging.error(
#                     f"{get_emoji('error')} {self.hostname}: Error running readiness checks: {e}"
#                 )
#                 return None
#         elif operation_type == "state_snapshot":
#             # Similar logic for "state_snapshot" operation
#             pass
#         # Additional elif blocks for other operation types like "report"
#         else:
#             logging.error(
#                 f"{get_emoji('error')} {self.hostname}: Invalid operation type: {operation_type}"
#             )
#             return results

# class UpgradeAssurance:
#     def __init__(self):
#         pass

#     def check_readiness_and_log(self, result: dict, hostname: str, test_name: str, test_info: dict) -> None:
#         # Function implementation here

#     def generate_diff_report_pdf(self, pre_post_diff: dict, file_path: str, hostname: str, target_version: str) -> None:
#         # Function implementation here
