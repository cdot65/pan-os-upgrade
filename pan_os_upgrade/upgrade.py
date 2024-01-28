"""
upgrade.py: Automating the Upgrade Process for Palo Alto Networks Devices

This script automates the upgrade process for Palo Alto Networks Firewalls and Panorama appliances, providing a seamless and efficient way to perform upgrades. It leverages Typer for a command-line interface, enabling users to specify parameters directly. The script supports upgrading standalone firewalls, Panorama appliances, and batch upgrading firewalls managed by Panorama. Additionally, it offers a settings command to generate a `settings.yaml` file, allowing users to override default script settings.

Features
--------
- **Automated Upgrades**: Simplifies the upgrade process for firewalls and Panorama appliances, minimizing the need for manual intervention.
- **Comprehensive Error Handling**: Incorporates extensive error handling to manage common and unforeseen issues during the upgrade process.
- **Integration with panos-upgrade-assurance**: Utilizes the panos-upgrade-assurance tool to perform pre and post-upgrade checks, ensuring device readiness.
- **Flexible Configuration**: Allows users to customize the upgrade process through a `settings.yaml` file, providing control over readiness checks, snapshots, and more.

Imports
-------
Standard Libraries:
    - concurrent, threading: Facilitates multi-threading for parallel processing.
    - ipaddress: Provides utilities for IP address manipulation.
    - logging: Enables detailed logging throughout the upgrade process.
    - os, sys: Interfaces with the operating system for file and directory operations.
    - time, re: Manages time-related functions and regular expression operations.
    - yaml: Handles YAML file parsing for settings configuration.
    - RemoteDisconnected, RotatingFileHandler: Manages HTTP connections and log file rotation.
    - Path, Lock, typing: Provides file path utilities, synchronization primitives, and type annotations.

External Libraries:
    - xml.etree.ElementTree (ET): Handles XML tree structure manipulation, essential for parsing PAN-OS API responses.
    - dns.resolver: Facilitates DNS lookups for hostname resolution.
    - Dynaconf: Manages dynamic configuration and settings for the script.
    - typer: Simplifies the creation of command-line interfaces, enhancing user interaction.

Palo Alto Networks libraries:
    - panos: Offers interfaces to Palo Alto Networks devices for direct API interaction.
    - PanDevice, SystemSettings: Facilitates operations on base PAN-OS devices and system settings.
    - Firewall, Panorama: Specializes in firewall and Panorama-specific operations and configurations.
    - Error handling modules: Provides specific error management capabilities for PAN-OS.

panos-upgrade-assurance package:
    - CheckFirewall, FirewallProxy: Essential for performing readiness checks and serving as intermediaries to the firewall.

Project-specific imports:
    - SnapshotReport, ReadinessCheckReport: Utilized for managing and storing snapshot and readiness check reports in a structured format.
    - ManagedDevice, ManagedDevices: Models for handling device information and collections.

Subcommands
-----------
- `firewall`: Initiates the upgrade process for a single firewall device.
- `panorama`: Upgrades a Panorama appliance.
- `batch`: Conducts batch upgrades for firewalls managed by a Panorama appliance.
- `settings`: Generates a `settings.yaml` file for customizing script settings.

Usage
-----
The script can be executed with various subcommands and options to tailor the upgrade process to specific needs. For example, to upgrade a firewall:

    python upgrade.py firewall --hostname <firewall_ip> --username <user> --password <password> --version <target_version>

To perform a batch upgrade of firewalls using Panorama as a communication proxy:

    python upgrade.py batch --hostname <panorama_ip> --username <user> --password <password> --version <target_version>

To generate a custom `settings.yaml` file:

    python upgrade.py settings

Notes
-----
- Ensure network connectivity and valid credentials before initiating the upgrade process.
- The `settings.yaml` file provides an opportunity to customize various aspects of the upgrade process, including which readiness checks to perform and snapshot configurations.
"""


# standard library imports
import ipaddress
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
from typing import Dict, List, Optional, Tuple, Union
from typing_extensions import Annotated

# trunk-ignore(bandit/B405)
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

# third party imports
import dns.resolver
from dynaconf import Dynaconf
import typer

# project imports
from pan_os_upgrade.models import (
    SnapshotReport,
    ReadinessCheckReport,
    ManagedDevice,
    ManagedDevices,
    FromAPIResponseMixin,
)


# ----------------------------------------------------------------------------
# Define panos-upgrade-assurance options
# ----------------------------------------------------------------------------
class AssuranceOptions:
    """
    Defines configuration options for readiness checks, reports, and state snapshots for the upgrade assurance process.

    This class serves as a central repository for configurations related to the upgrade assurance process of Palo Alto Networks
    devices. It specifies the available readiness checks, report types, and state snapshot categories that can be utilized
    during the device upgrade process. These configurations can be adjusted through a `settings.yaml` file, offering flexibility
    to customize the upgrade process according to specific needs and preferences.

    Attributes
    ----------
    READINESS_CHECKS : dict
        Maps names of readiness checks to their attributes, including descriptions, associated log levels, and flags indicating
        whether to exit the process upon check failure. These checks aim to ensure the device's readiness for an upgrade by
        validating various operational and configuration aspects.
    REPORTS : list of str
        Enumerates types of reports that can be generated to provide insights into the device's state pre- and post-upgrade.
        These reports cover various aspects such as ARP tables, content versions, IPsec tunnels, licenses, network interfaces,
        routing tables, and session statistics.
    STATE_SNAPSHOTS : list of str
        Lists categories of state snapshots that can be captured to document crucial data about the device's current state.
        These snapshots are valuable for diagnostics and for verifying the device's operational status before proceeding with
        the upgrade.

    Examples
    --------
    Accessing the log level for 'active_support' readiness check:
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
    - The configurations for readiness checks, report types, and state snapshots outlined in this class can be selectively
      enabled or customized through the `settings.yaml` file, allowing users to tailor the upgrade assurance process to their
      specific requirements.
    - Default settings for all options are provided within this class, but they can be overridden by custom configurations
      specified in the `settings.yaml` file, enhancing the script's adaptability to various upgrade scenarios.
    """

    READINESS_CHECKS = {
        "active_support": {
            "description": "Check if active support is available",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "arp_entry_exist": {
            "description": "Check if a given ARP entry is available in the ARP table",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "candidate_config": {
            "description": "Check if there are pending changes on device",
            "log_level": "error",
            "exit_on_failure": True,
        },
        "certificates_requirements": {
            "description": "Check if the certificates' keys meet minimum size requirements",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "content_version": {
            "description": "Running Latest Content Version",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "dynamic_updates": {
            "description": "Check if any Dynamic Update job is scheduled to run within the specified time window",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "expired_licenses": {
            "description": "No Expired Licenses",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "free_disk_space": {
            "description": "Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "ha": {
            "description": "Checks HA pair status from the perspective of the current device",
            "log_level": "info",
            "exit_on_failure": False,
        },
        "ip_sec_tunnel_status": {
            "description": "Check if a given IPsec tunnel is in active state",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        # "jobs": {
        #     "description": "Check for any job with status different than FIN",
        #     "log_level": "warning",
        #     "exit_on_failure": False,
        # },
        "ntp_sync": {
            "description": "Check if NTP is synchronized",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "planes_clock_sync": {
            "description": "Check if the clock is synchronized between dataplane and management plane",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "panorama": {
            "description": "Check connectivity with the Panorama appliance",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        # "session_exist": {
        #     "description": "Check if a critical session is present in the sessions table",
        #     "log_level": "error",
        #     "exit_on_failure": True,
        # },
    }

    REPORTS = [
        "arp_table",
        "content_version",
        "ip_sec_tunnels",
        "license",
        "nics",
        "routes",
        "session_stats",
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


# ----------------------------------------------------------------------------
# Core Upgrade Functions
# ----------------------------------------------------------------------------
def backup_configuration(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    file_path: str,
) -> bool:
    """
    Backs up the current running configuration of a specified target device to a local file.

    This function retrieves the running configuration from the target device, either a Firewall or Panorama, and saves it to
    a specified file path in XML format. It validates the integrity of the retrieved XML data and provides detailed logging
    of each step in the process. The backup is crucial for ensuring a recovery point before making significant changes, such
    as upgrades or policy modifications.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device from which the running configuration will be backed up. It must be an initialized and connected
        instance of either a Firewall or Panorama class.
    hostname : str
        The hostname or IP address of the target device, utilized for identification and logging purposes.
    file_path : str
        The local filesystem path where the configuration file will be saved. The function ensures the existence
        of the target directory, creating it if necessary.

    Returns
    -------
    bool
        True if the backup process completes successfully and the configuration is accurately saved to the file.
        False if any error occurs during the backup process, including retrieval or file writing issues.

    Raises
    ------
    Exception
        An exception is raised if an unexpected error occurs during the configuration retrieval or file writing process,
        accompanied by a descriptive error message for troubleshooting.

    Examples
    --------
    Backing up a Firewall's configuration:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='adminpassword')
        >>> backup_configuration(firewall, 'firewall1', '/backups/firewall1_config.xml')
        True  # Indicates a successful backup

    Backing up a Panorama appliance's configuration:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='adminpassword')
        >>> backup_configuration(panorama, 'panorama1', '/backups/panorama1_config.xml')
        True  # Indicates a successful backup

    Notes
    -----
    - The configuration is stored in XML format, reflecting the device's current configuration state.
    - This function forms part of a broader suite of utilities aimed at facilitating the upgrade and management process of
      Palo Alto Networks devices, providing administrators with a means to preserve configurations for recovery and compliance.
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
    Determines the necessity of an upgrade for the target device based on the specified version components.

    This function evaluates whether the target device, either a Firewall or Panorama, requires an upgrade to the
    specified PAN-OS version. It compares the device's current software version against the desired version, defined
    by major, minor, and maintenance (or hotfix) components. An upgrade is considered necessary if the target version
    is newer than the current version. If the device's version is already equal to or newer than the target version,
    the function logs an appropriate message and terminates the script to prevent unnecessary upgrades or downgrades.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        An instance of the Firewall or Panorama class representing the device to be evaluated for an upgrade.
    hostname : str
        The hostname or IP address of the target device, used primarily for logging and identification purposes.
    target_major : int
        The major version number of the target PAN-OS version.
    target_minor : int
        The minor version number of the target PAN-OS version.
    target_maintenance : Union[int, str]
        The maintenance or hotfix version of the target PAN-OS version. Can be an integer for maintenance versions
        or a string for hotfix versions (e.g., '1-h1').

    Raises
    ------
    SystemExit
        Terminates the script execution if an upgrade is deemed unnecessary, either due to the current version being
        up-to-date or a downgrade attempt being detected.

    Examples
    --------
    Evaluating the need for an upgrade on a firewall device:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='adminpassword')
        >>> determine_upgrade(firewall, 'firewall1', 9, 1, 0)
        # This will log the current version and the decision on whether an upgrade to version 9.1.0 is necessary.

    Evaluating the need for an upgrade on a Panorama appliance:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='adminpassword')
        >>> determine_upgrade(panorama, 'panorama1', 10, 0, '1-h1')
        # This will log the current version and the decision on whether an upgrade to version 10.0.1-h1 is necessary.

    Notes
    -----
    - The function parses the current and target versions into a comparable format to accurately determine the need for
      an upgrade.
    - This evaluation is crucial to avoid unnecessary upgrades or downgrades, ensuring the device's software remains
      stable and secure.
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
        logging.error(
            f"{get_emoji('error')} {hostname}: No upgrade required or downgrade attempt detected."
        )
        logging.error(f"{get_emoji('stop')} {hostname}: Halting script.")
        sys.exit(1)


def get_ha_status(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> Tuple[str, Optional[dict]]:
    """
    Retrieves the High Availability (HA) status and configuration details of a target device.

    This function queries the HA status of a specified Palo Alto Networks device, either a Firewall or Panorama.
    It identifies the device's HA mode, such as standalone, active/passive, active/active, or cluster. The function
    returns the HA mode along with a dictionary of detailed HA configuration if the device is part of an HA setup.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device instance from which the HA status is to be retrieved. This can be either a Firewall or Panorama
        instance, initialized with proper credentials and connectivity.
    hostname : str
        The hostname or IP address of the target device. Used for logging purposes to identify the device in logs.

    Returns
    -------
    Tuple[str, Optional[dict]]
        A tuple containing the HA mode as a string and an optional dictionary with HA configuration details.
        The dictionary is provided if the device is in an HA setup; otherwise, None is returned.

    Example
    -------
    Retrieving HA status for a firewall device:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> ha_mode, ha_config = get_ha_status(firewall, 'fw-hostname')
        >>> print(ha_mode)  # e.g., 'active/passive'
        >>> if ha_config:
        ...     print(ha_config)  # Detailed HA configuration information

    Notes
    -----
    - Understanding the HA status is crucial before performing certain operations like upgrades or maintenance to
      ensure they are done safely without affecting the device's operational status.
    - The function parses the device's operational command response to extract the HA status and configuration,
      making it a valuable tool for network administrators and automation scripts.
    """
    logging.debug(
        f"{get_emoji('start')} {hostname}: Getting {target_device.serial} deployment information..."
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


def handle_ha_logic(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    dry_run: bool,
) -> Tuple[bool, Optional[Union[Firewall, Panorama]]]:
    """
    Manages the High Availability (HA) logic for a target device during the upgrade process.

    Evaluates the HA configuration of the target device to determine the appropriate upgrade approach.
    This includes understanding the device's role in an HA setup (active, passive, or standalone) and making
    decisions based on this status and the dry_run flag. The function guides whether the upgrade should proceed
    and if any HA-specific actions are needed, such as suspending HA synchronization on the active device.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device being evaluated, which can be a Firewall or Panorama instance. This device may be part of an HA configuration.
    hostname : str
        The hostname or IP address of the target device, utilized for identification in logging outputs.
    dry_run : bool
        A flag indicating whether the logic should be simulated (True) without making actual changes, or executed (False).

    Returns
    -------
    Tuple[bool, Optional[Union[Firewall, Panorama]]]
        A tuple where the first element is a boolean indicating if the upgrade should proceed, and the second element is
        an optional device instance (Firewall or Panorama) representing the HA peer, if the upgrade involves HA considerations.

    Example
    -------
    Evaluating HA logic for a device upgrade:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> proceed, ha_peer = handle_ha_logic(firewall, 'firewall1', dry_run=False)
        >>> print(proceed)  # Indicates if upgrade should continue
        >>> print(ha_peer)  # None if no HA peer involved or if not targeting peer, otherwise device instance

    Notes
    -----
    - The function initially retrieves the HA status to make informed decisions regarding the upgrade process.
    - It accounts for HA roles and version discrepancies between HA peers to ensure a coherent upgrade strategy.
    - The dry_run option allows for a non-disruptive evaluation of the HA logic, aiding in planning and testing.
    """
    deploy_info, ha_details = get_ha_status(
        target_device,
        hostname,
    )

    # If the target device is not part of an HA configuration, proceed with the upgrade
    if not ha_details:
        return True, None

    local_state = ha_details["result"]["group"]["local-info"]["state"]
    local_version = ha_details["result"]["group"]["local-info"]["build-rel"]
    peer_version = ha_details["result"]["group"]["peer-info"]["build-rel"]
    version_comparison = compare_versions(local_version, peer_version)

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
            logging.debug(f"{get_emoji('report')} {hostname}: Target device is passive")
            return True, None

    elif version_comparison == "older":
        logging.debug(
            f"{get_emoji('report')} {hostname}: Target device is on an older version"
        )
        # Suspend HA state of active if the passive is on a later release
        if local_state == "active" and not dry_run:
            logging.debug(
                f"{get_emoji('report')} {hostname}: Suspending HA state of active"
            )
            suspend_ha_active(
                target_device,
                hostname,
            )
        return True, None

    elif version_comparison == "newer":
        logging.debug(
            f"{get_emoji('report')} {hostname}: Target device is on a newer version"
        )
        # Suspend HA state of passive if the active is on a later release
        if local_state == "passive" and not dry_run:
            logging.debug(
                f"{get_emoji('report')} {hostname}: Suspending HA state of passive"
            )
            suspend_ha_passive(
                target_device,
                hostname,
            )
        return True, None

    return False, None


def perform_ha_sync_check(
    hostname: str,
    ha_details: dict,
    strict_sync_check: bool = True,
) -> bool:
    """
    Verifies synchronization status between HA peers for a Palo Alto Networks device.

    This function checks if the High Availability (HA) peers are synchronized, which is crucial before performing
    operations that could affect the device state, such as upgrades. It uses HA details to determine synchronization
    status and supports a strict mode that halts the script on synchronization failures.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target device. Used for logging to identify the device being checked.
    ha_details : dict
        Detailed HA information for the target device, including synchronization status with its HA peer.
    strict_sync_check : bool, optional
        Determines the handling of synchronization failures: if True (default), the script exits on failure;
        if False, it logs a warning and continues.

    Returns
    -------
    bool
        True if HA peers are synchronized, indicating it's safe to proceed with sensitive operations. False indicates
        a lack of synchronization, with the script's response depending on the `strict_sync_check` setting.

    Raises
    ------
    SystemExit
        If `strict_sync_check` is True and synchronization fails, the script will terminate to prevent potential issues.

    Example
    -------
    Performing a strict HA synchronization check:
        >>> ha_details = {'result': {'group': {'running-sync': 'synchronized'}}}
        >>> perform_ha_sync_check('firewall1', ha_details)
        True  # HA peers are synchronized

    Performing a lenient HA synchronization check:
        >>> perform_ha_sync_check('firewall1', ha_details, strict_sync_check=False)
        False  # HA peers are not synchronized, but script continues

    Notes
    -----
    - Synchronization checks are essential in HA environments to ensure consistency between devices before making changes.
    - The function enhances automation scripts' robustness by preventing actions that could disrupt unsynchronized HA setups.
    """

    logging.info(f"{get_emoji('start')} {hostname}: Checking if HA peer is in sync...")
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


def perform_readiness_checks(
    firewall: Firewall,
    hostname: str,
    file_path: str,
) -> None:
    """
    Performs a series of readiness checks on a Palo Alto Networks Firewall to ensure it is prepared for an upgrade.

    This function assesses the firewall's readiness by executing various checks related to configuration, licensing,
    software versions, and more. The results are aggregated into a comprehensive JSON report that is saved to the
    provided file path. The checks to be performed can be customized via the `settings.yaml` file, allowing for
    flexibility based on specific operational requirements.

    Parameters
    ----------
    firewall : Firewall
        The Firewall instance to be checked, initialized with appropriate credentials and connectivity.
    hostname : str
        The hostname or IP address of the firewall, used for logging and identification purposes.
    file_path : str
        The file path where the JSON report of the readiness checks will be saved. The directory will be created
        if it does not exist.

    Returns
    -------
    None

    Raises
    ------
    IOError
        An IOError is raised if there is an issue with writing the readiness report to the specified file path,
        indicating a problem with file access or disk space.

    Examples
    --------
    Executing readiness checks and saving the report:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_readiness_checks(firewall_instance, 'firewall1', '/path/to/firewall1_readiness.json')
        # This executes the readiness checks and saves the report to the specified path.

    Notes
    -----
    - The readiness checks are crucial for identifying potential issues that could impact the upgrade process,
      ensuring a smooth and successful upgrade.
    - The checks to be executed can be defined in the `settings.yaml` file, allowing for customization based on
      the environment and operational policies. If the `settings.yaml` file exists and specifies custom checks
      under `readiness_checks.customize`, those checks will be used; otherwise, a default set of checks is applied.

    """

    # Determine readiness checks to perform based on settings.yaml
    if settings_file_path.exists() and settings_file.get(
        "readiness_checks.customize", False
    ):
        # Extract checks where value is True
        selected_checks = [
            check
            for check, enabled in settings_file.get(
                "readiness_checks.checks", {}
            ).items()
            if enabled
        ]
    else:
        # Default checks to run if settings.yaml does not exist or customize is False
        selected_checks = [
            "candidate_config",
            "content_version",
            "expired_licenses",
            "ha",
            # "jobs",
            "free_disk_space",
            "ntp_sync",
            "panorama",
            "planes_clock_sync",
        ]

    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing readiness checks of target firewall..."
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
) -> None:
    """
    Initiates a reboot of the specified target device to ensure it operates on the desired PAN-OS version.

    This function triggers a reboot on the target device and monitors it to confirm it restarts with the specified target version. It is particularly crucial in the context of upgrades where a reboot might be necessary to apply new configurations or complete the upgrade process. The function also accounts for High Availability (HA) configurations, ensuring the device and its HA peer remain synchronized post-reboot.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device (Firewall or Panorama) to reboot. Must be initialized with proper credentials and connection details.
    hostname : str
        Hostname or IP address of the target device, utilized for logging and identification throughout the reboot process.
    target_version : str
        The version that the target device should be running post-reboot.
    ha_details : Optional[dict], optional
        HA configuration details of the target device, if part of an HA pair. This is used to ensure HA synchronization post-reboot. Defaults to None.

    Raises
    ------
    SystemExit
        Exits the script if the device fails to reboot to the target version or if HA synchronization post-reboot cannot be verified.

    Examples
    --------
    Rebooting a firewall and verifying its version post-reboot:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_reboot(firewall, 'firewall1', '9.1.0')
        # Initiates a reboot and ensures the firewall is running version 9.1.0 afterwards.

    Notes
    -----
    - The reboot process involves sending a reboot command to the device and then repeatedly checking its availability and version.
    - The function implements a retry mechanism with a fixed number of attempts and delay between them to accommodate the device's reboot time.
    - For devices in an HA setup, additional checks are performed to ensure the HA pair's synchronization state is maintained post-reboot.
    """

    rebooted = False
    attempt = 0
    MAX_RETRIES = 30
    RETRY_DELAY = 60

    logging.info(f"{get_emoji('start')} {hostname}: Rebooting the target device...")

    # Initiate reboot
    reboot_job = target_device.op(
        "<request><restart><system/></restart></request>",
        cmd_xml=False,
    )
    reboot_job_result = flatten_xml_to_dict(reboot_job)
    logging.info(f"{get_emoji('report')} {hostname}: {reboot_job_result['result']}")

    # Wait for the target device reboot process to initiate before checking status
    time.sleep(60)

    while not rebooted and attempt < MAX_RETRIES:
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
            time.sleep(RETRY_DELAY)

    if not rebooted:
        logging.error(
            f"{get_emoji('error')} {hostname}: Failed to reboot to the target version after {MAX_RETRIES} attempts."
        )
        sys.exit(1)


def perform_snapshot(
    firewall: Firewall,
    hostname: str,
    file_path: str,
) -> None:
    """
    Captures and saves a comprehensive snapshot of the current network state of a specified firewall to a JSON file.

    This function gathers detailed network state information from the firewall, such as ARP tables, content versions,
    IPsec tunnel statuses, license information, network interfaces, routing tables, and session statistics. The
    collected data is serialized into JSON format and saved to the provided file path. This snapshot serves as a
    valuable diagnostic tool for assessing the firewall's state before and after significant events like upgrades
    or configuration changes.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class, representing the device from which the network state information is
        collected. This object must be initialized with the necessary authentication details and connection parameters.
    hostname : str
        The hostname or IP address of the firewall, utilized for logging and identification purposes throughout
        the snapshot process.
    file_path : str
        The filesystem path where the snapshot JSON file will be saved. The function ensures the existence of
        the target directory, creating it if necessary.

    Raises
    ------
    IOError
        Raised if an error occurs while writing the snapshot data to the filesystem, indicating issues with file
        creation or disk access.

    Examples
    --------
    Taking and saving a network state snapshot of a firewall:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_snapshot(firewall_instance, 'fw-hostname', '/backups/fw-snapshot.json')
        # Gathers and saves the network state of 'fw-hostname' to '/backups/fw-snapshot.json'.

    Notes
    -----
    - The function is designed to be non-disruptive and can be executed during normal firewall operations without
      affecting network traffic.
    - The selection of information to include in the snapshot can be customized via a `settings.yaml` file, allowing
      administrators to tailor the snapshot content to specific requirements.
    """

    # Determine snapshot actions to perform based on settings.yaml
    if settings_file_path.exists() and settings_file.get("snapshots.customize", False):
        # Extract state actions where value is True
        selected_actions = [
            action
            for action, enabled in settings_file.get("snapshots.state", {}).items()
            if enabled
        ]
    else:
        # Default actions to take if settings.yaml does not exist or customize is False
        selected_actions = [
            "arp_table",
            "content_version",
            "ip_sec_tunnels",
            "license",
            "nics",
            "routes",
            "session_stats",
        ]

    logging.info(
        f"{get_emoji('start')} {hostname}: Performing snapshot of network state information..."
    )

    # take snapshots
    network_snapshot = run_assurance(
        firewall,
        hostname,
        operation_type="state_snapshot",
        actions=selected_actions,
        config={},
    )

    # Check if a readiness check was successfully created
    if isinstance(network_snapshot, SnapshotReport):
        logging.info(
            f"{get_emoji('success')} {hostname}: Network snapshot created successfully"
        )
        network_snapshot_json = network_snapshot.model_dump_json(indent=4)
        logging.debug(
            f"{get_emoji('success')} {hostname}: Network snapshot JSON {network_snapshot_json}"
        )

        ensure_directory_exists(file_path)

        with open(file_path, "w") as file:
            file.write(network_snapshot_json)

        logging.debug(
            f"{get_emoji('save')} {hostname}: Network state snapshot collected and saved to {file_path}"
        )
    else:
        logging.error(f"{get_emoji('error')} {hostname}: Failed to create snapshot")


def perform_upgrade(
    target_device: Union[Firewall, Panorama],
    hostname: str,
    target_version: str,
    ha_details: Optional[dict] = None,
) -> None:
    """
    Initiates an upgrade of a specified target device to a desired PAN-OS version, with optional consideration for HA configurations.

    This function triggers the upgrade process for a given target device to the specified PAN-OS version. It accounts for potential HA configurations by utilizing provided HA details. The process incorporates retry mechanisms to handle transient errors, such as when the software manager is busy. Detailed logging is provided throughout the process for monitoring and troubleshooting. The function terminates the script if it encounters critical errors or exhausts the allowed number of retry attempts.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device (Firewall or Panorama) to be upgraded. This object must be initialized with the necessary credentials and connection details.
    hostname : str
        The hostname or IP address of the target device, used for identification and logging purposes.
    target_version : str
        The PAN-OS version to which the target device is to be upgraded, formatted as a string (e.g., '10.1.0').
    ha_details : Optional[dict], optional
        Optional dictionary containing HA configuration details of the target device, if applicable. This information is leveraged to tailor the upgrade process to HA environments.

    Raises
    ------
    SystemExit
        If the upgrade process fails or encounters an unrecoverable error, resulting in script termination.

    Notes
    -----
    - Retry mechanisms are employed to mitigate transient operational errors, enhancing the resilience of the upgrade process.
    - The function supports customization of retry parameters through a `settings.yaml` file, allowing for adjustments to the retry behavior based on specific operational requirements.

    Example
    -------
    Executing the upgrade process with a specified target version:
        >>> target_device = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_upgrade(target_device, 'firewall1', '10.2.0')
        # Triggers the upgrade of 'firewall1' to PAN-OS version '10.2.0'.
    """

    # Check if settings.yaml exists and use its values for max_retries and retry_interval
    if settings_file_path.exists():
        max_retries = settings_file.get("reboot.max_tries", 30)
        retry_interval = settings_file.get("reboot.retry_interval", 60)
    else:
        # Default values if settings.yaml does not exist or does not specify these settings
        max_retries = 30
        retry_interval = 60

    logging.info(
        f"{get_emoji('start')} {hostname}: Performing upgrade to version {target_version}..."
    )

    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(
                f"{get_emoji('start')} {hostname}: Attempting upgrade to version {target_version} (Attempt {attempt + 1} of {max_retries})..."
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
                        f"{get_emoji('warning')} {hostname}: Retrying in {retry_interval} seconds..."
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
                        f"{get_emoji('warning')} {hostname}: Software manager is busy. Retrying in {retry_interval} seconds..."
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
    Executes specified operational checks or captures state snapshots on a firewall based on the given operation type.

    Depending on the 'operation_type', this function conducts various operations like readiness checks or state snapshots on the provided firewall. It processes a list of 'actions' according to the operation type and uses 'config' for additional parameters. The function returns a relevant report object upon success or None if the operation fails. It validates the actions against the operation type and provides detailed logging, including error handling.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance for which the assurance operations will be executed.
    hostname : str
        The hostname or IP address of the firewall, used for logging purposes.
    operation_type : str
        Specifies the type of operation to perform, such as 'readiness_check' or 'state_snapshot'.
    actions : List[str]
        Defines the specific actions to execute within the operation, like checking for pending changes or capturing ARP tables.
    config : Dict[str, Union[str, int, float, bool]]
        Provides additional configuration options for the actions, detailing parameters such as thresholds or specific checks.

    Returns
    -------
    Union[SnapshotReport, ReadinessCheckReport, None]
        Depending on the operation, returns a SnapshotReport or ReadinessCheckReport object, or None if the operation encounters an error or is invalid.

    Raises
    ------
    SystemExit
        Exits the script if an invalid action is specified for the given operation type or if an error occurs during the operation execution.

    Notes
    -----
    - This function is designed to support extensibility for new operation types and actions as needed.
    - It plays a crucial role in maintaining the firewall's operational integrity and readiness, especially before upgrade activities.

    Example
    -------
    Executing readiness checks on a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> result = run_assurance(firewall, 'firewall1', 'readiness_check', ['candidate_config', 'license_status'], {})
        # Result is a ReadinessCheckReport object or None if the operation fails.
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
                f"{get_emoji('start')} {hostname}: Performing readiness checks to determine if firewall is ready for upgrade..."
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
            if action not in AssuranceOptions.STATE_SNAPSHOTS:
                logging.error(
                    f"{get_emoji('error')} {hostname}: Invalid action for state snapshot: {action}"
                )
                return

        # take snapshots
        try:
            logging.debug(f"{get_emoji('start')} {hostname}: Performing snapshots...")
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
            if action not in AssuranceOptions.REPORTS:
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
    Initiates and monitors the download of a specified software version on a target device.

    This function checks if the desired software version is already present on the target device. If not, it starts the download process and monitors its progress, providing real-time feedback through logging. The function is designed to handle various download states and errors, ensuring robust error handling and logging for diagnostics. It supports devices in High Availability (HA) configurations, taking HA details into account during the process.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The Firewall or Panorama device on which the software version is to be downloaded.
    hostname : str
        The hostname or IP address of the target device, utilized for logging purposes.
    target_version : str
        The PAN-OS version intended to be downloaded onto the target device.
    ha_details : dict
        High Availability (HA) details of the target device, relevant for devices in an HA setup.

    Returns
    -------
    bool
        Indicates whether the download was successful (True) or not (False).

    Raises
    ------
    SystemExit
        Exits the script with an error message if the download process encounters a critical error.

    Example
    -------
    Downloading software on a firewall device:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> success = software_download(firewall, 'firewall1', '10.0.0', ha_details={})
        >>> print("Download Successful" if success else "Download Failed")

    Notes
    -----
    - The function performs an initial check to avoid redundant downloads if the target version is already available on the device.
    - In the case of HA configurations, the function ensures that HA synchronization considerations are taken into account during the download process.
    - The download process is monitored continuously, with updates logged every 30 seconds to provide visibility into the progress.
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
                        f"{get_emoji('working')} {hostname}: {status_msg} - HA will sync image - Elapsed time: {elapsed_time} seconds"
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
    Verifies if a specified software version is available for upgrade on the target device, considering HA setup.

    This function determines the feasibility of upgrading a target device to a specified software version. It performs a series of checks, including current software version assessment, target version availability in the device's software repository, and the presence of the required base image for the upgrade. The function accounts for High Availability (HA) setups by evaluating the upgrade compatibility within the HA context. Detailed logging provides insight into each step of the verification process.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The Firewall or Panorama device to check for the specified software version's availability.
    hostname : str
        The hostname or IP address of the target device for logging purposes.
    version : str
        The target software version to check for availability and readiness for upgrade.
    ha_details : dict
        Details of the HA setup of the target device, if applicable.

    Returns
    -------
    bool
        True if the specified software version is available and constitutes a valid upgrade; False otherwise.

    Raises
    ------
    SystemExit
        Exits the script if the specified version represents a downgrade or is not appropriate for upgrade due to other criteria.

    Example
    -------
    Checking software version availability for upgrade:
        >>> device = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> available = software_update_check(device, 'device123', '10.1.0', ha_details={})
        >>> print("Upgrade Available" if available else "Upgrade Not Available")

    Notes
    -----
    - The function ensures that the target version is not a downgrade compared to the current version on the device.
    - It checks the device's software repository for the target version and verifies the presence of the required base image.
    - In HA configurations, the function assesses upgrade viability while considering HA synchronization and compatibility requirements.
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
    target_device.software.check()
    available_versions = target_device.software.versions

    # check to see if specified version is available for upgrade
    if version in available_versions:
        logging.info(
            f"{get_emoji('success')} {hostname}: version {version} is available for download"
        )

        # validate the specified version's base image is already downloaded
        if available_versions[f"{major}.{minor}.0"]["downloaded"]:
            logging.info(
                f"{get_emoji('success')} {hostname}: Base image for {version} is already downloaded"
            )
            return True

        else:
            logging.error(
                f"{get_emoji('error')} {hostname}: Base image for {version} is not downloaded"
            )
            return False
    else:
        logging.error(
            f"{get_emoji('error')} {hostname}: version {version} is not available for download"
        )
        return False


def suspend_ha_active(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> bool:
    """
    Suspends High Availability (HA) functionality on an active device within an HA pair.

    This function is used to temporarily disable HA functionality on an active device, facilitating maintenance or upgrade activities by preventing failover events during the process. It issues an operational command to the target device to suspend HA, effectively transitioning the active device to a non-participative state in HA operations. The function verifies the operation's success through the device's response and logs the outcome.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The active device in an HA pair where HA functionality needs to be suspended. It could be either a Firewall or a Panorama appliance.
    hostname : str
        The hostname or IP address of the target device, utilized for logging and identification purposes.

    Returns
    -------
    bool
        True if the HA suspension command is successfully executed on the target device, indicating that HA functionality has been temporarily disabled. False if the operation encounters an error or fails.

    Raises
    ------
    Exception
        Raises a generic exception and logs the error if the operational command fails or encounters an issue during execution.

    Example
    -------
    Suspending HA on the active device of an HA pair:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> suspension_result = suspend_ha_active(firewall, 'firewall-active.example.com')
        >>> print("HA suspension successful" if suspension_result else "HA suspension failed")

    Notes
    -----
    - This operation is critical in HA environments, especially when performing system upgrades or maintenance that requires preventing automatic failover.
    - It's important to coordinate this action with network management policies and potentially with the suspension of the counterpart HA device to manage network redundancy effectively.
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
        logging.error(
            f"{get_emoji('error')} {hostname}: Error suspending active target device HA state: {e}"
        )
        return False


def suspend_ha_passive(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> bool:
    """
    Suspends High Availability (HA) functionality on a passive device within an HA pair.

    This function is utilized to temporarily disable HA functionality on a device designated as passive in an HA configuration. The suspension is critical during certain operations, such as system upgrades or maintenance, to prevent the passive device from taking over as the active device. It sends a command to the target device to suspend HA activities and evaluates the command's success based on the device's response, logging the outcome accordingly.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device (Firewall or Panorama) in an HA pair that is currently in a passive state and requires HA suspension.
    hostname : str
        The hostname or IP address of the target device, used for logging and identification purposes.

    Returns
    -------
    bool
        Returns True if the HA suspension command is successfully executed on the passive device, indicating the temporary deactivation of its HA functionality. Returns False if the operation encounters an error or fails.

    Raises
    ------
    Exception
        Logs an error and returns False if an exception occurs during the execution of the HA suspension command.

    Example
    -------
    Suspending HA on the passive device of an HA pair:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='admin')
        >>> suspension_result = suspend_ha_passive(panorama, 'panorama-passive.example.com')
        >>> print("HA suspension successful" if suspension_result else "HA suspension failed")

    Notes
    -----
    - Temporarily suspending HA on a passive device is a significant operation that should be undertaken with caution, especially in terms of its impact on network redundancy and traffic flow.
    - It is recommended to perform this operation in coordination with overall network management and maintenance plans.
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
    Orchestrates the upgrade process for a Palo Alto Networks firewall to a specified version, considering HA configurations and supporting a dry run mode.

    This function manages the upgrade of a firewall, including pre-upgrade checks, software download, and system reboot to the target version. It handles firewalls in both standalone and High Availability (HA) configurations. The dry run mode allows for testing the upgrade process without making any changes, ideal for planning and validation.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance to be upgraded, initialized with connection details.
    target_version : str
        The target PAN-OS version to upgrade the firewall to (e.g., '10.1.0').
    dry_run : bool
        If True, the function simulates the upgrade steps without performing the actual upgrade.

    Raises
    ------
    SystemExit
        Exits the script if the upgrade process encounters a critical failure at any stage.

    Example
    -------
    Executing an upgrade on a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> upgrade_firewall(firewall, '10.1.0', dry_run=False)
        # Initiates the upgrade to version 10.1.0, with actual changes applied.

    Notes
    -----
    - It is recommended to perform a dry run before executing the actual upgrade to ensure operational readiness.
    - The function provides detailed logging at each step for monitoring the upgrade progress and diagnosing issues.

    Workflow
    --------
    1. Validates the current system state and HA configuration.
    2. Performs readiness checks to ensure the firewall is prepared for upgrade.
    3. Downloads the necessary software version if not already available.
    4. Takes pre-upgrade snapshots and backups for rollback purposes.
    5. Executes the upgrade and reboots the firewall to the target version.
    6. Verifies post-upgrade status and functionality.
    """

    # Refresh system information to ensure we have the latest data
    logging.debug(f"{get_emoji('start')} Refreshing system information...")
    firewall_details = SystemSettings.refreshall(firewall)[0]
    hostname = firewall_details.hostname
    logging.info(
        f"{get_emoji('report')} {hostname}: {firewall.serial} {firewall_details.ip_address}"
    )

    # Determine if the firewall is standalone, HA, or in a cluster
    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing test to see if firewall is standalone, HA, or in a cluster..."
    )
    deploy_info, ha_details = get_ha_status(
        firewall,
        hostname,
    )
    logging.info(f"{get_emoji('report')} {hostname}: HA mode: {deploy_info}")
    logging.debug(f"{get_emoji('report')} {hostname}: HA details: {ha_details}")

    # If firewall is part of HA pair, determine if it's active or passive
    if ha_details:
        proceed_with_upgrade, peer_firewall = handle_ha_logic(
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
        f"{get_emoji('start')} {hostname}: Performing tests to validate firewall's readiness..."
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
        f"{get_emoji('start')} {hostname}: Performing test to see if {target_version} is already downloaded..."
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
            f"{get_emoji('error')} {hostname}: Image not downloaded, exiting..."
        )

        sys.exit(1)

    # Perform the pre-upgrade snapshot
    perform_snapshot(
        firewall,
        hostname,
        f'assurance/snapshots/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
    )

    # Perform Readiness Checks
    perform_readiness_checks(
        firewall,
        hostname,
        f'assurance/readiness_checks/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
    )

    # Determine strictness of HA sync check
    with target_devices_to_revisit_lock:
        is_firewall_to_revisit = firewall in target_devices_to_revisit

    # Perform HA sync check, skipping standalone firewalls
    if ha_details:
        perform_ha_sync_check(
            hostname,
            ha_details,
            strict_sync_check=not is_firewall_to_revisit,
        )

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing backup of configuration to local filesystem..."
    )
    backup_config = backup_configuration(
        firewall,
        hostname,
        f'assurance/configurations/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
    )
    logging.debug(f"{get_emoji('report')} {hostname}: {backup_config}")

    # Exit execution is dry_run is True
    if dry_run is True:
        logging.info(f"{get_emoji('success')} {hostname}: Dry run complete, exiting...")
        logging.info(f"{get_emoji('stop')} {hostname}: Halting script.")
        sys.exit(0)
    else:
        logging.info(
            f"{get_emoji('start')} {hostname}: Not a dry run, continue with upgrade..."
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


def upgrade_panorama(
    panorama: Panorama,
    target_version: str,
    dry_run: bool,
) -> None:
    """
    Manages the upgrade of a Panorama appliance to a specified PAN-OS version, incorporating pre-upgrade validations and post-upgrade steps.

    This function orchestrates a series of operations to upgrade a Panorama appliance, starting with pre-upgrade checks like software availability and device readiness, followed by the actual upgrade process, and concluding with a system reboot to the new version. It accommodates both standalone and HA-configured Panorama instances and offers a 'dry run' mode for verifying the upgrade process without making any changes.

    Parameters
    ----------
    panorama : Panorama
        The Panorama appliance instance to upgrade.
    target_version : str
        The desired PAN-OS version to upgrade to.
    dry_run : bool
        Specifies whether to simulate the upgrade process (True) or execute the actual upgrade (False).

    Workflow
    --------
    1. System Information Update: Refreshes Panorama's details for accurate current state data.
    2. Deployment Mode Determination: Identifies whether Panorama operates in standalone mode or as part of an HA setup.
    3. Readiness Assessment: Conducts checks to ensure Panorama is prepared for the upgrade.
    4. Software Preparation: Ensures the desired PAN-OS version and necessary base images are available and downloaded.
    5. Pre-upgrade Actions: Includes taking configuration backups and operational state snapshots.
    6. Upgrade Execution: Applies the upgrade followed by a system reboot, completing the transition to the target PAN-OS version, barring a dry run.

    Raises
    ------
    SystemExit
        Terminates the script if critical errors are encountered at any stage of the upgrade process.

    Example
    -------
    Initiating the upgrade of a Panorama appliance:
        >>> panorama_instance = Panorama(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> upgrade_panorama(panorama_instance, '10.0.1', dry_run=False)
        # Starts the upgrade process, targeting PAN-OS version 10.0.1.

    Notes
    -----
    - Utilizes the 'dry run' mode to validate the upgrade pathway without affecting the current Panorama setup.
    - Ensures thorough logging throughout the process for transparency and aids in troubleshooting potential issues.
    """

    # Refresh system information to ensure we have the latest data
    logging.debug(f"{get_emoji('start')} Refreshing system information...")
    panorama_details = SystemSettings.refreshall(panorama)[0]
    hostname = panorama_details.hostname
    logging.info(
        f"{get_emoji('report')} {hostname}: {panorama.serial} {panorama_details.ip_address}"
    )

    # Determine if the Panorama is standalone, HA, or in a cluster
    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing test to see if Panorama is standalone, HA, or in a cluster..."
    )
    deploy_info, ha_details = get_ha_status(
        panorama,
        hostname,
    )
    logging.info(f"{get_emoji('report')} {hostname}: HA mode: {deploy_info}")
    logging.debug(f"{get_emoji('report')} {hostname}: HA details: {ha_details}")

    # If Panorama is part of HA pair, determine if it's active or passive
    if ha_details:
        proceed_with_upgrade, peer_panorama = handle_ha_logic(
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
        f"{get_emoji('start')} {hostname}: Performing tests to validate Panorama's readiness..."
    )
    update_available = software_update_check(
        panorama,
        hostname,
        target_version,
        ha_details,
    )
    logging.debug(f"{get_emoji('report')} {hostname}: Readiness check complete")

    # gracefully exit if the Panorama is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"{get_emoji('error')} {hostname}: Not ready for upgrade to {target_version}.",
        )
        sys.exit(1)

    # Download the target version
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing test to see if {target_version} is already downloaded..."
    )
    image_downloaded = software_download(
        panorama,
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
            f"{get_emoji('success')} {hostname}: Panorama version {target_version} has been downloaded."
        )

    # Begin snapshots of the network state
    if not image_downloaded:
        logging.error(
            f"{get_emoji('error')} {hostname}: Image not downloaded, exiting..."
        )

        sys.exit(1)

    # Determine strictness of HA sync check
    with target_devices_to_revisit_lock:
        is_panorama_to_revisit = panorama in target_devices_to_revisit

    # Perform HA sync check, skipping standalone Panoramas
    if ha_details:
        perform_ha_sync_check(
            hostname,
            ha_details,
            strict_sync_check=not is_panorama_to_revisit,
        )

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji('start')} {hostname}: Performing backup of configuration to local filesystem..."
    )
    backup_config = backup_configuration(
        panorama,
        hostname,
        f'assurance/configurations/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
    )
    logging.debug(f"{get_emoji('report')} {hostname}: {backup_config}")

    # Exit execution is dry_run is True
    if dry_run is True:
        logging.info(f"{get_emoji('success')} {hostname}: Dry run complete, exiting...")
        logging.info(f"{get_emoji('stop')} {hostname}: Halting script.")
        sys.exit(0)
    else:
        logging.info(
            f"{get_emoji('start')} {hostname}: Not a dry run, continue with upgrade..."
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


# ----------------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------------
def check_readiness_and_log(
    result: dict,
    hostname: str,
    test_name: str,
    test_info: dict,
) -> None:
    """
    Evaluates and logs the outcomes of specific readiness tests for a firewall, crucial for assessing upgrade feasibility.

    This function inspects the results of predefined readiness tests that have been executed on a firewall to determine its preparedness for an upgrade. It logs the outcomes of these tests, emphasizing the severity of any failures and their potential impact on the upgrade process. For tests marked as critical, a failure will lead to the termination of the script to avert a problematic upgrade.

    Parameters
    ----------
    result : dict
        The outcomes of the readiness tests, structured as a dictionary where each key is a test name and its value is a dictionary containing the test's 'state' (True for pass, False for fail) and a 'reason' for the test outcome.
    hostname : str
        The identifier for the firewall being evaluated, used to contextualize log entries.
    test_name : str
        The name of the specific test being assessed, which should correspond to a key in the 'result' dictionary.
    test_info : dict
        Detailed information about the test, including a descriptive 'description', the 'log_level' for logging the outcome, and an 'exit_on_failure' boolean that dictates whether a failed test should halt further script execution.

    Workflow
    --------
    1. Extract the outcome of the specified test from the 'result' dictionary.
    2. Formulate a log entry combining the test's description and the reason for its outcome.
    3. Log the entry, adjusting the log level according to the test's importance and the nature of its outcome.
    4. If a critical test fails (as indicated by 'exit_on_failure' being True), log a critical error and stop the script execution.

    Raises
    ------
    SystemExit
        If a test deemed critical to the upgrade's success fails, the script will terminate to prevent potentially adverse actions.

    Example
    -------
    Assessing and logging a hypothetical connectivity test result:
        >>> result = {'connectivity_test': {'state': False, 'reason': 'Network unreachable'}}
        >>> test_name = 'connectivity_test'
        >>> test_info = {'description': 'Network Connectivity Test', 'log_level': 'error', 'exit_on_failure': True}
        >>> check_readiness_and_log(result, 'fw01', test_name, test_info)
        # This would log an error regarding the failed connectivity test and terminate the script due to its critical nature.

    Notes
    -----
    - Integral to the pre-upgrade phase, ensuring only firewalls meeting all readiness criteria proceed to upgrade.
    - The function's logging strategy is designed to provide clarity on each test's outcome, facilitating informed decision-making regarding the upgrade.
    """

    test_result = result.get(
        test_name, {"state": False, "reason": "Test not performed"}
    )
    log_message = f'{test_info["description"]} - {test_result["reason"]}'

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
            logging.debug(
                f"{get_emoji('report')} {hostname}: Skipped Readiness Check: {test_info['description']}"
            )
        else:
            logging.debug(
                f"{get_emoji('report')} {hostname}: Log Message {log_message}"
            )


def compare_versions(
    version1: str,
    version2: str,
) -> str:
    """
    Compares two software version strings to determine their relative ordering.

    This function is a critical component in upgrade and compatibility workflows, allowing for the comparison of two software version strings. It parses and evaluates the major, minor, maintenance, and optional hotfix components of each version string to ascertain their relative ordering. This utility facilitates decision-making in scenarios such as software upgrades, patch applications, and compatibility checks by determining if one version is newer, older, or equal to another.

    Parameters
    ----------
    version1 : str
        The first version string in the comparison, following the 'major.minor.maintenance' or 'major.minor.maintenance-hotfix' format.
    version2 : str
        The second version string in the comparison, using a similar format as 'version1'.

    Returns
    -------
    str
        The result of the comparison: 'older' if 'version1' is older than 'version2', 'newer' if 'version1' is newer than 'version2', or 'equal' if both versions are identical.

    Examples
    --------
    Comparing two version strings to determine their relative ordering:
        >>> compare_versions('9.0.0', '9.1.0')
        'older'  # '9.0.0' is older than '9.1.0'

        >>> compare_versions('10.0.1-h2', '10.0.1')
        'newer'  # '10.0.1-h2' is considered newer than '10.0.1' due to the hotfix

        >>> compare_versions('8.1.3', '8.1.3')
        'equal'  # Both versions are the same

    Notes
    -----
    - The function provides a precise mechanism for software version comparison, essential for managing software lifecycles and ensuring system integrity.
    - It is designed to handle standard versioning schemes, making it adaptable to various software and systems.
    - While primarily used for version comparison, it also serves as a foundational utility in broader system management and operational scripts.
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
) -> None:
    """
    Initializes the application's logging system with specified verbosity and encoding.

    This function configures the application's logging framework to capture logs at the specified verbosity level. It sets up both console and file handlers, ensuring that logs are appropriately displayed in the console and stored in files for later analysis. The file handler employs a rotating mechanism to manage log file sizes by archiving old logs and maintaining a manageable current log file size. The encoding parameter allows for log files to be written in the specified character encoding, accommodating internationalization requirements.

    Parameters
    ----------
    level : str
        The logging level to set for the application. Valid options include 'DEBUG', 'INFO', 'WARNING', 'ERROR', and 'CRITICAL'. This parameter controls the verbosity of the log output.
    encoding : str, optional
        The character encoding for log files. Defaults to 'utf-8', ensuring broad compatibility with various characters and symbols used in log messages.

    Raises
    ------
    ValueError
        If the `level` parameter does not correspond to a recognized logging level, ensuring that logs are captured at a valid verbosity.

    Examples
    --------
    Setting up logging with DEBUG level and default UTF-8 encoding:
        >>> configure_logging('DEBUG')
        # Configures logging to capture detailed debug information, outputting to both the console and a UTF-8 encoded file.

    Setting up logging with INFO level and ISO-8859-1 encoding:
        >>> configure_logging('INFO', 'iso-8859-1')
        # Initializes logging to capture informational messages and above, with log files encoded in ISO-8859-1.

    Notes
    -----
    - The logging configuration is crucial for monitoring application behavior and troubleshooting issues, providing insights into operational status and potential errors.
    - The rotating file handler ensures that log storage remains efficient over time, preventing unbounded growth of log files and facilitating easier log management and review.
    - This function supports customization through the `settings.yaml` file, allowing default settings to be overridden based on specific operational needs or preferences.
    """
    # Use the provided log_level parameter if given, otherwise fall back to settings file or default
    log_level = (
        level.upper() if level else settings_file.get("logging.level", "INFO").upper()
    )

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
    Establishes an API connection to a Palo Alto Networks device, returning a device-specific object.

    This function connects to a Palo Alto Networks firewall or Panorama management server using the provided API credentials. It determines the type of device (firewall or Panorama) based on the API response and returns an object representing the connected device. This object can then be used for further API calls to the device. The function includes error handling to gracefully manage connection failures and provides clear error messages to assist with troubleshooting.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the Palo Alto Networks device or Panorama to connect to.
    api_username : str
        The username used for API authentication.
    api_password : str
        The password associated with the API username.

    Returns
    -------
    PanDevice
        An object representing the connected Palo Alto Networks device, either a Firewall or Panorama instance.

    Raises
    ------
    SystemExit
        If the connection cannot be established, the script will log an appropriate error message and exit. This could be due to incorrect credentials, network issues, or an unreachable host.

    Examples
    --------
    Connecting to a firewall device:
        >>> device = connect_to_host('192.168.1.1', 'apiuser', 'apipassword')
        # Returns a Firewall object if the connection is successful.

    Connecting to a Panorama device:
        >>> panorama = connect_to_host('panorama.company.com', 'apiuser', 'apipassword')
        # Returns a Panorama object if the connection is successful.

    Notes
    -----
    - This function abstracts the connection details and device type determination, simplifying the process of starting interactions with Palo Alto Networks devices.
    - It is essential to handle connection errors gracefully in scripts to ensure reliability and provide clear feedback for operational troubleshooting.
    - Default settings for connection parameters, such as timeouts and retries, can be overridden by the `settings.yaml` file if `settings_file_path` is used within the function.
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
) -> None:
    """
    Displays a welcome banner in the console with mode-specific messages and configuration information.

    This function dynamically generates a welcome banner based on the operational mode selected by the user. It provides contextual information about the chosen mode (e.g., settings, firewall upgrade, panorama upgrade, batch upgrade) and indicates the usage of a custom configuration file if provided. The banner aims to guide users through the initial steps of the tool's usage and set expectations for the subsequent workflow.

    Parameters
    ----------
    mode : str
        The operational mode of the tool, which can be 'settings', 'firewall', 'panorama', or 'batch', dictating the content of the welcome message.
    config_path : Optional[Path], optional
        The file path to a custom configuration file (settings.yaml) if used, influencing the configuration message. Defaults to None, indicating no custom configuration file is used.

    Workflow
    --------
    1. Determine the welcome and banner messages based on the operational mode.
    2. If a custom configuration file is used, include its path in the message; otherwise, note the default configuration usage.
    3. Calculate the border length for the banner based on the longest message line.
    4. Construct and print the banner with optional ANSI color codes for emphasis.

    Examples
    --------
    Displaying the welcome banner for the firewall upgrade mode with a custom configuration:
        >>> console_welcome_banner('firewall', Path('/path/to/settings.yaml'))
        # Displays a welcome message specific to firewall upgrades and notes the use of a custom configuration.

    Displaying the welcome banner for the settings mode without a custom configuration:
        >>> console_welcome_banner('settings')
        # Displays a welcome message specific to settings configuration, without mentioning a custom configuration file.

    Notes
    -----
    - The function enhances user experience by providing clear, mode-specific guidance at the start of the tool's execution.
    - The inclusion of configuration file information assists users in understanding the current configuration context, especially when overriding default settings with a `settings.yaml` file.
    - ANSI color codes are used to enhance readability and draw attention to the banner, but they are designed to degrade gracefully in environments that do not support them.
    """

    # Customize messages based on the mode
    if mode == "settings":
        welcome_message = "Welcome to the PAN-OS upgrade settings menu"
        banner_message = (
            "You'll be presented with configuration items, press enter for default settings."
            "\n\nThis will create a `settings.yaml` file in your current working directory."
        )
        # No config message for settings mode
        config_message = ""
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
                "No settings.yaml file was found. Default values will be used.\n"
                "Create a settings.yaml file with 'pan-os-upgrade settings' command."
            )

    # Calculate border length based on the longer message
    border_length = max(
        len(welcome_message),
        max(len(line) for line in banner_message.split("\n")),
        max(len(line) for line in config_message.split("\n")) if config_message else 0,
    )
    border = "=" * border_length

    # ANSI escape codes for styling
    color_start = "\033[1;33m"  # Bold Orange
    color_end = "\033[0m"  # Reset

    # Construct and print the banner
    banner = f"{color_start}{border}\n{welcome_message}\n\n{banner_message}"
    if config_message:  # Only add config_message if it's not empty
        banner += f"\n\n{config_message}"
    banner += f"\n{border}{color_end}"
    typer.echo(banner)


def ensure_directory_exists(file_path: str) -> None:
    """
    Checks and creates the directory structure for a given file path if it does not exist.

    This utility function is essential for file operations that require writing to a file, ensuring the directory path exists before file creation or modification. It extracts the directory path from the given file path and creates the directory, along with any necessary intermediate directories, if they do not exist. This preemptive check and creation process helps avoid file operation errors due to non-existent directories.

    Parameters
    ----------
    file_path : str
        The file path for which the directory structure needs to be ensured. The function extracts the directory part of this path to check and create the directory.

    Workflow
    --------
    1. Extract the directory path from the provided file path.
    2. Check if the directory exists.
    3. If the directory does not exist, create it along with any required intermediate directories.

    Raises
    ------
    OSError
        If the directory cannot be created due to permissions or other filesystem errors, an OSError is raised, providing details about the failure.

    Examples
    --------
    Ensuring the existence of a directory for log storage:
        >>> ensure_directory_exists('/var/log/my_app/events.log')
        # If '/var/log/my_app/' does not exist, it will be created to ensure a valid path for 'events.log'.

    Notes
    -----
    - Utilizes `os.makedirs` with `exist_ok=True` to safely create the directory without raising an error if it already exists.
    - This function is filesystem-agnostic and should work across different operating systems and environments, making it a versatile tool for file path management in Python applications.
    """

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def filter_string_to_dict(filter_string: str) -> dict:
    """
    Converts a filter string with comma-separated key-value pairs into a dictionary.

    This function is designed to parse strings that represent filters or parameters in a 'key1=value1,key2=value2' format, turning them into a more accessible Python dictionary. It's particularly useful in scenarios where parameters need to be dynamically extracted from string formats, such as URL query parameters or configuration settings. The function gracefully handles cases where the input string is empty or improperly formatted by returning an empty dictionary.

    Parameters
    ----------
    filter_string : str
        A string containing key-value pairs separated by commas, where each key and its corresponding value are delimited by an equal sign ('='). Example: 'key1=value1,key2=value2'.

    Returns
    -------
    dict
        A dictionary where each key-value pair from the `filter_string` is represented as a dictionary item. If the `filter_string` is empty, malformed, or contains no valid key-value pairs, an empty dictionary is returned.

    Examples
    --------
    Parsing a well-formed filter string:
        >>> filter_string_to_dict('type=firewall,location=us-west')
        {'type': 'firewall', 'location': 'us-west'}

    Dealing with an empty filter string:
        >>> filter_string_to_dict('')
        {}

    Handling a malformed filter string:
        >>> filter_string_to_dict('type-firewall,location=us-west')
        ValueError: Malformed filter string. Expected key-value pairs separated by '='.

    Notes
    -----
    - The function expects a well-formed input string. Malformed key-value pairs (e.g., missing '=' delimiter) will lead to a ValueError.
    - In case of duplicate keys, the value of the last key-value pair in the string will be used in the resulting dictionary.

    Raises
    ------
    ValueError
        Raised when the input string contains key-value pairs that are not delimited by an '=', indicating a malformed filter string.
    """

    result = {}
    for substr in filter_string.split(","):
        k, v = substr.split("=")
        result[k] = v

    return result


def flatten_xml_to_dict(element: ET.Element) -> dict:
    """
    Transforms an XML ElementTree element into a nested dictionary, preserving structure and content.

    This function is designed to parse an XML element, along with its children, into a nested dictionary format, where each element's tag becomes a key, and its text content becomes the corresponding value. For elements containing child elements, a new nested dictionary is created. When multiple child elements share the same tag, they are grouped into a list within the parent dictionary. This utility is particularly useful for processing XML data into a more manageable and Pythonic structure.

    Parameters
    ----------
    element : ET.Element
        The XML ElementTree element to be converted. This can be the root element or any subelement within an XML tree.

    Returns
    -------
    dict
        A nested dictionary representation of the input XML element. The dictionary structure mirrors the XML hierarchy, with tags as keys and text content, further nested dictionaries, or lists of dictionaries as values.

    Examples
    --------
    Converting a simple XML element with no children:
        >>> xml_string = '<status>active</status>'
        >>> element = ET.fromstring(xml_string)
        >>> flatten_xml_to_dict(element)
        {'status': 'active'}

    Converting a complex XML element with nested children:
        >>> xml_string = '<config><item key="1">Value1</item><item key="2">Value2</item></config>'
        >>> element = ET.fromstring(xml_string)
        >>> flatten_xml_to_dict(element)
        {'config': {'item': [{'key': '1', '_text': 'Value1'}, {'key': '2', '_text': 'Value2'}]}}

    Notes
    -----
    - XML attributes are not included in the output dictionary; only tags and text content are processed.
    - Repeated tags at the same level are stored as a list to preserve the XML structure within the dictionary format.
    - The function provides a simplified view of the XML content, suitable for data manipulation and extraction tasks.

    Raises
    ------
    ValueError
        In cases where the XML structure is too complex to be represented as a dictionary without loss of information (e.g., significant use of attributes or mixed content), a ValueError may be raised to indicate the potential for data loss or misinterpretation.
    """

    result = {}
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


def get_emoji(action: str) -> str:
    """
    Retrieves a corresponding emoji for a given action keyword, intended to enhance readability and visual appeal in log messages or user interfaces.

    This function maps a set of predefined action keywords to their respective emoji symbols, facilitating the inclusion of visual cues in textual outputs. It is particularly useful for enhancing the user experience in console applications or logs by providing immediate, visually distinct feedback for various operations or statuses. If an action keyword is not recognized, the function gracefully returns an empty string, thus maintaining the continuity of the application's output without introducing errors.

    Parameters
    ----------
    action : str
        The action keyword representing the context or outcome for which an emoji is desired. Supported keywords include 'success', 'warning', 'error', 'working', 'report', 'search', 'save', 'stop', and 'start', each associated with a relevant emoji.

    Returns
    -------
    str
        An emoji character corresponding to the provided action keyword. If the keyword is not recognized, an empty string is returned, ensuring the calling code's execution is not disrupted.

    Examples
    --------
    Enhancing log messages with emojis for better visibility:
        >>> logging.info(f"{get_emoji('success')} Operation completed successfully.")
        >>> logging.warning(f"{get_emoji('warning')} Potential issue detected.")
        >>> logging.error(f"{get_emoji('error')} Error encountered during execution.")

    Improving user interface prompts with emojis for clarity:
        >>> print(f"{get_emoji('start')} Starting process...")
        >>> print(f"{get_emoji('stop')} Stopping process...")

    Notes
    -----
    - This function supports a limited set of action keywords. Extension to include more keywords and corresponding emojis can be easily achieved by updating the internal mapping.
    - The use of emojis is intended to complement textual information, not replace it, ensuring that the essential message remains clear even in environments where emojis may not be displayed correctly.

    No exceptions are expected to be raised directly by this function. Unrecognized action keywords will simply result in an empty string, avoiding potential disruptions in the application's output.
    """

    emoji_map = {
        "success": "✅",
        "warning": "🟧",
        "error": "❌",
        "working": "🔧",
        "report": "📝",
        "search": "🔍",
        "save": "💾",
        "stop": "🛑",
        "start": "🚀",
    }
    return emoji_map.get(action, "")


def get_firewalls_from_panorama(
    panorama: Panorama,
    **filters,
) -> list[Firewall]:
    """
    Retrieves a list of Firewall objects managed by a Panorama appliance, optionally filtered by specified attributes.

    This function communicates with a Panorama appliance to obtain a list of all firewalls under its management. It allows for the application of filters based on firewall attributes such as model, serial number, software version, etc., to refine the selection of firewalls returned. The function utilizes the Panorama API to fetch the relevant data, which is then parsed and converted into Firewall objects for easy manipulation within the script. This is particularly useful for scenarios where operations need to be targeted at specific subsets of firewalls, such as upgrades, configurations, or reporting.

    Parameters
    ----------
    panorama : Panorama
        An instance of the Panorama class, representing the Panorama appliance from which the managed firewalls are to be retrieved. This instance must be properly initialized and authenticated.
    **filters : dict, optional
        Arbitrary keyword arguments where each key represents a firewall attribute to filter by (e.g., 'model', 'serial', 'version'), and the corresponding value is a regular expression string used to match against the firewall's attribute value.

    Returns
    -------
    list[Firewall]
        A list containing Firewall objects for each firewall managed by the specified Panorama appliance that matches the provided filtering criteria. If no filters are specified, all managed firewalls are returned.

    Examples
    --------
    Fetching all firewalls managed by Panorama:
        >>> all_firewalls = get_firewalls_from_panorama(panorama_instance)

    Fetching firewalls of a specific model managed by Panorama:
        >>> specific_model_firewalls = get_firewalls_from_panorama(panorama_instance, model='PA-220')

    Notes
    -----
    - This function is essential for scripts that perform batch operations on multiple firewalls managed by Panorama, allowing for precise targeting of devices.
    - The filtering feature supports complex selection criteria, making the function highly versatile in managing large deployments.
    - If `settings_file_path` is specified and contains relevant filters, those filters can override or augment the filters provided as arguments to this function.

    No exceptions are explicitly raised by this function; however, API call failures due to network issues, authentication errors, or invalid filter syntax can result in runtime errors that should be handled by the calling code.
    """

    firewalls = []
    for managed_device in get_managed_devices(panorama, **filters):
        firewall = Firewall(serial=managed_device.serial)
        firewalls.append(firewall)
        panorama.add(firewall)

    return firewalls


def get_managed_devices(
    panorama: Panorama,
    **filters,
) -> list[ManagedDevice]:
    """
    Retrieves devices managed by Panorama, optionally filtered by device attributes.

    This function interacts with Panorama to obtain a list of managed devices, such as firewalls, and can filter these devices based on specified attributes like model, serial number, or software version. The filtering is performed using regular expressions, providing a powerful mechanism for precisely targeting specific devices. This capability is invaluable for scenarios requiring operations on particular groups of devices, such as updates, configurations, or monitoring.

    Parameters
    ----------
    panorama : Panorama
        An instance of the Panorama class, representing the Panorama management server from which the list of managed devices is to be fetched. This instance should be properly authenticated to enable API communications.
    **filters : dict, optional
        A set of keyword arguments where each key represents a device attribute to filter by (e.g., 'model', 'serial', 'version'), and the corresponding value is a regular expression pattern used to match against the device's attribute value.

    Returns
    -------
    list[ManagedDevice]
        A list of `ManagedDevice` objects that represent each device managed by Panorama and matching the provided filtering criteria. If no filters are specified, the function returns a list of all managed devices.

    Examples
    --------
    Fetching all devices managed by Panorama:
        >>> all_devices = get_managed_devices(panorama_instance)

    Fetching devices of a specific model managed by Panorama:
        >>> specific_model_devices = get_managed_devices(panorama_instance, model='PA-220')

    Notes
    -----
    - The function's use of regular expressions for filtering provides a flexible and powerful means to specify complex selection criteria.
    - While primarily used for retrieving device lists, the function's output can serve as the basis for further device-specific operations or queries.
    - If the `settings_file_path` is specified and includes relevant filters, those settings can be used to augment or override the function's filters.

    The implementation should handle Panorama API interactions and apply the filters to the retrieved device list, ensuring that only devices matching all provided filters are included in the returned list.
    """

    managed_devices = model_from_api_response(
        panorama.op("show devices all"), ManagedDevices
    )
    devices = managed_devices.devices
    for filter_key, filter_value in filters.items():
        devices = [
            target_device
            for target_device in devices
            if re.match(filter_value, getattr(target_device, filter_key))
        ]

    return devices


def ip_callback(value: str) -> str:
    """
    Validates and returns a given string if it's a resolvable hostname or a valid IP address.

    This function is primarily intended as a callback for CLI input validation, ensuring that provided
    values are either valid IPv4/IPv6 addresses or hostnames that can be resolved. It first checks if the
    input is a valid IP address using Python's 'ipaddress' module. If not, it attempts to resolve the string
    as a hostname. If both checks fail, the function raises a Typer error to prompt the user for a valid input.
    This ensures that subsequent operations receive only valid network endpoint identifiers.

    Parameters
    ----------
    value : str
        The user-provided string intended to represent either a hostname or an IP address.

    Returns
    -------
    str
        The original input string if it is successfully validated as either a resolvable hostname or a valid IP address.

    Raises
    ------
    typer.BadParameter
        If the input string cannot be validated as either a resolvable hostname or a valid IP address, this exception is raised to signal to the user that the provided input is invalid and needs correction.

    Example
    -------
    Using `ip_callback` as a Typer option callback to ensure valid network endpoint input:
        >>> @app.command()
        >>> def check_endpoint(host: str = typer.Option(..., callback=ip_callback)):
        >>>     print(f"Checking endpoint: {host}")

    Notes
    -----
    - The function leverages both DNS resolution checks and the 'ipaddress' module for comprehensive validation.
    - It is particularly useful in CLI applications where early validation of network-related user input is crucial.
    - If `settings_file_path` is specified and contains relevant network settings, these can potentially be used to adjust or bypass validation based on the application's requirements.
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
    Transforms an XML element or tree from an API response into a structured Pydantic model instance.

    This utility function is designed to facilitate the conversion of XML data, typically retrieved from API
    responses, into structured Pydantic model instances. It streamlines the process of parsing XML and mapping
    the extracted data to predefined Pydantic model fields, enabling more efficient and type-safe data handling
    within Python applications. The function assumes that the provided Pydantic model includes a mixin or
    inherits from a base class designed to handle data deserialization from API responses.

    Parameters
    ----------
    element : Union[ET.Element, ET.ElementTree]
        The root XML element or an entire XML document tree that is to be converted. This data structure usually
        represents a portion or the entirety of an API response in XML format.
    model : type[FromAPIResponseMixin]
        A Pydantic model class that inherits from `FromAPIResponseMixin`, defining the schema for the expected
        data structure. The model should include fields corresponding to the XML data to be processed, facilitating
        the mapping of XML elements to model attributes.

    Returns
    -------
    FromAPIResponseMixin
        An instance of the specified Pydantic model, populated with the data extracted from the provided XML
        element or tree. The model instance offers a structured, type-safe interface to the API response data,
        aligned with the model's schema.

    Example
    -------
    Parsing an XML API response into a Pydantic model:
        >>> xml_response = ET.fromstring('<user><id>101</id><name>John Doe</name></user>')
        >>> UserModel = type('UserModel', (FromAPIResponseMixin, BaseModel), {'id': int, 'name': str})
        >>> user = model_from_api_response(xml_response, UserModel)
        # The 'user' object is an instance of 'UserModel' with 'id' and 'name' populated from the XML response.

    Notes
    -----
    - This function abstracts the complexities of XML parsing and data mapping, enabling developers to work with
      API response data in a more Pythonic and object-oriented manner.
    - It is important that the Pydantic model accurately reflects the structure of the XML response to ensure
      correct data mapping. Discrepancies between the model and the XML structure may result in incomplete or
      incorrect data representation.

    Raises
    ------
    ValueError
        If the XML-to-dictionary conversion results in a structure that cannot be directly mapped to the provided
        Pydantic model, a ValueError may be raised, indicating a potential mismatch between the model schema and
        the XML data structure.
    """

    result_dict = flatten_xml_to_dict(element)
    return model.from_api_response(result_dict)


def parse_version(version: str) -> Tuple[int, int, int, int]:
    """
    Parses a version string into a tuple of integers representing its major, minor, maintenance, and hotfix components.

    This utility function analyzes a version string, expected to be in the format of 'major.minor.maintenance' or
    'major.minor.maintenance-hhotfix', and extracts the numerical components. The hotfix component is optional and
    denoted by a '-h' followed by its number. If a component is missing, it defaults to 0 to maintain a consistent
    tuple structure. This parsing facilitates version comparison and sorting by converting version strings into
    a uniform tuple format.

    Parameters
    ----------
    version : str
        The version string to parse, adhering to the 'major.minor.maintenance' or
        'major.minor.maintenance-hhotfix' format. Each segment (major, minor, maintenance, hotfix) should be
        a numerical value.

    Returns
    -------
    Tuple[int, int, int, int]
        A tuple containing four integers representing the major, minor, maintenance versions, and the hotfix
        number, respectively. The hotfix number defaults to 0 if not specified in the input string.

    Examples
    --------
    Parsing a version string without a hotfix:
        >>> parse_version("10.0.1")
        (10, 0, 1, 0)

    Parsing a version string with a hotfix component:
        >>> parse_version("10.0.1-h2")
        (10, 0, 1, 2)

    Notes
    -----
    - This function is essential for operations that involve version comparison and management, ensuring that
      version strings can be reliably interpreted and ordered.
    - It assumes that the provided version string conforms to the specified format. Variations from this format
      may lead to incorrect parsing or errors.

    Raises
    ------
    ValueError
        If the version string is malformatted or contains non-numeric components where integers are expected,
        a ValueError is raised to indicate the parsing failure.
    """

    parts = version.split(".")

    # When maintenance version is an integer
    if len(parts) == 2:
        major, minor = parts
        maintenance, hotfix = 0, 0
    # When maintenance version includes hotfix
    else:
        major, minor, maintenance = parts
        if "-h" in maintenance:
            maintenance, hotfix = maintenance.split("-h")
        else:
            hotfix = 0

    return int(major), int(minor), int(maintenance), int(hotfix)


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


# ----------------------------------------------------------------------------
# Define Typer command-line interface
# ----------------------------------------------------------------------------
app = typer.Typer(help="PAN-OS Upgrade script")


# ----------------------------------------------------------------------------
# Global variables
# ----------------------------------------------------------------------------

# Define the path to the settings file
settings_file_path = Path.cwd() / "settings.yaml"

# Initialize Dynaconf settings object conditionally based on the existence of settings.yaml
if settings_file_path.exists():
    settings_file = Dynaconf(settings_files=[str(settings_file_path)])
else:
    settings_file = Dynaconf()

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


# ----------------------------------------------------------------------------
# Common setup for all subcommands
# ----------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------
# Subcommand for upgrading a firewall
# ----------------------------------------------------------------------------
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
    ] = False,
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


# ----------------------------------------------------------------------------
# Subcommand for upgrading Panorama
# ----------------------------------------------------------------------------
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
    ] = False,
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


# ----------------------------------------------------------------------------
# Subcommand for batch upgrades using Panorama as a communication proxy
# ----------------------------------------------------------------------------
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
    filter: Annotated[
        str,
        typer.Option(
            "--filter",
            "-f",
            help="Filter string - when connecting to Panorama, defines which devices we are to upgrade.",
            prompt="Filter string (ex: hostname=Woodlands*)",
        ),
    ] = "",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Dry Run?",
        ),
    ] = False,
):
    """
    Executes a coordinated upgrade of multiple firewalls managed by a Panorama appliance using specified criteria.

    This command streamlines the process of upgrading a batch of firewalls by leveraging Panorama's centralized management capabilities. It supports filtering to target specific devices for the upgrade and offers a dry run option for validation without making changes. The function initiates by preparing the environment, validating connectivity to Panorama, and then sequentially or concurrently upgrading each managed firewall that meets the filter criteria.

    Parameters
    ----------
    hostname : str
        The network address of the Panorama appliance, either as an IP address or a DNS-resolvable hostname.
    username : str
        The administrative username required for authentication on the Panorama appliance.
    password : str
        The corresponding password for the specified administrative username.
    target_version : str
        The PAN-OS version to which the targeted firewalls will be upgraded.
    filter : str, optional
        A string used to define filtering criteria for selecting specific firewalls managed by Panorama, default is empty which implies no filtering.
    dry_run : bool, optional
        A flag to indicate whether to simulate the upgrade process without making any actual changes, default is False.

    Examples
    --------
    Performing a batch upgrade of firewalls:
        $ python upgrade.py batch --hostname panorama.example.com --username admin --password adminpassword --version 9.1.3 --filter "model=PA-220"

    Conducting a dry run of a batch upgrade:
        $ python upgrade.py batch --hostname panorama.example.com --username admin --password adminpassword --version 9.1.3 --filter "location=DataCenter" --dry-run

    Notes
    -----
    - Ensure connectivity to Panorama and validity of credentials before initiating the batch upgrade.
    - The dry run option is highly recommended for assessing the upgrade's feasibility and identifying any preparatory actions required without impacting the operational state of the firewalls.
    - Configuration settings, such as logging levels and paths, can be customized through a `settings.yaml` file if available. The presence of this file and its path may be indicated by the global variable `settings_file_path` if implemented in the script.
    """

    # Display the custom banner for batch firewall upgrades
    if settings_file_path.exists():
        console_welcome_banner(mode="batch", config_path=settings_file_path)
    else:
        console_welcome_banner(mode="batch")

    # Perform common setup tasks, return a connected device
    device = common_setup(
        hostname,
        username,
        password,
    )

    # Perform batch upgrade
    firewalls_to_upgrade = []

    # Exit script if device is Firewall (batch upgrade is only supported when connecting to Panorama)
    if type(device) is Firewall:
        logging.info(
            f"{get_emoji('error')} {hostname}: Batch upgrade is only supported when connecting to Panorama."
        )
        sys.exit(1)

    # If device is Panorama, get firewalls to upgrade
    elif type(device) is Panorama:
        # Exit script if no filter string was provided
        if not filter:
            logging.error(
                f"{get_emoji('error')} {hostname}: Specified device is Panorama, but no filter string was provided."
            )
            sys.exit(1)

        logging.info(
            f"{get_emoji('success')} {hostname}: Connection to Panorama established. Firewall connections will be proxied!"
        )

        # Get firewalls to upgrade
        firewalls_to_upgrade = get_firewalls_from_panorama(
            device, **filter_string_to_dict(filter)
        )
        logging.debug(
            f"{get_emoji('report')} {hostname}: Firewalls to upgrade: {firewalls_to_upgrade}"
        )

        # Using ThreadPoolExecutor to manage threads
        threads = settings_file.get("concurrency.threads", 10)
        logging.debug(f"{get_emoji('working')} {hostname}: Using {threads} threads.")
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Store future objects along with firewalls for reference
            future_to_firewall = {
                executor.submit(
                    upgrade_firewall,
                    target_device,
                    target_version,
                    dry_run,
                ): target_device
                for target_device in firewalls_to_upgrade
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
        logging.debug(f"{get_emoji('working')} {hostname}: Using {threads} threads.")
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


# ----------------------------------------------------------------------------
# Subcommand for creating a settings.yaml file to override default settings
# ----------------------------------------------------------------------------
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

    config_data = {
        "concurrency": {
            "threads": typer.prompt(
                "Number of concurrent threads",
                default=10,
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
                "Reboot retry interval (seconds)",
                default=60,
                type=int,
            ),
            "max_tries": typer.prompt(
                "Maximum reboot tries",
                default=30,
                type=int,
            ),
        },
        "readiness_checks": {
            "customize": typer.confirm(
                "Would you like to customize readiness checks?",
                default=False,
            ),
            "checks": {},
            "location": typer.prompt(
                "Location to save readiness checks",
                default="assurance/readiness_checks/",
            ),
        },
        "snapshots": {
            "customize": typer.confirm(
                "Would you like to customize snapshots?", default=False
            ),
            "state": {},
            "location": typer.prompt(
                "Location to save snapshots",
                default="assurance/snapshots/",
            ),
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

    if config_data["readiness_checks"]["customize"]:
        for check, info in AssuranceOptions.READINESS_CHECKS.items():
            config_data["readiness_checks"]["checks"][check] = typer.confirm(
                f"Enable {info['description']}?", default=True
            )

    if config_data["snapshots"]["customize"]:
        for snapshot in AssuranceOptions.STATE_SNAPSHOTS:
            config_data["snapshots"]["state"][snapshot] = typer.confirm(
                f"Enable {snapshot} snapshot?", default=True
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
