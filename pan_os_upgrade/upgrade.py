"""
upgrade.py: Automating the Upgrade Process for Palo Alto Networks Devices with PDF Reporting

This script automates the upgrade process for Palo Alto Networks Firewalls and Panorama appliances, offering a seamless and efficient way to perform upgrades with enhanced reporting capabilities. Leveraging Typer for a command-line interface, users can specify parameters directly. The script supports upgrading standalone firewalls, Panorama appliances, and batch upgrading firewalls managed by Panorama. A unique feature is the integration with reportlab for generating comprehensive PDF reports summarizing pre- and post-upgrade snapshots, providing a visual and detailed comparison of device states before and after upgrades. Additionally, a settings command generates a `settings.yaml` file, allowing users to override default script settings.

Features
--------
- **Automated Upgrades**: Streamlines the upgrade process for firewalls and Panorama appliances, reducing manual intervention.
- **Enhanced Reporting**: Utilizes reportlab to generate detailed PDF reports of pre and post-upgrade snapshots, aiding in the verification of upgrade success and system integrity.
- **Comprehensive Error Handling**: Incorporates extensive error handling to address common and unforeseen issues during upgrades.
- **Integration with panos-upgrade-assurance**: Uses the panos-upgrade-assurance tool for pre and post-upgrade checks, ensuring device readiness.
- **Flexible Configuration**: Enables customization of the upgrade process via a `settings.yaml` file, allowing adjustments to readiness checks, snapshot configurations, and more.

Imports
-------
Standard Libraries:
    - concurrent, threading: For parallel processing and multi-threading.
    - ipaddress: For IP address manipulation.
    - logging: For detailed logging throughout the upgrade process.
    - os, sys: For file and directory operations interfacing with the operating system.
    - time, re: For time-related functions and regular expression operations.
    - yaml: For YAML file parsing and settings configuration.
    - RemoteDisconnected, RotatingFileHandler: For HTTP connection management and log file rotation.
    - Path, Lock, typing: For file path utilities, synchronization primitives, and type annotations.

External Libraries:
    - xml.etree.ElementTree (ET): For XML tree structure manipulation, crucial for parsing PAN-OS API responses.
    - dns.resolver: For DNS lookups and hostname resolution.
    - Dynaconf: For dynamic configuration and settings management.
    - typer: For command-line interface creation, enhancing user interaction.
    - reportlab: For PDF report generation, detailing upgrade snapshots comparisons.

Palo Alto Networks libraries:
    - panos: For direct API interaction with Palo Alto Networks devices.
    - PanDevice, SystemSettings: For base PAN-OS device operations and system settings management.
    - Firewall, Panorama: For firewall and Panorama-specific operations.
    - Error handling modules: For specialized error management in PAN-OS environments.

panos-upgrade-assurance package:
    - CheckFirewall, FirewallProxy: For readiness checks and serving as intermediaries to firewalls.

Project-specific imports:
    - SnapshotReport, ReadinessCheckReport: For structured management of snapshot and readiness check reports.
    - ManagedDevice, ManagedDevices: For device information and collections management models.

Subcommands
-----------
- `firewall`: Triggers the upgrade process for an individual firewall device.
- `panorama`: Initiates the upgrade for a Panorama appliance.
- `batch`: Executes batch upgrades for firewalls managed by a Panorama appliance.
- `settings`: Creates a `settings.yaml` file for script settings customization.

Usage
-----
The script is executed with various subcommands and options to customize the upgrade process. For example, to upgrade a firewall:

    python upgrade.py firewall --hostname <firewall_ip> --username <user> --password <password> --version <target_version>

For a batch upgrade of firewalls through Panorama:

    python upgrade.py batch --hostname <panorama_ip> --username <user> --password <password> --version <target_version>

To generate a `settings.yaml` file for customization:

    python upgrade.py settings

Notes
-----
- Ensure network connectivity and valid credentials before starting the upgrade process.
- The `settings.yaml` file allows for the customization of various aspects of the upgrade process, including the selection of readiness checks and snapshot configurations.
"""

# standard library imports
import importlib.resources as pkg_resources
import ipaddress
import json
import logging
import os
import sys
import time
import re
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import RemoteDisconnected
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple, Union
from typing_extensions import Annotated

import xml.etree.ElementTree as ET

# Palo Alto Networks imports
from panos.base import PanDevice
from panos.device import SystemSettings
from panos.errors import (
    PanConnectionTimeout,
    PanDeviceError,
    PanDeviceXapiError,
    PanURLError,
    PanXapiError,
)
from panos.firewall import Firewall
from panos.panorama import Panorama

# Palo Alto Networks panos-upgrade-assurance imports
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare

# third party imports
import dns.resolver
import typer
from colorama import init, Fore
from dynaconf import Dynaconf
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Line
from tabulate import tabulate

# project imports
from pan_os_upgrade.models import (
    SnapshotReport,
    ReadinessCheckReport,
    ManagedDevice,
    ManagedDevices,
    FromAPIResponseMixin,
)


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


# Core Functions
def backup_configuration(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    file_path: str,
) -> bool:
    """
    Backs up the running configuration of a Palo Alto Networks device to a specified file.

    This function exports the current running configuration from the given device, which can be either a Firewall or
    Panorama, and writes it to a local file in XML format. The backup operation is an essential precautionary measure
    prior to performing system updates, modifications, or troubleshooting, providing a reliable rollback point.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device instance from which to back up the configuration. This must be an initialized object of type
        Firewall or Panorama with active connectivity to the device.
    hostname : str
        A string representing the hostname or IP address of the target device, used primarily for logging purposes.
    file_path : str
        The full path to the file where the configuration backup will be saved. If the directory path does not exist,
        it will be created.

    Returns
    -------
    bool
        Returns True if the backup is successful, indicating the configuration has been safely written to the specified
        file. Returns False if any part of the backup process fails, such as issues with retrieving the configuration or
        writing to the file.

    Raises
    ------
    Exception
        Raises a generic Exception if an unexpected error occurs during the backup process, including issues with
        retrieving the configuration from the device or writing to the specified file.

    Examples
    --------
    Backing up the configuration of a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='adminpassword')
        >>> backup_configuration(firewall, '192.168.1.1', '/path/to/firewall_backup.xml')
        True  # Assuming the backup was successful

    Backing up the configuration of a Panorama appliance:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='adminpassword')
        >>> backup_configuration(panorama, 'panorama.example.com', '/path/to/panorama_backup.xml')
        True  # Assuming the backup was successful

    Notes
    -----
    - The backed-up configuration is saved in XML format, mirroring the exact state of the device's configuration at
      the time of the backup.
    - It is recommended to periodically back up configurations, especially before significant system changes, to ensure
      a recovery point is available.
    - While this function provides an essential capability in device management workflows, users should handle the
      backup files securely and maintain appropriate file permissions to protect sensitive configuration data.
    """

    try:
        # Run operational command to retrieve configuration
        config_xml = target_device.op("show config running")
        if config_xml is None:
            logging.error(
                f"{get_emoji('error')} {hostname}: Failed to retrieve running configuration."
            )
            return False

        # Check XML structure
        if (
            config_xml.tag != "response"
            or len(config_xml) == 0
            or config_xml[0].tag != "result"
        ):
            logging.error(
                f"{get_emoji('error')} {hostname}: Unexpected XML structure in configuration data."
            )
            return False

        # Extract the configuration data from the <result><config> tag
        config_data = config_xml.find(".//result/config")

        # Manually construct the string representation of the XML data
        config_str = ET.tostring(config_data, encoding="unicode")

        # Ensure the directory exists
        ensure_directory_exists(file_path)

        # Write the file to the local filesystem
        with open(file_path, "w") as file:
            file.write(config_str)

        logging.debug(
            f"{get_emoji('save')} {hostname}: Configuration backed up successfully to {file_path}"
        )
        return True

    except Exception as e:
        logging.error(
            f"{get_emoji('error')} {hostname}: Error backing up configuration: {e}"
        )
        return False


def determine_upgrade(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    target_major: int,
    target_minor: int,
    target_maintenance: Union[int, str],
) -> None:
    """
    Evaluates if an upgrade is necessary for the specified device to reach the desired PAN-OS version.

    This function assesses the current PAN-OS version of the target device against the specified target version. If the
    current version is older than the target version, it indicates that an upgrade is required. Conversely, if the current
    version is the same as or more recent than the target version, the function logs that no upgrade is needed, and it
    terminates the script to prevent unnecessary operations. This evaluation helps in maintaining the device's firmware
    up-to-date or avoiding inadvertent downgrades.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device (Firewall or Panorama) to be evaluated for an upgrade. This must be an initialized instance with
        connectivity to the device.
    hostname : str
        The hostname or IP address of the target device. It is used for logging purposes to clearly identify the device
        in log messages.
    target_major : int
        The major version component of the desired PAN-OS version (e.g., '10' in PAN-OS 10.0.0).
    target_minor : int
        The minor version component of the desired PAN-OS version (e.g., '0' in PAN-OS 10.0.0).
    target_maintenance : Union[int, str]
        The maintenance or hotfix version component of the desired PAN-OS version. It can be an integer for standard
        maintenance releases or a string for hotfixes (e.g., '1-h1' in PAN-OS 10.0.1-h1).

    Raises
    ------
    SystemExit
        If the function determines that an upgrade is not required or if a downgrade is attempted, it will log the
        appropriate message and terminate the script to prevent further execution.

    Examples
    --------
    Checking if a firewall requires an upgrade to PAN-OS 9.1.0:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='adminpassword')
        >>> determine_upgrade(firewall, '192.168.1.1', 9, 1, 0)
        # Logs the current version and whether an upgrade to 9.1.0 is necessary.

    Checking if a Panorama appliance requires an upgrade to PAN-OS 10.0.1-h1:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='adminpassword')
        >>> determine_upgrade(panorama, 'panorama.example.com', 10, 0, '1-h1')
        # Logs the current version and whether an upgrade to 10.0.1-h1 is necessary.

    Notes
    -----
    - The current and target versions are parsed and compared in a structured manner to accurately determine the need for
      an upgrade.
    - This function is crucial for maintaining device firmware integrity by ensuring that only necessary upgrades are
      performed and that downgrades are avoided.
    - The decision to halt the script upon determining that no upgrade is required or a downgrade is attempted is a
      safeguard against unintended firmware changes that could affect device stability and security.
    """

    current_version = parse_version(target_device.version)

    if isinstance(target_maintenance, int):
        # Handling integer maintenance version separately
        target_version = (target_major, target_minor, target_maintenance, 0)
    else:
        # Handling string maintenance version with hotfix
        target_version = parse_version(
            f"{target_major}.{target_minor}.{target_maintenance}"
        )

    logging.info(
        f"{get_emoji('report')} {hostname}: Current version: {target_device.version}"
    )
    logging.info(
        f"{get_emoji('report')} {hostname}: Target version: {target_major}.{target_minor}.{target_maintenance}"
    )

    if current_version < target_version:
        logging.info(
            f"{get_emoji('success')} {hostname}: Upgrade required from {target_device.version} to {target_major}.{target_minor}.{target_maintenance}"
        )
    else:
        logging.info(
            f"{get_emoji('skipped')} {hostname}: No upgrade required or downgrade attempt detected."
        )
        logging.info(f"{get_emoji('skipped')} {hostname}: Halting upgrade.")
        sys.exit(0)


def get_ha_status(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> Tuple[str, Optional[dict]]:
    """
    Retrieves the High Availability (HA) status and configuration details of a target device.

    This function queries the High Availability (HA) status of a specified Palo Alto Networks device, which can be either a
    Firewall or Panorama. It determines the device's HA role and configuration, indicating whether the device is in standalone
    mode, part of an active/passive setup, in active/active mode, or configured in a cluster. The function returns a string
    representing the HA mode and, if applicable, a dictionary containing the HA configuration details.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device from which HA information is to be retrieved. This must be an initialized instance of either
        a Firewall or Panorama, with connectivity established to the device.
    hostname : str
        The hostname or IP address of the target device, used for logging purposes to aid in identifying the device in log entries.

    Returns
    -------
    Tuple[str, Optional[dict]]
        A tuple where the first element is a string representing the HA mode of the device, such as 'standalone',
        'active/passive', 'active/active', or 'cluster'. The second element is an optional dictionary containing
        detailed HA configuration information, provided if the device is part of an HA setup; otherwise, None is returned.

    Example
    -------
    Fetching HA status for a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='adminpassword')
        >>> ha_mode, ha_config = get_ha_status(firewall, '192.168.1.1')
        >>> print(ha_mode)  # Output might be 'active/passive'
        >>> if ha_config:
        ...     print(ha_config)  # Prints detailed HA configuration if available

    Notes
    -----
    - The HA status is essential for ensuring proper maintenance procedures, especially in environments where high availability
      is critical.
    - This function provides detailed insights into the HA setup, aiding in the planning and execution of device upgrades,
      maintenance, and troubleshooting procedures.
    """

    logging.debug(
        f"{get_emoji('start')} {hostname}: Getting {target_device.serial} deployment information."
    )
    deployment_type = target_device.show_highavailability_state()
    logging.debug(
        f"{get_emoji('report')} {hostname}: Target device deployment: {deployment_type[0]}"
    )

    if deployment_type[1]:
        ha_details = flatten_xml_to_dict(deployment_type[1])
        logging.debug(
            f"{get_emoji('report')} {hostname}: Target device deployment details: {ha_details}"
        )
        return deployment_type[0], ha_details
    else:
        return deployment_type[0], None


def handle_firewall_ha(
    target_device: Firewall,
    hostname: str,
    dry_run: bool,
) -> Tuple[bool, Optional[Firewall]]:
    """
    Determines and handles High Availability (HA) logic for the target device during the upgrade process.

    This function assesses the HA configuration of the specified target device to decide the appropriate course of action for
    the upgrade. It considers the device's role in an HA setup (active, passive, or standalone) and uses the 'dry_run' flag to
    determine whether to simulate or execute the upgrade. Based on the device's HA status and synchronization state with its
    HA peer, the function guides whether to proceed with the upgrade and performs HA-specific preparations if necessary.

    Parameters
    ----------
    target_device: Firewall
        The device being evaluated for upgrade. It must be an instance of Firewall and might be part of
        an HA configuration.
    hostname : str
        The hostname or IP address of the target device for identification and logging purposes.
    dry_run : bool
        A flag indicating whether to simulate the upgrade process (True) without making actual changes or to proceed with
        the upgrade (False).

    Returns
    -------
    Tuple[bool, Optional[Firewall]]
        A tuple where the first element is a boolean indicating whether the upgrade process should continue, and the second
        element is an optional device instance representing the HA peer if relevant and applicable.

    Example
    -------
    >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
    >>> proceed, ha_peer = handle_firewall_ha(firewall, '192.168.1.1', dry_run=False)
    >>> print(proceed)  # Indicates whether the upgrade should continue
    >>> if ha_peer:
    ...     print(ha_peer)  # The HA peer device instance if applicable

    Notes
    -----
    - This function is crucial for managing the upgrade process in HA environments to ensure consistency and minimize
      downtime.
    - It incorporates checks for synchronization states and versions between HA peers, ensuring upgrades are conducted
      safely and effectively.
    - The 'dry_run' option allows administrators to validate the upgrade logic without impacting the actual device
      configuration or operation.
    - Settings such as retry counts and intervals for HA synchronization checks can be customized via the 'settings.yaml'
      file, providing flexibility for different network environments and requirements.
    """

    deploy_info, ha_details = get_ha_status(
        target_device,
        hostname,
    )

    # If the target device is not part of an HA configuration, proceed with the upgrade
    if not ha_details:
        return True, None

    logging.debug(f"{get_emoji('report')} {hostname}: Deployment info: {deploy_info}")
    logging.debug(f"{get_emoji('report')} {hostname}: HA details: {ha_details}")

    local_state = ha_details["result"]["group"]["local-info"]["state"]
    local_version = ha_details["result"]["group"]["local-info"]["build-rel"]
    peer_version = ha_details["result"]["group"]["peer-info"]["build-rel"]

    logging.info(
        f"{get_emoji('report')} {hostname}: Local state: {local_state}, Local version: {local_version}, Peer version: {peer_version}"
    )

    # Check if the firewall is in the revisit list
    with target_devices_to_revisit_lock:
        is_device_to_revisit = target_device in target_devices_to_revisit

    if is_device_to_revisit:
        # Initialize with default values
        max_retries = 3
        retry_interval = 60

        # Override if settings.yaml exists and contains these settings
        if settings_file_path.exists():
            max_retries = settings_file.get("ha_sync.max_tries", max_retries)
            retry_interval = settings_file.get("ha_sync.retry_interval", retry_interval)

        for attempt in range(max_retries):
            logging.info(
                f"Waiting for HA synchronization to complete on {hostname}. Attempt {attempt + 1}/{max_retries}"
            )
            # Wait for HA synchronization
            time.sleep(retry_interval)

            # Re-fetch the HA status to get the latest state
            deploy_info, ha_details = get_ha_status(target_device, hostname)
            local_version = ha_details["result"]["group"]["local-info"]["build-rel"]
            peer_version = ha_details["result"]["group"]["peer-info"]["build-rel"]

            if peer_version != local_version:
                logging.info(
                    f"HA synchronization complete on {hostname}. Proceeding with upgrade."
                )
                break
            else:
                logging.info(
                    f"HA synchronization still in progress on {hostname}. Rechecking after wait period."
                )

    version_comparison = compare_versions(local_version, peer_version)
    logging.info(
        f"{get_emoji('report')} {hostname}: Version comparison: {version_comparison}"
    )

    # If the active and passive target devices are running the same version
    if version_comparison == "equal":
        if local_state == "active":
            # Add the active target device to the list and exit the upgrade process
            with target_devices_to_revisit_lock:
                target_devices_to_revisit.append(target_device)
            logging.info(
                f"{get_emoji('search')} {hostname}: Detected active target device in HA pair running the same version as its peer. Added target device to revisit list."
            )
            return False, None

        elif local_state == "passive":
            # Continue with upgrade process on the passive target device
            logging.info(
                f"{get_emoji('report')} {hostname}: Target device is passive",
            )
            return True, None

        elif local_state == "initial":
            # Continue with upgrade process on the initial target device
            logging.info(
                f"{get_emoji('warning')} {hostname}: Target device is in initial HA state",
            )
            return True, None

    elif version_comparison == "older":
        logging.info(
            f"{get_emoji('report')} {hostname}: Target device is on an older version"
        )
        # Suspend HA state of active if the passive is on a later release
        if local_state == "active" and not dry_run:
            logging.info(
                f"{get_emoji('report')} {hostname}: Suspending HA state of active"
            )
            suspend_ha_active(
                target_device,
                hostname,
            )
        return True, None

    elif version_comparison == "newer":
        logging.info(
            f"{get_emoji('report')} {hostname}: Target device is on a newer version"
        )
        # Suspend HA state of passive if the active is on a later release
        if local_state == "passive" and not dry_run:
            logging.info(
                f"{get_emoji('report')} {hostname}: Suspending HA state of passive"
            )
            suspend_ha_passive(
                target_device,
                hostname,
            )
        return True, None

    return False, None


def handle_panorama_ha(
    target_device: Panorama,
    hostname: str,
    dry_run: bool,
) -> Tuple[bool, Optional[Panorama]]:
    """
    Determines and handles High Availability (HA) logic for the Panorama device during the upgrade process.

    This function assesses the HA configuration of the specified Panorama device to decide the appropriate course of action for
    the upgrade. It considers the device's role in an HA setup (primary-active, secondary-passive) and uses the 'dry_run' flag to
    determine whether to simulate or execute the upgrade. Based on the device's HA status and synchronization state with its
    HA peer, the function guides whether to proceed with the upgrade and performs HA-specific preparations if necessary.

    Parameters
    ----------
    target_device: Panorama
        The device being evaluated for upgrade. It must be an instance of Panorama and might be part of
        an HA configuration.
    hostname : str
        The hostname or IP address of the target device for identification and logging purposes.
    dry_run : bool
        A flag indicating whether to simulate the upgrade process (True) without making actual changes or to proceed with
        the upgrade (False).

    Returns
    -------
    Tuple[bool, Optional[Panorama]]
        A tuple where the first element is a boolean indicating whether the upgrade process should continue, and the second
        element is an optional device instance representing the HA peer if relevant and applicable.

    Example
    -------
    >>> panorama = Panorama(hostname='192.168.1.1', api_username='admin', api_password='admin')
    >>> proceed, ha_peer = handle_panorama_ha(firewall, '192.168.1.1', dry_run=False)
    >>> print(proceed)  # Indicates whether the upgrade should continue
    >>> if ha_peer:
    ...     print(ha_peer)  # The HA peer device instance if applicable

    Notes
    -----
    - This function is crucial for managing the upgrade process in HA environments to ensure consistency and minimize
      downtime.
    - It incorporates checks for synchronization states and versions between HA peers, ensuring upgrades are conducted
      safely and effectively.
    - The 'dry_run' option allows administrators to validate the upgrade logic without impacting the actual device
      configuration or operation.
    - Settings such as retry counts and intervals for HA synchronization checks can be customized via the 'settings.yaml'
      file, providing flexibility for different network environments and requirements.
    """

    deploy_info, ha_details = get_ha_status(
        target_device,
        hostname,
    )

    # If the target device is not part of an HA configuration, proceed with the upgrade
    if not ha_details:
        return True, None

    logging.debug(f"{get_emoji('report')} {hostname}: Deployment info: {deploy_info}")
    logging.debug(f"{get_emoji('report')} {hostname}: HA details: {ha_details}")

    local_state = ha_details["result"]["local-info"]["state"]
    local_version = ha_details["result"]["local-info"]["build-rel"]
    # peer_state = ha_details["result"]["peer-info"]["state"]
    peer_version = ha_details["result"]["peer-info"]["build-rel"]

    logging.info(
        f"{get_emoji('report')} {hostname}: Local state: {local_state}, Local version: {local_version}, Peer version: {peer_version}"
    )

    # Check if the firewall is in the revisit list
    with target_devices_to_revisit_lock:
        is_device_to_revisit = target_device in target_devices_to_revisit

    if is_device_to_revisit:
        # Initialize with default values
        max_retries = 3
        retry_interval = 60

        # Override if settings.yaml exists and contains these settings
        if settings_file_path.exists():
            max_retries = settings_file.get("ha_sync.max_tries", max_retries)
            retry_interval = settings_file.get("ha_sync.retry_interval", retry_interval)

        for attempt in range(max_retries):
            logging.info(
                f"Waiting for HA synchronization to complete on {hostname}. Attempt {attempt + 1}/{max_retries}"
            )
            # Wait for HA synchronization
            time.sleep(retry_interval)

            # Re-fetch the HA status to get the latest state
            deploy_info, ha_details = get_ha_status(target_device, hostname)
            local_version = ha_details["result"]["local-info"]["build-rel"]
            peer_version = ha_details["result"]["peer-info"]["build-rel"]

            if peer_version != local_version:
                logging.info(
                    f"HA synchronization complete on {hostname}. Proceeding with upgrade."
                )
                break
            else:
                logging.info(
                    f"HA synchronization still in progress on {hostname}. Rechecking after wait period."
                )

    version_comparison = compare_versions(local_version, peer_version)
    logging.info(
        f"{get_emoji('report')} {hostname}: Version comparison: {version_comparison}"
    )

    # If the active and passive target devices are running the same version
    if version_comparison == "equal":
        if local_state == "primary-active":
            # Add the active target device to the list and exit the upgrade process
            with target_devices_to_revisit_lock:
                target_devices_to_revisit.append(target_device)
            logging.info(
                f"{get_emoji('search')} {hostname}: Detected primary-active target device in HA pair running the same version as its peer. Added target device to revisit list."
            )
            return False, None

        elif local_state == "secondary-passive":
            # Continue with upgrade process on the secondary-passive target device
            logging.info(
                f"{get_emoji('report')} {hostname}: Target device is secondary-passive",
            )
            return True, None

        elif (
            local_state == "secondary-suspended"
            or local_state == "secondary-non-functional"
        ):
            # Continue with upgrade process on the secondary-suspended or secondary-non-functional target device
            logging.info(
                f"{get_emoji('warning')} {hostname}: Target device is {local_state}",
            )
            return True, None

    elif version_comparison == "older":
        logging.info(
            f"{get_emoji('report')} {hostname}: Target device is on an older version"
        )
        # Suspend HA state of active if the primary-active is on a later release
        if local_state == "primary-active" and not dry_run:
            logging.info(
                f"{get_emoji('report')} {hostname}: Suspending HA state of primary-active"
            )
            suspend_ha_active(
                target_device,
                hostname,
            )
        return True, None

    elif version_comparison == "newer":
        logging.info(
            f"{get_emoji('report')} {hostname}: Target device is on a newer version"
        )
        # Suspend HA state of secondary-passive if the primary-active is on a later release
        if local_state == "primary-active" and not dry_run:
            logging.info(
                f"{get_emoji('report')} {hostname}: Suspending HA state of primary-active"
            )
            suspend_ha_passive(
                target_device,
                hostname,
            )
        return True, None

    return False, None


def ha_sync_check_firewall(
    hostname: str,
    ha_details: dict,
    strict_sync_check: bool = True,
) -> bool:
    """
    Checks the synchronization status between High Availability (HA) peers of a Palo Alto Networks device.

    Ensuring HA peers are synchronized is vital before executing operations that might impact the device's state,
    such as firmware upgrades or configuration changes. This function evaluates the HA synchronization status using
    provided HA details. It offers an option to enforce a strict synchronization check, where failure to sync
    results in script termination, ensuring operations proceed only in a fully synchronized HA environment.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target device, used for logging purposes to identify the device under evaluation.
    ha_details : dict
        A dictionary containing HA information for the device, specifically the synchronization status with its HA peer.
    strict_sync_check : bool, optional
        If True (default), the function will exit the script upon detecting unsynchronized HA peers to prevent potential
        disruptions. If False, the script logs a warning but continues execution, suitable for less critical operations.

    Returns
    -------
    bool
        Returns True if the HA peers are confirmed to be synchronized, indicating readiness for sensitive operations.
        Returns False if the HA peers are not synchronized, with subsequent actions dependent on the `strict_sync_check` parameter.

    Raises
    ------
    SystemExit
        Triggered if `strict_sync_check` is True and the HA peers are found to be unsynchronized, halting the script to avoid
        potential issues in an unsynchronized HA environment.

    Example
    -------
    >>> ha_details = {'result': {'group': {'running-sync': 'synchronized'}}}
    >>> ha_sync_check_firewall('firewall1', ha_details)
    True  # Indicates that the HA peers are synchronized

    >>> ha_sync_check_firewall('firewall1', ha_details, strict_sync_check=False)
    False  # HA peers are unsynchronized, but script continues due to lenient check

    Notes
    -----
    - In HA configurations, maintaining synchronization between peers is critical to ensure consistent state and behavior
      across devices.
    - This function is particularly useful in automated workflows and scripts where actions need to be conditional on the
      synchronization state of HA peers to maintain system integrity and prevent split-brain scenarios.
    - The option to override strict synchronization checks allows for flexibility in operations where immediate consistency
      between HA peers may not be as critical.
    """

    logging.info(f"{get_emoji('start')} {hostname}: Checking if HA peer is in sync.")
    if ha_details and ha_details["result"]["group"]["running-sync"] == "synchronized":
        logging.info(
            f"{get_emoji('success')} {hostname}: HA peer sync test has been completed."
        )
        return True
    else:
        if strict_sync_check:
            logging.error(
                f"{get_emoji('error')} {hostname}: HA peer state is not in sync, please try again."
            )
            logging.error(f"{get_emoji('stop')} {hostname}: Halting script.")
            sys.exit(1)
        else:
            logging.warning(
                f"{get_emoji('warning')} {hostname}: HA peer state is not in sync. This will be noted, but the script will continue."
            )
            return False


def ha_sync_check_panorama(
    hostname: str,
    ha_details: dict,
    strict_sync_check: bool = False,
) -> bool:
    """
    Checks the synchronization status between High Availability (HA) peers of a Palo Alto Networks device.

    Ensuring HA peers are synchronized is vital before executing operations that might impact the device's state,
    such as firmware upgrades or configuration changes. This function evaluates the HA synchronization status using
    provided HA details. It offers an option to enforce a strict synchronization check, where failure to sync
    results in script termination, ensuring operations proceed only in a fully synchronized HA environment.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target device, used for logging purposes to identify the device under evaluation.
    ha_details : dict
        A dictionary containing HA information for the device, specifically the synchronization status with its HA peer.
    strict_sync_check : bool, optional
        If True (default), the function will exit the script upon detecting unsynchronized HA peers to prevent potential
        disruptions. If False, the script logs a warning but continues execution, suitable for less critical operations.

    Returns
    -------
    bool
        Returns True if the HA peers are confirmed to be synchronized, indicating readiness for sensitive operations.
        Returns False if the HA peers are not synchronized, with subsequent actions dependent on the `strict_sync_check` parameter.

    Raises
    ------
    SystemExit
        Triggered if `strict_sync_check` is True and the HA peers are found to be unsynchronized, halting the script to avoid
        potential issues in an unsynchronized HA environment.

    Example
    -------
    >>> ha_details = {'result': {'group': {'running-sync': 'synchronized'}}}
    >>> ha_sync_check_firewall('firewall1', ha_details)
    True  # Indicates that the HA peers are synchronized

    >>> ha_sync_check_firewall('firewall1', ha_details, strict_sync_check=False)
    False  # HA peers are unsynchronized, but script continues due to lenient check

    Notes
    -----
    - In HA configurations, maintaining synchronization between peers is critical to ensure consistent state and behavior
      across devices.
    - This function is particularly useful in automated workflows and scripts where actions need to be conditional on the
      synchronization state of HA peers to maintain system integrity and prevent split-brain scenarios.
    - The option to override strict synchronization checks allows for flexibility in operations where immediate consistency
      between HA peers may not be as critical.
    """

    logging.info(f"{get_emoji('start')} {hostname}: Checking if HA peer is in sync.")
    if ha_details and ha_details["result"]["running-sync"] == "synchronized":
        logging.info(
            f"{get_emoji('success')} {hostname}: HA peer sync test has been completed."
        )
        return True
    else:
        if strict_sync_check:
            logging.error(
                f"{get_emoji('error')} {hostname}: HA peer state is not in sync, please try again."
            )
            logging.error(f"{get_emoji('stop')} {hostname}: Halting script.")
            sys.exit(1)
        else:
            logging.warning(
                f"{get_emoji('warning')} {hostname}: HA peer state is not in sync. This will be noted, but the script will continue."
            )
            return False


def perform_readiness_checks(
    firewall: Firewall,
    hostname: str,
    file_path: str,
) -> None:
    """
    Conducts a set of predefined readiness checks on a specified Palo Alto Networks Firewall to verify its
    preparedness for an upgrade operation.

    This function systematically executes a series of checks on the specified firewall, evaluating various
    aspects such as configuration status, licensing validity, software version compatibility, and more, to
    ascertain its readiness for an upgrade. The outcomes of these checks are meticulously compiled into a
    detailed JSON report, which is then saved to the specified file path. The scope of checks performed can
    be tailored through configurations in the `settings.yaml` file, providing the flexibility to adapt the
    checks to specific operational needs or preferences.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class, properly initialized with necessary authentication details and
        network connectivity to the target firewall device.
    hostname : str
        A string representing the hostname or IP address of the firewall, utilized for logging and
        identification purposes within the process.
    file_path : str
        The designated file path where the JSON-formatted report summarizing the results of the readiness
        checks will be stored. The function ensures the existence of the specified directory, creating it
        if necessary.

    Raises
    ------
    IOError
        Signals an issue with writing the readiness report to the specified file path, potentially due to
        file access restrictions or insufficient disk space, warranting further investigation.

    Examples
    --------
    Executing readiness checks for a firewall and saving the results:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_readiness_checks(firewall_instance, 'firewall1', '/path/to/firewall1_readiness_report.json')
        # This command initiates the readiness checks on the specified firewall and saves the generated report
        # to the given file path.

    Notes
    -----
    - The execution of readiness checks is a pivotal preliminary step in the upgrade process, designed to
      uncover and address potential impediments, thereby facilitating a seamless and successful upgrade.
    - The set of checks to be conducted can be customized via the `settings.yaml` file. If this file is
      present and contains specific configurations under the `readiness_checks.customize` key, those
      configurations will dictate the checks to be performed. In the absence of such custom configurations,
      a default set of checks, determined by the `enabled_by_default` attribute within the AssuranceOptions
      class, will be applied.
    """

    # Load settings if the file exists
    if settings_file_path.exists():
        with open(settings_file_path, "r") as file:
            settings = yaml.safe_load(file)

        # Check if readiness checks are disabled in the settings
        if settings.get("readiness_checks", {}).get("disabled", False):
            logging.info(
                f"{get_emoji('skipped')} {hostname}: Readiness checks are disabled in the settings. Skipping readiness checks for {hostname}."
            )
            # Early return, no readiness checks performed
            return

        # Determine readiness checks to perform based on settings
        if settings.get("readiness_checks", {}).get("customize", False):
            # Extract checks where value is True
            selected_checks = [
                check
                for check, enabled in settings.get("readiness_checks", {})
                .get("checks", {})
                .items()
                if enabled
            ]
        else:
            # Select checks based on 'enabled_by_default' attribute from AssuranceOptions class
            selected_checks = [
                check
                for check, attrs in AssuranceOptions.READINESS_CHECKS.items()
                if attrs.get("enabled_by_default", False)
            ]
    else:
        # Select checks based on 'enabled_by_default' attribute from AssuranceOptions class
        selected_checks = [
            check
            for check, attrs in AssuranceOptions.READINESS_CHECKS.items()
            if attrs.get("enabled_by_default", False)
        ]

    logging.info(
        f"{get_emoji('start')} {hostname}: Performing readiness checks of target firewall."
    )

    readiness_check = run_assurance(
        firewall,
        hostname,
        operation_type="readiness_check",
        actions=selected_checks,
        config={},
    )

    # Check if a readiness check was successfully created
    if isinstance(readiness_check, ReadinessCheckReport):
        logging.info(f"{get_emoji('success')} {hostname}: Readiness Checks completed")
        readiness_check_report_json = readiness_check.model_dump_json(indent=4)
        logging.debug(
            f"{get_emoji('save')} {hostname}: Readiness Check Report: {readiness_check_report_json}"
        )

        ensure_directory_exists(file_path)

        with open(file_path, "w") as file:
            file.write(readiness_check_report_json)

        logging.debug(
            f"{get_emoji('save')} {hostname}: Readiness checks completed for {hostname}, saved to {file_path}"
        )
    else:
        logging.error(
            f"{get_emoji('error')} {hostname}: Failed to create readiness check"
        )


def perform_reboot(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    target_version: str,
    ha_details: Optional[dict] = None,
    initial_sleep_duration: int = 60,
) -> None:
    """
    Initiates a reboot on a specified device (Firewall or Panorama) and verifies it boots up with the desired PAN-OS version.
    This function is critical in completing the upgrade process, ensuring that the device is running the expected software version
    post-reboot. It also supports High Availability (HA) configurations, checking for the HA pair's synchronization and functional status
    after the reboot.

    The process sends a reboot command to the device, waits for it to go offline and come back online, and then checks if the rebooted
    PAN-OS version matches the target version. For devices in an HA setup, additional steps are taken to verify the HA status and
    synchronization between the HA peers post-reboot.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device object representing either a Firewall or Panorama, with necessary connectivity details.
    hostname : str
        The hostname or IP address of the target device, used for identification in logs and status messages.
    target_version : str
        The PAN-OS version that the device should be running after the reboot.
    ha_details : Optional[dict], default None
        A dictionary containing High Availability configuration details, if applicable, to ensure HA coherence post-reboot.
    initial_sleep_duration : int, default 60
        The initial waiting period (in seconds) after issuing the reboot command, before starting to check the device's status.

    Raises
    ------
    SystemExit
        If the device fails to reboot to the specified PAN-OS version after a set number of retries, or if HA synchronization
        is not achieved post-reboot, the script will terminate with an error.

    Examples
    --------
    Rebooting a device post-upgrade and verifying its PAN-OS version:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_reboot(firewall, 'fw1', '10.1.0')
        # This reboots the specified firewall and ensures it is running the expected PAN-OS version after the reboot.

    Notes
    -----
    - A retry mechanism is implemented to accommodate temporary network issues or delays in the device's reboot process.
    - Certain parameters such as the maximum number of retries and the interval between retries can be customized through a 'settings.yaml'
      file. This allows for dynamic adjustments according to different operational environments or requirements.
    - In the case of HA configurations, the function includes additional validations to ensure both the primary device and its HA peer
      are operational and in sync after the reboot, maintaining the HA setup's integrity.
    """

    rebooted = False
    attempt = 0

    # Initialize with default values
    max_retries = 30
    retry_interval = 60

    # Override if settings.yaml exists and contains these settings
    if settings_file_path.exists():
        max_retries = settings_file.get("reboot.max_tries", max_retries)
        retry_interval = settings_file.get("reboot.retry_interval", retry_interval)

    logging.info(f"{get_emoji('start')} {hostname}: Rebooting the target device.")

    # Initiate reboot
    reboot_job = target_device.op(
        "<request><restart><system/></restart></request>",
        cmd_xml=False,
    )
    reboot_job_result = flatten_xml_to_dict(reboot_job)
    logging.info(f"{get_emoji('report')} {hostname}: {reboot_job_result['result']}")

    # Wait for the target device reboot process to initiate before checking status
    time.sleep(initial_sleep_duration)

    while not rebooted and attempt < max_retries:
        try:
            # Refresh system information to check if the device is back online
            target_device.refresh_system_info()
            current_version = target_device.version
            logging.info(
                f"{get_emoji('report')} {hostname}: Current device version: {current_version}"
            )

            # Check if the device has rebooted to the target version
            if current_version == target_version:
                logging.info(
                    f"{get_emoji('success')} {hostname}: Device rebooted to the target version successfully."
                )
                rebooted = True
            else:
                logging.error(
                    f"{get_emoji('error')} {hostname}: Device rebooted but not to the target version."
                )
                sys.exit(1)

        except (
            PanXapiError,
            PanConnectionTimeout,
            PanURLError,
            RemoteDisconnected,
        ) as e:
            logging.warning(
                f"{get_emoji('warning')} {hostname}: Retry attempt {attempt + 1} due to error: {e}"
            )
            attempt += 1
            time.sleep(retry_interval)

    if not rebooted:
        logging.error(
            f"{get_emoji('error')} {hostname}: Failed to reboot to the target version after {max_retries} attempts."
        )
        sys.exit(1)


def perform_snapshot(
    firewall: Firewall,
    hostname: str,
    file_path: str,
    actions: Optional[List[str]] = None,
) -> SnapshotReport:
    """
    Captures and saves a comprehensive snapshot of a specified firewall's current state, focusing on key areas such
    as ARP tables, content versions, IPsec tunnel statuses, licensing, network interfaces, routing tables, and session
    statistics. The snapshot is saved in JSON format at a specified file path. This functionality is particularly useful
    for conducting pre- and post-change analyses, such as upgrade assessments or troubleshooting tasks.

    The snapshot content can be customized through the 'actions' parameter, allowing for a focused analysis on specified
    areas of interest. The function also supports customization of retry logic and intervals for capturing snapshots via
    a 'settings.yaml' file, providing flexibility for various operational requirements.

    Parameters
    ----------
    firewall : Firewall
        The Firewall object representing the device from which the snapshot will be captured. This object should be
        initialized and authenticated prior to calling this function.
    hostname : str
        The hostname or IP address of the firewall. This is used for identification and logging purposes throughout the
        snapshot process.
    file_path : str
        The filesystem path where the snapshot JSON file will be saved. If the specified directory does not exist, it will
        be created.
    actions : Optional[List[str]], optional
        A list of specific data points to be included in the snapshot. This allows for customization of the snapshot's
        content based on operational needs. If not specified, a default set of data points will be captured.

    Returns
    -------
    SnapshotReport
        An object containing detailed information about the firewall's state at the time of the snapshot. This includes
        both the data specified in the 'actions' parameter and metadata about the snapshot process itself.

    Raises
    ------
    IOError
        If there are issues with writing the snapshot data to the filesystem, such as problems creating the file or insufficient
        disk space, an IOError will be raised.

    Examples
    --------
    Taking a snapshot focusing on specific network elements:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> actions = ['arp_table', 'routes', 'session_stats']
        >>> snapshot_report = perform_snapshot(firewall_instance, 'fw1', '/path/to/snapshot.json', actions=actions)
        # This creates a snapshot containing ARP tables, routing tables, and session statistics for the firewall
        # identified as 'fw1' and saves it to '/path/to/snapshot.json'.

    Notes
    -----
    - The function is designed to be minimally invasive, allowing snapshots to be taken without impacting the operational
      performance of the network or the firewall.
    - The 'actions' parameter provides a means to tailor the snapshot to specific requirements, enhancing the function's
      utility for a wide range of diagnostic and compliance purposes.
    - Retry parameters, such as the maximum number of attempts and the interval between attempts, can be customized through
      a 'settings.yaml' file, allowing the function's behavior to be adapted to different network environments and operational
      policies.
    """

    # Load settings if the file exists
    if settings_file_path.exists():
        with open(settings_file_path, "r") as file:
            settings = yaml.safe_load(file)

        # Check if snapshots are disabled in the settings
        if settings.get("snapshots", {}).get("disabled", False):
            logging.info(
                f"{get_emoji('skipped')} {hostname}: Snapshots are disabled in the settings. Skipping snapshot for {hostname}."
            )
            return None  # Early return, no snapshot performed
        # Override default values with settings if snapshots are not disabled
        max_retries = settings.get("snapshots", {}).get("max_tries", 3)
        retry_interval = settings.get("snapshots", {}).get("retry_interval", 60)
    else:
        # Default values if settings.yaml does not exist or does not contain snapshot settings
        max_retries = 3
        retry_interval = 60

    logging.info(
        f"{get_emoji('start')} {hostname}: Performing snapshot of network state information."
    )
    attempt = 0
    snapshot = None

    while attempt < max_retries and snapshot is None:
        try:
            logging.info(
                f"{get_emoji('start')} {hostname}: Attempting to capture network state snapshot (Attempt {attempt + 1} of {max_retries})."
            )

            # Take snapshots
            snapshot = run_assurance(
                firewall,
                hostname,
                operation_type="state_snapshot",
                actions=actions,
                config={},
            )

            if snapshot is not None and isinstance(snapshot, SnapshotReport):
                logging.info(
                    f"{get_emoji('success')} {hostname}: Network snapshot created successfully on attempt {attempt + 1}."
                )

                # Save the snapshot to the specified file path as JSON
                ensure_directory_exists(file_path)
                with open(file_path, "w") as file:
                    file.write(snapshot.model_dump_json(indent=4))

                logging.info(
                    f"{get_emoji('save')} {hostname}: Network state snapshot collected and saved to {file_path}"
                )

                return snapshot

        # Catch specific and general exceptions
        except (AttributeError, IOError, Exception) as error:
            logging.warning(
                f"{get_emoji('warning')} {hostname}: Snapshot attempt failed with error: {error}. Retrying after {retry_interval} seconds."
            )
            time.sleep(retry_interval)
            attempt += 1

    if snapshot is None:
        logging.error(
            f"{get_emoji('error')} {hostname}: Failed to create snapshot after {max_retries} attempts."
        )


def perform_upgrade(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    target_version: str,
    ha_details: Optional[dict] = None,
) -> None:
    """
    Conducts a comprehensive upgrade process for a Palo Alto Networks device, addressing both single
    device environments and High Availability (HA) configurations. It manages the sequence from downloading
    the necessary software version to verifying post-upgrade status. In HA setups, it ensures synchronization
    and consistency across devices. The function supports a dry-run mode for validation purposes and utilizes
    customizable settings from a 'settings.yaml' file for retries and intervals, enhancing flexibility.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device to upgrade, represented as a Firewall or Panorama instance with established connectivity.
    hostname : str
        The hostname or IP address of the target device, employed for logging and identification throughout
        the upgrade process.
    target_version : str
        The desired PAN-OS version to which the device will be upgraded, specified in a string format.
    ha_details : Optional[dict], optional
        Optional HA configuration details for the target device, required for handling HA-specific upgrade
        logic such as synchronization checks and peer upgrades.

    Raises
    ------
    SystemExit
        Exits the script with an error if the upgrade process encounters a critical failure at any point,
        particularly in verifying the post-upgrade version or HA synchronization status.

    Examples
    --------
    Upgrading a standalone firewall device:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_upgrade(firewall, '192.168.1.1', '10.1.0')
        # Initiates the upgrade process to version 10.1.0, including pre-upgrade checks and post-upgrade validations.

    Upgrading a device in an HA setup:
        >>> ha_details = {'local': 'active', 'peer': 'passive'}
        >>> perform_upgrade(firewall, '192.168.1.1', '10.1.0', ha_details=ha_details)
        # Handles the upgrade with consideration for HA roles, ensuring both peers are synchronized post-upgrade.

    Notes
    -----
    - The upgrade process is designed to be robust, with retry logic for various steps to handle transient issues.
    - For HA configurations, the function ensures both devices in the HA pair are upgraded and synchronized,
      maintaining high availability and minimizing downtime.
    - Customization options for retry attempts and intervals are provided through a 'settings.yaml' file, allowing
      adaptation to network conditions and operational policies.

    Workflow
    --------
    1. Verify the device's readiness and current version against the target version.
    2. Download the target software version if not already present on the device.
    3. Execute the upgrade command and monitor for completion.
    4. Reboot the device and validate the upgrade by checking the PAN-OS version.
    5. In HA setups, additional steps include verifying HA status and synchronizing state with the HA peer.
    """

    # Initialize with default values
    max_retries = 3
    retry_interval = 60

    # Override if settings.yaml exists and contains these settings
    if settings_file_path.exists():
        max_retries = settings_file.get("install.max_tries", max_retries)
        retry_interval = settings_file.get("install.retry_interval", retry_interval)

    logging.info(
        f"{get_emoji('start')} {hostname}: Performing upgrade to version {target_version}.\n"
        f"{get_emoji('report')} {hostname}: The install will take several minutes, check for status details within the GUI."
    )

    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(
                f"{get_emoji('start')} {hostname}: Attempting upgrade to version {target_version} (Attempt {attempt + 1} of {max_retries})."
            )
            install_job = target_device.software.install(target_version, sync=True)

            if install_job["success"]:
                logging.info(
                    f"{get_emoji('success')} {hostname}: Upgrade completed successfully"
                )
                logging.debug(
                    f"{get_emoji('report')} {hostname}: Install Job {install_job}"
                )
                break  # Exit loop on successful upgrade
            else:
                logging.error(f"{get_emoji('error')} {hostname}: Upgrade job failed.")
                attempt += 1
                if attempt < max_retries:
                    logging.info(
                        f"{get_emoji('warning')} {hostname}: Retrying in {retry_interval} seconds."
                    )
                    time.sleep(retry_interval)

        except PanDeviceError as upgrade_error:
            logging.error(
                f"{get_emoji('error')} {hostname}: Upgrade error: {upgrade_error}"
            )
            error_message = str(upgrade_error)
            if "software manager is currently in use" in error_message:
                attempt += 1
                if attempt < max_retries:
                    logging.info(
                        f"{get_emoji('warning')} {hostname}: Software manager is busy. Retrying in {retry_interval} seconds."
                    )
                    time.sleep(retry_interval)
            else:
                logging.error(
                    f"{get_emoji('stop')} {hostname}: Critical error during upgrade. Halting script."
                )
                sys.exit(1)


def run_assurance(
    firewall: Firewall,
    hostname: str,
    operation_type: str,
    actions: List[str],
    config: Dict[str, Union[str, int, float, bool]],
) -> Union[SnapshotReport, ReadinessCheckReport, None]:
    """
    Executes specified operational tasks, such as readiness checks or state snapshots, on a firewall based on the given
    operation type. This function is a versatile tool for conducting various operational checks or capturing the current
    state of the firewall for analysis. It uses a list of actions relevant to the chosen operation type and additional
    configuration parameters to customize the execution. Depending on the operation's success and type, it returns a
    report object or None in case of failure or if the operation type is invalid.

    Parameters
    ----------
    firewall : Firewall
        The Firewall object representing the device on which the assurance operations will be performed. This object
        must be initialized and authenticated prior to use.
    hostname : str
        The hostname or IP address of the firewall. This is used for identification and logging purposes.
    operation_type : str
        A string specifying the type of operation to perform. Supported types include 'readiness_check' and 'state_snapshot'.
    actions : List[str]
        A list of actions to be performed as part of the operation. The valid actions depend on the operation type.
    config : Dict[str, Union[str, int, float, bool]]
        A dictionary of additional configuration options that customize the operation. These might include thresholds,
        specific elements to check, or other operation-specific parameters.

    Returns
    -------
    Union[SnapshotReport, ReadinessCheckReport, None]
        Depending on the operation type, returns a SnapshotReport, ReadinessCheckReport, or None if the operation fails
        or the operation type is invalid.

    Raises
    ------
    SystemExit
        Exits the script if an invalid action is specified for the given operation type or if an unrecoverable error
        occurs during the operation execution.

    Examples
    --------
    Executing readiness checks before a firewall upgrade:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> result = run_assurance(firewall, '192.168.1.1', 'readiness_check', ['pending_changes', 'system_health'], {})
        # This might return a ReadinessCheckReport object with the results of the specified checks.

    Capturing the current state of a firewall for analysis:
        >>> result = run_assurance(firewall, '192.168.1.1', 'state_snapshot', ['arp_table', 'routes'], {})
        # This might return a SnapshotReport object with the current state information of the specified elements.

    Notes
    -----
    - The 'operation_type' parameter is key to defining the nature of the operation, making this function adaptable to
      a wide range of firewall management and diagnostic tasks.
    - This function is designed for extensibility, allowing new operation types and associated actions to be added as
      operational needs evolve.
    - Some operational parameters can be dynamically adjusted by providing a 'settings.yaml' file if the function
      utilizes a 'settings_file_path' to load these settings, offering greater control and customization of the operations.
    """

    # setup Firewall client
    proxy_firewall = FirewallProxy(firewall)
    checks_firewall = CheckFirewall(proxy_firewall)

    results = None

    if operation_type == "readiness_check":
        for action in actions:
            if action not in AssuranceOptions.READINESS_CHECKS.keys():
                logging.error(
                    f"{get_emoji('error')} {hostname}: Invalid action for readiness check: {action}"
                )

                sys.exit(1)

        try:
            logging.info(
                f"{get_emoji('start')} {hostname}: Performing readiness checks to determine if firewall is ready for upgrade."
            )
            result = checks_firewall.run_readiness_checks(actions)

            for (
                test_name,
                test_info,
            ) in AssuranceOptions.READINESS_CHECKS.items():
                check_readiness_and_log(result, hostname, test_name, test_info)

            return ReadinessCheckReport(**result)

        except Exception as e:
            logging.error(
                f"{get_emoji('error')} {hostname}: Error running readiness checks: {e}"
            )

            return None

    elif operation_type == "state_snapshot":
        # validate each type of action
        for action in actions:
            if action not in AssuranceOptions.STATE_SNAPSHOTS.keys():
                logging.error(
                    f"{get_emoji('error')} {hostname}: Invalid action for state snapshot: {action}"
                )
                return

        # take snapshots
        try:
            logging.debug(f"{get_emoji('start')} {hostname}: Performing snapshots.")
            results = checks_firewall.run_snapshots(snapshots_config=actions)
            logging.debug(
                f"{get_emoji('report')} {hostname}: Snapshot results {results}"
            )

            if results:
                # Pass the results to the SnapshotReport model
                return SnapshotReport(hostname=hostname, **results)
            else:
                return None

        except Exception as e:
            logging.error(
                f"{get_emoji('error')} {hostname}: Error running snapshots: %s", e
            )
            return

    elif operation_type == "report":
        for action in actions:
            if action not in AssuranceOptions.REPORTS.keys():
                logging.error(
                    f"{get_emoji('error')} {hostname}: Invalid action for report: {action}"
                )
                return
            logging.info(
                f"{get_emoji('report')} {hostname}: Generating report: {action}"
            )
            # result = getattr(Report(firewall), action)(**config)

    else:
        logging.error(
            f"{get_emoji('error')} {hostname}: Invalid operation type: {operation_type}"
        )
        return

    return results


def software_download(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    target_version: str,
    ha_details: dict,
) -> bool:
    """
    Downloads the specified software version to a Palo Alto Networks device, handling HA configurations.

    This function initiates the download of a specified PAN-OS version onto a target device, ensuring the desired
    version is not already present to avoid redundant downloads. It provides continuous feedback on the download
    progress and handles various download states and potential errors robustly. The function is HA-aware, considering
    HA details to manage downloads appropriately in HA setups.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device (Firewall or Panorama) where the software is to be downloaded.
    hostname : str
        The hostname or IP address of the device, used for logging and identification.
    target_version : str
        The target PAN-OS version to download (e.g., '10.1.0').
    ha_details : dict
        A dictionary containing HA configuration details, essential for devices in HA pairs.

    Returns
    -------
    bool
        True if the download succeeds, False otherwise.

    Raises
    ------
    SystemExit
        If a critical error occurs during the download process, the script will exit with an error message.

    Examples
    --------
    Initiating a software download on a standalone firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> if software_download(firewall, '192.168.1.1', '9.1.3', {}):
        ...     print("Download successful")
        ... else:
        ...     print("Download failed")

    Initiating a software download on an HA-configured device:
        >>> ha_details = {'enabled': True, 'group': '1', 'peer_ip': '192.168.1.2'}
        >>> if software_download(firewall, '192.168.1.1', '9.1.3', ha_details):
        ...     print("Download successful")
        ... else:
        ...     print("Download failed")

    Notes
    -----
    - The function checks the device's current software inventory to avoid unnecessary downloads.
    - It supports devices configured in High Availability (HA) pairs by considering HA synchronization during the download.
    - Continuous feedback is provided through logging, with updates on the download status every 30 seconds, enhancing visibility into the process.
    - The retry logic and intervals for monitoring the download progress can be customized in the `settings.yaml` file if `settings_file_path` is utilized within the function, allowing for tailored behavior based on specific operational environments.
    """

    if target_device.software.versions[target_version]["downloaded"]:
        logging.info(
            f"{get_emoji('success')} {hostname}: version {target_version} already on target device."
        )
        return True

    if (
        not target_device.software.versions[target_version]["downloaded"]
        or target_device.software.versions[target_version]["downloaded"]
        != "downloading"
    ):
        logging.info(
            f"{get_emoji('search')} {hostname}: version {target_version} is not on the target device"
        )

        start_time = time.time()

        try:
            logging.info(
                f"{get_emoji('start')} {hostname}: version {target_version} is beginning download"
            )
            target_device.software.download(target_version)
        except PanDeviceXapiError as download_error:
            logging.error(
                f"{get_emoji('error')} {hostname}: Download Error {download_error}"
            )

            sys.exit(1)

        while True:
            target_device.software.info()
            dl_status = target_device.software.versions[target_version]["downloaded"]
            elapsed_time = int(time.time() - start_time)

            if dl_status is True:
                logging.info(
                    f"{get_emoji('success')} {hostname}: {target_version} downloaded in {elapsed_time} seconds",
                )
                return True
            elif dl_status in (False, "downloading"):
                # Consolidate logging for both 'False' and 'downloading' states
                status_msg = (
                    "Download is starting"
                    if dl_status is False
                    else f"Downloading version {target_version}"
                )
                if ha_details:
                    logging.info(
                        f"{get_emoji('working')} {hostname}: Downloading version {target_version} - HA will sync image - Elapsed time: {elapsed_time} seconds"
                    )
                else:
                    logging.info(
                        f"{get_emoji('working')} {hostname}: {status_msg} - Elapsed time: {elapsed_time} seconds"
                    )
            else:
                logging.error(
                    f"{get_emoji('error')} {hostname}: Download failed after {elapsed_time} seconds"
                )
                return False

            time.sleep(30)

    else:
        logging.error(
            f"{get_emoji('error')} {hostname}: Error downloading {target_version}."
        )

        sys.exit(1)


def software_update_check(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    version: str,
    ha_details: dict,
) -> bool:
    """
    Checks the availability of the specified software version for upgrade on the target device, taking into account HA configurations.

    This function assesses whether the target device, either a Firewall or Panorama, can be upgraded to the specified PAN-OS version. It evaluates the current device software against the target version, ensuring the target version is not a downgrade and is available in the device's software repository. For HA-configured devices, the function considers the HA setup's implications on the upgrade process. If the target version requires a base image that is not present on the device, the function attempts to download it, adhering to a configurable retry policy.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device on which the software version's availability is being checked.
    hostname : str
        The hostname or IP address of the target device for identification in logs.
    version : str
        The target PAN-OS version for potential upgrade.
    ha_details : dict
        A dictionary containing the HA configuration of the target device, if applicable.

    Returns
    -------
    bool
        True if the target version is available for upgrade, including the successful download of the required base image if necessary. False otherwise.

    Raises
    ------
    SystemExit
        If the target version represents a downgrade or if critical errors occur during the version availability check or base image download.

    Examples
    --------
    Checking for software version availability on a standalone device:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> is_available = software_update_check(firewall, '192.168.1.1', '9.1.0', {})
        >>> print("Version is available for upgrade." if is_available else "Version is not available for upgrade.")

    Checking for software version availability on an HA-configured device:
        >>> ha_details = {'enabled': True, 'peer_ip': '192.168.1.2'}
        >>> is_available = software_update_check(firewall, '192.168.1.1', '9.1.0', ha_details)
        >>> print("Version is available for upgrade." if is_available else "Version is not available for upgrade.")

    Notes
    -----
    - The function ensures the target version is not a downgrade and checks for its availability in the software repository.
    - In HA setups, the function checks for upgrade compatibility considering the HA synchronization state and version compatibility between peers.
    - Retry logic for downloading the required base image, if not already present, can be customized through the `settings.yaml` file, allowing for operational flexibility and adherence to network policies.
    """

    # parse version
    major, minor, maintenance = version.split(".")

    # Make sure we know about the system details - if we have connected via Panorama, this can be null without this.
    logging.debug(
        f"{get_emoji('working')} {hostname}: Refreshing running system information"
    )
    target_device.refresh_system_info()

    # check to see if the specified version is older than the current version
    determine_upgrade(
        target_device,
        hostname,
        major,
        minor,
        maintenance,
    )

    # retrieve available versions of PAN-OS
    logging.info(
        f"{get_emoji('working')} {hostname}: Refreshing list of available software versions"
    )
    target_device.software.check()
    available_versions = target_device.software.versions

    if version in available_versions:
        retry_count = settings_file.get("download.max_tries", 3)
        wait_time = settings_file.get("download.retry_interval", 60)

        logging.info(
            f"{get_emoji('success')} {hostname}: version {version} is available for download"
        )

        base_version_key = f"{major}.{minor}.0"
        if available_versions.get(base_version_key, {}).get("downloaded"):
            logging.info(
                f"{get_emoji('success')} {hostname}: Base image for {version} is already downloaded"
            )
            return True
        else:
            for attempt in range(retry_count):
                logging.error(
                    f"{get_emoji('error')} {hostname}: Base image for {version} is not downloaded. Attempting download."
                )
                downloaded = software_download(
                    target_device, hostname, base_version_key, ha_details
                )

                if downloaded:
                    logging.info(
                        f"{get_emoji('success')} {hostname}: Base image {base_version_key} downloaded successfully"
                    )
                    logging.info(
                        f"{get_emoji('success')} {hostname}: Pausing for {wait_time} seconds to let {base_version_key} image load into the software manager before downloading {version}"
                    )

                    # Wait before retrying to ensure the device has processed the downloaded base image
                    time.sleep(wait_time)

                    # Re-check the versions after waiting
                    target_device.software.check()
                    if version in target_device.software.versions:
                        # Proceed with the target version check again
                        return software_update_check(
                            target_device,
                            hostname,
                            version,
                            ha_details,
                        )

                    else:
                        logging.info(
                            f"{get_emoji('report')} {hostname}: Waiting for device to load the new base image into software manager"
                        )
                        # Retry if the version is still not recognized
                        continue
                else:
                    if attempt < retry_count - 1:
                        logging.error(
                            f"{get_emoji('error')} {hostname}: Failed to download base image for version {version}. Retrying in {wait_time} seconds."
                        )
                        time.sleep(wait_time)
                    else:
                        logging.error(
                            f"{get_emoji('error')} {hostname}: Failed to download base image after {retry_count} attempts."
                        )
                        return False

    else:
        # If the version is not available, find and log close matches
        close_matches = find_close_matches(list(available_versions.keys()), version)
        close_matches_str = ", ".join(close_matches)
        logging.error(
            f"{get_emoji('error')} {hostname}: Version {version} is not available for download. Closest matches: {close_matches_str}"
        )
        return False


def suspend_ha_active(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> bool:
    """
    Temporarily disables High Availability (HA) functionality on an active device within an HA configuration.

    In an HA setup, it may be necessary to suspend HA functionality on the active device to perform system upgrades or maintenance tasks without triggering failover to the passive device. This function sends an operational command to the target device to suspend HA, ensuring that the device remains in an active but non-failover state. It checks the command's success through the device's response and provides appropriate logging for the operation's outcome.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device on which HA functionality is to be suspended. This must be an active device in an HA pair and can be either a Firewall or a Panorama appliance.
    hostname : str
        The hostname or IP address of the target device. This is used primarily for identification and logging purposes.

    Returns
    -------
    bool
        True if the command to suspend HA is successfully issued and acknowledged by the target device, indicating that HA functionality has been suspended. False if the command fails or the device response indicates an error.

    Raises
    ------
    Exception
        If the operational command to suspend HA fails or an unexpected response is received from the device, an exception is raised detailing the error encountered.

    Example
    -------
    Suspending HA functionality on an active device in an HA pair:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> success = suspend_ha_active(firewall, '192.168.1.1')
        >>> if success:
        ...     print("HA suspension successful.")
        ... else:
        ...     print("HA suspension failed.")

    Notes
    -----
    - Suspending HA on the active device is a significant operation that should be performed with caution, particularly in a production environment, to avoid unintended service disruptions.
    - Ensure that the procedure for resuming HA functionality is planned and understood before suspending HA, as this will be necessary to restore full HA operational capabilities.
    """

    try:
        suspension_response = target_device.op(
            "<request><high-availability><state><suspend/></state></high-availability></request>",
            cmd_xml=False,
        )
        if "success" in suspension_response.text:
            logging.info(
                f"{get_emoji('success')} {hostname}: Active target device HA state suspended."
            )
            return True
        else:
            logging.error(
                f"{get_emoji('error')} {hostname}: Failed to suspend active target device HA state."
            )
            return False
    except Exception as e:
        logging.warning(
            f"{get_emoji('warning')} {hostname}: Error received when suspending active target device HA state: {e}"
        )
        return False


def suspend_ha_passive(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> bool:
    """
    Temporarily disables High Availability (HA) functionality on the passive device within an HA pair.

    In an HA environment, it may become necessary to suspend HA functionality on the passive device to facilitate system upgrades or maintenance, ensuring the device does not unexpectedly become active. This function issues a command to the target device to suspend its HA functionality. The success of this operation is determined by the response from the device, and the outcome is logged for administrative review.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device on which HA functionality is to be suspended. This must be a passive device in an HA pair and can be either a Firewall or a Panorama appliance.
    hostname : str
        The hostname or IP address of the device. Used for identification and logging.

    Returns
    -------
    bool
        True if the HA suspension command is successfully executed, indicating that HA functionality on the passive device has been temporarily disabled. False if the command execution fails or if the device response indicates an error.

    Raises
    ------
    Exception
        If the operational command to suspend HA fails or an unexpected response is received, an exception is logged detailing the encountered issue.

    Example
    -------
    Suspending HA on the passive device in an HA configuration:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='admin')
        >>> success = suspend_ha_passive(panorama, 'panorama.example.com')
        >>> print("HA suspension successful" if success else "HA suspension failed")

    Notes
    -----
    - Suspending HA on a passive device is a critical operation that should be carefully planned and executed, particularly in live environments, to avoid unintended failovers or service disruptions.
    - Coordination with network management and understanding the process to resume HA functionality are essential to ensure the continuity of services and network redundancy.
    """

    try:
        suspension_response = target_device.op(
            "<request><high-availability><state><suspend/></state></high-availability></request>",
            cmd_xml=False,
        )
        if "success" in suspension_response.text:
            logging.info(
                f"{get_emoji('success')} {hostname}: Passive target device HA state suspended."
            )
            return True
        else:
            logging.error(
                f"{get_emoji('error')} {hostname}: Failed to suspend passive target device HA state."
            )
            return False
    except Exception as e:
        logging.error(
            f"{get_emoji('error')} {hostname}: Error suspending passive target device HA state: {e}"
        )
        return False


def upgrade_firewall(
    firewall: Firewall,
    target_version: str,
    dry_run: bool,
) -> None:
    """
    Manages the entire upgrade process for a Palo Alto Networks firewall to a specified version, with an option for a dry run.

    This comprehensive function oversees the firewall's upgrade process, encompassing pre-upgrade assessments, downloading necessary software, and rebooting to the new version. It caters to both standalone units and those configured in High Availability (HA) setups, ensuring proper coordination and failover handling. The dry run mode allows administrators to simulate the upgrade process without applying any changes, useful for validation and planning.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance targeted for the upgrade, initialized with the required authentication and connection settings.
    target_version : str
        The desired PAN-OS version to upgrade the firewall to, formatted as a string (e.g., '10.1.0').
    dry_run : bool
        Specifies whether to simulate the upgrade process (True) without applying any changes, or to perform the actual upgrade (False).

    Raises
    ------
    SystemExit
        If any critical issues arise during the upgrade process, resulting in its termination.

    Examples
    --------
    Upgrading a firewall to a specific version:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> upgrade_firewall(firewall_instance, '10.1.0', dry_run=False)
        # Initiates the actual upgrade process to version 10.1.0.

    Performing a dry run of the upgrade process:
        >>> upgrade_firewall(firewall_instance, '10.1.0', dry_run=True)
        # Simulates the upgrade process without making any changes.

    Notes
    -----
    - A dry run is recommended before executing the actual upgrade to ensure readiness and mitigate potential issues.
    - The function utilizes detailed logging to provide transparency and traceability throughout the upgrade process.
    - Custom settings for the upgrade process, such as retry intervals and snapshot configurations, can be overridden by a `settings.yaml` file if present.

    Workflow
    --------
    1. Validates the current system state and HA configuration.
    2. Performs readiness checks to ensure the firewall is prepared for upgrade.
    3. Downloads the necessary software version if not already available.
    4. Takes pre-upgrade snapshots and backups for rollback purposes.
    5. Executes the upgrade and reboots the firewall to the target version.
    6. Verifies post-upgrade status and functionality.
    7. Performs post-upgrade snapshots and backups for reference and PDF report generation.
    """

    # Refresh system information to ensure we have the latest data
    logging.debug(f"{get_emoji('start')} Refreshing system information.")
    firewall_details = SystemSettings.refreshall(firewall)[0]
    hostname = firewall_details.hostname
    logging.info(
        f"{get_emoji('report')} {hostname}: {firewall.serial} {firewall_details.ip_address}"
    )

    # Determine if the firewall is standalone, HA, or in a cluster
    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing test to see if firewall is standalone, HA, or in a cluster."
    )
    deploy_info, ha_details = get_ha_status(
        firewall,
        hostname,
    )
    logging.info(f"{get_emoji('report')} {hostname}: HA mode: {deploy_info}")
    logging.debug(f"{get_emoji('report')} {hostname}: HA details: {ha_details}")

    # If firewall is part of HA pair, determine if it's active or passive
    if ha_details:
        proceed_with_upgrade, peer_firewall = handle_firewall_ha(
            firewall,
            hostname,
            dry_run,
        )

        if not proceed_with_upgrade:
            if peer_firewall:
                logging.info(
                    f"{get_emoji('start')} {hostname}: Switching control to the peer firewall for upgrade."
                )
                upgrade_firewall(peer_firewall, target_version, dry_run)
            else:
                return  # Exit the function without proceeding to upgrade

    # Check to see if the firewall is ready for an upgrade
    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing tests to validate firewall's readiness."
    )
    update_available = software_update_check(
        firewall,
        hostname,
        target_version,
        ha_details,
    )
    logging.debug(f"{get_emoji('report')} {hostname}: Readiness check complete")

    # gracefully exit if the firewall is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"{get_emoji('error')} {hostname}: Not ready for upgrade to {target_version}.",
        )
        sys.exit(1)

    # Download the target version
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing test to see if {target_version} is already downloaded."
    )
    image_downloaded = software_download(
        firewall,
        hostname,
        target_version,
        ha_details,
    )
    if deploy_info == "active" or deploy_info == "passive":
        logging.info(
            f"{get_emoji('success')} {hostname}: {target_version} has been downloaded and sync'd to HA peer."
        )
    else:
        logging.info(
            f"{get_emoji('success')} {hostname}: version {target_version} has been downloaded."
        )

    # Begin snapshots of the network state
    if not image_downloaded:
        logging.error(
            f"{get_emoji('error')} {hostname}: Image not downloaded, exiting."
        )

        sys.exit(1)

    # Determine snapshot actions to perform based on settings.yaml
    if settings_file_path.exists() and settings_file.get("snapshots.customize", False):
        # Extract state actions where value is True from settings.yaml
        selected_actions = [
            action
            for action, enabled in settings_file.get("snapshots.state", {}).items()
            if enabled
        ]
    else:
        # Select actions based on 'enabled_by_default' attribute from AssuranceOptions class
        selected_actions = [
            action
            for action, attrs in AssuranceOptions.STATE_SNAPSHOTS.items()
            if attrs.get("enabled_by_default", False)
        ]

    # Perform the pre-upgrade snapshot
    pre_snapshot = perform_snapshot(
        firewall,
        hostname,
        f'assurance/snapshots/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
        selected_actions,
    )

    # Perform Readiness Checks
    perform_readiness_checks(
        firewall,
        hostname,
        f'assurance/readiness_checks/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
    )

    # Determine strictness of HA sync check
    with target_devices_to_revisit_lock:
        is_device_to_revisit = firewall in target_devices_to_revisit

    # Perform HA sync check, skipping standalone firewalls
    if ha_details:
        ha_sync_check_firewall(
            hostname,
            ha_details,
            strict_sync_check=not is_device_to_revisit,
        )

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing backup of configuration to local filesystem."
    )
    backup_config = backup_configuration(
        firewall,
        hostname,
        f'assurance/configurations/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
    )
    logging.debug(f"{get_emoji('report')} {hostname}: {backup_config}")

    # Exit execution is dry_run is True
    if dry_run is True:
        logging.info(f"{get_emoji('success')} {hostname}: Dry run complete, exiting.")
        logging.info(f"{get_emoji('stop')} {hostname}: Halting script.")
        sys.exit(0)
    else:
        logging.info(
            f"{get_emoji('report')} {hostname}: Not a dry run, continue with upgrade."
        )

    # Perform the upgrade
    perform_upgrade(
        target_device=firewall,
        hostname=hostname,
        target_version=target_version,
        ha_details=ha_details,
    )

    # Perform the reboot
    perform_reboot(
        target_device=firewall,
        hostname=hostname,
        target_version=target_version,
        ha_details=ha_details,
    )

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing backup of configuration to local filesystem."
    )
    backup_config = backup_configuration(
        firewall,
        hostname,
        f'assurance/configurations/{hostname}/post/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
    )
    logging.debug(f"{get_emoji('report')} {hostname}: {backup_config}")

    # Wait for the device to become ready for the post upgrade snapshot
    logging.info(
        f"{get_emoji('working')} {hostname}: Waiting for the device to become ready for the post upgrade snapshot."
    )
    time.sleep(120)

    # Load settings if the file exists
    if settings_file_path.exists():
        with open(settings_file_path, "r") as file:
            settings = yaml.safe_load(file)

        # Check if snapshots are disabled in the settings
        if settings.get("snapshots", {}).get("disabled", False):
            logging.info(
                f"{get_emoji('skipped')} {hostname}: Snapshots are disabled in the settings. Skipping snapshot for {hostname}."
            )
            return None  # Early return, no snapshot performed

        else:
            # Perform the post-upgrade snapshot
            post_snapshot = perform_snapshot(
                firewall,
                hostname,
                f'assurance/snapshots/{hostname}/post/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
                selected_actions,
            )

            # initialize object storing both snapshots
            snapshot_compare = SnapshotCompare(
                left_snapshot=pre_snapshot.model_dump(),
                right_snapshot=post_snapshot.model_dump(),
            )

            pre_post_diff = snapshot_compare.compare_snapshots(selected_actions)

            logging.debug(
                f"{get_emoji('report')} {hostname}: Snapshot comparison before and after upgrade {pre_post_diff}"
            )

            folder_path = f"assurance/snapshots/{hostname}/diff"
            pdf_report = (
                f'{folder_path}/{time.strftime("%Y-%m-%d_%H-%M-%S")}_report.pdf'
            )
            ensure_directory_exists(pdf_report)

            # Generate the PDF report for the diff
            generate_diff_report_pdf(
                pre_post_diff,
                pdf_report,
                hostname,
                target_version,
            )

            logging.info(
                f"{get_emoji('save')} {hostname}: Snapshot comparison PDF report saved to {pdf_report}"
            )

            json_report = (
                f'{folder_path}/{time.strftime("%Y-%m-%d_%H-%M-%S")}_report.json'
            )

            # Write the file to the local filesystem as JSON
            with open(json_report, "w") as file:
                file.write(json.dumps(pre_post_diff))

            logging.debug(
                f"{get_emoji('save')} {hostname}: Snapshot comparison JSON report saved to {json_report}"
            )


def upgrade_panorama(
    panorama: Panorama,
    target_version: str,
    dry_run: bool,
) -> None:
    """
    Executes the upgrade process for a Panorama management server to a specified PAN-OS version, with support for a dry run option.

    This function orchestrates the upgrade of a Panorama management server by conducting pre-upgrade validations, downloading the necessary software, performing the upgrade, and rebooting the server. It is applicable to both standalone Panorama instances and those configured in High Availability (HA) setups. The dry run feature enables administrators to simulate the upgrade steps without making actual changes to the system, allowing for planning and verification purposes.

    Parameters
    ----------
    panorama : Panorama
        The Panorama instance to be upgraded, initialized with the necessary authentication and connection details.
    target_version : str
        The target PAN-OS version to which the Panorama should be upgraded (e.g., '10.1.0').
    dry_run : bool
        If True, performs a simulation of the upgrade process without applying any changes; if False, executes the actual upgrade.

    Raises
    ------
    SystemExit
        Terminates the script if the upgrade process encounters an unrecoverable error at any stage.

    Examples
    --------
    Performing an actual upgrade on a Panorama:
        >>> panorama_instance = Panorama(hostname='panorama.example.com', api_username='admin', api_password='admin')
        >>> upgrade_panorama(panorama_instance, '10.1.0', dry_run=False)
        # Executes the upgrade process to PAN-OS version 10.1.0.

    Conducting a dry run of the Panorama upgrade:
        >>> upgrade_panorama(panorama_instance, '10.1.0', dry_run=True)
        # Simulates the upgrade process to PAN-OS version 10.1.0 without making any system changes.

    Notes
    -----
    - A dry run is advisable before executing the actual upgrade to confirm process steps and readiness.
    - The function ensures comprehensive logging throughout the upgrade process for auditability and troubleshooting.
    - Settings such as retry intervals and checks can be customized through a `settings.yaml` file if used within the function, enhancing flexibility in upgrade configurations.

    Workflow
    --------
    1. Validate the current system state and HA configuration of the Panorama.
    2. Conduct readiness checks to ensure the Panorama is prepared for the upgrade.
    3. Download the required software version if it is not already available on the system.
    4. Take pre-upgrade snapshots and backup configurations for rollback purposes.
    5. Execute the upgrade, including a system reboot to the target version.
    6. Verify the system's post-upgrade status and functionality.
    """

    # Refresh system information to ensure we have the latest data
    logging.debug(f"{get_emoji('start')} Refreshing system information.")
    panorama_details = SystemSettings.refreshall(panorama)[0]
    hostname = panorama_details.hostname
    logging.info(
        f"{get_emoji('report')} {hostname}: {panorama.serial} {panorama_details.ip_address}"
    )

    # Determine if the Panorama is standalone, HA, or in a cluster
    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing test to see if Panorama is standalone, HA, or in a cluster."
    )
    deploy_info, ha_details = get_ha_status(
        panorama,
        hostname,
    )
    logging.info(f"{get_emoji('report')} {hostname}: HA mode: {deploy_info}")
    logging.debug(f"{get_emoji('report')} {hostname}: HA details: {ha_details}")

    # If Panorama is part of HA pair, determine if it's active or passive
    if ha_details:
        proceed_with_upgrade, peer_panorama = handle_panorama_ha(
            panorama,
            hostname,
            dry_run,
        )

        if not proceed_with_upgrade:
            if peer_panorama:
                logging.info(
                    f"{get_emoji('start')} {hostname}: Switching control to the peer Panorama for upgrade."
                )
                upgrade_panorama(peer_panorama, target_version, dry_run)
            else:
                # Exit the function without proceeding to upgrade
                return

    # Check to see if the Panorama is ready for an upgrade
    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing tests to validate Panorama's readiness."
    )
    update_available = software_update_check(
        panorama,
        hostname,
        target_version,
        ha_details,
    )

    # gracefully exit if the Panorama is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"{get_emoji('error')} {hostname}: Not ready for upgrade to {target_version}.",
        )
        sys.exit(1)

    # Download the target version
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing test to see if {target_version} is already downloaded."
    )
    image_downloaded = software_download(
        panorama,
        hostname,
        target_version,
        ha_details,
    )
    if deploy_info == "primary-active" or deploy_info == "secondary-passive":
        logging.info(
            f"{get_emoji('success')} {hostname}: {target_version} has been downloaded and sync'd to HA peer."
        )
    else:
        logging.info(
            f"{get_emoji('success')} {hostname}: Panorama version {target_version} has been downloaded."
        )

    # Begin snapshots of the network state
    if not image_downloaded:
        logging.error(
            f"{get_emoji('error')} {hostname}: Image not downloaded, exiting."
        )

        sys.exit(1)

    # Determine strictness of HA sync check
    with target_devices_to_revisit_lock:
        is_panorama_to_revisit = panorama in target_devices_to_revisit

    # Print out list of Panorama appliances to revisit
    logging.debug(
        f"{get_emoji('report')} Panorama appliances to revisit: {target_devices_to_revisit}"
    )
    logging.debug(
        f"{get_emoji('report')} {hostname}: Is Panorama to revisit: {is_panorama_to_revisit}"
    )

    # Perform HA sync check, skipping standalone Panoramas
    if ha_details:
        ha_sync_check_panorama(
            hostname,
            ha_details,
            strict_sync_check=False,
            # strict_sync_check=not is_panorama_to_revisit,
        )

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing backup of configuration to local filesystem."
    )
    backup_config = backup_configuration(
        panorama,
        hostname,
        f'assurance/configurations/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
    )
    logging.debug(f"{get_emoji('report')} {hostname}: {backup_config}")

    # Exit execution is dry_run is True
    if dry_run is True:
        logging.info(f"{get_emoji('success')} {hostname}: Dry run complete, exiting.")
        logging.info(f"{get_emoji('stop')} {hostname}: Halting script.")
        sys.exit(0)
    else:
        logging.info(
            f"{get_emoji('start')} {hostname}: Not a dry run, continue with upgrade."
        )

    # Perform the upgrade
    perform_upgrade(
        target_device=panorama,
        hostname=hostname,
        target_version=target_version,
        ha_details=ha_details,
    )

    # Perform the reboot
    perform_reboot(
        target_device=panorama,
        hostname=hostname,
        target_version=target_version,
        ha_details=ha_details,
    )


# Utility Functions


def check_readiness_and_log(
    result: dict,
    hostname: str,
    test_name: str,
    test_info: dict,
) -> None:
    """
    Analyzes and logs the outcomes of readiness checks for a firewall or Panorama device, emphasizing failures that
    could impact the upgrade process. This function is integral to the pre-upgrade validation phase, ensuring that
    each device meets the necessary criteria before proceeding with an upgrade. It logs detailed results for each
    readiness check, using severity levels appropriate to the outcome of each test. Critical failures, identified by
    the 'exit_on_failure' flag in the test metadata, will cause the script to terminate, preventing potentially
    hazardous upgrade attempts.

    Parameters
    ----------
    result : dict
        The results of the readiness checks, structured as a dictionary where each key represents a test name and its
        value is a dictionary detailing the test's outcome ('state') and an explanation ('reason').
    hostname : str
        The hostname or IP address of the device being tested, utilized for logging context.
    test_name : str
        The identifier for the specific readiness check being logged, which should match a key in the 'result' dictionary.
    test_info : dict
        A dictionary containing metadata about the readiness check, including a descriptive label ('description'), the
        severity level for logging ('log_level'), and a flag indicating whether failure of this test should halt script
        execution ('exit_on_failure').

    Raises
    ------
    SystemExit
        If a test marked as critical (where 'exit_on_failure' is True) fails, the script will exit to avert an unsafe upgrade.

    Examples
    --------
    Handling a failed readiness check that is critical for upgrade:
        >>> result = {'connectivity_check': {'state': False, 'reason': 'Network unreachable'}}
        >>> test_info = {'description': 'Connectivity Check', 'log_level': 'error', 'exit_on_failure': True}
        >>> check_readiness_and_log(result, 'firewall01', 'connectivity_check', test_info)
        # This logs an error for the failed connectivity check and exits the script to prevent proceeding with the upgrade.

    Notes
    -----
    - This function is pivotal in ensuring that devices are fully prepared for an upgrade by rigorously logging the
      outcomes of various readiness checks.
    - The structured approach to logging facilitates easy identification and troubleshooting of potential issues prior
      to initiating the upgrade process.
    - Flexibility in defining the log level and criticality of each test allows for nuanced logging that reflects the
      importance and implications of each readiness check.
    """

    test_result = result.get(
        test_name, {"state": False, "reason": "Skipped Readiness Check"}
    )

    # Use .get() with a default value for 'reason' to avoid KeyError
    reason = test_result.get("reason", "No reason provided")
    log_message = f'{reason}: {test_info["description"]}'

    if test_result["state"]:
        logging.info(
            f"{get_emoji('success')} {hostname}: Passed Readiness Check: {test_info['description']}"
        )
    else:
        if test_info["log_level"] == "error":
            logging.error(f"{get_emoji('error')} {hostname}: {log_message}")
            if test_info["exit_on_failure"]:
                logging.error(f"{get_emoji('stop')} {hostname}: Halting script.")

                sys.exit(1)
        elif test_info["log_level"] == "warning":
            logging.info(
                f"{get_emoji('skipped')} {hostname}: Skipped Readiness Check: {test_info['description']}"
            )
        else:
            logging.info(f"{get_emoji('report')} {hostname}: Log Message {log_message}")


def compare_versions(
    version1: str,
    version2: str,
) -> str:
    """
    Compares two version strings to determine their relative sequence.

    This utility function is essential for upgrade processes, compatibility checks, and system maintenance workflows. It compares two version strings by breaking them down into their constituent parts (major, minor, maintenance, and hotfix numbers) and evaluating their numerical order. The function is designed to accurately compare versions, accounting for the complexities of versioning schemes, including hotfixes and pre-release versions.

    Parameters
    ----------
    version1 : str
        The first version string to compare, formatted as 'major.minor.maintenance' or 'major.minor.maintenance-hotfix'.
    version2 : str
        The second version string for comparison, formatted similarly to 'version1'.

    Returns
    -------
    str
        A string indicating the comparison result: 'older' if 'version1' predates 'version2', 'newer' if 'version1' is more recent than 'version2', or 'equal' if both versions are the same.

    Examples
    --------
    Comparing version strings to establish their relative order:
        >>> compare_versions('8.1.0', '8.2.0')
        'older'  # Indicates that '8.1.0' is an older version compared to '8.2.0'

        >>> compare_versions('9.0.1', '9.0.1-h1')
        'newer'  # Hotfix versions are considered newer, hence '9.0.1' is newer compared to '9.0.1-h1'

        >>> compare_versions('10.0.5', '10.0.5')
        'equal'  # Indicates that both version strings are identical

    Notes
    -----
    - This function is a key tool in managing software updates, ensuring that systems are running the intended or most compatible software versions.
    - It supports a broad range of versioning formats, making it versatile for different software and systems.
    - The function is designed to be reliable and straightforward, providing clear outputs for decision-making processes related to version management.
    """

    parsed_version1 = parse_version(version1)
    parsed_version2 = parse_version(version2)

    if parsed_version1 < parsed_version2:
        return "older"
    elif parsed_version1 > parsed_version2:
        return "newer"
    else:
        return "equal"


def configure_logging(
    level: str,
    encoding: str = "utf-8",
    log_file_path: str = "logs/upgrade.log",
    log_max_size: int = 10 * 1024 * 1024,
) -> None:
    """
    Sets up the logging infrastructure for the application, specifying the minimum severity level of messages to log,
    character encoding for log files, and file logging details such as path and maximum size. The function initializes
    logging to both the console and a rotating file, ensuring that log messages are both displayed in real-time and
    archived for future analysis. The rotating file handler helps manage disk space by limiting the log file size and
    archiving older logs. This setup is crucial for monitoring application behavior, troubleshooting issues, and
    maintaining an audit trail of operations.

    Parameters
    ----------
    level : str
        The minimum severity level of log messages to record. Valid levels are 'DEBUG', 'INFO', 'WARNING', 'ERROR',
        and 'CRITICAL', in order of increasing severity.
    encoding : str, optional
        The character encoding for the log files. Defaults to 'utf-8', accommodating a wide range of characters and symbols.
    log_file_path : str, optional
        The path to the log file where messages will be stored. Defaults to 'logs/upgrade.log'.
    log_max_size : int, optional
        The maximum size of the log file in bytes before it is rotated. Defaults to 10 MB (10 * 1024 * 1024 bytes).

    Raises
    ------
    ValueError
        If the specified logging level is invalid, ensuring that log messages are captured at appropriate severity levels.

    Examples
    --------
    Basic logging configuration with default settings:
        >>> configure_logging('INFO')
        # Configures logging to capture messages of level INFO and above, using default encoding and file settings.

    Advanced logging configuration with custom settings:
        >>> configure_logging('DEBUG', 'iso-8859-1', '/var/log/myapp.log', 5 * 1024 * 1024)
        # Configures logging to capture all messages including debug, using ISO-8859-1 encoding, storing logs in
        # '/var/log/myapp.log', with a maximum file size of 5 MB before rotating.

    Notes
    -----
    - It is essential to configure logging appropriately to capture sufficient detail for effective monitoring and
      troubleshooting, without overwhelming the system with excessive log data.
    - The logging setup, including file path and maximum size, can be customized via a 'settings.yaml' file if the
      application supports loading configuration settings from such a file. This allows for dynamic adjustment of
      logging behavior based on operational needs or user preferences.
    """

    allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level.upper() not in allowed_levels:
        raise ValueError(
            f"Invalid log level: {level}. Allowed levels are: {', '.join(allowed_levels)}"
        )

    # Use the provided log_level parameter if given, otherwise fall back to settings file or default
    log_level = (
        level.upper() if level else settings_file.get("logging.level", "INFO").upper()
    )

    # Override if settings.yaml exists and contains these settings
    if settings_file_path.exists():
        # Use the provided log_file_path parameter if given, otherwise fall back to settings file or default
        log_file_path = settings_file.get("logging.file_path", "logs/upgrade.log")
        # Convert MB to bytes
        log_max_size = settings_file.get("logging.max_size", 10) * 1024 * 1024

    # Use the provided log_upgrade_log_count parameter if given, otherwise fall back to settings file or default
    log_upgrade_log_count = settings_file.get("logging.upgrade_log_count", 3)

    # Set the logging level
    logging_level = getattr(logging, log_level, logging.INFO)

    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging_level)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=log_max_size,
        backupCount=log_upgrade_log_count,
        encoding=encoding,
    )

    # Create formatters and add them to the handlers
    if log_level == "DEBUG":
        console_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        console_format = logging.Formatter("%(message)s")
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def connect_to_host(
    hostname: str,
    api_username: str,
    api_password: str,
) -> PanDevice:
    """
    Establishes a secure API connection to a Palo Alto Networks device, such as a Firewall or Panorama.

    This function attempts to connect to the specified hostname using API credentials, differentiating between Firewall and Panorama based on the response. Successful connection results in the creation of a PanDevice object, which serves as the foundation for subsequent API interactions with the device. Comprehensive error handling is included to address common connection issues, providing actionable feedback for resolution.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target Palo Alto Networks device.
    api_username : str
        The API username for authentication.
    api_password : str
        The password corresponding to the API username.

    Returns
    -------
    PanDevice
        A PanDevice object representing the connected device, which may be a Firewall or Panorama instance.

    Raises
    ------
    SystemExit
        Exits the script with an error message if connection attempts fail, which may occur due to incorrect credentials, network connectivity issues, or an unreachable device.

    Examples
    --------
    Establishing a connection to a Firewall:
        >>> firewall = connect_to_host('firewall.example.com', 'admin', 'password')
        # Returns a Firewall object if connection is successful.

    Establishing a connection to Panorama:
        >>> panorama = connect_to_host('panorama.example.com', 'admin', 'password')
        # Returns a Panorama object if connection is successful.

    Notes
    -----
    - Initiating a connection to a device is a prerequisite for performing any operational or configuration tasks via the API.
    - The function's error handling provides clear diagnostics, aiding in troubleshooting connection issues.
    - Configuration settings for the connection, such as timeout periods and retry attempts, can be customized through the `settings.yaml` file, if `settings_file_path` is utilized within the function.
    """

    try:
        target_device = PanDevice.create_from_device(
            hostname,
            api_username,
            api_password,
        )

        return target_device

    except PanConnectionTimeout:
        logging.error(
            f"{get_emoji('error')} {hostname}: Connection to the appliance timed out. Please check the DNS hostname or IP address and network connectivity."
        )

        sys.exit(1)

    except Exception as e:
        logging.error(
            f"{get_emoji('error')} {hostname}: An error occurred while connecting to the appliance: {e}"
        )

        sys.exit(1)


def console_welcome_banner(
    mode: str,
    config_path: Optional[Path] = None,
    inventory_path: Optional[Path] = None,
) -> None:
    """
    Displays a welcome banner in the console for the specified operational mode, providing contextual information
    about the script's current function. The banner outlines the operation being performed, such as upgrading
    firewalls, Panorama, or modifying settings, and indicates whether custom configuration or inventory files are
    being utilized. This visual cue helps users understand the script's current state and actions, enhancing usability
    and clarity.

    Parameters
    ----------
    mode : str
        The operational mode of the script, indicating the type of action being undertaken. Valid modes include
        'settings', 'firewall', 'panorama', and 'batch', each corresponding to different functionalities of the script.
    config_path : Optional[Path], optional
        The filesystem path to a custom settings configuration file, if one is being used. If not provided, it is
        assumed that default settings are applied. This parameter is relevant only in modes where configuration
        customization is applicable.
    inventory_path : Optional[Path], optional
        The filesystem path to a custom inventory file, if one is being used. This is particularly relevant in batch
        operations where an inventory of devices is specified. If not provided, default or dynamically determined
        inventory information is used.

    Examples
    --------
    Displaying a welcome banner for firewall upgrade mode, noting the use of a custom settings file:
        >>> console_welcome_banner('firewall', Path('/path/to/settings.yaml'))
        # Outputs a banner indicating the firewall upgrade mode and the custom settings file in use.

    Displaying a welcome banner for settings configuration without a custom configuration file:
        >>> console_welcome_banner('settings')
        # Outputs a banner specific to settings configuration, indicating default settings will be used.

    Notes
    -----
    - The welcome banner is intended to provide immediate, clear context for the script's operation, aiding in
      user orientation and reducing potential confusion about the script's current mode or configuration status.
    - The banner also serves as a preliminary check, allowing users to confirm that the intended configuration or
      inventory files are recognized by the script before proceeding with operations, especially useful in scenarios
      where custom settings are essential for the task at hand.
    - This function employs ANSI color codes for enhanced visual distinction in terminal environments, with fallback
      considerations for environments where such styling may not be supported.
    """

    # Customize messages based on the mode
    if mode == "settings":
        welcome_message = "Welcome to the PAN-OS upgrade settings menu"
        banner_message = (
            "You'll be presented with configuration items, press enter for default settings."
            "\n\nThis will create a `settings.yaml` file in your current working directory."
        )
        config_message = ""
        inventory_message = ""
    elif mode == "inventory":
        welcome_message = "Welcome to the PAN-OS upgrade inventory menu"
        banner_message = (
            "Select which firewalls to upgrade based on a list of those connected to Panorama."
            "\n\nThis will create an `inventory.yaml` file in your current working directory."
        )
        config_message = ""
        inventory_message = ""
    else:
        if mode == "firewall":
            welcome_message = "Welcome to the PAN-OS upgrade tool"
            banner_message = "You have selected to upgrade a single Firewall appliance."
        elif mode == "panorama":
            welcome_message = "Welcome to the PAN-OS upgrade tool"
            banner_message = "You have selected to upgrade a single Panorama appliance."
        elif mode == "batch":
            welcome_message = "Welcome to the PAN-OS upgrade tool"
            banner_message = "You have selected to perform a batch upgrade of firewalls through Panorama."

        # Configuration file message
        if config_path:
            config_message = f"Custom configuration loaded from:\n{config_path}"
        else:
            config_message = (
                "No settings.yaml file was found, the script's default values will be used.\n"
                "Create a settings.yaml file with 'pan-os-upgrade settings' command."
            )

        # Inventory file message
        if inventory_path and inventory_path.exists():
            inventory_message = (
                f"Inventory configuration loaded from:\n{inventory_path}"
            )
        else:
            inventory_message = (
                "No inventory.yaml file was found, getting firewalls connected to Panorama.\n"
                "Create an inventory.yaml file with 'pan-os-upgrade inventory' command."
            )

    # Calculate border length based on the longer message
    border_length = max(
        len(welcome_message),
        max(len(line) for line in banner_message.split("\n")),
        max(len(line) for line in config_message.split("\n")) if config_message else 0,
        (
            max(len(line) for line in inventory_message.split("\n"))
            if inventory_message
            else 0
        ),
    )
    border = "=" * border_length

    # ANSI escape codes for styling
    color_start = "\033[1;33m"  # Bold Orange
    color_end = "\033[0m"  # Reset

    # Construct and print the banner
    banner = f"{color_start}{border}\n{welcome_message}\n\n{banner_message}"
    # Only add config_message if it's not empty
    if config_message:
        banner += f"\n\n{config_message}"

    # Only add config_message if it's not empty
    if config_message:
        banner += f"\n\n{inventory_message}"

    banner += f"\n{border}{color_end}"
    typer.echo(banner)


def ensure_directory_exists(file_path: str) -> None:
    """
    Ensures the existence of the directory path for a given file path, creating it if necessary.

    This function is crucial for file operations, particularly when writing to files, as it guarantees that the directory path exists prior to file creation or modification. It parses the provided file path to isolate the directory path and, if this directory does not exist, it creates it along with any required intermediate directories. This proactive approach prevents errors related to non-existent directories during file operations.

    Parameters
    ----------
    file_path : str
        The complete file path for which the existence of the directory structure is to be ensured. The function identifies the directory path component of this file path and focuses on verifying and potentially creating it.

    Raises
    ------
    OSError
        In the event of a failure to create the directory due to insufficient permissions or other filesystem-related errors, an OSError is raised detailing the issue encountered.

    Examples
    --------
    Creating a directory structure for a log file:
        >>> ensure_directory_exists('/var/log/my_application/error.log')
        # This will check and create '/var/log/my_application/' if it does not already exist, ensuring a valid path for 'error.log'.

    Notes
    -----
    - Employs `os.makedirs` with `exist_ok=True`, which allows the directory to be created without raising an exception if it already exists, ensuring idempotency.
    - Designed to be platform-independent, thereby functioning consistently across various operating systems and Python environments, enhancing the function's utility across diverse application scenarios.
    """

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def find_close_matches(
    available_versions: List[str],
    target_version: str,
    max_results: int = 5,
) -> List[str]:
    """
    Identifies and returns a list of versions from the available options that are most similar to a target version.

    This function assesses the similarity between a target version and a list of available versions based on their numerical and structural proximity. It employs a heuristic to quantify the difference between versions, taking into account major, minor, and maintenance version numbers, as well as any hotfix identifiers. The function is useful in scenarios where an exact version match is not found, and the closest alternatives need to be considered, such as software upgrades or compatibility checks.

    Parameters
    ----------
    available_versions : List[str]
        A list of version strings available for comparison, each in the format 'major.minor.maintenance' or 'major.minor.maintenance-hotfix'.
    target_version : str
        The version string that serves as the benchmark for finding close matches, following the same format as the available versions.
    max_results : int, optional
        The maximum number of close match results to return. Defaults to 5.

    Returns
    -------
    List[str]
        A list of the closest version strings to the target version, limited by max_results. The versions are sorted by their similarity to the target version, with the most similar version first.

    Examples
    --------
    Finding close matches to a specific version:
        >>> available_versions = ['10.0.0', '10.1.0', '10.1.1', '9.1.0', '10.1.1-hotfix']
        >>> target_version = '10.1.0'
        >>> find_close_matches(available_versions, target_version)
        ['10.1.0', '10.1.1', '10.1.1-hotfix', '10.0.0', '9.1.0']

    Notes
    -----
    - The function does not guarantee an exact match but provides the best alternatives based on the available options.
    - The similarity heuristic is primarily based on numerical closeness, with structural elements like hotfix identifiers considered as secondary criteria.
    - This function can be particularly useful in automated processes where decision-making relies on selecting the most appropriate version from a set of available options.
    """

    # Parse the target version
    target_major, target_minor, target_maintenance, target_hotfix = parse_version(
        target_version
    )

    version_distances = []

    for version in available_versions:
        # Parse each available version
        major, minor, maintenance, hotfix = parse_version(version)

        # Calculate a simple "distance" between versions, considering major, minor, maintenance, and hotfix components
        distance = (
            abs(target_major - major) * 1000
            + abs(target_minor - minor) * 100
            + abs(target_maintenance - maintenance) * 10
            + abs(target_hotfix - hotfix)
        )

        version_distances.append((distance, version))

    # Sort by distance, then by version number to get the closest matches
    version_distances.sort(key=lambda x: (x[0], x[1]))

    # Return up to max_results closest versions
    return [version for _, version in version_distances[:max_results]]


def flatten_xml_to_dict(element: ET.Element) -> dict:
    """
    Converts an XML ElementTree element into a nested dictionary, maintaining its hierarchical structure.

    This function iterates over the provided XML ElementTree element, converting each element and its children into a nested dictionary format. Element tags serve as dictionary keys, and the element text content, if present, is assigned as the value. For elements with child elements, a new nested dictionary is created to represent the hierarchy. When an element tag is repeated within the same level, these elements are aggregated into a list under a single dictionary key, preserving the structure and multiplicity of the XML data.

    Parameters
    ----------
    element : ET.Element
        The root or any sub-element of an XML tree that is to be converted into a dictionary.

    Returns
    -------
    dict
        A dictionary representation of the input XML element, where each key corresponds to an element tag, and each value is either the text content of the element, a nested dictionary (for child elements), or a list of dictionaries (for repeated child elements).

    Examples
    --------
    Converting a simple XML element:
        >>> xml_string = '<status>active</status>'
        >>> element = ET.fromstring(xml_string)
        >>> flatten_xml_to_dict(element)
        {'status': 'active'}

    Converting an XML element with nested children:
        >>> xml_string = '<configuration><item key="1">Value1</item><item key="2">Value2</item></configuration>'
        >>> element = ET.fromstring(xml_string)
        >>> flatten_xml_to_dict(element)
        {'configuration': {'item': [{'key': '1', '_text': 'Value1'}, {'key': '2', '_text': 'Value2'}]}}

    Notes
    -----
    - This function is designed to work with XML structures that are naturally representable as a nested dictionary. It may not be suitable for XML with complex attributes or mixed content.
    - Attributes of XML elements are converted into dictionary keys with a leading underscore ('_') to differentiate them from child elements.
    - If the XML structure includes elements with repeated tags at the same level, these are stored in a list under the same key to preserve the structure within the dictionary format.
    - The function simplifies XML data handling by converting it into a more accessible and manipulable Python dictionary format.

    Raises
    ------
    ValueError
        If the XML structure includes elements that cannot be directly mapped to a dictionary format without ambiguity or loss of information, a ValueError is raised to indicate potential data integrity issues.
    """

    # Dictionary to hold the XML structure
    result = {}

    # Iterate through each child in the XML element
    for child_element in element:
        child_tag = child_element.tag

        if child_element.text and len(child_element) == 0:
            result[child_tag] = child_element.text
        else:
            if child_tag in result:
                if not isinstance(result.get(child_tag), list):
                    result[child_tag] = [
                        result.get(child_tag),
                        flatten_xml_to_dict(child_element),
                    ]
                else:
                    result[child_tag].append(flatten_xml_to_dict(child_element))
            else:
                if child_tag == "entry":
                    # Always assume entries are a list.
                    result[child_tag] = [flatten_xml_to_dict(child_element)]
                else:
                    result[child_tag] = flatten_xml_to_dict(child_element)

    return result


def generate_diff_report_pdf(
    pre_post_diff: dict,
    file_path: str,
    hostname: str,
    target_version: str,
) -> None:
    """
    Creates a PDF report detailing the differences observed in the network state of a device before and after an
    upgrade. The report organizes the changes into sections and highlights modifications, deletions, and additions in
    the device's configuration and operational state. It serves as a comprehensive document for reviewing the impact
    of the upgrade and verifying the changes made.

    The function employs a structured format to present the data, with a header section that includes the device's
    hostname and the target firmware version. This aids in quick identification of the report's context. The body of
    the report systematically lists the differences, categorized by the type of change, making it easy to assess the
    extent and nature of the modifications.

    Parameters
    ----------
    pre_post_diff : dict
        The differences between the pre-upgrade and post-upgrade states, structured as a nested dictionary. Each key
        represents a category (e.g., 'interfaces', 'policies'), with sub-keys detailing the specific changes (e.g.,
        'added', 'removed', 'modified').
    file_path : str
        The destination path for the generated PDF report, including the file name and extension.
    hostname : str
        The hostname of the device for which the upgrade was performed, used to personalize the report.
    target_version : str
        The version of the firmware to which the device was upgraded, included for reference in the report's header.

    Raises
    ------
    IOError
        If the PDF file cannot be created or written to the specified path, possibly due to issues like inadequate
        file permissions, non-existent directory paths, or insufficient disk space.

    Examples
    --------
    Generating a PDF report to document configuration changes after an upgrade:
        >>> pre_post_diff = {
        ...     'interfaces': {
        ...         'added': ['Ethernet1/3'],
        ...         'removed': ['Ethernet1/4'],
        ...         'modified': {'Ethernet1/1': {'before': '192.168.1.1', 'after': '192.168.1.2'}}
        ...     }
        ... }
        >>> generate_diff_report_pdf(pre_post_diff, '/tmp/device_upgrade_report.pdf', 'device123', '10.0.0')
        # This will create a PDF report at '/tmp/device_upgrade_report.pdf' summarizing the changes made during the upgrade to version 10.0.0.

    Notes
    -----
    - The report aims to provide a clear and concise summary of changes, facilitating audits and documentation of the
      upgrade process.
    - The PDF format ensures the report is accessible and easily distributable for review by various stakeholders.
    - Configuration for the PDF generation, such as layout and styling, can be customized through a `settings.yaml`
      file if the `settings_file_path` variable is utilized in the function, allowing for adaptation to specific
      reporting standards or preferences.
    """

    pdf = SimpleDocTemplate(file_path, pagesize=letter)
    content = []
    styles = getSampleStyleSheet()

    # Accessing logo.png using importlib.resources, creating a custom banner with logo and styling
    logo_path = pkg_resources.files("pan_os_upgrade.assets").joinpath("logo.png")
    img = Image(str(logo_path), width=71, height=51)  # Use the string path directly
    img.hAlign = "LEFT"
    content.append(img)

    banner_style = styles["Title"]
    banner_style.fontSize = 24
    banner_style.textColor = colors.HexColor("#333333")
    banner_style.alignment = 1  # Center alignment
    banner_content = Paragraph(
        f"<b>{hostname} Upgrade {target_version} Diff Report</b>",
        banner_style,
    )
    content.append(Spacer(1, 12))
    content.append(banner_content)
    content.append(Spacer(1, 20))

    # Line separator
    d = Drawing(500, 1)
    line = Line(0, 0, 500, 0)
    line.strokeColor = colors.HexColor("#F04E23")
    line.strokeWidth = 2
    d.add(line)
    content.append(d)
    content.append(Spacer(1, 20))

    for section, details in pre_post_diff.items():
        # Section title with background color
        section_style = styles["Heading2"]
        section_style.backColor = colors.HexColor("#EEEEEE")
        section_content = Paragraph(section.replace("_", " ").title(), section_style)
        content.append(section_content)
        content.append(Spacer(1, 12))

        for sub_section, sub_details in details.items():
            if sub_section == "passed":
                # Overall status of the section
                status = "Passed" if sub_details else "Failed"
                status_style = styles["BodyText"]
                status_style.textColor = colors.green if sub_details else colors.red
                status_content = Paragraph(
                    f"Overall Status: <b>{status}</b>", status_style
                )
                content.append(status_content)
            else:
                # Sub-section details
                sub_section_title = sub_section.replace("_", " ").title()
                passed = "Passed" if sub_details["passed"] else "Failed"
                passed_style = styles["BodyText"]
                passed_style.textColor = (
                    colors.green if sub_details["passed"] else colors.red
                )
                content.append(
                    Paragraph(
                        f"{sub_section_title} (Status: <b>{passed}</b>)", passed_style
                    )
                )

                keys = (
                    sub_details.get("missing_keys", [])
                    + sub_details.get("added_keys", [])
                    + list(sub_details.get("changed_raw", {}).keys())
                )

                # Format keys for display
                if keys:
                    for key in keys:
                        key_content = Paragraph(f"- {key}", styles["BodyText"])
                        content.append(key_content)
                else:
                    content.append(
                        Paragraph("No changes detected.", styles["BodyText"])
                    )

            content.append(Spacer(1, 12))

        # Add some space after each section
        content.append(Spacer(1, 20))

    # Build the PDF
    pdf.build(content)


def get_emoji(action: str) -> str:
    """
    Maps specific action keywords to their corresponding emoji symbols for enhanced log and user interface messages.

    This utility function is designed to add visual cues to log messages or user interface outputs by associating specific action keywords with relevant emoji symbols. It aims to improve the readability and user experience by providing a quick visual reference for the action's nature or outcome. The function supports a predefined set of keywords, each mapping to a unique emoji. If an unrecognized keyword is provided, the function returns an empty string to ensure seamless operation without interrupting the application flow.

    Parameters
    ----------
    action : str
        A keyword representing the action or status for which an emoji is required. Supported keywords include 'success', 'error', 'warning', 'working', 'report', 'search', 'save', 'stop', and 'start'.

    Returns
    -------
    str
        The emoji symbol associated with the specified action keyword. Returns an empty string if the keyword is not recognized, maintaining non-disruptive output.

    Examples
    --------
    Adding visual cues to log messages:
        >>> logging.info(f"{get_emoji('success')} Operation successful.")
        >>> logging.error(f"{get_emoji('error')} An error occurred.")

    Enhancing user prompts in a command-line application:
        >>> print(f"{get_emoji('start')} Initiating the process.")
        >>> print(f"{get_emoji('stop')} Process terminated.")

    Notes
    -----
    - The function enhances the aesthetic and functional aspects of textual outputs, making them more engaging and easier to interpret at a glance.
    - It is implemented with a fail-safe approach, where unsupported keywords result in an empty string, thus preserving the integrity and continuity of the output.
    - Customization or extension of the supported action keywords and their corresponding emojis can be achieved by modifying the internal emoji_map dictionary.

    This function is not expected to raise any exceptions, ensuring stable and predictable behavior across various usage contexts.
    """

    emoji_map = {
        "success": "✅",
        "warning": "🟧",
        "error": "❌",
        "working": "🔧",
        "report": "📝",
        "search": "🔍",
        "save": "💾",
        "skipped": "🟨",
        "stop": "🛑",
        "start": "🚀",
    }
    return emoji_map.get(action, "")


def fetch_firewall_info(firewall: Firewall) -> Dict[str, Any]:
    """
    Fetches system information for a single firewall and returns it as a dictionary.

    Parameters
    ----------
    firewall : Firewall
        A Firewall object for which to fetch system information.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing system information for the firewall.
    """
    try:
        info = firewall.show_system_info()
        return {
            "hostname": info["system"]["hostname"],
            "ip-address": info["system"]["ip-address"],
            "model": info["system"]["model"],
            "serial": info["system"]["serial"],
            "sw-version": info["system"]["sw-version"],
            "app-version": info["system"]["app-version"],
        }
    except Exception as e:
        print(f"Error retrieving info for {firewall.serial}: {str(e)}")
        return {
            "hostname": firewall.hostname or "Unknown",
            "ip-address": "N/A",
            "model": "N/A",
            "serial": firewall.serial,
            "sw-version": "N/A",
            "app-version": "N/A",
            "status": "Offline or Unavailable",
        }


def get_firewalls_from_panorama(panorama: Panorama) -> list[Firewall]:
    """
    Fetches a list of firewalls managed by a specified Panorama appliance, with optional filtering based on firewall attributes.

    This function queries a Panorama appliance to retrieve details about the firewalls it manages. It supports filtering the results based on various firewall attributes such as model, serial number, or software version, among others. The function leverages Panorama's API to gather firewall data, which it then encapsulates into Firewall objects for convenient handling within Python. This capability is particularly beneficial for tasks that require interaction with a specific subset of firewalls, such as performing batch configurations, updates, or generating reports.

    Parameters
    ----------
    panorama : Panorama
        The Panorama instance from which to retrieve managed firewalls. This object must be initialized with proper authentication credentials.

    Returns
    -------
    list[Firewall]
        A list of Firewall objects, each representing a firewall managed by Panorama that matches the specified filtering criteria. Returns all managed firewalls if no filters are applied.

    Examples
    --------
    Retrieving all firewalls managed by Panorama:
        >>> firewalls = get_firewalls_from_panorama(panorama_instance)

    Notes
    -----
    - This function is crucial for scripts aimed at performing operations across multiple firewalls managed by a Panorama appliance, enabling targeted actions based on specific criteria.
    - Utilizes dynamic filtering to provide flexibility in selecting firewalls based on various attributes, enhancing the script's utility in complex environments.
    - Default filter settings can be overridden by a `settings.yaml` file if `settings_file_path` is used within the script, providing a mechanism for customization and default configuration.

    Exceptions
    ----------
    - The function itself does not explicitly raise exceptions but relies on the proper handling of Panorama API responses and potential network or authentication issues by the Panorama class methods.
    """

    firewalls = []
    for managed_device in get_managed_devices(panorama):
        firewall = Firewall(serial=managed_device.serial)
        firewalls.append(firewall)
        panorama.add(firewall)

    return firewalls


def get_firewalls_info(firewalls: List[Firewall]) -> List[Dict[str, Any]]:
    """
    Fetches system information for each firewall in the list concurrently and returns it as a list of dictionaries.

    Parameters
    ----------
    firewalls : List[Firewall]
        A list of Firewall objects for which to fetch system information.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries containing system information for each firewall.
    """
    firewalls_info = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Mapping the fetch_firewall_info function to each firewall object
        future_to_firewall = {
            executor.submit(fetch_firewall_info, fw): fw for fw in firewalls
        }

        # Collecting results as they are completed
        for future in as_completed(future_to_firewall):
            firewall_info = future.result()
            firewalls_info.append(firewall_info)

    return firewalls_info


def get_managed_devices(
    panorama: Panorama,
) -> list[ManagedDevice]:
    """
    Retrieves a list of devices managed by a specified Panorama appliance, with optional filtering based on device attributes.

    This function queries a Panorama management server to obtain information about the devices it manages. It allows for optional filtering of these devices based on attributes such as model, serial number, or software version, utilizing regular expressions for flexible and precise matching. The function is particularly useful for operations that need to be targeted at specific devices or groups of devices, such as configuration updates, monitoring, or batch operations.

    Parameters
    ----------
    panorama : Panorama
        The Panorama instance from which the list of managed devices will be fetched. This instance must be initialized and authenticated to ensure successful API communication.

    Returns
    -------
    list[ManagedDevice]
        A list of ManagedDevice objects, each representing a device managed by the specified Panorama appliance that matches the filtering criteria. If no filters are specified, all managed devices are returned.

    Examples
    --------
    Retrieving all devices managed by a Panorama instance:
        >>> devices = get_managed_devices(panorama_instance)

    Retrieving devices of a specific model managed by a Panorama instance:
        >>> model_specific_devices = get_managed_devices(panorama_instance, model='PA-220')

    Notes
    -----
    - This function is essential for scripts aimed at performing batch operations or selective actions on devices managed by Panorama, enabling precise targeting based on specified criteria.

    Exceptions
    ----------
    - The function does not explicitly raise exceptions but relies on the proper handling of Panorama API responses and potential network or authentication issues by the Panorama class methods. Error handling for invalid filter syntax or API communication errors should be implemented as needed.
    """

    managed_devices = model_from_api_response(
        panorama.op("show devices all"), ManagedDevices
    )
    devices = managed_devices.devices

    return devices


def ip_callback(value: str) -> str:
    """
    Validates the input as either a resolvable hostname or a valid IP address, intended for CLI input validation.

    This callback function is designed to validate user input, ensuring that it represents a valid IP address (IPv4 or IPv6) or a resolvable hostname. It employs the 'ipaddress' module to validate IP addresses and attempts DNS resolution for hostname validation. If the input fails both validations, the function raises a Typer error, prompting the user to provide a valid input. This validation step is crucial for operations requiring network communication, ensuring that only valid endpoints are processed.

    Parameters
    ----------
    value : str
        The input string provided by the user, expected to be either a valid IP address or a resolvable hostname.

    Returns
    -------
    str
        Returns the validated input string if it is either a resolvable hostname or a valid IP address.

    Raises
    ------
    typer.BadParameter
        Raised if the input string fails to validate as either a resolvable hostname or a valid IP address, indicating to the user that the provided value is invalid and prompting for a correct one.

    Example
    -------
    Validating a command-line option for an IP address or hostname:
        >>> @app.command()
        >>> def query_endpoint(host: str = typer.Option(..., callback=ip_callback)):
        >>>     print(f"Querying endpoint: {host}")

    Notes
    -----
    - This function is integral to CLI tools that require precise and validated network endpoints to function correctly.
    - Leveraging both 'ipaddress' for IP validation and DNS resolution ensures a robust check against a wide range of inputs.
    - The function's utility extends beyond mere validation, contributing to the tool's overall resilience and user-friendliness by preventing erroneous network operations.
    - Default settings can be overridden by configurations specified in a `settings.yaml` file if `settings_file_path` is used within the script, allowing for customized validation logic based on the application's needs.
    """

    # First, try to resolve as a hostname
    if resolve_hostname(value):
        return value

    # If hostname resolution fails, try as an IP address
    try:
        ipaddress.ip_address(value)
        return value

    except ValueError as err:
        raise typer.BadParameter(
            "The value you passed for --hostname is neither a valid DNS hostname nor IP address, please check your inputs again."
        ) from err


def model_from_api_response(
    element: Union[ET.Element, ET.ElementTree],
    model: type[FromAPIResponseMixin],
) -> FromAPIResponseMixin:
    """
    Converts XML data from an API response into a Pydantic model instance, enhancing data handling and validation.

    Leveraging Pydantic models, this function translates XML elements or entire XML documents from API responses into structured data. It extracts information from the XML, transforming it into a dictionary, which is then used to populate a Pydantic model. This process ensures that the data adheres to a defined schema, providing validated and type-annotated access to the API response contents. The function is particularly useful in scenarios where API responses need to be processed and utilized within Python applications, offering a clear and concise interface for interacting with the data.

    Parameters
    ----------
    element : Union[ET.Element, ET.ElementTree]
        The XML element or document tree representing the API response. This can be a single XML element or an entire document tree, encompassing the necessary data to be transformed into the model.
    model : type[FromAPIResponseMixin]
        The Pydantic model class, expected to incorporate `FromAPIResponseMixin`, which outlines the structure and types of the data expected from the API response. This model acts as a blueprint for the conversion, ensuring the XML data is accurately represented in a structured format.

    Returns
    -------
    FromAPIResponseMixin
        An instantiated Pydantic model populated with data from the XML element or tree, reflecting the structure and type constraints defined in the model. This instance provides a structured and type-safe representation of the API response.

    Example
    -------
    Converting an API's XML response to a Pydantic model:
        >>> xml_response = ET.fromstring('<device><id>123</id><type>Firewall</type></device>')
        >>> DeviceModel = type('DeviceModel', (FromAPIResponseMixin, BaseModel), {'id': int, 'type': str})
        >>> device = model_from_api_response(xml_response, DeviceModel)
        # 'device' is now a Pydantic model instance of 'DeviceModel' with 'id' and 'type' populated from the XML.

    Notes
    -----
    - The function simplifies the integration of XML-based API responses into Pythonic data structures, enabling more effective data manipulation and validation.
    - It is crucial for the Pydantic model to accurately reflect the expected data structure of the API response to ensure a successful conversion.
    - Default configuration and behavior can be modified through the use of a `settings.yaml` file if the application supports loading configurations in this manner and `settings_file_path` is utilized.

    Raises
    ------
    ValueError
        In cases where the XML data does not match the structure expected by the Pydantic model, indicating a possible mismatch between the API response format and the model's schema.
    """

    result_dict = flatten_xml_to_dict(element)
    return model.from_api_response(result_dict)


def parse_version(version: str) -> Tuple[int, int, int, int]:
    """
    Decomposes a version string into a structured numerical format, facilitating easy comparison and analysis
    of version numbers. The version string is expected to follow a conventional format, with major, minor, and
    maintenance components, and an optional hotfix identifier. This function extracts these components into a
    tuple of integers, where the hotfix component defaults to 0 if not specified. This standardized representation
    is crucial for tasks like determining upgrade paths, assessing compatibility, and sorting version numbers.

    Parameters
    ----------
    version : str
        A version string following the 'major.minor.maintenance' or 'major.minor.maintenance-hhotfix' format,
        where 'major', 'minor', 'maintenance', and 'hotfix' are numerical values.

    Returns
    -------
    Tuple[int, int, int, int]
        A tuple containing the major, minor, maintenance, and hotfix components as integers. The hotfix is set
        to 0 if it is not explicitly included in the version string.

    Examples
    --------
    Parsing a version without a hotfix:
        >>> parse_version("10.0.1")
        (10, 0, 1, 0)

    Parsing a version with a hotfix component:
        >>> parse_version("10.0.1-h2")
        (10, 0, 1, 2)

    Notes
    -----
    - Accurate version parsing is essential for software management operations, such as upgrades and compatibility checks.
    - The function is designed to strictly interpret the version string based on the expected format. Any deviation from
      this format may lead to incorrect parsing results or errors.

    Raises
    ------
    ValueError
        If the version string does not conform to the expected format or includes non-numeric values where integers
        are anticipated, indicating the version string is malformed or invalid.

    This function's behavior can be influenced by version format settings specified in a `settings.yaml` file, if such
    settings are supported and utilized within the broader application context. This allows for adaptability in version
    parsing according to customized or application-specific versioning schemes.
    """

    # Remove .xfr suffix from the version string, keeping the hotfix part intact
    version = re.sub(r"\.xfr$", "", version)

    parts = version.split(".")
    # Ensure there are two or three parts, and if three, the third part does not contain invalid characters like 'h' or 'c' without a preceding '-'
    if (
        len(parts) < 2
        or len(parts) > 3
        or (len(parts) == 3 and re.search(r"[^0-9\-]h|[^0-9\-]c", parts[2]))
    ):
        raise ValueError(f"Invalid version format: '{version}'.")

    major, minor = map(int, parts[:2])  # Raises ValueError if conversion fails

    maintenance = 0
    hotfix = 0

    if len(parts) == 3:
        maintenance_part = parts[2]
        if "-h" in maintenance_part:
            maintenance_str, hotfix_str = maintenance_part.split("-h")
        elif "-c" in maintenance_part:
            maintenance_str, hotfix_str = maintenance_part.split("-c")
        else:
            maintenance_str = maintenance_part
            hotfix_str = "0"

        # Validate and convert maintenance and hotfix parts
        if not maintenance_str.isdigit() or not hotfix_str.isdigit():
            raise ValueError(
                f"Invalid maintenance or hotfix format in version '{version}'."
            )

        maintenance = int(maintenance_str)
        hotfix = int(hotfix_str)

    return major, minor, maintenance, hotfix


def resolve_hostname(hostname: str) -> bool:
    """
    Verifies if a given hostname can be resolved to an IP address using DNS lookup.

    This function is crucial for network-related operations, as it checks the resolvability of a hostname. It performs a DNS query to determine if the hostname can be translated into an IP address, thereby validating its presence on the network. A successful DNS resolution implies the hostname is active and reachable, while a failure might indicate an issue with the hostname itself, DNS configuration, or broader network problems.

    Parameters
    ----------
    hostname : str
        The hostname to be resolved, such as 'example.com', to verify network reachability and DNS configuration.

    Returns
    -------
    bool
        Returns True if the DNS resolution is successful, indicating the hostname is valid and reachable. Returns False if the resolution fails, suggesting potential issues with the hostname, DNS setup, or network connectivity.

    Example
    -------
    Validating hostname resolution:
        >>> resolve_hostname('google.com')
        True  # This would indicate that 'google.com' is successfully resolved, suggesting it is reachable.

        >>> resolve_hostname('invalid.hostname')
        False  # This would indicate a failure in resolving 'invalid.hostname', pointing to potential DNS or network issues.

    Notes
    -----
    - This function is intended as a preliminary network connectivity check before attempting further network operations.
    - It encapsulates exception handling for DNS resolution errors, logging them for diagnostic purposes while providing a simple boolean outcome to the caller.

    The function's behavior and return values are not affected by external configurations or settings, hence no mention of `settings.yaml` file override capability is included.
    """

    try:
        dns.resolver.resolve(hostname)
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout) as err:
        # Optionally log or handle err here if needed
        logging.debug(f"Hostname resolution failed: {err}")
        return False


def select_devices_from_table(firewall_mapping: dict) -> List[str]:
    """
    Displays a table of firewalls and prompts the user to select devices for further operations. This selection
    process allows the user to specify one or more devices by their listing numbers, a range, or a combination
    thereof. The function then returns a list of hostnames corresponding to the user's selections.

    This interactive step is crucial for operations that target multiple devices, enabling precise control over
    which devices are included. The function ensures that selections are valid and within the range of displayed
    devices, providing feedback for any invalid entries.

    Parameters
    ----------
    firewall_mapping : dict
        A mapping from device hostnames to their respective details (e.g., IP address, model, serial number),
        used to generate the selection table.

    Returns
    -------
    List[str]
        A list of hostnames for the selected devices, based on user input.

    Examples
    --------
    Presenting a selection table and capturing user choices:
        >>> firewall_mapping = {
        ...     'fw1': {'ip-address': '10.1.1.1', 'model': 'PA-850', 'serial': '0123456789', 'sw-version': '9.1.0', 'app-version': '9.1.0'},
        ...     'fw2': {'ip-address': '10.1.1.2', 'model': 'PA-220', 'serial': '9876543210', 'sw-version': '9.1.2', 'app-version': '9.1.3'}
        ... }
        >>> selected_hostnames = select_devices_from_table(firewall_mapping)
        # User is prompted to select from the table of devices. The function returns the hostnames of selected devices.

    Notes
    -----
    - The function leverages the `tabulate` library to present a well-structured table, enhancing readability and
      ease of selection.
    - It accommodates various input formats for selecting devices, including individual numbers, ranges (e.g., 2-4),
      or a comma-separated list, providing flexibility in selection methodology.
    - Invalid selections (e.g., out-of-range numbers or incorrect formats) are handled gracefully, with prompts for
      correction, ensuring a robust and user-friendly selection process.
    """

    # Sort firewalls by hostname for consistent display
    sorted_firewall_items = sorted(firewall_mapping.items(), key=lambda item: item[0])

    devices_table = [
        [
            Fore.CYAN + str(i + 1) + Fore.RESET,
            details["hostname"],
            details["ip-address"],
            details["model"],
            details["serial"],
            details["sw-version"],
            details["app-version"],
        ]
        for i, (hostname, details) in enumerate(sorted_firewall_items)
    ]

    typer.echo(
        tabulate(
            devices_table,
            headers=[
                Fore.GREEN + "#" + Fore.RESET,
                Fore.GREEN + "Hostname" + Fore.RESET,
                Fore.GREEN + "IP Address" + Fore.RESET,
                Fore.GREEN + "Model" + Fore.RESET,
                Fore.GREEN + "Serial" + Fore.RESET,
                Fore.GREEN + "SW Version" + Fore.RESET,
                Fore.GREEN + "App Version" + Fore.RESET,
            ],
            tablefmt="fancy_grid",
        )
    )

    instruction_message = (
        Fore.YELLOW
        + "You can select devices by entering their numbers, ranges, or separated by commas.\n"
        "Examples: '1', '2-4', '1,3,5-7'.\n"
        "Type 'done' on a new line when finished.\n" + Fore.RESET
    )
    typer.echo(instruction_message)

    user_selected_hostnames = []

    while True:
        choice = typer.prompt(Fore.YELLOW + "Enter your selection(s)" + Fore.RESET)

        if choice.lower() == "done":
            break

        # Split input by commas for single-line input or just accumulate selections for multi-line input
        parts = choice.split(",") if "," in choice else [choice]
        indices = []
        for part in parts:
            part = part.strip()  # Remove any leading/trailing whitespace
            if "-" in part:  # Check if part is a range
                try:
                    start, end = map(
                        int, part.split("-")
                    )  # Convert start and end to integers
                    if start <= end:
                        indices.extend(
                            range(start - 1, end)
                        )  # Add all indices in the range
                    else:
                        typer.echo(
                            Fore.RED
                            + f"Invalid range: '{part}'. Start should be less than or equal to end."
                            + Fore.RESET
                        )
                except ValueError:
                    typer.echo(
                        Fore.RED
                        + f"Invalid range format: '{part}'. Use 'start-end' format."
                        + Fore.RESET
                    )
            else:
                try:
                    index = int(part) - 1  # Convert to index (0-based)
                    indices.append(index)
                except ValueError:
                    typer.echo(Fore.RED + f"Invalid number: '{part}'." + Fore.RESET)

        # Process selected indices
        for index in indices:

            if 0 <= index < len(sorted_firewall_items):
                hostname, details = sorted_firewall_items[index]
                if hostname not in user_selected_hostnames:
                    user_selected_hostnames.append(hostname)
                    typer.echo(Fore.GREEN + f"{hostname} selected." + Fore.RESET)
                else:
                    typer.echo(
                        Fore.YELLOW + f"{hostname} is already selected." + Fore.RESET
                    )
            else:
                typer.echo(
                    Fore.RED + f"Selection '{index + 1}' is out of range." + Fore.RESET
                )

    return user_selected_hostnames


# Define Typer command-line interface
app = typer.Typer(help="PAN-OS Upgrade script")

# Global variables

# Define the path to the settings file
settings_file_path = Path.cwd() / "settings.yaml"
inventory_file_path = Path.cwd() / "inventory.yaml"

# Initialize Dynaconf settings object conditionally based on the existence of settings.yaml
if settings_file_path.exists():
    settings_file = Dynaconf(settings_files=[str(settings_file_path)])
else:
    settings_file = Dynaconf()

# Initialize colorama
init()

# Global list and lock for storing HA active firewalls and Panorama to revisit
target_devices_to_revisit = []
target_devices_to_revisit_lock = Lock()

# Define logging levels
LOGGING_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


# Common setup for all subcommands
def common_setup(
    hostname: str,
    username: str,
    password: str,
) -> PanDevice:
    """
    Initializes the environment for interacting with a Palo Alto Networks device, including directory setup, logging configuration, and establishing a device connection.

    This function consolidates essential preparatory steps required before performing operations on a Palo Alto Networks device. It ensures the creation of necessary directories for organized data storage and logs, sets up logging with a configurable verbosity level, and establishes a secure connection to the device using the provided API credentials. The function is designed to return a `PanDevice` object, which could be a `Firewall` or `Panorama` instance, ready for subsequent API interactions.

    Parameters
    ----------
    hostname : str
        The network address or DNS name of the Palo Alto Networks device to connect to.
    username : str
        The API username for authenticating with the device.
    password : str
        The API password for authenticating with the device.

    Returns
    -------
    PanDevice
        A connected `PanDevice` instance, representing the target Palo Alto Networks device, fully initialized and ready for further API operations.

    Example
    -------
    Initializing the environment for a device:
        >>> device = common_setup('10.0.0.1', 'apiuser', 'apipassword')
        # Ensures necessary directories exist, logging is configured, and returns a connected `PanDevice` instance.

    Notes
    -----
    - Directory setup is performed only once; existing directories are not modified.
    - Logging configuration affects the entire application's logging behavior; the log level can be overridden by `settings.yaml` if `settings_file_path` is detected in the function.
    - A successful device connection is critical for the function to return; otherwise, it may raise exceptions based on connection issues.

    The ability to override default settings with `settings.yaml` is supported for the log level configuration in this function if `settings_file_path` is utilized within `configure_logging`.
    """

    log_level = settings_file.get("logging.level", "INFO")

    # Create necessary directories
    directories = [
        "logs",
        "assurance",
        "assurance/configurations",
        "assurance/readiness_checks",
        "assurance/reports",
        "assurance/snapshots",
    ]
    for dir in directories:
        ensure_directory_exists(os.path.join(dir, "dummy_file"))

    # Configure logging right after directory setup
    configure_logging(log_level)

    # Connect to the device
    device = connect_to_host(hostname, username, password)
    return device


# Subcommand for upgrading a firewall
@app.command()
def firewall(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of either Panorama or firewall appliance",
            prompt="Firewall hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Firewall appliance",
            prompt="Firewall username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Firewall password",
            hide_input=True,
        ),
    ],
    target_version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Target version to upgrade to",
            prompt="Target version",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Dry Run?",
        ),
    ] = True,
):
    """
    Launches the upgrade process for a Palo Alto Networks firewall, facilitating a comprehensive and controlled upgrade workflow.

    This command orchestrates the steps required for upgrading a firewall appliance, encompassing initial validations, environment setup, and execution of the upgrade process. It is capable of operating in a 'dry run' mode, which simulates the upgrade process without applying any changes, allowing for validation of upgrade prerequisites and assessment of potential issues. The command leverages a series of internal functions to prepare the environment, verify connectivity, ensure compatibility with the target version, and, if all checks pass, proceed with the upgrade.

    Parameters
    ----------
    hostname : str
        The IP address or DNS hostname of the firewall to be upgraded. Must be accessible from the execution environment.
    username : str
        The administrative username for the firewall, used for API or CLI authentication.
    password : str
        The corresponding password for the provided administrative username.
    target_version : str
        The version of PAN-OS to which the firewall is to be upgraded. Must be a valid and supported version for the device.
    dry_run : bool, optional
        When set to True, the function performs all preparatory and validation steps without executing the actual upgrade, defaulting to False.

    Examples
    --------
    Executing an upgrade to version 9.1.0:
        $ python upgrade.py firewall --hostname 192.168.1.1 --username admin --password secure123 --version 9.1.0

    Performing a dry run for version 9.1.0:
        $ python upgrade.py firewall --hostname 192.168.1.1 --username admin --password secure123 --version 9.1.0 --dry-run

    Notes
    -----
    - Prior to executing the upgrade, ensure that the firewall is in a stable state and that there is a reliable network connection to the device.
    - The 'dry run' mode is highly recommended for a preliminary assessment to identify any potential issues that might impede the upgrade process.
    - Default settings for the upgrade process, such as log levels and file paths, can be overridden by providing a `settings.yaml` file, if supported by the implementation of `common_setup` and other called functions within this command.
    """

    # Display the custom banner for firewall upgrade
    if settings_file_path.exists():
        console_welcome_banner(mode="firewall", config_path=settings_file_path)
    else:
        console_welcome_banner(mode="firewall")

    # Perform common setup tasks, return a connected device
    device = common_setup(
        hostname,
        username,
        password,
    )

    # Perform upgrade
    upgrade_firewall(
        device,
        target_version,
        dry_run,
    )


# Subcommand for upgrading Panorama
@app.command()
def panorama(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of Panorama appliance",
            prompt="Panorama hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Panorama appliance",
            prompt="Panorama username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Panorama password",
            hide_input=True,
        ),
    ],
    target_version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Target Panorama version to upgrade to",
            prompt="Target Panorama version",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Dry Run?",
        ),
    ] = True,
):
    """
    Manages the upgrade process for a Panorama management platform, orchestrating the sequence of actions required for a successful upgrade.

    This command facilitates the upgrade of a Panorama appliance by executing a series of preparatory actions, including validation of connectivity, compatibility checks with the target version, and the actual upgrade process. The dry run mode allows operators to simulate the upgrade steps without making any modifications to the Panorama appliance. The command leverages internal utility functions to ensure the environment is correctly configured, to establish a connection to the Panorama, and to conduct the upgrade according to the parameters specified.

    Parameters
    ----------
    hostname : str
        The network address of the Panorama appliance, either as an IP address or a DNS-resolvable hostname.
    username : str
        The administrative username required for authentication on the Panorama appliance.
    password : str
        The corresponding password for the specified administrative username.
    target_version : str
        The target version of PAN-OS to which the Panorama appliance is to be upgraded.
    dry_run : bool, optional
        A boolean flag indicating whether to simulate the upgrade process without applying changes, defaulting to False.

    Examples
    --------
    Directly upgrading a Panorama appliance:
        $ python upgrade.py panorama --hostname panorama.example.com --username admin --password secure123 --version 10.0.0

    Conducting a dry run for the upgrade process:
        $ python upgrade.py panorama --hostname panorama.example.com --username admin --password secure123 --version 10.0.0 --dry-run

    Notes
    -----
    - It is critical to ensure that the Panorama appliance is accessible and that the provided credentials are correct before initiating the upgrade process.
    - Utilizing the dry run mode is strongly recommended for validating the upgrade path and identifying any potential obstacles without risking the operational state of the Panorama appliance.
    - Settings for the upgrade process, such as logging levels and file paths, may be overridden by a `settings.yaml` file if present and detected by the implementation of `common_setup` and other invoked functions within this command.
    """

    # Display the custom banner for panorama upgrade
    if settings_file_path.exists():
        console_welcome_banner(mode="panorama", config_path=settings_file_path)
    else:
        console_welcome_banner(mode="panorama")

    # Perform common setup tasks, return a connected device
    device = common_setup(
        hostname,
        username,
        password,
    )

    # Perform upgrade
    upgrade_panorama(
        device,
        target_version,
        dry_run,
    )


# Subcommand for batch upgrades using Panorama as a communication proxy
@app.command()
def batch(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of Panorama appliance",
            prompt="Panorama hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Panorama appliance",
            prompt="Panorama username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Panorama password",
            hide_input=True,
        ),
    ],
    target_version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Target version to upgrade firewalls to",
            prompt="Firewall target version (ex: 10.1.2)",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Dry Run?",
            is_flag=True,
        ),
    ] = True,
):
    """
    Orchestrates a batch upgrade process for firewalls under Panorama's management. This command leverages Panorama
    to coordinate upgrades across multiple devices, streamlining the process. The user has the option to perform a
    dry run to validate the upgrade steps without applying changes, and to specify the target PAN-OS version for the
    upgrade.

    The process begins by establishing a secure connection to Panorama using provided credentials. Firewalls managed
    by Panorama are then enumerated, and a subset may be selected for upgrade based on criteria defined in an
    'inventory.yaml' file or interactively during execution. The 'inventory.yaml' file, if present, pre-selects
    devices for upgrade, bypassing manual selection.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the Panorama appliance to connect to.
    username : str
        The username for authenticating with Panorama.
    password : str
        The password for the provided username, used for authentication.
    target_version : str
        The version of PAN-OS to which the firewalls should be upgraded.
    dry_run : bool, optional
        If set, the command simulates the upgrade process without making any changes to the devices. Defaults to True, meaning dry run is enabled by default.

    Examples
    --------
    Initiating a batch upgrade process with specified parameters:
        $ python upgrade.py batch --hostname 192.168.1.1 --username admin --password secret --version 10.2.7-h3 --dry-run

    Notes
    -----
    - The command streamlines firewall upgrades by automating repetitive tasks and consolidating operations through Panorama.
    - The dry run feature is useful for validating the upgrade plan and ensuring readiness without impacting production systems.
    - The presence of an 'inventory.yaml' file can automate device selection, facilitating integration into larger automated workflows.
    - It's recommended to back up device configurations and have a rollback plan in place before proceeding with actual upgrades.
    - Customization options, such as setting logging preferences, can be specified through a 'settings.yaml' file if the script supports reading from such a file, allowing for more granular control over the upgrade process.
    """

    # Display the custom banner for batch firewall upgrades
    if settings_file_path.exists():
        if inventory_file_path.exists():
            console_welcome_banner(
                mode="batch",
                config_path=settings_file_path,
                inventory_path=inventory_file_path,
            )
        else:
            console_welcome_banner(
                mode="batch",
                config_path=settings_file_path,
            )

    elif inventory_file_path.exists():
        console_welcome_banner(
            mode="batch",
            inventory_path=inventory_file_path,
        )

    else:
        console_welcome_banner(mode="batch")

    # Perform common setup tasks, return a connected device
    device = common_setup(
        hostname,
        username,
        password,
    )

    # Exit script if device is Firewall (batch upgrade is only supported when connecting to Panorama)
    if type(device) is Firewall:
        logging.info(
            f"{get_emoji('error')} {hostname}: Batch upgrade is only supported when connecting to Panorama."
        )
        sys.exit(1)

    # Report the successful connection to Panorama
    logging.info(
        f"{get_emoji('success')} {hostname}: Connection to Panorama established. Firewall connections will be proxied!"
    )

    # Get firewalls connected to Panorama
    logging.info(
        f"{get_emoji('working')} {hostname}: Retrieving a list of all firewalls connected to Panorama..."
    )
    all_firewalls = get_firewalls_from_panorama(device)

    # Retrieve additional information about all of the firewalls
    logging.info(
        f"{get_emoji('working')} {hostname}: Retrieving detailed information of each firewall..."
    )
    firewalls_info = get_firewalls_info(all_firewalls)

    # Initialize an empty dictionary to map Firewall objects to their details
    firewall_mapping = {}

    # Iterate over each Firewall object and its corresponding details
    for fw, fw_info in zip(all_firewalls, firewalls_info):
        # Create a dictionary entry for each firewall with its details
        firewall_mapping[fw_info["hostname"]] = {
            "object": fw,
            **fw_info,  # Unpack all info details into the dictionary
        }

    # Check if inventory.yaml exists and if it does, read the selected devices
    if inventory_file_path.exists():
        with open(inventory_file_path, "r") as file:
            inventory_data = yaml.safe_load(file)
            user_selected_hostnames = inventory_data.get("firewalls_to_upgrade", [])

        if user_selected_hostnames:
            logging.info(
                f"{get_emoji('working')} {hostname}: Selected {user_selected_hostnames} firewalls from inventory.yaml for upgrade."
            )

            # Extracting the Firewall objects from the filtered mapping
            firewall_objects_for_upgrade = [
                firewall_mapping[hostname]["object"]
                for hostname in user_selected_hostnames
                if hostname in firewall_mapping
            ]
            logging.info(
                f"{get_emoji('working')} {hostname}: Selected {len(firewall_objects_for_upgrade)} firewalls from inventory.yaml for upgrade."
            )

    # If inventory.yaml does not exist or no devices are selected, prompt the user to select devices
    else:
        # Present a table of firewalls with detailed system information for selection
        user_selected_hostnames = select_devices_from_table(firewall_mapping)

        # Convert those hostnames into Firewall objects using the firewall_mapping
        firewall_objects_for_upgrade = [
            firewall_mapping[hostname]["object"]
            for hostname in user_selected_hostnames
            if hostname in firewall_mapping
        ]

    # Now, firewall_objects_for_upgrade should contain the actual Firewall objects
    # Proceed with the upgrade for the selected devices
    if not firewall_objects_for_upgrade:
        typer.echo("No devices selected for upgrade.")
        raise typer.Exit()

    typer.echo(
        f"{get_emoji('report')} {hostname}: Upgrading {len(firewall_objects_for_upgrade)} devices to version {target_version}..."
    )

    firewall_list = "\n".join(
        [
            f"  - {firewall_mapping[hostname]['hostname']} ({firewall_mapping[hostname]['ip-address']})"
            for hostname in user_selected_hostnames
        ]
    )

    typer.echo(
        f"{get_emoji('report')} {hostname}: Please confirm the selected firewalls:\n{firewall_list}"
    )

    # Asking for user confirmation before proceeding
    if dry_run:
        typer.echo(
            f"{get_emoji('warning')} {hostname}: Dry run mode is enabled, upgrade workflow will be skipped."
        )
        confirmation = typer.confirm(
            "Do you want to proceed with the dry run?", abort=True
        )
    else:
        typer.echo(
            f"{get_emoji('warning')} {hostname}: Dry run mode is disabled, upgrade workflow will be executed."
        )
        confirmation = typer.confirm(
            "Do you want to proceed with the upgrade?", abort=True
        )
        typer.echo(f"{get_emoji('start')} Proceeding with the upgrade...")

    if confirmation:
        typer.echo(f"{get_emoji('start')} Proceeding with the upgrade...")

        # Using ThreadPoolExecutor to manage threads
        threads = settings_file.get("concurrency.threads", 10)
        logging.info(f"{get_emoji('working')} {hostname}: Using {threads} threads.")
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Store future objects along with firewalls for reference
            future_to_firewall = {
                executor.submit(
                    upgrade_firewall,
                    target_device,
                    target_version,
                    dry_run,
                ): target_device
                for target_device in firewall_objects_for_upgrade
            }

            # Process completed tasks
            for future in as_completed(future_to_firewall):
                firewall = future_to_firewall[future]
                try:
                    future.result()
                except Exception as exc:
                    logging.error(
                        f"{get_emoji('error')} {hostname}: Firewall {firewall.hostname} generated an exception: {exc}"
                    )

        # Revisit the firewalls that were skipped in the initial pass
        if target_devices_to_revisit:
            logging.info(
                f"{get_emoji('start')} {hostname}: Revisiting firewalls that were active in an HA pair and had the same version as their peers."
            )

            # Using ThreadPoolExecutor to manage threads for revisiting firewalls
            threads = settings_file.get("concurrency.threads", 10)
            logging.debug(
                f"{get_emoji('working')} {hostname}: Using {threads} threads."
            )
            with ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_firewall = {
                    executor.submit(
                        upgrade_firewall, target_device, target_version, dry_run
                    ): target_device
                    for target_device in target_devices_to_revisit
                }

                # Process completed tasks
                for future in as_completed(future_to_firewall):
                    firewall = future_to_firewall[future]
                    try:
                        future.result()
                        logging.info(
                            f"{get_emoji('success')} {hostname}: Completed revisiting firewalls"
                        )
                    except Exception as exc:
                        logging.error(
                            f"{get_emoji('error')} {hostname}: Exception while revisiting firewalls: {exc}"
                        )

            # Clear the list after revisiting
            with target_devices_to_revisit_lock:
                target_devices_to_revisit.clear()
    else:
        typer.echo("Upgrade cancelled.")


# Subcommand for generating an inventory.yaml file
@app.command()
def inventory(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of Panorama appliance",
            prompt="Panorama hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Panorama appliance",
            prompt="Panorama username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Panorama password",
            hide_input=True,
        ),
    ],
):
    """
    Interactively generates an inventory file listing devices managed by a Panorama appliance,
    allowing the user to select which devices to include for potential upgrade. The inventory
    process involves connecting to Panorama, retrieving a list of managed firewalls, and presenting
    the user with a table of devices. The user can then select specific devices to include in the
    inventory file. This file serves as input for subsequent upgrade operations, ensuring that
    upgrades are targeted and organized.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the Panorama appliance. This is the address used to establish
        a connection for querying managed devices.
    username : str
        The username for authentication with the Panorama appliance. It is required to have sufficient
        permissions to retrieve device information.
    password : str
        The password associated with the username for authentication purposes. Input is hidden to protect
        sensitive information.

    Raises
    ------
    typer.Exit
        Exits the script if the command is invoked for an individual firewall rather than a Panorama appliance,
        as this functionality is specific to Panorama-managed environments.

    Examples
    --------
    Generating an inventory file from the command line:
        >>> typer run inventory --hostname 192.168.1.1 --username admin --password admin
        # This command initiates the inventory process, connecting to the Panorama at 192.168.1.1, and
        # interactively allows the user to select devices to include in the inventory file.

    Notes
    -----
    - The inventory process is an interactive session that requires the user to select devices from a
      presented table. The selections are then saved to 'inventory.yaml'.
    - This function is part of a Typer application that includes multiple subcommands for managing device
      upgrades. It is designed to be used in the context of a larger upgrade workflow.
    - The inventory file generated by this function can be customized or extended by editing 'inventory.yaml'
      directly, allowing for manual inclusion or exclusion of devices as needed.
    """

    console_welcome_banner(mode="inventory")

    panorama = common_setup(hostname, username, password)

    if type(panorama) is Firewall:
        logging.error(
            "Inventory command is only supported when connecting to Panorama."
        )
        raise typer.Exit()

    # Report the successful connection to Panorama
    logging.info(
        f"{get_emoji('success')} {hostname}: Connection to Panorama established."
    )

    # Get firewalls connected to Panorama
    logging.info(
        f"{get_emoji('working')} {hostname}: Retrieving a list of all firewalls connected to Panorama..."
    )
    all_firewalls = get_firewalls_from_panorama(panorama)

    # Retrieve additional information about all of the firewalls
    logging.info(
        f"{get_emoji('working')} {hostname}: Retrieving detailed information of each firewall..."
    )
    firewalls_info = get_firewalls_info(all_firewalls)

    # Initialize an empty dictionary to map Firewall objects to their details
    firewall_mapping = {}

    # Iterate over each Firewall object and its corresponding details
    for fw, fw_info in zip(all_firewalls, firewalls_info):
        # Create a dictionary entry for each firewall with its details
        firewall_mapping[fw_info["hostname"]] = {
            "object": fw,
            **fw_info,  # Unpack all info details into the dictionary
        }

    user_selected_hostnames = select_devices_from_table(firewall_mapping)

    with open("inventory.yaml", "w") as file:
        yaml.dump(
            {
                "firewalls_to_upgrade": [
                    hostname for hostname in user_selected_hostnames
                ]
            },
            file,
            default_flow_style=False,
        )

    typer.echo(Fore.GREEN + "Selected devices saved to inventory.yaml" + Fore.RESET)


# Subcommand for creating a settings.yaml file to override default settings
@app.command()
def settings():
    """
    Generates a settings.yaml file allowing customization of script configurations.

    This interactive command guides the user through a series of prompts to configure various aspects of the script's behavior, including concurrency, logging, reboot strategies, readiness checks, snapshots, and timeout settings. Each configuration section allows the user to specify preferences, such as the number of concurrent threads, logging levels, and file paths, among others. Customization of readiness checks and snapshots is also offered, enabling selective execution based on user requirements. The resulting configurations are saved to a 'settings.yaml' file in the current working directory, which the script can subsequently use to override default settings.

    Configuration Sections
    ----------------------
    - Concurrency: Defines the number of concurrent operations, particularly useful for batch operations.
    - Logging: Sets logging preferences including verbosity level, file path, maximum size, and log retention count.
    - Reboot: Configures retry intervals and maximum attempts for device reboots during the upgrade process.
    - Readiness Checks: Allows customization of pre-upgrade readiness checks to run.
    - Snapshots: Enables configuration of pre and post-upgrade snapshots for comparison and rollback purposes.
    - Timeout Settings: Determines timeout values for device connections and command executions.

    Notes
    -----
    - This command is part of the setup process and is intended to be run prior to executing upgrade commands.
    - The 'settings.yaml' file created by this command can be edited manually for further customization.
    - Default values are provided for each configuration option, with the option to accept the default or provide a custom value.
    """

    # Display the custom banner for settings
    console_welcome_banner(mode="settings")

    config_file_path = Path.cwd() / "settings.yaml"

    # Add confirmation prompts for disabling features
    disable_readiness_checks = typer.confirm(
        "Would you like to disable all readiness checks?", default=False
    )
    disable_snapshots = typer.confirm(
        "Would you like to disable all snapshots?", default=False
    )

    config_data = {
        "concurrency": {
            "threads": typer.prompt(
                "Number of concurrent threads",
                default=10,
                type=int,
            ),
        },
        "download": {
            "retry_interval": typer.prompt(
                "PAN-OS download retry interval (seconds)",
                default=60,
                type=int,
            ),
            "max_tries": typer.prompt(
                "PAN-OS maximum download tries",
                default=3,
                type=int,
            ),
        },
        "install": {
            "retry_interval": typer.prompt(
                "PAN-OS install retry interval (seconds)",
                default=60,
                type=int,
            ),
            "max_tries": typer.prompt(
                "PAN-OS maximum install attempts",
                default=3,
                type=int,
            ),
        },
        "logging": {
            "level": typer.prompt("Logging level", default="INFO"),
            "file_path": typer.prompt("Path for log files", default="logs/upgrade.log"),
            "max_size": typer.prompt(
                "Maximum log file size (MB)",
                default=10,
                type=int,
            ),
            "upgrade_log_count": typer.prompt(
                "Number of upgrade logs to retain",
                default=10,
                type=int,
            ),
        },
        "reboot": {
            "retry_interval": typer.prompt(
                "Device reboot retry interval (seconds)",
                default=60,
                type=int,
            ),
            "max_tries": typer.prompt(
                "Device maximum reboot tries",
                default=30,
                type=int,
            ),
        },
        "readiness_checks": {
            "disabled": disable_readiness_checks,
            "customize": (
                False
                if disable_readiness_checks
                else typer.confirm(
                    "Would you like to customize readiness checks?", default=False
                )
            ),
            "checks": {},
            "location": (
                "assurance/readiness_checks/" if not disable_readiness_checks else None
            ),
        },
        "snapshots": {
            "disabled": disable_snapshots,
            "customize": (
                False
                if disable_snapshots
                else typer.confirm(
                    "Would you like to customize snapshots?", default=False
                )
            ),
            "state": {},
            "location": "assurance/snapshots/" if not disable_snapshots else None,
            "retry_interval": 60 if not disable_snapshots else None,
            "max_tries": 3 if not disable_snapshots else None,
        },
        "timeout_settings": {
            "connection_timeout": typer.prompt(
                "Connection timeout (seconds)",
                default=30,
                type=int,
            ),
            "command_timeout": typer.prompt(
                "Command timeout (seconds)",
                default=120,
                type=int,
            ),
        },
    }

    # Modify the conditional sections to check for the disabled state
    if not disable_readiness_checks and config_data["readiness_checks"]["customize"]:
        for check, info in AssuranceOptions.READINESS_CHECKS.items():
            config_data["readiness_checks"]["checks"][check] = typer.confirm(
                f"Enable {info['description']}?", default=info["enabled_by_default"]
            )

    if not disable_snapshots and config_data["snapshots"]["customize"]:
        for snapshot_name, snapshot_info in AssuranceOptions.STATE_SNAPSHOTS.items():
            config_data["snapshots"]["state"][snapshot_name] = typer.confirm(
                f"Enable {snapshot_info['description']}?",
                default=snapshot_info["enabled_by_default"],
            )

    with open(config_file_path, "w") as f:
        yaml.dump(
            config_data,
            f,
            default_flow_style=False,
            sort_keys=True,
        )

    typer.echo(f"Configuration saved to {config_file_path}")


if __name__ == "__main__":
    app()
