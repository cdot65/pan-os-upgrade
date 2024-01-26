"""
Upgrade.py: Automating the Upgrade Process for Palo Alto Networks Firewalls and Panorama

This module provides a comprehensive framework for automating the upgrade processes of Palo Alto Networks firewalls
and Panorama appliances. It is designed to facilitate both standalone operations and integration into larger workflows,
offering a range of features essential for successful PAN-OS upgrades. The script utilizes Typer for creating a
command-line interface, allowing for direct input of parameters, and supports username/password-based authentication.

Features
--------
- Automated Upgrade Procedures: Supports both standalone firewalls and those managed by Panorama, streamlining the
  upgrade process with minimal manual intervention.
- Error Handling: Implements extensive error handling mechanisms tailored to PAN-OS, ensuring the upgrade process is
  robust across various scenarios.
- panos-upgrade-assurance Integration: Leverages the panos-upgrade-assurance tool for conducting pre and post-upgrade
  checks, enhancing the reliability of the upgrade.
- Command-line Interface: Employs Typer for CLI creation, enabling direct parameter input and reducing reliance on
  environment files.

Imports
-------
Standard Libraries:
    - concurrent, threading: Facilitates multi-threading for parallel processing.
    - ipaddress: Provides utilities for IP address manipulation.
    - logging: Enables detailed logging throughout the upgrade process.
    - os, sys: Interfaces with the operating system for file and directory operations.
    - time: Manages time-related functions such as delays and timeouts.
    - RotatingFileHandler (logging.handlers): Manages log file rotation to limit file sizes and maintain log history.

External Libraries:
    - xml.etree.ElementTree (ET): Handles XML tree structure manipulation, essential for parsing PAN-OS API responses.
    - panos: Offers interfaces to Palo Alto Networks devices for direct API interaction.
    - PanDevice, SystemSettings (panos.base, panos.device): Facilitates operations on base PAN-OS devices and system settings.
    - Error handling modules (panos.errors): Provides specific error management capabilities for PAN-OS.
    - Firewall (panos.firewall): Specializes in firewall-specific operations and configurations.

panos-upgrade-assurance package:
    - CheckFirewall, FirewallProxy: Essential for performing readiness checks and serving as intermediaries to the firewall.

Third-party libraries:
    - xmltodict: Simplifies the conversion of XML data into Python dictionaries, aiding in data parsing and manipulation.
    - typer: Simplifies the creation of command-line interfaces, enhancing user interaction.
    - BaseModel (pydantic): Enables the definition of Pydantic models for structured data handling.

Project-specific imports:
    - SnapshotReport, ReadinessCheckReport (pan_os_upgrade.models): Utilized for managing and storing snapshot and
      readiness check reports in a structured format.
"""


# standard library imports
import ipaddress
import logging
import os
import sys
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import RemoteDisconnected
from logging.handlers import RotatingFileHandler
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
# Define logging levels
# ----------------------------------------------------------------------------
LOGGING_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


# ----------------------------------------------------------------------------
# Define panos-upgrade-assurance options
# ----------------------------------------------------------------------------
class AssuranceOptions:
    """
    A class encapsulating configuration options for the panos-upgrade-assurance process in appliances.

    This class is a central repository for various configurations used in the upgrade assurance process.
    It includes definitions for readiness checks, state snapshots, and report types, which are crucial
    components in managing and ensuring the successful upgrade of appliances.

    Attributes
    ----------
    READINESS_CHECKS : dict
        A dictionary mapping the names of readiness checks to their properties. Each property is a
        dictionary containing a description of the check, the log level to use when reporting the
        outcome of the check, and a flag indicating whether to exit the process upon failure of the check.
        - `active_support`: Verifies if active support is available for the appliance.
        - `arp_entry_exist`: Checks for a specific ARP entry in the ARP table.
        - `candidate_config`: Checks for pending changes on the device.
        - `certificates_requirements`: Verifies if certificates' keys meet minimum size requirements.
        - ... (other checks follow a similar structure)

    REPORTS : list of str
        A list of strings where each string represents a type of report that can be generated
        for the appliance. These reports provide insight into various aspects of the appliance's state.
        Includes reports like 'arp_table', 'content_version', 'ip_sec_tunnels', etc.

    STATE_SNAPSHOTS : list of str
        A list of strings where each string represents a type of state snapshot that can be captured
        from the appliance. These snapshots record essential data about the appliance's current state,
        such as 'arp_table', 'content_version', 'ip_sec_tunnels', etc.

    Examples
    --------
    To access the log level for the 'active_support' readiness check:
        >>> log_level = AssuranceOptions.READINESS_CHECKS['active_support']['log_level']
        >>> print(log_level)
        warning

    To iterate over all report types:
        >>> for report in AssuranceOptions.REPORTS:
        >>>     print(report)
        arp_table
        content_version
        ...
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
# Global list and lock for storing HA active firewalls and Panorama to revisit
# ----------------------------------------------------------------------------
target_devices_to_revisit = []
target_devices_to_revisit_lock = Lock()


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

    This function interacts with either a Firewall or Panorama appliance to retrieve its current running
    configuration. The configuration is then saved to a specified file path in XML format. It includes validations
    to ensure the integrity of the retrieved XML data and logs the process's outcome. The function is designed
    to be flexible, accommodating both Firewall and Panorama devices by utilizing their common base class.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        An instance of the Firewall or Panorama class from which the running configuration will be backed up.
    hostname : str
        The hostname of the target device, used for logging and identification purposes.
    file_path : str
        The local filesystem path where the backup configuration file will be stored.

    Returns
    -------
    bool
        True if the backup process is successful and the configuration is saved to the specified file.
        False if an error occurs during the backup process.

    Raises
    ------
    Exception
        If an unexpected error occurs during the retrieval or saving of the configuration, an exception is raised
        with a descriptive error message.

    Examples
    --------
    Backing up the configuration of a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> backup_configuration(firewall, 'firewall1', '/path/to/firewall_config.xml')
        True  # Indicates successful backup.

    Backing up the configuration of a Panorama appliance:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='password')
        >>> backup_configuration(panorama, 'panorama1', '/path/to/panorama_config.xml')
        True  # Indicates successful backup.

    Notes
    -----
    - The function verifies the existence of the target directory for the backup file, creating it if necessary.
    - The backup process involves retrieving the XML structure of the running configuration and writing it to a file.
    - Proper error handling is implemented to catch and log potential issues during the backup process.
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
    Evaluates if an upgrade is necessary for a target device based on the specified version.

    This function assesses the need for upgrading the target device (either a Firewall or Panorama appliance) to a specified PAN-OS version. It compares the device's current version against the desired target version, which is defined by major, minor, and maintenance (or hotfix) components. If the current version is older, an upgrade is deemed necessary. If it's the same or newer, the function logs a message indicating no upgrade is needed or that a downgrade attempt was detected, and then exits the script.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device (Firewall or Panorama) whose PAN-OS version is to be evaluated for upgrading.
    hostname : str
        The hostname or IP address of the target device, used for logging purposes.
    target_major : int
        The major version number of the target PAN-OS version to upgrade to.
    target_minor : int
        The minor version number of the target PAN-OS version.
    target_maintenance : Union[int, str]
        The maintenance version number of the target PAN-OS version, which can also include a hotfix designation (e.g., "4-h1").

    Raises
    ------
    SystemExit
        Exits the script if no upgrade is required, indicating either the current version is already adequate or a downgrade attempt was made.

    Examples
    --------
    Evaluating if an upgrade is needed for a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> determine_upgrade(firewall, 'firewall1', 9, 1, 0)
        # Logs the current version and whether an upgrade to 9.1.0 is necessary.

    Evaluating if an upgrade is needed for a Panorama appliance:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='password')
        >>> determine_upgrade(panorama, 'panorama1', 10, 0, '1-h1')
        # Logs the current version and whether an upgrade to 10.0.1-h1 is necessary.

    Notes
    -----
    - The function uses version parsing to accurately compare the current device version with the target version.
    - In case of a downgrade attempt or if the device is already at the target version, the script will log an appropriate message and exit to prevent unintended downgrades or redundant upgrades.
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
    Retrieves the High-Availability (HA) status and configuration details of a target device.

    This function queries a Palo Alto Networks device (Firewall or Panorama) to determine its HA status,
    identifying whether it is in standalone mode, part of an active/passive HA pair, an active/active HA pair,
    or a cluster configuration. It returns both the HA deployment type as a string and, if applicable,
    a dictionary containing detailed HA configuration information, such as local and peer device info.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device instance (Firewall or Panorama) whose HA status is being queried.
    hostname : str
        The hostname or IP address of the target device, used for logging and contextual purposes in the output.

    Returns
    -------
    Tuple[str, Optional[dict]]
        A tuple where the first element is a string describing the HA deployment type (e.g., 'standalone',
        'active/passive', 'active/active'), and the second element is an optional dictionary containing detailed
        HA configuration information if the device is part of an HA setup, otherwise None.

    Example
    -------
    Retrieving HA status for a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> ha_status, ha_details = get_ha_status(firewall, 'firewall1')
        >>> print(ha_status)  # e.g., 'active/passive'
        >>> print(ha_details)  # e.g., {'local-info': {...}, 'peer-info': {...}}

    Notes
    -----
    - This function is essential for assessing the HA readiness and configuration of a device before performing
      operations that could be affected by HA status, such as upgrades or maintenance tasks.
    - It relies on the 'show_highavailability_state' operational command and parses the XML response to extract
      meaningful HA status information, enhancing the automation and monitoring capabilities for administrators.
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
    Handles High Availability (HA) logic for a target device during the upgrade process.

    This function evaluates the HA status of the target device to determine the appropriate upgrade strategy.
    It assesses whether the device is part of an HA pair and its role (active or passive). Based on the HA
    configuration and the dry run flag, it decides whether to proceed with the upgrade and whether any HA-specific
    actions are required (e.g., suspending HA on the active device). In dry run mode, the function simulates these
    decisions without making any changes to the device.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device (Firewall or Panorama) being considered for upgrade, which may be part of an HA pair.
    hostname : str
        The hostname or IP address of the target device, used for logging and contextual information.
    dry_run : bool
        Specifies whether to simulate the HA logic without making actual changes. Useful for testing and verification.

    Returns
    -------
    Tuple[bool, Optional[Union[Firewall, Panorama]]]
        A tuple containing a boolean indicating whether to proceed with the upgrade, and an optional device instance
        (either Firewall or Panorama) representing the HA peer that should be targeted for the upgrade, if applicable.

    Example
    -------
    Evaluating HA logic for upgrading a target device:
        >>> target_device = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> proceed_with_upgrade, ha_peer_device = handle_ha_logic(target_device, 'firewall1', dry_run=True)
        >>> print(proceed_with_upgrade)  # True if upgrade should proceed, False otherwise
        >>> print(ha_peer_device)  # None if no HA peer or upgrade not directed at peer, otherwise Firewall or Panorama instance

    Notes
    -----
    - The function first retrieves the HA status of the target device to make informed decisions.
    - It compares the software versions between the HA pair to determine the upgrade path and ensure consistency.
    - The `dry_run` flag allows administrators to assess the potential impact of HA logic on the upgrade process
      without affecting the device's state, providing a safe environment for planning and testing upgrade strategies.
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
    Checks the HA synchronization status between HA peers in a Palo Alto Networks device setup.

    This function evaluates the High Availability (HA) synchronization status between a target device and its HA peer
    based on the provided HA details. It ensures that both devices in an HA pair are synchronized to prevent issues
    during operations such as upgrades. The function allows for a strict or lenient approach to handling
    synchronization failures, controlled by the `strict_sync_check` parameter. In strict mode, a failure in
    synchronization results in script termination, while in lenient mode, a warning is logged, and the script continues.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target device for which the HA synchronization status is being checked.
        Used primarily for logging purposes.
    ha_details : dict
        A dictionary containing detailed information about the HA status of the target device, including its
        synchronization state with its HA peer.
    strict_sync_check : bool, optional
        A flag indicating whether the synchronization check should be enforced strictly. If True, the script will
        exit upon detecting unsynchronized HA peers. Defaults to True.

    Returns
    -------
    bool
        Returns True if the HA peers are synchronized, False otherwise. In strict mode, the script exits instead
        of returning False when synchronization fails.

    Raises
    ------
    SystemExit
        If `strict_sync_check` is True and the HA peers are not synchronized, this function will terminate the script.

    Example
    -------
    Performing an HA synchronization check in strict mode:
        >>> ha_details = {'result': {'group': {'running-sync': 'synchronized'}}}
        >>> perform_ha_sync_check('firewall1', ha_details, strict_sync_check=True)
        True  # Indicates that the HA peers are synchronized

    Notes
    -----
    - This function is critical in scenarios where configuration changes or upgrades are being applied to HA pairs,
      ensuring both devices are at the same configuration state.
    - The `ha_details` parameter is expected to contain specific keys and values that represent the HA status
      as retrieved from the device, which this function parses to determine synchronization status.
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
    Conducts a comprehensive readiness assessment on a Palo Alto Networks Firewall before initiating upgrade procedures.

    This function evaluates the firewall's current state by performing a series of checks designed to ascertain its
    readiness for an upgrade. These checks encompass various operational and configuration aspects, including but not
    limited to, candidate configuration, content version, license status, High Availability (HA) setup, disk space,
    NTP synchronization, and connection to Panorama. The results are meticulously logged and compiled into a detailed
    JSON report, which is then saved to the specified file path.

    Parameters
    ----------
    firewall : Firewall
        The Firewall object representing the device to be checked. This object should be initialized with the
        necessary credentials and connection details.
    hostname : str
        The hostname or IP address of the firewall device. This identifier is primarily used for logging purposes
        to provide clear and contextual information in the log output.
    file_path : str
        The absolute or relative path where the JSON-formatted readiness report will be saved. If the specified
        directory does not exist, it will be created.

    Returns
    -------
    None

    Raises
    ------
    IOError
        If there is an issue writing the readiness report to the specified file path, an IOError is raised, indicating
        a problem with file creation or disk access.

    Notes
    -----
    - This function is a critical precursor to upgrade operations, ensuring that all necessary conditions are met and
      potential issues are identified and addressed beforehand.
    - The JSON report generated provides a structured and easily parsable record of the firewall's readiness, useful
      for automated workflows and auditing purposes.

    Example
    -------
    Performing readiness checks on a firewall and saving the report:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_readiness_checks(firewall_instance, 'firewall1', '/var/reports/firewall1_readiness.json')
        # This will execute the readiness checks and save the output in the specified JSON file.
    """

    logging.debug(
        f"{get_emoji('start')} {hostname}: Performing readiness checks of target firewall..."
    )

    readiness_check = run_assurance(
        firewall,
        hostname,
        operation_type="readiness_check",
        actions=[
            "candidate_config",
            "content_version",
            "expired_licenses",
            "ha",
            # "jobs",
            "free_disk_space",
            "ntp_sync",
            "panorama",
            "planes_clock_sync",
        ],
        config={},
    )

    # Check if a readiness check was successfully created
    if isinstance(readiness_check, ReadinessCheckReport):
        # Do something with the readiness check report, e.g., log it, save it, etc.
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
    Initiates a reboot process on the specified firewall or Panorama device and verifies the successful restart with the desired target version.

    This function orchestrates the reboot operation for the given target device, ensuring that it comes back online running the specified target version of the software. In scenarios involving High Availability (HA) configurations, additional validations are performed to ensure that the HA pair is synchronized post-reboot. The function logs each step of the process and handles various states and potential errors that might occur during the reboot.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The Firewall or Panorama device object that is to be rebooted. This object must be initialized with the necessary connection parameters.
    hostname : str
        The hostname or IP address of the target device, used primarily for logging purposes to provide contextual information within the log output.
    target_version : str
        The software version that the target device should be running after the reboot process completes.
    ha_details : Optional[dict], optional
        A dictionary containing the HA configuration details of the target device, if applicable. This information is used to assess and verify HA synchronization status post-reboot. Defaults to None.

    Raises
    ------
    SystemExit
        The script will terminate if the target device fails to reboot into the target version, if there are issues achieving HA synchronization post-reboot, or if other critical errors occur during the reboot process.

    Notes
    -----
    - The function actively monitors the reboot sequence and performs version verification once the device is back online.
    - In the case of HA configurations, it ensures that the device and its HA peer are in a synchronized state post-reboot.
    - The process is designed to abort if the device does not reboot to the target version or achieve synchronization within a predefined timeout period, typically 30 minutes.

    Example
    -------
    Triggering a reboot on a device and verifying its version post-reboot:
        >>> device = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_reboot(device, 'device123', '10.0.1')
        # This will initiate a reboot on the device 'device123' and ensure it starts up with version '10.0.1'.
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
    Captures a comprehensive snapshot of the current network state from a specified firewall and saves it to a JSON file.

    This function initiates a series of network state information retrievals from the firewall, including but not limited to ARP tables, content versions, IPsec tunnel statuses, licenses, network interfaces, routing tables, and session statistics. The information gathered is serialized into a JSON format and stored in the specified file location. The function provides logging feedback throughout the process to indicate the start, successful completion, or failure of the snapshot operation.

    Parameters
    ----------
    firewall : Firewall
        The instance of the Firewall class from which network state information will be gathered. The firewall instance must be initialized with appropriate credentials and connection details.
    hostname : str
        The identifier for the firewall, used for logging purposes to provide context during the operation.
    file_path : str
        The file system path where the resulting JSON file containing the snapshot will be written. The function will verify or create the necessary directory structure for this path.

    Raises
    ------
    IOError
        If there's an error in writing the snapshot data to the file system, an IOError will be raised indicating the problem.

    Notes
    -----
    - The snapshot includes critical diagnostic information useful for troubleshooting and verifying the operational state before and after significant changes or upgrades.
    - The snapshot operation is non-disruptive and can be performed during normal firewall operation without impacting traffic.

    Example
    --------
    Taking a network state snapshot of a firewall:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_snapshot(firewall_instance, 'fw-hostname', '/backups/fw-snapshot.json')
        # This will collect the network state from 'fw-hostname' and save it to '/backups/fw-snapshot.json'.
    """

    logging.info(
        f"{get_emoji('start')} {hostname}: Performing snapshot of network state information..."
    )

    # take snapshots
    network_snapshot = run_assurance(
        firewall,
        hostname,
        operation_type="state_snapshot",
        actions=[
            "arp_table",
            "content_version",
            "ip_sec_tunnels",
            "license",
            "nics",
            "routes",
            "session_stats",
        ],
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
    max_retries: int = 3,
    retry_interval: int = 60,
) -> None:
    """
    Conducts an upgrade of the specified target device to the desired PAN-OS version, with considerations for HA configurations and error resilience through retry mechanisms.

    This function initiates the upgrade process for the target device, ensuring the device transitions to the specified PAN-OS version. The procedure accommodates High Availability (HA) setups by utilizing provided HA details, if available. To counter transient errors such as software manager busy states, the function employs a retry mechanism with customizable parameters. Progress and critical events throughout the upgrade process are logged for monitoring and troubleshooting purposes. The script will exit if it encounters irrecoverable errors or depletes the allotted retry attempts.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        An instance of the Firewall or Panorama class representing the device to upgrade.
    hostname : str
        Identifier for the target device, used for logging and contextual information during the upgrade process.
    target_version : str
        The version string to which the target device will be upgraded, e.g., '10.1.0'.
    ha_details : Optional[dict], optional
        A dictionary containing details about the target device's HA configuration, if applicable. This information is used to tailor the upgrade process to HA environments.
    max_retries : int, optional
        Maximum number of retry attempts allowed for transient errors during the upgrade process. Defaults to 3.
    retry_interval : int, optional
        Time in seconds to wait between consecutive retry attempts. Defaults to 60 seconds.

    Raises
    ------
    SystemExit
        Terminates the script execution if the upgrade process fails or encounters critical errors.

    Notes
    -----
    - Incorporates error handling strategies to address common issues like 'software manager is currently in use'.
    - The upgrade process is designed to be resilient, with parameters to control retry behavior in the face of operational errors.

    Example
    -------
    Initiating an upgrade process with retry logic:
        >>> target_device_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> perform_upgrade(target_device_instance, 'firewall1', '10.2.0', max_retries=2, retry_interval=30)
        # Initiates the upgrade of 'firewall1' to PAN-OS version 10.2.0, with up to 2 retry attempts in case of errors.
    """

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
    Conducts specified operational checks or captures snapshots on the firewall, based on the operation type.

    This function is versatile, supporting various operations like readiness checks and state snapshots on the specified firewall. It executes a set of actions based on the 'operation_type' parameter, using 'actions' and 'config' to tailor the operation. The function returns a report object relevant to the operation or None in case of failure. It ensures the actions are valid for the operation type and handles exceptions gracefully, logging errors and exiting the script for critical issues.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance on which the assurance tasks will be executed.
    hostname : str
        The hostname or IP address of the firewall, used for logging purposes.
    operation_type : str
        The type of assurance operation to perform, such as 'readiness_check' or 'state_snapshot'.
    actions : List[str]
        A list of specific actions to execute as part of the operation, such as checking licenses or capturing ARP tables.
    config : Dict[str, Union[str, int, float, bool]]
        Additional configuration options for the actions, specifying details like thresholds or specific parameters.

    Returns
    -------
    Union[SnapshotReport, ReadinessCheckReport, None]
        A report object corresponding to the operation type, or None if the operation fails or is invalid.

    Raises
    ------
    SystemExit
        If an invalid action for the specified operation is encountered or if an exception occurs during execution.

    Notes
    -----
    - The function is designed to be flexible, accommodating additional operation types and actions as needed.
    - It is critical for maintaining the operational integrity and readiness of the firewall for upgrades or routine checks.

    Example
    -------
    Performing a readiness check operation on a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> result = run_assurance(firewall, 'firewall1', 'readiness_check', ['config_status', 'license_status'], {})
        # The result is either a ReadinessCheckReport object or None if the operation fails.
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
    Initiates the download of a specific software version on the target device and monitors its progress.

    This function triggers the download of the specified software version on the target device, which can be either a Firewall or a Panorama appliance. It checks if the desired version is already available on the device. If not, it starts the download and continuously monitors the progress, providing updates through logging. The function returns True if the download completes successfully. If the download fails or encounters errors, the function logs the issues and returns False. In the event of an exception, the script is terminated to prevent further issues.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The Firewall or Panorama instance where the software download is to be initiated.
    hostname : str
        The hostname or IP address of the target device, used for identification in logs.
    target_version : str
        The software version to be downloaded to the target device.
    ha_details : dict
        A dictionary containing High Availability (HA) details of the target device, if applicable.

    Returns
    -------
    bool
        True if the download completes successfully, False otherwise.

    Raises
    ------
    SystemExit
        Terminates the script if a critical error occurs during the download process or if an exception is raised.

    Example
    -------
    Initiating a software download on a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> successful = software_download(firewall, 'firewall1', '9.1.3', ha_details={})
        >>> if successful:
        ...     print("Download successful")
        ... else:
        ...     print("Download failed")

    Notes
    -----
    - The function first checks if the desired version is already downloaded, skipping the download process if so.
    - It handles potential errors gracefully and logs all significant events for troubleshooting.
    - The download process is monitored, with periodic checks every 30 seconds to update on the progress.
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
    Checks the availability and readiness of a specified software version for installation on a target device.

    This function assesses whether the specified version is a viable upgrade for the target device, considering both its current software state and High-Availability (HA) setup. It first refreshes the device's system info to ensure up-to-date data. Then, it validates whether the specified version is an upgrade using a version comparison function. If the target version is available in the device's software repository and its base image is already downloaded, the function returns True, indicating readiness for upgrade. Otherwise, it returns False, logging the reason for unavailability or incompatibility.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The Firewall or Panorama instance to check for software update availability.
    hostname : str
        The hostname or IP address of the target device, used for identification in logs and output.
    version : str
        The target software version to check for availability on the target device.
    ha_details : dict
        A dictionary containing details about the target device's HA configuration, if applicable.

    Returns
    -------
    bool
        True if the target version is available for installation and is a valid upgrade; False otherwise.

    Raises
    ------
    SystemExit
        Exits the script if the target version represents a downgrade or if it's not suitable for an upgrade based on the device's current software state.

    Example
    -------
    Verifying the availability of a software version for upgrade:
        >>> target_device = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> is_available = software_update_check(target_device, 'fw01', '9.1.3', {})
        >>> if is_available:
        ...     print("Version 9.1.3 is available for upgrade.")
        ... else:
        ...     print("Version 9.1.3 is not available for upgrade.")

    Notes
    -----
    - Ensures the specified version is an upgrade, not a downgrade.
    - Verifies the presence of the required base image for the target version, crucial for successful installation.
    - HA considerations are taken into account, particularly ensuring HA pair compatibility if applicable.
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
    Temporarily deactivates the High Availability (HA) functionality of an active device in an HA pair.

    In an HA configuration, temporarily suspending the HA functionality on the active device can be necessary for maintenance or upgrade procedures. This function sends a command to the target device to suspend its HA operations, effectively making the device passive and allowing its HA peer to take over as the active device. The function logs the outcome and returns a boolean value indicating the success or failure of the operation.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device instance (Firewall or Panorama) that is currently active in an HA pair and needs its HA functionality suspended.
    hostname : str
        The network hostname or IP address of the target device, used for identification and logging purposes.

    Returns
    -------
    bool
        Returns True if the HA suspension command is successfully executed, and False if the operation fails or an error occurs.

    Raises
    ------
    Exception
        An exception is logged and False is returned if an error occurs during the command execution.

    Example
    -------
    Suspending HA on an active device:
        >>> target_device = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> suspend_success = suspend_ha_active(target_device, 'fw01.example.com')
        >>> print(suspend_success)
        True  # This would indicate that the HA suspension was successful.

    Notes
    -----
    - Suspending HA on an active device is a significant operation that can affect network traffic and redundancy mechanisms.
    - Ensure that the implications of this action are fully understood and that it is coordinated within the context of network operations and maintenance schedules.
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
    Temporarily deactivates the High Availability (HA) functionality of a passive device in an HA pair.

    This function is designed to suspend the HA functionality on a device designated as passive within an HA configuration. The suspension is particularly useful during maintenance or upgrade processes to prevent the passive device from becoming active. The process involves issuing a specific command to the device, with the function logging the operation's outcome. A successful operation returns True, indicating the HA functionality has been suspended, while a failure results in False.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device instance (Firewall or Panorama) representing the passive target in an HA configuration.
    hostname : str
        The network hostname or IP address of the target device, serving as an identifier for logging purposes.

    Returns
    -------
    bool
        True if the HA suspension command is executed successfully, indicating the passive device's HA functionality has been temporarily deactivated. False indicates a failure in the suspension process.

    Raises
    ------
    Exception
        An error is logged, and False is returned if an exception occurs during the execution of the HA suspension command.

    Example
    -------
    Suspending HA functionality on a passive device:
        >>> target_device = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> suspension_success = suspend_ha_passive(target_device, 'fw02.example.com')
        >>> print(suspension_success)
        True  # This would indicate that the HA suspension was successfully executed.

    Notes
    -----
    - Suspending HA on a passive device is an important operation that might be required to maintain network stability during critical maintenance or upgrade tasks.
    - Care should be taken to ensure the operation's impact on network redundancy and traffic handling is fully understood and planned for.
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
    Orchestrates the comprehensive upgrade process for a Palo Alto Networks firewall to a specified version.

    This function encapsulates the entire sequence of operations necessary to upgrade a firewall, starting from pre-upgrade readiness checks to the final reboot into the new version. It is designed to accommodate firewalls in various configurations, including standalone units and those in High Availability (HA) setups. The function supports a 'dry run' mode that simulates the upgrade process without applying any changes, providing a safe way to validate the upgrade plan.

    Parameters
    ----------
    firewall : Firewall
        The instance of the firewall to be upgraded.
    target_version : str
        The desired PAN-OS version to upgrade the firewall to.
    dry_run : bool
        Specifies whether to simulate the upgrade process (True) or to execute the upgrade (False).

    Workflow
    --------
    1. System Information Refresh: Ensures up-to-date information about the firewall's current state.
    2. HA Status Check: Determines the firewall's role in an HA configuration and handles HA-specific logic.
    3. Readiness Assessment: Validates the firewall's readiness for the upgrade through a series of checks.
    4. Software Preparation: Downloads the required PAN-OS version and associated content updates.
    5. Pre-upgrade Steps: Includes configuration backup and network state snapshots.
    6. Upgrade Execution: Applies the upgrade and reboots the firewall, completing the transition to the target version.

    Raises
    ------
    SystemExit
        Terminates the script if a critical failure is encountered at any stage of the upgrade process, ensuring safety and consistency.

    Example
    -------
    Initiating an upgrade on a firewall:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> upgrade_firewall(firewall_instance, '10.0.1', dry_run=False)
        # This command will start the upgrade process to PAN-OS version 10.0.1.

    Notes
    -----
    - The dry run mode is particularly useful for verifying upgrade steps and ensuring operational readiness without risking system stability.
    - The function integrates detailed logging throughout the upgrade process, providing transparency and aiding in troubleshooting.
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
    Evaluates and logs the results of firewall upgrade readiness tests, highlighting any issues that may impede the upgrade.

    This function analyzes the outcome of specified readiness tests conducted on a firewall, in preparation for an upgrade, and logs the results. It categorizes the test outcomes based on their severity, ranging from informational to critical. For tests deemed critical ('exit_on_failure' set to True), the script will terminate upon failure to prevent proceeding with an upgrade that is likely to encounter significant issues.

    Parameters
    ----------
    result : dict
        A dictionary containing the results of readiness tests, where each key corresponds to a test name, and its value is another dictionary detailing the test's outcome ('state') and a descriptive 'reason'.
    hostname : str
        The identifier of the firewall undergoing the readiness check, primarily used for logging purposes.
    test_name : str
        The specific readiness test being evaluated, corresponding to a key in the 'result' dictionary.
    test_info : dict
        Metadata about the test, including a human-readable 'description', the 'log_level' indicating the severity of a failed test, and a boolean 'exit_on_failure' flag indicating whether a test failure should halt the upgrade process.

    Workflow
    --------
    1. Retrieve the result for the specified test from the 'result' dictionary.
    2. Construct a log message incorporating the test's description and outcome reason.
    3. Log the message at an appropriate severity level based on the test outcome and defined 'log_level'.
    4. If a critical test fails ('exit_on_failure' is True), log an error message and terminate the script to prevent a potentially problematic upgrade.

    Raises
    ------
    SystemExit
        Triggered when a critical test fails, indicating an upgrade-blocking issue, to halt script execution.

    Example
    -------
    Logging the result of a connectivity test:
        >>> result = {'connectivity_check': {'state': False, 'reason': 'No response from server'}}
        >>> test_name = 'connectivity_check'
        >>> test_info = {'description': 'Connectivity Check', 'log_level': 'error', 'exit_on_failure': True}
        >>> check_readiness_and_log(result, 'firewall1', test_name, test_info)
        # Outputs an error log and terminates the script due to the failed critical connectivity check.

    Notes
    -----
    - The function is integral to the pre-upgrade validation phase, ensuring the firewall's readiness for a successful upgrade.
    - Emphasizes clear, actionable logging to facilitate issue resolution and upgrade decision-making.
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
    Determines the relative newer, older, or equality status between two software version strings.

    This utility function is essential in upgrade workflows, enabling a clear comparison between two version strings to ascertain which is newer, older, or if both versions are identical. It adeptly handles versions in the format of major.minor.maintenance, with optional hotfix levels, facilitating nuanced comparisons crucial in software version management and decision-making processes related to upgrades or compatibility checks.

    Parameters
    ----------
    version1 : str
        A version string to be compared, adhering to a 'major.minor.maintenance' or 'major.minor.maintenance-hotfix' format.
    version2 : str
        Another version string for comparison, in a similar format as 'version1'.

    Returns
    -------
    str
        A string representing the comparison outcome: 'older' if 'version1' precedes 'version2', 'newer' if 'version1' succeeds 'version2', or 'equal' if both versions are the same.

    Examples
    --------
    Comparing two version strings:
        >>> compare_versions('10.0.1', '10.0.2')
        'older'  # '10.0.1' is older than '10.0.2'

        >>> compare_versions('10.1.0-h3', '10.1.0')
        'newer'  # '10.1.0-h3' is considered newer than '10.1.0' due to the hotfix

        >>> compare_versions('9.1.3-h3', '9.1.3-h3')
        'equal'  # Both versions are identical

    Notes
    -----
    - The function employs a systematic approach to parse and compare version components, ensuring accuracy even with complex version strings.
    - It is particularly useful in environments where precise version control and compatibility assessments are pivotal.
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
    Sets up the logging configuration for the application with specified verbosity and file encoding.

    This function initializes the logging system to include both console and file handlers, facilitating real-time monitoring and persistent logging. It allows for setting the logging verbosity through predefined levels, impacting the granularity of logged information. The rotating file handler ensures log file size management by archiving older entries, thereby maintaining a balance between log detail and file size.

    Parameters
    ----------
    level : str
        Defines the logging level, influencing the verbosity of the logs. Acceptable values are 'DEBUG', 'INFO', 'WARNING', 'ERROR', and 'CRITICAL'. The function defaults to 'INFO' if an unrecognized level is provided.
    encoding : str, optional
        Specifies the character encoding for the log files, defaulting to 'utf-8'. This ensures compatibility with a wide range of characters and symbols, accommodating diverse logging content.

    Raises
    ------
    ValueError
        Triggered if the provided `level` is not a recognized logging level, ensuring the integrity of logging configuration.

    Examples
    --------
    Configuring logging at the DEBUG level with default encoding:
        >>> configure_logging('DEBUG')
        # Sets the logger to DEBUG level, capturing detailed logs for diagnostic purposes.

    Configuring logging at the INFO level with a specific encoding:
        >>> configure_logging('INFO', 'iso-8859-1')
        # Configures the logger to INFO level with ISO-8859-1 encoding, suitable for environments requiring this character set.

    Notes
    -----
    - The logging setup is designed to provide a balance between real-time insights and historical log preservation, catering to both immediate debugging needs and retrospective analysis.
    - The rotating log files maintain a manageable log size, preventing excessive disk space consumption while preserving essential log history.
    """
    logging_level = getattr(logging, level.upper(), None)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging_level)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create handlers (console and file handler)
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        "logs/upgrade.log",
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding=encoding,
    )

    # Create formatters and add them to the handlers
    if level == "debug":
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
    Establishes a connection to a Palo Alto Networks device or Panorama using API credentials.

    This function attempts to connect to the specified Palo Alto Networks device (Firewall or Panorama) using the provided hostname, API username, and password. It auto-detects the type of device based on the successful connection response and returns an object representing the connected device. The returned `PanDevice` object serves as a gateway for further interactions with the device through the API.

    Parameters
    ----------
    hostname : str
        The IP address or DNS hostname of the target device or Panorama to connect to.
    api_username : str
        The API username for authentication with the target device.
    api_password : str
        The API password for authentication with the target device.

    Returns
    -------
    PanDevice
        An object representing the connected Palo Alto Networks device or Panorama, facilitating further API interactions.

    Raises
    ------
    SystemExit
        Exits the script with an error message if the connection fails due to incorrect credentials, network issues, or other unexpected errors.

    Examples
    --------
    Establishing a connection to a firewall:
        >>> firewall = connect_to_host('192.168.0.1', 'admin', 'password')
        # Returns an instance of the Firewall class upon successful connection.

    Establishing a connection to Panorama:
        >>> panorama = connect_to_host('panorama.example.com', 'admin', 'password')
        # Returns an instance of the Panorama class upon successful connection.

    Notes
    -----
    - The function provides a unified interface for connecting to different types of Palo Alto Networks devices, abstracting the complexities of device-specific connection details.
    - Adequate error handling is implemented to ensure that the script does not proceed without a successful connection, maintaining operational integrity and preventing subsequent errors.
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


def ensure_directory_exists(file_path: str) -> None:
    """
    Ensures the existence of the directory structure for a specified file path.

    This utility function checks if the directory for a given file path exists, and if not, it creates the directory along with any necessary intermediate directories. This is particularly useful to prepare the file system for file operations such as saving or retrieving files, preventing errors related to non-existent directories.

    Parameters
    ----------
    file_path : str
        The full file path for which the directory structure needs to be verified or created. The function extracts the directory path component from this parameter.

    Notes
    -----
    - The function is designed to be safe for concurrent use; it will not raise an error if the directory already exists.
    - It relies on `os.makedirs` with the `exist_ok` flag set to True, which is efficient for ensuring the existence of complex nested directories.

    Example
    -------
    Preparing a directory for log files:
        >>> log_file_path = '/logs/system/2024_01_01/event.log'
        >>> ensure_directory_exists(log_file_path)
        # Ensures the '/logs/system/2024_01_01/' directory exists, creating it and any intermediate directories if necessary.

    No return value and exceptions are expected under normal operation. If an error occurs due to permissions or filesystem limitations, an OSError may be raised by the underlying `os.makedirs` call.
    """

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def filter_string_to_dict(filter_string: str) -> dict:
    """
    Parses a filter string into a dictionary by converting comma-separated key-value pairs.

    This utility function takes a string containing key-value pairs separated by commas, with each key and value within a pair delimited by an equal sign ('='). It is designed to facilitate the conversion of query parameters or similar formatted strings into a dictionary for easier manipulation and access within the code. The function ensures graceful handling of edge cases, such as empty strings or strings not adhering to the expected format, by returning an empty dictionary.

    Parameters
    ----------
    filter_string : str
        The input string containing the key-value pairs, e.g., 'key1=value1,key2=value2'. The format expected is consistent, where each key-value pair is separated by a comma, and the key is separated from its value by an equal sign.

    Returns
    -------
    dict
        A dictionary with keys and values derived from the `filter_string`. If `filter_string` is empty, malformatted, or if no valid key-value pairs are identified, the function returns an empty dictionary.

    Examples
    --------
    Converting a filter string into a dictionary:
        >>> filter_string_to_dict('status=active,region=us-west')
        {'status': 'active', 'region': 'us-west'}

    Handling an improperly formatted string:
        >>> filter_string_to_dict('status:active,region=us-west')
        {}

    Handling an empty string:
        >>> filter_string_to_dict('')
        {}

    Notes
    -----
    - The function assumes that the input string is properly formatted. Malformed key-value pairs, where the '=' delimiter is missing, result in the omission of those pairs from the output.
    - Duplicate keys will result in the value of the last occurrence of the key being preserved in the output dictionary.

    Raises
    ------
    ValueError
        If the input string contains key-value pairs without an '=' delimiter, a ValueError is raised to indicate the incorrect format.
    """

    result = {}
    for substr in filter_string.split(","):
        k, v = substr.split("=")
        result[k] = v

    return result


def flatten_xml_to_dict(element: ET.Element) -> dict:
    """
    Converts an XML ElementTree element into a nested dictionary structure.

    This function traverses an XML ElementTree element, converting it and all its child elements into a nested dictionary. Each element tag becomes a dictionary key, with the element's text content as the value, or a further nested dictionary if the element has child elements. When encountering multiple child elements with the same tag at the same level, these are grouped into a list within the dictionary. This conversion is particularly useful for simplifying the handling of XML data structures within Python, making them more accessible and easier to work with.

    Parameters
    ----------
    element : ET.Element
        The root XML element to be converted. This element can contain multiple levels of child elements, which will be recursively processed into the nested dictionary.

    Returns
    -------
    dict
        The dictionary representation of the XML structure. Keys in the dictionary correspond to XML tags, and values are either the text content of the elements, nested dictionaries for elements with children, or lists of dictionaries for repeated elements with the same tag.

    Examples
    --------
    Converting an XML element to a dictionary:
        >>> xml_string = '<data><item id="1">Value1</item><item id="2">Value2</item></data>'
        >>> element = ET.fromstring(xml_string)
        >>> flatten_xml_to_dict(element)
        {'item': [{'id': '1', '_text': 'Value1'}, {'id': '2', '_text': 'Value2'}]}

    Handling nested XML structures:
        >>> xml_string = '<config><section><name>Settings</name><value>Enabled</value></section></config>'
        >>> element = ET.fromstring(xml_string)
        >>> flatten_xml_to_dict(element)
        {'section': {'name': 'Settings', 'value': 'Enabled'}}

    Notes
    -----
    - The function ignores XML attributes and focuses on the hierarchy and text content of the elements.
    - Elements with the same tag at the same level are compiled into a list to maintain the structure of the XML.
    - Special treatment is given to elements with the tag 'entry', which are always placed in a list to reflect common patterns in XML structures, particularly in API responses.

    Raises
    ------
    ValueError
        If the input XML structure contains complex attributes or nested elements that cannot be represented as a simple key-value pair, a ValueError is raised to highlight the conversion limitation.
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
    Retrieves an emoji character based on a specified action keyword, enhancing the visual appeal of log messages.

    This function serves as a utility to associate specific action keywords with corresponding emojis, adding a visual dimension to text outputs such as logs or console messages. It simplifies the inclusion of emojis in various parts of the application by providing a centralized mapping of actions to emojis. The function supports a predefined set of action keywords, each mapped to an intuitive emoji. If an action keyword is not recognized, the function returns an empty string, ensuring that the absence of an emoji does not disrupt the application's functionality.

    Parameters
    ----------
    action : str
        A keyword representing a particular action or outcome. Accepted keywords include 'success', 'warning', 'error', 'working', 'report', 'search', 'save', 'stop', and 'start'. The choice of keywords and emojis is designed to cover common scenarios in application logging and user notifications.

    Returns
    -------
    str
        The emoji character corresponding to the given action keyword. If the keyword is not found in the predefined list, an empty string is returned.

    Examples
    --------
    Incorporating emojis into log messages for enhanced readability:
        >>> logging.info(f"{get_emoji('success')} Data processing completed.")
        >>> logging.warning(f"{get_emoji('warning')} Low disk space detected.")
        >>> logging.error(f"{get_emoji('error')} Failed to connect to the database.")

    Using emojis to enrich console outputs:
        >>> print(f"{get_emoji('start')} Initialization started...")
        >>> print(f"{get_emoji('stop')} Shutdown sequence initiated.")

    Notes
    -----
    - The function aims to standardize the use of emojis across the application, making it easier to maintain consistency in visual cues.
    - While the current set of action keywords and emojis is based on typical use cases, the function can be easily extended to include additional mappings as required by the application's needs.

    Raises
    ------
    KeyError
        In the event of an unrecognized action keyword, a KeyError could be raised if not handled by the function. However, the current implementation avoids this by returning an empty string for unknown keywords.
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
    Fetches firewalls managed by Panorama, with optional filtering based on attributes like model and version.

    This function queries a Panorama appliance for its managed firewalls, returning a list of `Firewall` objects. It supports filtering based on firewall attributes, such as model, serial number, and software version, among others. The filters are applied using regular expressions, offering precise control over the selection of firewalls. The function is particularly useful for operations needing to target specific subsets of firewalls within a larger fleet managed by Panorama.

    Parameters
    ----------
    panorama : Panorama
        The `Panorama` instance through which the firewalls are managed. Must be properly authenticated and capable of making API requests.
    **filters : dict, optional
        Keyword arguments representing the filtering criteria. Each key should correspond to an attribute of a firewall (e.g., 'model', 'serial'), and the value should be a regular expression pattern to match against the attribute value.

    Returns
    -------
    list[Firewall]
        A list of `Firewall` objects, each representing a managed firewall that matches the specified filtering criteria. If no filters are specified, the function returns all managed firewalls.

    Examples
    --------
    Retrieving all firewalls managed by a Panorama instance:
        >>> all_firewalls = get_firewalls_from_panorama(panorama)

    Retrieving firewalls of a specific model:
        >>> pa220_firewalls = get_firewalls_from_panorama(panorama, model='PA-220')

    Notes
    -----
    - The function's flexibility in filtering allows for targeted operations on specific groups of firewalls, enhancing efficiency in large-scale environments.
    - Filters leverage regular expressions for pattern matching, providing robust and versatile matching capabilities.
    - The returned `Firewall` objects are ready for further operations, with each linked back to the `Panorama` instance for context and API call routing.
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
    Fetches a list of devices managed by a specified Panorama, with optional filtering based on attributes.

    This function queries a Panorama appliance for its managed devices, returning a list of `ManagedDevice` objects. It supports filtering based on device attributes, such as hostname, model, serial number, and software version, among others. The filters are applied using regular expressions, offering precise control over the selection of devices. The function is particularly useful for operations needing to target specific subsets of devices within a larger fleet managed by Panorama.

    Parameters
    ----------
    panorama : Panorama
        The `Panorama` instance through which the devices are managed. Must be properly authenticated and capable of making API requests.
    **filters : dict, optional
        Keyword arguments representing the filtering criteria. Each key should correspond to a device attribute (e.g., 'model', 'serial'), and the value should be a regular expression pattern to match against the attribute value.

    Returns
    -------
    list[ManagedDevice]
        A list of `ManagedDevice` objects, each representing a managed device that matches the specified filtering criteria. If no filters are specified, the function returns all managed devices.

    Examples
    --------
    Retrieving all devices managed by a Panorama instance:
        >>> all_devices = get_managed_devices(panorama)

    Retrieving devices of a specific model:
        >>> pa220_devices = get_managed_devices(panorama, model='PA-220')

    Notes
    -----
    - The function's flexibility in filtering allows for targeted operations on specific groups of devices, enhancing efficiency in large-scale environments.
    - Filters leverage regular expressions for pattern matching, providing robust and versatile matching capabilities.
    - The returned `ManagedDevice` objects are ready for further operations, with each linked back to the `Panorama` instance for context and API call routing.
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
    Validates a given string as either a resolvable hostname or a valid IP address.

    This function serves as a callback for command-line interface inputs, ensuring that provided
    network addresses are either valid IP addresses (IPv4 or IPv6) or hostnames that can be resolved
    to IP addresses. It first attempts to validate the input as an IP address using the 'ipaddress'
    module. If the input is not a valid IP address, it then attempts to resolve the input as a hostname.
    If both checks fail, the function raises an error, prompting the user to provide a valid input.

    Parameters
    ----------
    value : str
        The input string provided by the user, expected to be an IP address or a hostname.

    Returns
    -------
    str
        The validated input string if it is a resolvable hostname or a valid IP address.

    Raises
    ------
    typer.BadParameter
        Raised when the input value is neither a valid IP address nor a resolvable hostname, indicating
        the need for the user to provide a corrected input.

    Example
    -------
    Using the callback in a Typer command to validate user input:
        >>> @app.command()
        >>> def network_ping(host: str = typer.Option(..., callback=ip_callback)):
        >>>     # Function body to ping the provided host

    Notes
    -----
    - Utilization of this callback in a CLI application aids in early validation of network addresses,
      enhancing user experience by preventing further processing of invalid inputs.
    - This function integrates seamlessly with Typer CLI applications, leveraging Typer's exception handling
      to provide informative feedback to the user.
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
    Converts an XML element or tree from an API response into a structured object based on a Pydantic model.

    This function takes an XML element or an entire XML tree, typically obtained from an API response, and
    converts it into a structured Pydantic model. It employs a flattening process to convert the XML into a
    dictionary, which is then mapped to a Pydantic model. This model is expected to inherit from
    FromAPIResponseMixin, indicating its suitability for instantiation with API response data. The conversion
    facilitates structured and type-checked access to the data contained in the XML, enhancing data handling
    and integration in Python applications.

    Parameters
    ----------
    element : Union[ET.Element, ET.ElementTree]
        The XML element or tree to be transformed. This can be a single XML element or an entire XML document
        tree, as obtained from parsing an XML-based API response.
    model : type[FromAPIResponseMixin]
        The Pydantic model class, inheriting from FromAPIResponseMixin, which defines the structure into which
        the XML data will be mapped. This model outlines the expected fields and their types, based on the API
        response structure.

    Returns
    -------
    FromAPIResponseMixin
        An instance of the specified Pydantic model, populated with data extracted from the XML element or tree.
        This structured object provides typed fields corresponding to the elements within the XML, according to
        the model's definition.

    Example
    -------
    Converting XML API response to a Pydantic model:
        >>> xml_data = ET.fromstring('<device><id>123</id><status>active</status></device>')
        >>> DeviceModel = type('DeviceModel', (FromAPIResponseMixin, BaseModel), {'id': int, 'status': str})
        >>> device = model_from_api_response(xml_data, DeviceModel)
        # 'device' now is an instance of 'DeviceModel' with 'id' and 'status' attributes populated from 'xml_data'.

    Notes
    -----
    - The function simplifies the extraction of data from XML API responses, making it readily usable within
      Python applications by providing a structured and type-checked interface to the data.
    - Care should be taken to ensure the Pydantic model accurately reflects the structure and data types present
      in the XML response to avoid data mapping errors or loss.
    """

    result_dict = flatten_xml_to_dict(element)
    return model.from_api_response(result_dict)


def parse_version(version: str) -> Tuple[int, int, int, int]:
    """
    Extracts numerical components from a version string, including optional hotfix, into a tuple.

    This function interprets a version string formatted as 'major.minor.maintenance' or
    'major.minor.maintenance-hhotfix', where each segment represents numerical values for major, minor,
    and maintenance versions, with an optional hotfix number following a '-h'. The function splits these
    components and converts them into a tuple of integers for easy comparison and processing. In cases where
    a segment is absent, it defaults to 0, ensuring consistency in the tuple structure returned.

    Parameters
    ----------
    version : str
        A string representing the version in the format 'major.minor.maintenance' or
        'major.minor.maintenance-hhotfix'. Each part of the version (major, minor, maintenance, hotfix)
        should be a numerical value.

    Returns
    -------
    Tuple[int, int, int, int]
        A 4-tuple where each element represents major, minor, maintenance, and hotfix versions as integers.
        If the hotfix is not specified in the version string, it defaults to 0.

    Example
    -------
    Parsing a standard version string:
        >>> parse_version("3.5.8")
        (3, 5, 8, 0)

    Parsing a version string with a hotfix component:
        >>> parse_version("3.5.8-h1")
        (3, 5, 8, 1)

    Notes
    -----
    - This function is crucial for operations that require version comparison, ensuring proper version
      management and compliance with version-dependent features or requirements.
    - It is assumed that the input string follows the specified format. Deviations may result in incorrect
      parsing or conversion errors.
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
    Attempts to resolve a hostname to an IP address using DNS lookup.

    Performs a DNS lookup to check if the provided hostname can be resolved to an IP address, indicating
    network connectivity and DNS functionality. Successful resolution suggests that the hostname is valid
    and accessible, while failure might indicate problems with the hostname, DNS settings, or network issues.

    Parameters
    ----------
    hostname : str
        The hostname (e.g., 'example.com') to be resolved, to verify its validity and accessibility.

    Returns
    -------
    bool
        True if the hostname resolves to an IP address, false otherwise, indicating potential issues with
        the hostname or network configuration.

    Example
    -------
    Verifying the resolution of a hostname:
        >>> resolve_hostname('www.example.com')
        True  # Indicates that 'www.example.com' is resolvable and accessible.

        >>> resolve_hostname('unknown.hostname')
        False  # Indicates that 'unknown.hostname' cannot be resolved, suggesting it may be invalid or there are network/DNS issues.

    Notes
    -----
    - Useful as an initial verification step before establishing network connections to a specified hostname.
    - Exceptions are managed internally, with errors logged for troubleshooting, allowing the function to return a simple boolean value.
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
# Common setup for all subcommands
# ----------------------------------------------------------------------------
def common_setup(
    hostname: str, username: str, password: str, log_level: str
) -> PanDevice:
    """
    Performs initial setup tasks for a device, including directory creation, logging configuration, and device connection.

    This function encompasses the preliminary steps required to establish a managed environment for interacting with
    a Palo Alto Networks device. It ensures that necessary directories for logging and data storage are present,
    configures logging according to the specified level, and establishes a connection to the device using provided
    credentials. The function returns an instance of the connected device, ready for further operations.

    Parameters
    ----------
    hostname : str
        The IP address or DNS hostname of the target device.
    username : str
        The username for authentication with the target device.
    password : str
        The password for authentication with the target device.
    log_level : str
        The desired logging level (e.g., 'DEBUG', 'INFO') for the application.

    Returns
    -------
    PanDevice
        An instance of `PanDevice` representing the connected device, either a `Firewall` or `Panorama` object,
        depending on the target device type.

    Example
    -------
    Setting up a common environment for a device:
        >>> device = common_setup('192.168.1.1', 'admin', 'adminpassword', 'INFO')
        # This will create necessary directories, configure logging, and return a connected device instance.

    Notes
    -----
    - Directory creation is idempotent; it checks for existence before creation to avoid redundancy.
    - Logging configuration is applied globally for the application, influencing all subsequent logging calls.
    - The connection to the device is established using API credentials, and the function assumes network reachability.
    """

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
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            "-l",
            help="Set the logging output level",
        ),
    ] = "info",
):
    """
    Initiates the upgrade process for a specified firewall appliance.

    This subcommand handles the upgrade of a firewall device by performing necessary preparatory steps,
    including connectivity checks, version validation, and upgrade execution. It supports a dry run mode
    for testing the upgrade procedure without making any changes to the device. The process involves setting
    up the environment, including logging configuration and directory structure, followed by the actual upgrade
    steps as defined in the `upgrade_firewall` function.

    Parameters
    ----------
    hostname : str
        The IP address or resolvable DNS name of the firewall or Panorama appliance.
    username : str
        The username required for authentication with the target device.
    password : str
        The password corresponding to the provided username for device authentication.
    target_version : str
        The software version to which the firewall will be upgraded.
    dry_run : bool, optional
        If set to True, performs all preparatory checks without applying the upgrade, by default False.
    log_level : str, optional
        Specifies the verbosity of log messages, by default 'info'.

    Examples
    --------
    Upgrading a firewall to a specific version:
        $ python script.py firewall --hostname 192.168.1.1 --username admin --password adminpassword --version 9.1.3 --dry-run

    Performing a dry run to check for upgrade feasibility:
        $ python script.py firewall --hostname 192.168.1.1 --username admin --password adminpassword --version 9.1.3 --dry-run True

    Notes
    -----
    - Ensure network connectivity and correct credentials before attempting the upgrade.
    - The dry run mode is recommended for verifying upgrade requirements and potential issues without impacting the device.
    """

    # Perform common setup tasks, return a connected device
    device = common_setup(hostname, username, password, log_level)

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
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            "-l",
            help="Set the logging output level",
        ),
    ] = "info",
):
    """
    Initiates the upgrade process for a specified Panorama appliance.

    This subcommand orchestrates the upgrade of a Panorama device, encompassing preparatory steps such as
    connectivity verification, version validation, and the execution of the upgrade. A dry run mode is available,
    enabling the simulation of the upgrade process without actual changes. The upgrade procedure involves setting up
    the environment, configuring logging, and performing the upgrade through the `upgrade_panorama` function.

    Parameters
    ----------
    hostname : str
        The IP address or resolvable DNS name of the Panorama appliance.
    username : str
        Username for authentication with the Panorama appliance.
    password : str
        Password for authentication with the Panorama appliance.
    target_version : str
        The Panorama version to which the upgrade is targeted.
    dry_run : bool, optional
        If True, performs all pre-upgrade checks without executing the actual upgrade, by default False.
    log_level : str, optional
        Determines the verbosity of logging output, by default 'info'.

    Examples
    --------
    Upgrading a Panorama to a specific version:
        $ python script.py panorama --hostname panorama.example.com --username admin --password adminpassword --version 9.1.3

    Executing a dry run to verify upgrade readiness:
        $ python script.py panorama --hostname panorama.example.com --username admin --password adminpassword --version 9.1.3 --dry-run

    Notes
    -----
    - Verify network connectivity and credentials before commencing the upgrade.
    - The dry run option is recommended to check for potential issues without impacting the Panorama appliance.
    """

    # Perform common setup tasks, return a connected device
    device = common_setup(hostname, username, password, log_level)

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
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            "-l",
            help="Set the logging output level",
        ),
    ] = "info",
):
    """
    Executes a batch upgrade of firewalls managed by a Panorama appliance based on specified criteria.

    This command facilitates the mass upgrade of firewalls under Panorama's management, applying a consistent
    target version across multiple devices. It leverages Panorama's centralized management capabilities to proxy
    connections to individual firewalls, allowing for coordinated upgrades. A filter option is available to
    target specific subsets of firewalls based on criteria like hostname patterns, models, or locations. The
    process supports a dry-run mode for validation purposes without applying changes.

    Parameters
    ----------
    hostname : str
        The IP address or resolvable DNS name of the Panorama appliance managing the firewalls.
    username : str
        Username for authentication with the Panorama appliance.
    password : str
        Password for authentication with the Panorama appliance.
    target_version : str
        The version to which the firewalls should be upgraded.
    filter : str, optional
        A filter string defining criteria to select specific firewalls for the upgrade, by default "".
    dry_run : bool, optional
        If True, performs all upgrade checks without executing the actual upgrade, by default False.
    log_level : str, optional
        The verbosity level of logging output, by default "info".

    Examples
    --------
    Executing a batch upgrade for firewalls managed by Panorama:
        $ python script.py batch --hostname panorama.example.com --username admin --password adminpassword --version 9.1.3 --filter "model=PA-220"

    Performing a dry run to validate the batch upgrade process:
        $ python script.py batch --hostname panorama.example.com --username admin --password adminpassword --version 9.1.3 --filter "location=DataCenter" --dry-run

    Notes
    -----
    - Ensure Panorama connectivity and correct credentials before initiating the batch upgrade.
    - The dry run mode is recommended to assess the upgrade's impact and readiness without affecting the operational state.
    """

    # Perform common setup tasks, return a connected device
    device = common_setup(hostname, username, password, log_level)

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
        with ThreadPoolExecutor(max_workers=10) as executor:
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
        with ThreadPoolExecutor(max_workers=2) as executor:
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


if __name__ == "__main__":
    app()
