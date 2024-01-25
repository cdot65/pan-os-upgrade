"""
Upgrade.py: Automating the Upgrade Process for PAN-OS Firewalls

This script provides a comprehensive solution for automating the upgrade of Palo Alto Networks firewalls.
It covers a broad range of functionalities essential for successful PAN-OS upgrades, including interaction
with the panos-upgrade-assurance tool, system settings management, and PAN-OS specific error handling.
Designed for both standalone utility and integration into larger workflows, the script leverages Typer for
command-line interface creation and supports username/password-based authentication.

Features:
- Automated upgrade procedures for both standalone and Panorama-managed Palo Alto Networks firewalls.
- Extensive error handling specific to PAN-OS, ensuring robust operation under various scenarios.
- Utilization of the panos-upgrade-assurance tool for pre and post-upgrade checks.
- Direct command-line argument input for parameters, moving away from .env file reliance.

Imports:
    Standard Libraries:
        - concurrent, threading: Provides multi-threading capabilities.
        - ipaddress: Handles IP address manipulations.
        - logging: Provides logging functionalities.
        - os, sys: Interacts with the operating system and accesses system-specific parameters.
        - time: Manages time-related functions.
        - RotatingFileHandler (logging.handlers): Manages log file rotation.

    External Libraries:
        - xml.etree.ElementTree (ET): Manipulates XML tree structures.
        - panos: Interfaces with Palo Alto Networks devices.
        - PanDevice, SystemSettings (panos.base, panos.device): Manages base PAN-OS device operations.
        - Error handling modules (panos.errors): Manages specific PAN-OS errors.
        - Firewall (panos.firewall): Handles firewall-specific operations.

    panos-upgrade-assurance package:
        - CheckFirewall, FirewallProxy: Performs checks and acts as a proxy to the firewall.

    Third-party libraries:
        - xmltodict: Converts XML data to Python dictionaries.
        - typer: Builds command-line interface applications.
        - BaseModel (pydantic): Creates Pydantic base models.

    Project-specific imports:
        - SnapshotReport, ReadinessCheckReport (pan_os_upgrade.models): Manages snapshot and readiness check reports.
"""
# standard library imports
import ipaddress
import logging
import os
import sys
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging.handlers import RotatingFileHandler
from threading import Lock
from typing import Dict, List, Optional, Tuple, Union
from typing_extensions import Annotated

# trunk-ignore(bandit/B405)
import xml.etree.ElementTree as ET

# Palo Alto Networks PAN-OS imports
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
# Define Typer command-line interface
# ----------------------------------------------------------------------------
app = typer.Typer(help="PAN-OS Upgrade script")


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
    A class encapsulating configuration options for the panos-upgrade-assurance process in PAN-OS appliances.

    This class is a central repository for various configurations used in the upgrade assurance process.
    It includes definitions for readiness checks, state snapshots, and report types, which are crucial
    components in managing and ensuring the successful upgrade of PAN-OS appliances.

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
        for the PAN-OS appliance. These reports provide insight into various aspects of the appliance's state.
        Includes reports like 'arp_table', 'content_version', 'ip_sec_tunnels', etc.

    STATE_SNAPSHOTS : list of str
        A list of strings where each string represents a type of state snapshot that can be captured
        from the PAN-OS appliance. These snapshots record essential data about the appliance's current state,
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
# Global list and lock for storing firewalls to revisit
# ----------------------------------------------------------------------------
firewalls_to_revisit = []
firewalls_to_revisit_lock = Lock()


# ----------------------------------------------------------------------------
# Core Upgrade Functions
# ----------------------------------------------------------------------------
def backup_configuration(
    firewall: Firewall,
    hostname: str,
    file_path: str,
) -> bool:
    """
    Backs up the current running configuration of a specified firewall to a local file.

    This function retrieves the current running configuration from the specified firewall and
    saves it as an XML file at the provided file path. It performs checks to ensure the
    validity of the retrieved XML data and logs the outcome of the backup process.

    Parameters
    ----------
    firewall : Firewall
        The instance of the firewall from which the running configuration is to be backed up.
    hostname : str
        The hostname of the firewall. This is used for logging and reporting purposes.
    file_path : str
        The filesystem path where the configuration backup file will be stored.

    Returns
    -------
    bool
        True if the backup is successfully created; False if any error occurs during the backup process.

    Raises
    ------
    Exception
        If any error occurs during the retrieval or saving of the configuration data.

    Notes
    -----
    - The function checks the XML structure of the retrieved configuration to ensure its integrity.
    - The directory for the backup file is verified, and if it does not exist, it is created.
    - The configuration data is saved in XML format to the specified path.

    Example
    --------
    Backing up the configuration of a firewall:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> backup_configuration(firewall_instance, 'firewall1', '/path/to/config_backup.xml')
        True  # Indicates that the backup was successful.
    """
    try:
        # Run operational command to retrieve configuration
        config_xml = firewall.op("show config running")
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
    firewall: Firewall,
    hostname: str,
    target_major: int,
    target_minor: int,
    target_maintenance: Union[int, str],
) -> None:
    """
    Determines whether an upgrade is necessary for a firewall to a specific PAN-OS version.

    This function evaluates whether the firewall's current PAN-OS version needs to be upgraded by
    comparing it with the specified target version. The target version is detailed by major, minor,
    and maintenance version numbers. The maintenance version may be an integer or a string including hotfix information.
    The function logs both the current and target versions. If the current version is lower than the target,
    an upgrade is deemed necessary. If the current version is equal to or higher than the target, it implies
    no upgrade is needed, or a downgrade is attempted, and the script exits.

    Parameters
    ----------
    firewall : Firewall
        The Firewall instance whose PAN-OS version is under evaluation.
    hostname : str
        The hostname of the firewall. This is used for logging and reporting purposes.
    target_major : int
        The major version number of the target PAN-OS.
    target_minor : int
        The minor version number of the target PAN-OS.
    target_maintenance : Union[int, str]
        The maintenance or hotfix version number of the target PAN-OS, which can be either an integer or a string.

    Raises
    ------
    SystemExit
        Exits the script if the target version does not necessitate an upgrade, suggesting either a downgrade attempt
        or the current version is already at or beyond the target version.

    Notes
    -----
    - The function parses PAN-OS version strings into tuples of integers for an accurate comparison.
    - Logging with emojis is used for clear and user-friendly status updates.

    Examples
    --------
    Determining the need for an upgrade:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> determine_upgrade(firewall_instance, 'firewall1', 10, 0, 1)
        # Logs information about the current version and the necessity of an upgrade to version 10.0.1.
    """
    current_version = parse_version(firewall.version)

    if isinstance(target_maintenance, int):
        # Handling integer maintenance version separately
        target_version = (target_major, target_minor, target_maintenance, 0)
    else:
        # Handling string maintenance version with hotfix
        target_version = parse_version(
            f"{target_major}.{target_minor}.{target_maintenance}"
        )

    logging.info(
        f"{get_emoji('report')} {hostname}: Current PAN-OS version: {firewall.version}"
    )
    logging.info(
        f"{get_emoji('report')} {hostname}: Target PAN-OS version: {target_major}.{target_minor}.{target_maintenance}"
    )

    if current_version < target_version:
        logging.info(
            f"{get_emoji('success')} {hostname}: Upgrade required from {firewall.version} to {target_major}.{target_minor}.{target_maintenance}"
        )
    else:
        logging.error(
            f"{get_emoji('error')} {hostname}: No upgrade required or downgrade attempt detected."
        )
        logging.error(f"{get_emoji('stop')} {hostname}: Halting script.")
        sys.exit(1)


def get_ha_status(
    firewall: Firewall,
    hostname: str,
) -> Tuple[str, Optional[dict]]:
    """
    Retrieves the High-Availability (HA) status and configuration details of a specified firewall.

    This function queries the specified firewall to determine its HA deployment status. It can distinguish
    between standalone mode, active/passive HA pair, active/active HA pair, or cluster configurations.
    The function fetches both the deployment type (as a string) and, if applicable, a dictionary containing
    detailed HA configuration information.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance to query for HA status.
    hostname : str
        The hostname of the firewall. This is used for logging and reporting purposes.

    Returns
    -------
    Tuple[str, Optional[dict]]
        A tuple containing:
        - A string indicating the HA deployment type (e.g., 'standalone', 'active/passive', 'active/active').
        - An optional dictionary with detailed HA configuration. Provided if the firewall is in an HA setup;
          otherwise, None is returned.

    Example
    -------
    Assessing the HA status of a firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> ha_status, ha_config = get_ha_status(firewall, 'firewall1')
        >>> print(ha_status)  # e.g., 'active/passive'
        >>> print(ha_config)  # e.g., {'local-info': {...}, 'peer-info': {...}}

    Notes
    -----
    - The function employs the 'show_highavailability_state' method from the Firewall class for querying HA status.
    - Uses 'flatten_xml_to_dict' to convert XML responses into a more accessible dictionary format.
    - This function is crucial for understanding the HA configuration of a firewall, especially in complex network setups.
    """
    logging.debug(
        f"{get_emoji('start')} {hostname}: Getting {firewall.serial} deployment information..."
    )
    deployment_type = firewall.show_highavailability_state()
    logging.debug(
        f"{get_emoji('report')} {hostname}: Firewall deployment: {deployment_type[0]}"
    )

    if deployment_type[1]:
        ha_details = flatten_xml_to_dict(deployment_type[1])
        logging.debug(
            f"{get_emoji('report')} {hostname}: Firewall deployment details: {ha_details}"
        )
        return deployment_type[0], ha_details
    else:
        return deployment_type[0], None


def handle_ha_logic(
    firewall: Firewall,
    hostname: str,
    dry_run: bool,
) -> Tuple[bool, Optional[Firewall]]:
    """
    Manages High Availability (HA) specific logic during the upgrade process of a firewall.

    This function assesses the HA role of a specified firewall and determines the appropriate action
    in the context of upgrading to a target PAN-OS version. It considers whether the firewall is active
    or passive in an HA configuration and whether it is appropriate to proceed with the upgrade. In a dry run,
    the function simulates the HA logic without actual state changes.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance to be evaluated for HA related upgrade logic.
    hostname : str
        The hostname of the firewall. This is used for logging and reporting purposes.
    dry_run : bool
        If True, simulates the HA logic without executing state changes.

    Returns
    -------
    Tuple[bool, Optional[Firewall]]
        A tuple where the first element is a boolean indicating whether the upgrade should proceed,
        and the second element is an optional Firewall instance representing the HA peer if it should be
        the target for the upgrade.

    Example
    -------
    Handling HA logic for a firewall upgrade:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> proceed, peer_firewall = handle_ha_logic(firewall, 'firewall1', dry_run=False)
        >>> print(proceed) # True or False
        >>> print(peer_firewall) # Firewall instance or None

    Notes
    -----
    - The function determines the HA status and version comparison between the HA pair.
    - For active firewalls with passive peers on the same version, the function defers the upgrade process.
    - In dry run mode, the function does not perform state changes like suspending HA states.
    """
    deploy_info, ha_details = get_ha_status(
        firewall,
        hostname,
    )

    # If the firewall is not part of an HA configuration, proceed with the upgrade
    if not ha_details:
        return True, None

    local_state = ha_details["result"]["group"]["local-info"]["state"]
    local_version = ha_details["result"]["group"]["local-info"]["build-rel"]
    peer_version = ha_details["result"]["group"]["peer-info"]["build-rel"]
    version_comparison = compare_versions(local_version, peer_version)

    # If the active and passive firewalls are running the same version
    if version_comparison == "equal":
        if local_state == "active":
            # Add the active firewall to the list and exit the upgrade process
            with firewalls_to_revisit_lock:
                firewalls_to_revisit.append(firewall)
            logging.info(
                f"{get_emoji('search')} {hostname}: Detected active firewall in HA pair running the same version as its peer. Added firewall to revisit list."
            )
            return False, None
        elif local_state == "passive":
            # Continue with upgrade process on the passive firewall
            logging.debug(f"{get_emoji('report')} {hostname}: Firewall is passive")
            return True, None

    elif version_comparison == "older":
        logging.debug(
            f"{get_emoji('report')} {hostname}: Firewall is on an older version"
        )
        # Suspend HA state of active if the passive is on a later release
        if local_state == "active" and not dry_run:
            logging.debug(
                f"{get_emoji('report')} {hostname}: Suspending HA state of active"
            )
            suspend_ha_active(
                firewall,
                hostname,
            )
        return True, None

    elif version_comparison == "newer":
        logging.debug(
            f"{get_emoji('report')} {hostname}: Firewall is on a newer version"
        )
        # Suspend HA state of passive if the active is on a later release
        if local_state == "passive" and not dry_run:
            logging.debug(
                f"{get_emoji('report')} {hostname}: Suspending HA state of passive"
            )
            suspend_ha_passive(
                firewall,
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
    Verifies the synchronization status of the High Availability (HA) peer firewall.

    This function checks whether the HA peer firewall is synchronized with the primary firewall.
    It logs the synchronization status and takes action based on the strictness of the sync check.
    In strict mode, the script exits if synchronization is not achieved; otherwise, it logs a warning
    but continues execution.

    Parameters
    ----------
    hostname : str
        The hostname of the firewall. This is used for logging and reporting purposes.
    ha_details : dict
        A dictionary containing the HA status details of the firewall.
    strict_sync_check : bool, optional
        Determines the strictness of the synchronization check. If True, the function will halt the script on
        unsuccessful synchronization. Defaults to True.

    Returns
    -------
    bool
        True if the HA synchronization is successful, False otherwise.

    Raises
    ------
    SystemExit
        Exits the script if strict synchronization check fails.

    Example
    --------
    Checking HA synchronization status:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> ha_details = {'result': {'group': {'running-sync': 'synchronized'}}}
        >>> perform_ha_sync_check('firewall1', ha_details, strict_sync_check=True)
        True  # If the HA peer is synchronized

    Notes
    -----
    - The function logs detailed synchronization status, aiding in debugging and operational monitoring.
    - It is essential in maintaining HA integrity during operations like upgrades or configuration changes.
    """
    logging.info(f"{get_emoji('start')} {hostname}: Checking if HA peer is in sync...")
    if ha_details["result"]["group"]["running-sync"] == "synchronized":
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
    Executes and records readiness checks for a specified firewall prior to operations like upgrades.

    This function conducts a variety of checks on a firewall to ensure it is ready for further operations,
    such as upgrades. These checks include verifying configuration status, content version, license validity,
    High Availability (HA) status, and more. The results are logged and stored in a JSON report at a specified
    file path.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance for which the readiness checks are to be performed.
    hostname : str
        The hostname of the firewall. This is used for logging and reporting purposes.
    file_path : str
        The file path where the JSON report of the readiness checks will be stored.

    Returns
    -------
    None

    Raises
    ------
    IOError
        Raises an IOError if the report file cannot be written.

    Notes
    -----
    - The function employs the `run_assurance` function for executing the readiness checks.
    - It ensures that the directory for the report file exists before writing the file.
    - The readiness report is stored in JSON format for easy readability and parsing.

    Example
    -------
    Executing readiness checks and saving the report:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> perform_readiness_checks(firewall, 'firewall1', '/path/to/readiness_report.json')
        # The readiness report for 'firewall1' is saved at '/path/to/readiness_report.json'.
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
    firewall: Firewall,
    hostname: str,
    target_version: str,
    ha_details: Optional[dict] = None,
) -> None:
    """
    Initiates the reboot of a firewall and ensures it successfully restarts with the target PAN-OS version.

    This function manages the reboot process of a specified firewall, tracking its progress and
    confirming it restarts with the intended PAN-OS version. In HA (High Availability) setups, it
    additionally checks for synchronization with the HA peer post-reboot. It logs various steps and
    handles different states and potential errors encountered during the reboot.

    Parameters
    ----------
    firewall : Firewall
        The firewall to be rebooted.
    hostname : str
        The hostname of the firewall. This is used for logging and reporting purposes.
    target_version : str
        The target PAN-OS version to be verified post-reboot.
    ha_details : Optional[dict], optional
        High Availability details of the firewall, used to check HA synchronization post-reboot. Default is None.

    Raises
    ------
    SystemExit
        Exits the script if the firewall fails to reboot to the target version, encounters HA synchronization issues,
        or if critical errors arise during the reboot process.

    Notes
    -----
    - The function monitors the reboot process and verifies the firewall's PAN-OS version post-reboot.
    - It confirms successful synchronization in HA setups.
    - The script terminates if the firewall fails to reach the target version or synchronize within 30 minutes.

    Example
    -------
    Rebooting and verifying a firewall's version:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> perform_reboot(firewall, 'firewall1, '10.1.0')
        # The firewall reboots and the script monitors until it successfully reaches version 10.1.0.
    """

    reboot_start_time = time.time()
    rebooted = False

    # Check if HA details are available
    if ha_details:
        logging.info(
            f"{get_emoji('start')} {hostname}: Rebooting the passive HA firewall..."
        )

    # Reboot standalone firewall
    else:
        logging.info(
            f"{get_emoji('start')} {hostname}: Rebooting the standalone firewall..."
        )

    reboot_job = firewall.op(
        "<request><restart><system/></restart></request>", cmd_xml=False
    )
    reboot_job_result = flatten_xml_to_dict(reboot_job)
    logging.info(f"{get_emoji('report')} {hostname}: {reboot_job_result['result']}")

    # Wait for the firewall reboot process to initiate before checking status
    time.sleep(60)

    # Counter that tracks if the rebooted firewall is online but not yet synced on configuration
    reboot_and_sync_check = 0

    while not rebooted:
        # Check if HA details are available
        if ha_details:
            try:
                deploy_info, current_ha_details = get_ha_status(
                    firewall,
                    hostname,
                )
                logging.debug(
                    f"{get_emoji('report')} {hostname}: deploy_info: {deploy_info}"
                )
                logging.debug(
                    f"{get_emoji('report')} {hostname}: current_ha_details: {current_ha_details}"
                )

                if current_ha_details and deploy_info in ["active", "passive"]:
                    if (
                        current_ha_details["result"]["group"]["running-sync"]
                        == "synchronized"
                    ):
                        logging.info(
                            f"{get_emoji('success')} {hostname}: HA passive firewall rebooted and synchronized with its peer in {int(time.time() - reboot_start_time)} seconds"
                        )
                        rebooted = True
                    else:
                        reboot_and_sync_check += 1
                        if reboot_and_sync_check >= 5:
                            logging.warning(
                                f"{get_emoji('warning')} {hostname}: HA passive firewall rebooted but did not complete a configuration sync with the active after 5 attempts."
                            )
                            # Set rebooted to True to exit the loop
                            rebooted = True
                            break
                        else:
                            logging.info(
                                f"{get_emoji('working')} {hostname}: HA passive firewall rebooted but not yet synchronized with its peer. Will try again in 60 seconds."
                            )
                            time.sleep(60)
            except (PanXapiError, PanConnectionTimeout, PanURLError):
                logging.info(
                    f"{get_emoji('working')} {hostname}: Firewall is rebooting..."
                )
                time.sleep(60)

        # Reboot standalone firewall
        else:
            try:
                firewall.refresh_system_info()
                logging.info(
                    f"{get_emoji('report')} {hostname}: Firewall version: {firewall.version}"
                )

                if firewall.version == target_version:
                    logging.info(
                        f"{get_emoji('success')} {hostname}: Firewall rebooted in {int(time.time() - reboot_start_time)} seconds"
                    )
                    rebooted = True
                else:
                    logging.error(
                        f"{get_emoji('stop')} {hostname}: Firewall rebooted but running the target version. Please try again."
                    )
                    sys.exit(1)
            except (PanXapiError, PanConnectionTimeout, PanURLError):
                logging.info(
                    f"{get_emoji('working')} {hostname}: Firewall is rebooting..."
                )
                time.sleep(60)

        # Check if 30 minutes have passed
        if time.time() - reboot_start_time > 1800:
            logging.error(
                f"{get_emoji('error')} {hostname}: Firewall did not become available and/or establish a Connected sync state with its HA peer after 30 minutes. Please check the firewall status manually."
            )
            break


def perform_snapshot(
    firewall: Firewall,
    hostname: str,
    file_path: str,
) -> None:
    """
    Executes a network state snapshot on the specified firewall and saves it as a JSON file.

    This function collects various network state information from the firewall, such as ARP table, content version,
    IPsec tunnels, etc. The collected data is then serialized into JSON format and saved to the provided file path.
    It logs the beginning of the operation, its success, or any failures encountered during the snapshot creation.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance from which to collect the network state information.
    hostname : str
        Hostname of the firewall, used primarily for logging purposes.
    file_path : str
        Path to the file where the snapshot JSON will be saved.

    Notes
    -----
    - Utilizes the `run_assurance` function to collect the required network state information.
    - Ensures the existence of the directory where the snapshot file will be saved.
    - Logs a success message and the JSON representation of the snapshot if the operation is successful.
    - Logs an error message if the snapshot creation fails.

    Example
    --------
    Creating a network state snapshot:
        >>> firewall = Firewall(hostname='192.168.1.1', 'admin', 'password')
        >>> perform_snapshot(firewall, 'firewall1', '/path/to/snapshot.json')
        # Snapshot file is saved to the specified path.
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
    firewall: Firewall,
    hostname: str,
    target_version: str,
    ha_details: Optional[dict] = None,
    max_retries: int = 3,
    retry_interval: int = 60,
) -> None:
    """
    Upgrades a specified firewall to a designated PAN-OS version, accounting for retries and HA considerations.

    This function orchestrates the upgrade of the firewall to a specified PAN-OS version. It integrates logic for
    handling High Availability (HA) setups and provides robust error handling, including retries for transient issues.
    The function logs the progress of the upgrade and terminates the script in case of unrecoverable errors or after
    exhausting the maximum retry attempts. The retry mechanism is particularly useful for handling scenarios where the
    software manager is temporarily busy.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance that is to be upgraded.
    hostname : str
        The hostname of the firewall, mainly used for logging.
    target_version : str
        The target version of PAN-OS to upgrade the firewall to.
    ha_details : Optional[dict], optional
        High Availability details of the firewall, defaults to None.
    max_retries : int, optional
        The maximum number of retry attempts in case of failures, defaults to 3.
    retry_interval : int, optional
        The interval in seconds between retry attempts, defaults to 60.

    Raises
    ------
    SystemExit
        Exits the script if the upgrade fails or if critical errors are encountered.

    Notes
    -----
    - Handles retries based on 'max_retries' and 'retry_interval'.
    - Specifically accounts for 'software manager is currently in use' errors.
    - Ensures compatibility with HA configurations.

    Example
    -------
    Upgrading a firewall to a specific version with retry logic:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> perform_upgrade(firewall, 'firewall1', '10.2.0', max_retries=2, retry_interval=30)
        # The firewall is upgraded to version 10.2.0, with a maximum of 2 retries if needed.
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
            install_job = firewall.software.install(target_version, sync=True)

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
    Executes specified operational tasks on a firewall, returning reports or results based on the operation.

    This function facilitates various operational tasks on the firewall, such as readiness checks, state snapshots,
    or report generation, depending on the 'operation_type' specified. It performs the tasks as defined in 'actions'
    and 'config'. Successful executions return appropriate report objects, while invalid operations or execution errors
    result in logging an error and returning None. The function ensures that the specified actions align with the
    operation type and handles any exceptions that arise during task execution.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance on which the operations will be performed.
    hostname : str
        The IP address or DNS hostname of the firewall.
    operation_type : str
        The type of operation to perform, such as 'readiness_check', 'state_snapshot', or 'report'.
    actions : List[str]
        A list specifying actions to execute for the operation.
    config : Dict[str, Union[str, int, float, bool]]
        Configuration settings for executing the specified actions.

    Returns
    -------
    Union[SnapshotReport, ReadinessCheckReport, None]
        Depending on the operation, returns either a SnapshotReport, a ReadinessCheckReport, or None in case of failure or invalid operations.

    Raises
    ------
    SystemExit
        Exits the script if an invalid action for the specified operation is encountered or in case of an exception during execution.

    Notes
    -----
    - 'readiness_check' assesses the firewall's readiness for upgrades.
    - 'state_snapshot' captures the current operational state of the firewall.
    - 'report' (pending implementation) will generate detailed reports based on the action.

    Example
    -------
    Running a state snapshot operation:
        >>> firewall = Firewall(hostname='192.168.1.1', 'admin', 'password')
        >>> result = run_assurance(firewall, 'firewall1', 'state_snapshot', ['arp_table', 'ip_sec_tunnels'], {})
        >>> print(result)  # Outputs: SnapshotReport object or None
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
    firewall: Firewall,
    hostname: str,
    target_version: str,
    ha_details: dict,
) -> bool:
    """
    Initiates and monitors the download of a specified PAN-OS version on a firewall.

    This function triggers the download of a target PAN-OS version on the provided firewall instance.
    It continually monitors and logs the download progress. Upon successful completion of the download,
    the function returns True; if errors are encountered or the download fails, it logs these issues
    and returns False. In case of exceptions, the script is terminated for safety.

    Parameters
    ----------
    firewall : Firewall
        The instance of the Firewall where the software is to be downloaded.
    hostname : str
        The hostname of the firewall, used for logging and reporting purposes.
    target_version : str
        The specific PAN-OS version targeted for download.
    ha_details : dict
        High Availability (HA) details of the firewall, if applicable.

    Returns
    -------
    bool
        True if the software download completes successfully, False otherwise.

    Raises
    ------
    SystemExit
        Exits the script if an exception occurs or if a critical error is encountered during the download.

    Example
    --------
    Downloading a specific PAN-OS version:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> success = software_download(firewall, 'firewall1', '10.1.0', ha_details={})
        >>> print(success)  # Outputs: True if successful, False otherwise

    Notes
    -----
    - The function first checks if the target version is already downloaded on the firewall.
    - Utilizes the 'download' method from the Firewall's software module.
    - The download status is checked at 30-second intervals to allow for progress.
    """

    if firewall.software.versions[target_version]["downloaded"]:
        logging.info(
            f"{get_emoji('success')} {hostname}: PAN-OS version {target_version} already on firewall."
        )
        return True

    if (
        not firewall.software.versions[target_version]["downloaded"]
        or firewall.software.versions[target_version]["downloaded"] != "downloading"
    ):
        logging.info(
            f"{get_emoji('search')} {hostname}: PAN-OS version {target_version} is not on the firewall"
        )

        start_time = time.time()

        try:
            logging.info(
                f"{get_emoji('start')} {hostname}: PAN-OS version {target_version} is beginning download"
            )
            firewall.software.download(target_version)
        except PanDeviceXapiError as download_error:
            logging.error(
                f"{get_emoji('error')} {hostname}: Download Error {download_error}"
            )

            sys.exit(1)

        while True:
            firewall.software.info()
            dl_status = firewall.software.versions[target_version]["downloaded"]
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
                    else f"Downloading PAN-OS version {target_version}"
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
    firewall: Firewall,
    hostname: str,
    version: str,
    ha_details: dict,
) -> bool:
    """
    Verifies the availability and readiness of a specified PAN-OS version for upgrade on a firewall.

    This function checks if a target PAN-OS version is ready for upgrade on the given firewall. It first
    refreshes the firewall's system information for current data and then uses the `determine_upgrade` function
    to assess if the target version constitutes an upgrade. The function verifies the presence of the target
    version in the list of available PAN-OS versions and checks if its base image is downloaded. It returns
    True if the target version is available and the base image is present, and False if the version is unavailable,
    the base image is not downloaded, or a downgrade is attempted.

    Parameters
    ----------
    firewall : Firewall
        The instance of the Firewall to be checked for software update availability.
    hostname : str
        The hostname of the firewall, used for logging and reporting purposes.
    version : str
        The target PAN-OS version for the upgrade.
    ha_details : dict
        High-Availability (HA) details of the firewall, essential for considering HA synchronization during the update.

    Returns
    -------
    bool
        True if the target PAN-OS version is available and ready for the upgrade, False otherwise.

    Raises
    ------
    SystemExit
        Exits the script if a downgrade is attempted or if the target version is inappropriate for an upgrade.

    Example
    --------
    Checking the availability of a specific PAN-OS version for upgrade:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> software_update_check(firewall, 'firewall1', '10.1.0', ha_details={})
        True  # Indicates that version 10.1.0 is available and ready for upgrade.

    Notes
    -----
    - This function is a prerequisite step before initiating a firewall upgrade.
    - It is important to ensure that the target version is not only present but also compatible for an upgrade to avoid downgrade scenarios.
    """
    # parse version
    major, minor, maintenance = version.split(".")

    # Make sure we know about the system details - if we have connected via Panorama, this can be null without this.
    logging.debug(
        f"{get_emoji('working')} {hostname}: Refreshing running system information"
    )
    firewall.refresh_system_info()

    # check to see if the specified version is older than the current version
    determine_upgrade(
        firewall,
        hostname,
        major,
        minor,
        maintenance,
    )

    # retrieve available versions of PAN-OS
    firewall.software.check()
    available_versions = firewall.software.versions

    # check to see if specified version is available for upgrade
    if version in available_versions:
        logging.info(
            f"{get_emoji('success')} {hostname}: PAN-OS version {version} is available for download"
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
            f"{get_emoji('error')} {hostname}: PAN-OS version {version} is not available for download"
        )
        return False


def suspend_ha_active(
    firewall: Firewall,
    hostname: str,
) -> bool:
    """
    Suspends the High-Availability (HA) state of the active firewall in an HA pair.

    This function issues a command to suspend the HA state on the specified firewall,
    which is expected to be the active member in an HA configuration. Suspending the HA
    state on the active firewall allows its passive counterpart to take over as the active unit.
    The function logs the outcome of this operation and returns a boolean status indicating the
    success or failure of the suspension.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the active firewall in an HA pair.
    hostname: str
        The hostname of the firewall, used for logging and reporting purposes.

    Returns
    -------
    bool
        Returns True if the HA state is successfully suspended, or False in case of failure.

    Raises
    ------
    Exception
        Logs an error and returns False if an exception occurs during the HA suspension process.

    Notes
    -----
    - This function should be invoked only when it is confirmed that the firewall is the active member in an HA setup.
    - The HA state suspension is a critical operation and should be handled with caution to avoid service disruptions.

    Example
    -------
    Suspending the HA state of an active firewall in an HA pair:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> suspend_ha_active(firewall, 'firewall1')
        True  # Indicates successful suspension of the HA state.

    """
    try:
        suspension_response = firewall.op(
            "<request><high-availability><state><suspend/></state></high-availability></request>",
            cmd_xml=False,
        )
        if "success" in suspension_response.text:
            logging.info(
                f"{get_emoji('success')} {hostname}: Active firewall HA state suspended."
            )
            return True
        else:
            logging.error(
                f"{get_emoji('error')} {hostname}: Failed to suspend active firewall HA state."
            )
            return False
    except Exception as e:
        logging.error(
            f"{get_emoji('error')} {hostname}: Error suspending active firewall HA state: {e}"
        )
        return False


def suspend_ha_passive(
    firewall: Firewall,
    hostname: str,
) -> bool:
    """
    Suspends the High-Availability (HA) state of the passive firewall in an HA pair.

    This function issues a command to suspend the HA state on the specified firewall,
    which is expected to be the passive member in an HA configuration. The suspension
    prevents the passive firewall from becoming active, particularly useful during
    maintenance or upgrade processes. The function logs the operation's outcome and
    returns a boolean status indicating the success or failure of the suspension.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the passive firewall in an HA pair.
    hostname: str
        The hostname of the firewall, used for logging and reporting purposes.

    Returns
    -------
    bool
        Returns True if the HA state is successfully suspended, or False in case of failure.

    Raises
    ------
    Exception
        Logs an error and returns False if an exception occurs during the HA suspension process.

    Notes
    -----
    - This function should be invoked only when it is confirmed that the firewall is the passive member in an HA setup.
    - Suspending the HA state on a passive firewall is a key step in controlled maintenance or upgrade procedures.

    Example
    -------
    Suspending the HA state of a passive firewall in an HA pair:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> suspend_ha_passive(firewall, 'firewall1')
        True  # Indicates successful suspension of the HA state.

    """
    try:
        suspension_response = firewall.op(
            "<request><high-availability><state><suspend/></state></high-availability></request>",
            cmd_xml=False,
        )
        if "success" in suspension_response.text:
            logging.info(
                f"{get_emoji('success')} {hostname}: Passive firewall HA state suspended."
            )
            return True
        else:
            logging.error(
                f"{get_emoji('error')} {hostname}: Failed to suspend passive firewall HA state."
            )
            return False
    except Exception as e:
        logging.error(
            f"{get_emoji('error')} {hostname}: Error suspending passive firewall HA state: {e}"
        )
        return False


def upgrade_firewall(
    firewall: Firewall,
    target_version: str,
    dry_run: bool,
) -> None:
    """
    Orchestrates the upgrade process of a single firewall to a specified PAN-OS version.

    This comprehensive function manages the entire upgrade process for a firewall. It includes
    initial readiness checks, software download, configuration backup, and the execution of the upgrade
    and reboot phases. The function supports a dry run mode, allowing simulation of the upgrade process
    without applying actual changes. It is compatible with both standalone firewalls and those in High
    Availability (HA) configurations.

    Parameters
    ----------
    firewall : Firewall
        The Firewall instance to be upgraded.
    target_version : str
        The PAN-OS version to upgrade the firewall to.
    dry_run : bool
        If True, performs a dry run of the upgrade process without making changes.
        If False, executes the actual upgrade process.

    Raises
    ------
    SystemExit
        Exits the script if a critical failure occurs at any stage of the upgrade process.

    Workflow
    --------
    1. Refreshes the firewall's system information.
    2. Determines the firewall's deployment mode (standalone, HA).
    3. Validates the readiness for the upgrade.
    4. Downloads the target PAN-OS version, if not already available.
    5. Executes pre-upgrade steps: snapshots, readiness checks, and configuration backup.
    6. Proceeds with the actual upgrade and subsequent reboot, unless in dry run mode.

    Notes
    -----
    - In HA configurations, additional checks and steps are performed to ensure synchronization and readiness.
    - The script handles all logging, error checking, and state validation throughout the upgrade process.

    Example
    -------
    Upgrading a firewall to a specific PAN-OS version:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> upgrade_firewall(firewall, '10.1.0', dry_run=False)
        # Initiates the upgrade process of the firewall to PAN-OS version 10.1.0.

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

    # Download the target PAN-OS version
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
            f"{get_emoji('success')} {hostname}: PAN-OS version {target_version} has been downloaded."
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
    with firewalls_to_revisit_lock:
        is_firewall_to_revisit = firewall in firewalls_to_revisit

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
        firewall=firewall,
        hostname=hostname,
        target_version=target_version,
        ha_details=ha_details,
    )

    # Perform the reboot
    perform_reboot(
        firewall=firewall,
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
    Assesses and logs the outcome of a specified readiness test for a firewall upgrade process.

    This function examines the results of a designated readiness test, logging the outcome with an
    appropriate level of severity (info, warning, error) based on the test's criticality and its results.
    For critical tests marked as 'exit_on_failure', the function will halt the script execution if the
    test fails, indicating a condition that precludes a successful upgrade.

    Parameters
    ----------
    result : dict
        The result dictionary containing keys for each readiness test. Each key maps to another dictionary
        with 'state' (boolean indicating pass or fail) and 'reason' (string describing the result).
    hostname : str
        The hostname of the firewall, used primarily for logging purposes.
    test_name : str
        The name of the readiness test to be evaluated, which should match a key in the 'result' dictionary.
    test_info : dict
        A dictionary providing details about the test, including its description, logging level (info, warning, error),
        and a boolean flag 'exit_on_failure' indicating whether script execution should be terminated on test failure.

    Raises
    ------
    SystemExit
        If a test marked with 'exit_on_failure': True fails, the function will terminate the script execution to
        prevent proceeding with an upgrade that is likely to fail or cause issues.

    Notes
    -----
    - Utilizes custom logging levels and emojis for enhanced readability and user experience in log outputs.
    - The function is part of a larger upgrade readiness assessment process, ensuring the firewall is prepared for an upgrade.

    Example
    -------
    Evaluating and logging a readiness test result:
        >>> result = {'test_connectivity': {'state': True, 'reason': 'Successful connection'}}
        >>> test_name = 'test_connectivity'
        >>> test_info = {'description': 'Test Connectivity', 'log_level': 'info', 'exit_on_failure': False}
        >>> check_readiness_and_log(result, 'firewall1', test_name, test_info)
        # Logs "✅ Passed Readiness Check: Test Connectivity - Successful connection"
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
    Compares two PAN-OS version strings and determines their relative ordering.

    This function parses and compares two version strings to identify which is newer, older, or if they are identical.
    It is designed to work with PAN-OS versioning scheme, handling standard major.minor.maintenance (and optional hotfix) formats.
    The comparison is useful for upgrade processes, version checks, and ensuring compatibility or prerequisites are met.

    Parameters
    ----------
    version1 : str
        The first PAN-OS version string to compare. Example format: '10.0.1', '9.1.3-h3'.
    version2 : str
        The second PAN-OS version string to compare. Example format: '10.0.2', '9.1.4'.

    Returns
    -------
    str
        - 'older' if version1 is older than version2.
        - 'newer' if version1 is newer than version2.
        - 'equal' if both versions are the same.

    Notes
    -----
    - Version strings are parsed and compared based on numerical ordering of their components (major, minor, maintenance, hotfix).
    - Hotfix versions (if present) are considered in the comparison, with higher numbers indicating newer versions.

    Example
    -------
    Comparing two PAN-OS versions:
        >>> compare_versions('10.0.1', '10.0.2')
        'older'
        >>> compare_versions('10.1.0-h3', '10.1.0')
        'newer'
        >>> compare_versions('9.1.3-h3', '9.1.3-h3')
        'equal'

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
    Configures the logging system for the application, specifying log level and file encoding.

    Initializes the logging framework with a dual-handler approach: console and file output. The console output
    provides real-time logging information in the terminal, while the file output stores log messages in a
    rotating log file. The function allows customization of the logging level, impacting the verbosity of log
    messages. The file handler employs a rotating mechanism to manage log file size and preserve log history.

    Parameters
    ----------
    level : str
        The logging level to set for the logger. Accepted values include 'DEBUG', 'INFO', 'WARNING', 'ERROR',
        and 'CRITICAL', with case insensitivity. Defaults to 'INFO' if an unrecognized level is specified.
    encoding : str, optional
        Character encoding for log files. Defaults to 'utf-8', ensuring broad compatibility and support for
        international characters.

    Notes
    -----
    - Logging setup includes formatting for both console and file handlers, with more detailed formatting applied
      to file logs.
    - The file logging employs `RotatingFileHandler` for automatic log rotation, maintaining up to three backup
      files, each limited to 1MB.
    - The function clears existing handlers to prevent duplication and ensure that logging configuration
      reflects the specified parameters.

    Examples
    --------
    Setting up logging with default encoding:
        >>> configure_logging('debug')
        # Configures logging with DEBUG level and utf-8 encoding.

    Setting up logging with custom encoding:
        >>> configure_logging('info', 'iso-8859-1')
        # Configures logging with INFO level and ISO-8859-1 encoding.

    Raises
    ------
    ValueError
        If the `level` parameter does not correspond to a valid logging level, a ValueError is raised to
        indicate the invalid input.
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
    Initiates a connection to a specified PAN-OS device or Panorama using API credentials.

    Attempts to connect to a Palo Alto Networks device (either a firewall or a Panorama management server)
    using the hostname (or IP address) along with the API username and password provided. The function determines
    the type of device based on the response and establishes a session. On successful connection, it returns an
    instance of the device as a `PanDevice` object, which can be either a `Firewall` or `Panorama` instance,
    depending on the target device.

    Parameters
    ----------
    hostname : str
        The IP address or DNS hostname of the target PAN-OS device or Panorama.
    api_username : str
        The username for API access.
    api_password : str
        The password for API access.

    Returns
    -------
    PanDevice
        A `PanDevice` object representing the connected PAN-OS device or Panorama.

    Raises
    ------
    SystemExit
        Terminates the script if there is a failure to connect, such as due to incorrect credentials,
        network issues, or other connection errors.

    Examples
    --------
    Connecting to a firewall device:
        >>> device = connect_to_host('192.168.1.1', 'apiuser', 'apipass')
        >>> print(type(device))
        <class 'panos.firewall.Firewall'>

    Connecting to a Panorama device:
        >>> panorama = connect_to_host('panorama.company.com', 'apiuser', 'apipass')
        >>> print(type(panorama))
        <class 'panos.panorama.Panorama'>

    Notes
    -----
    - This function abstracts the connection logic, handling both firewall and Panorama connections seamlessly.
    - Error handling within the function ensures that any connection issues are clearly logged, and the script
      is exited gracefully to avoid proceeding without a valid connection.
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
    Checks and creates the directory structure for a given file path if it does not already exist.

    This utility function is used to verify the existence of a directory path derived from a full file path.
    If the directory does not exist, the function creates it along with any intermediate directories. This
    ensures that subsequent file operations such as saving or reading files can proceed without directory
    not found errors.

    Parameters
    ----------
    file_path : str
        The full path to a file, including the filename. The function will extract the directory path from
        this and ensure that the directory exists.

    Notes
    -----
    - This function is useful for preparing the file system to store files at specified locations,
      especially when the directory structure may not have been created in advance.
    - The function uses `os.makedirs` which allows creating intermediate directories needed to ensure the
      full path exists.

    Example
    -------
    Creating a directory structure for storing a configuration backup:
        >>> file_path = '/var/backups/firewall/config_backup.xml'
        >>> ensure_directory_exists(file_path)
        # This will create the '/var/backups/firewall/' directory if it doesn't exist.
    """
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def filter_string_to_dict(filter_string: str) -> dict:
    """
    Converts a filter string with comma-separated key-value pairs into a dictionary.

    This function is designed to parse strings formatted with key-value pairs, where each pair is
    separated by a comma, and the key and value within a pair are separated by an equal sign ('=').
    It's particularly useful for processing query parameters or configuration settings where this
    format is commonly used. The function ensures that even if the input string is empty or not properly
    formatted, the operation is handled gracefully, returning an empty dictionary in such cases.

    Parameters
    ----------
    filter_string : str
        A string containing key-value pairs separated by commas, e.g., 'key1=value1,key2=value2'.
        Keys and values are expected to be strings. If the string is empty or does not conform to the
        expected format, the function returns an empty dictionary.

    Returns
    -------
    dict
        A dictionary representation of the key-value pairs extracted from `filter_string`.
        If `filter_string` is empty or malformatted, an empty dictionary is returned.

    Examples
    --------
    Converting a well-formed filter string:
        >>> filter_string_to_dict('type=firewall,model=PA-220')
        {'type': 'firewall', 'model': 'PA-220'}

    Handling an empty string:
        >>> filter_string_to_dict('')
        {}

    Handling a string without equal signs:
        >>> filter_string_to_dict('incorrect,format')
        {}

    Notes
    -----
    - This function does not validate the keys and values extracted from the input string; it simply
      splits the string based on the expected delimiters (',' and '=').
    - If the same key appears multiple times in the input string, the value associated with the last
      occurrence of the key will be retained in the output dictionary.
    """
    result = {}
    for substr in filter_string.split(","):
        k, v = substr.split("=")
        result[k] = v

    return result


def flatten_xml_to_dict(element: ET.Element) -> dict:
    """
    Flattens an XML ElementTree element into a nested dictionary, preserving the hierarchical structure.

    This utility function is particularly useful for processing XML data returned by APIs, such as the PAN-OS XML API.
    It iterates through the given XML element and its children, converting each element into a dictionary key-value pair,
    where the key is the element's tag and the value is the element's text content or a nested dictionary representing
    any child elements. Elements with the same tag name at the same level are grouped into a list. This function
    simplifies complex XML structures, making them more accessible for Pythonic manipulation and analysis.

    Parameters
    ----------
    element : ET.Element
        The root XML element to convert into a dictionary. This element may contain nested child elements, which will
        be recursively processed into nested dictionaries.

    Returns
    -------
    dict
        A dictionary representation of the input XML element. Each key in the dictionary corresponds to a tag in the XML,
        and each value is either the text content of the element, a nested dictionary for child elements, or a list of
        dictionaries for repeated child elements. Special handling is applied to elements with the tag 'entry', which are
        always treated as lists to accommodate common XML structures in PAN-OS API responses.

    Examples
    --------
    Converting a simple XML structure without attributes:
        >>> xml_str = '<configuration><device><name>Firewall1</name><location>Office</location></device></configuration>'
        >>> element = ET.fromstring(xml_str)
        >>> flatten_xml_to_dict(element)
        {'device': {'name': 'Firewall1', 'location': 'Office'}}

    Handling multiple child elements with the same tag:
        >>> xml_str = '<servers><server>Server1</server><server>Server2</server></servers>'
        >>> element = ET.fromstring(xml_str)
        >>> flatten_xml_to_dict(element)
        {'server': ['Server1', 'Server2']}

    Notes
    -----
    - The function ignores XML attributes and focuses solely on tags and text content.
    - Repeated tags at the same level are grouped into a list to preserve the XML structure.
    - The 'entry' tag, frequently used in PAN-OS XML API responses, is always treated as a list item to reflect its typical use as a container for multiple items.
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
    Provides a visual representation in the form of an emoji for various logging and notification actions.

    This utility function maps a set of predefined action keywords to their corresponding emoji characters,
    enhancing the user experience by adding a visual cue to log messages, console outputs, or user interfaces.
    It supports a variety of action keywords, each associated with a specific emoji that intuitively represents
    the action's nature or outcome.

    Parameters
    ----------
    action : str
        The action keyword representing the specific operation or outcome. Supported keywords include 'success',
        'warning', 'error', 'working', 'report', 'search', 'save', 'stop', and 'start'. The function is designed
        to be easily extendable with additional keywords and emojis as needed.

    Returns
    -------
    str
        An emoji character as a string corresponding to the provided action keyword. If the keyword is not
        recognized, the function returns an empty string, ensuring graceful handling of unsupported actions.

    Examples
    --------
    Adding visual cues to log messages:
        >>> logging.info(f"{get_emoji('success')} Operation completed successfully.")
        >>> logging.warning(f"{get_emoji('warning')} Proceed with caution.")
        >>> logging.error(f"{get_emoji('error')} An error occurred.")

    Enhancing console outputs:
        >>> print(f"{get_emoji('start')} Starting the process...")
        >>> print(f"{get_emoji('stop')} Process terminated.")

    Notes
    -----
    - The function is designed for extensibility, allowing easy addition of new action keywords and corresponding
      emojis without impacting existing functionality.
    - Emojis are selected to universally convey the essence of the action, ensuring clarity and immediacy in
      communication.
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
    Retrieves a list of firewalls managed by a specified Panorama, optionally filtered by custom criteria.

    This function interacts with a Panorama appliance to obtain a list of managed firewalls. It allows for
    filtering the firewalls based on various attributes, such as model, serial number, or software version,
    using regular expressions. Each matched firewall is instantiated as a `Firewall` object, facilitating
    subsequent operations on these firewalls through their respective `Firewall` instances. The filtering
    mechanism provides a flexible way to selectively work with subsets of firewalls under Panorama management.

    Parameters
    ----------
    panorama : Panorama
        The Panorama instance through which the firewalls are managed. This should be an authenticated
        instance with access to the Panorama's API.
    **filters : dict
        Arbitrary keyword arguments representing the filter criteria. Each keyword corresponds to a firewall
        attribute (e.g., model, serial number), and its value is a regex pattern against which the attribute is matched.

    Returns
    -------
    list[Firewall]
        A list containing `Firewall` instances for each firewall managed by Panorama that matches the provided
        filter criteria. If no filters are provided, all managed firewalls are returned.

    Example
    -------
    Retrieving firewalls of a specific model from Panorama:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='password')
        >>> filtered_firewalls = get_firewalls_from_panorama(panorama, model='PA-220')
        # This will return all firewalls of model PA-220 managed by the specified Panorama.

    Notes
    -----
    - The function requires an authenticated Panorama instance to query the Panorama API.
    - Filters are applied using regular expressions, providing flexibility in specifying match criteria.
    - Instantiated `Firewall` objects are linked to the Panorama instance, allowing API calls to be proxied.
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
    Retrieves a list of devices managed by a specified Panorama, optionally filtered by custom criteria.

    This function communicates with a Panorama appliance to fetch a list of managed devices, allowing for
    filtering based on various attributes such as hostname, model, serial number, etc., using regular expressions.
    The matched devices are returned as instances of `ManagedDevice`, facilitating further operations on these
    devices. The filtering mechanism provides a flexible way to work selectively with subsets of devices under
    Panorama management.

    Parameters
    ----------
    panorama : Panorama
        The Panorama instance through which the managed devices are accessed. This should be an authenticated
        instance with the capability to execute API calls against the Panorama.
    **filters : dict
        Arbitrary keyword arguments representing the filter criteria. Each keyword corresponds to a managed
        device attribute (e.g., hostname, model), and its value is a regex pattern against which the attribute
        is matched.

    Returns
    -------
    list[ManagedDevice]
        A list containing `ManagedDevice` instances for each device managed by Panorama that matches the
        provided filter criteria. If no filters are provided, all managed devices are returned.

    Example
    -------
    Retrieving managed devices from Panorama with specific model filters:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='password')
        >>> filtered_devices = get_managed_devices(panorama, model='PA-220')
        # This will return all managed devices of model PA-220.

    Notes
    -----
    - The function requires an authenticated Panorama instance to query the Panorama API.
    - Filters are applied using regular expressions, providing flexibility in specifying match criteria.
    - The `ManagedDevice` instances facilitate further interactions with the managed devices through the Panorama.
    """
    managed_devices = model_from_api_response(
        panorama.op("show devices all"), ManagedDevices
    )
    devices = managed_devices.devices
    for filter_key, filter_value in filters.items():
        devices = [d for d in devices if re.match(filter_value, getattr(d, filter_key))]

    return devices


def ip_callback(value: str) -> str:
    """
    Validates and returns an IP address or resolvable hostname provided as a command-line argument.

    This callback function is intended for use with command-line interfaces built with Typer. It ensures that
    the user-provided input is either a valid IPv4/IPv6 address or a hostname that can be resolved to an IP address.
    The function first attempts to resolve the input as a hostname. If unsuccessful, it then checks if the input
    is a valid IP address. This dual check ensures flexibility in accepting either form of network address identification.

    Parameters
    ----------
    value : str
        The user input string intended to represent an IP address or hostname.

    Returns
    -------
    str
        The original input value if it is a valid IP address or resolvable hostname.

    Raises
    ------
    typer.BadParameter
        This exception is raised if the input value is neither a valid IP address nor a resolvable hostname,
        providing feedback to the user to correct their input.

    Example
    --------
    Validating a user-provided IP address or hostname:
        >>> @app.command()
        >>> def command(hostname: str = typer.Option(..., callback=ip_callback)):
        >>>     print(f"Hostname/IP: {hostname}")
        # This CLI command requires a valid hostname or IP address as an argument.

    Notes
    -----
    - The function leverages the 'ipaddress' standard library for IP address validation and a custom
      'resolve_hostname' function (not shown) for DNS resolution.
    - Intended for use with Typer-based CLI applications to validate network address inputs.
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
    Transforms an XML element or tree from an API response into a structured Pydantic model.

    This utility function streamlines the conversion of XML data, commonly encountered in API responses,
    into a structured format by leveraging Pydantic models. It employs a two-step process: first, it flattens
    the XML structure into a dictionary using a recursive approach, and then it maps this dictionary onto a
    Pydantic model that's capable of handling data derived from API responses. This process facilitates the
    extraction and utilization of specific data points from complex XML structures in a more Pythonic and
    accessible manner.

    Parameters
    ----------
    element : Union[ET.Element, ET.ElementTree]
        An XML element or tree obtained from parsing an API's XML response, representing the data to be
        converted into a Pydantic model.
    model : type[FromAPIResponseMixin]
        A Pydantic model class that includes FromAPIResponseMixin, indicating it's designed to be populated
        with data from an API response. This model defines the structure and fields expected from the XML data.

    Returns
    -------
    FromAPIResponseMixin
        An instance of the specified Pydantic model populated with the data extracted from the input XML element
        or tree. The model instance provides structured access to the data, adhering to the definitions within the model.

    Example
    -------
    Parsing an API's XML response into a Pydantic model:
        >>> xml_response = ET.fromstring('<user><name>John Doe</name><email>john@example.com</email></user>')
        >>> UserModel = type('UserModel', (FromAPIResponseMixin, BaseModel), {'name': str, 'email': str})
        >>> user = model_from_api_response(xml_response, UserModel)
        # 'user' is an instance of 'UserModel' with 'name' and 'email' fields populated from 'xml_response'.

    Notes
    -----
    - The function assumes that the input XML element/tree structure corresponds to the structure expected by
      the Pydantic model. Mismatches between the XML data and the model's fields may result in incomplete or
      incorrect model instantiation.
    - This function is particularly useful in scenarios where API responses need to be deserialized into
      concrete Python objects for further processing, validation, or manipulation.
    """
    result_dict = flatten_xml_to_dict(element)
    return model.from_api_response(result_dict)


def parse_version(version: str) -> Tuple[int, int, int, int]:
    """
    Parses a version string into a tuple of integers representing its components.

    This function takes a PAN-OS version string and splits it into major, minor, maintenance,
    and hotfix components. The version string is expected to be in the format 'major.minor.maintenance'
    or 'major.minor.maintenance-hhotfix', where 'major', 'minor', 'maintenance', and 'hotfix' are integers.
    If the 'maintenance' version includes a hotfix indicated by '-h', it is separated into its own component.
    Missing components are defaulted to 0.

    Parameters
    ----------
    version : str
        The version string to be parsed. Expected formats include 'major.minor.maintenance' or
        'major.minor.maintenance-hhotfix'.

    Returns
    -------
    Tuple[int, int, int, int]
        A tuple containing four integers representing the major, minor, maintenance, and hotfix
        components of the version. Missing components are defaulted to 0.

    Example
    -------
    Parsing a version string without a hotfix:
        >>> parse_version("10.1.2")
        (10, 1, 2, 0)

    Parsing a version string with a hotfix:
        >>> parse_version("10.1.2-h3")
        (10, 1, 2, 3)

    Notes
    -----
    - The function assumes that the version string is correctly formatted. Malformed strings may
      lead to unexpected results.
    - This utility is particularly useful for comparing PAN-OS versions, facilitating upgrades and
      ensuring compatibility requirements are met.
    """
    parts = version.split(".")
    if len(parts) == 2:  # When maintenance version is an integer
        major, minor = parts
        maintenance, hotfix = 0, 0
    else:  # When maintenance version includes hotfix
        major, minor, maintenance = parts
        if "-h" in maintenance:
            maintenance, hotfix = maintenance.split("-h")
        else:
            hotfix = 0

    return int(major), int(minor), int(maintenance), int(hotfix)


def resolve_hostname(hostname: str) -> bool:
    """
    Attempts to resolve a hostname to an IP address using DNS lookup.

    This function checks if the provided hostname is resolvable by performing a DNS lookup.
    It uses the DNS resolver settings configured on the system to query for the IP address associated
    with the hostname. A successful resolution indicates network connectivity and DNS functionality
    with respect to the hostname, while a failure may suggest issues with the hostname, DNS configuration,
    or network connectivity.

    Parameters
    ----------
    hostname : str
        The hostname (e.g., 'example.com') that needs to be resolved to check its validity and network
        accessibility.

    Returns
    -------
    bool
        True if the hostname is successfully resolved to an IP address, indicating it is valid and
        accessible. False if the hostname cannot be resolved, suggesting it may be invalid, the DNS
        servers are unreachable, or the network is experiencing issues.

    Example
    -------
    Checking if a hostname can be resolved:
        >>> resolve_hostname('www.example.com')
        True  # Assuming 'www.example.com' is resolvable

        >>> resolve_hostname('nonexistent.hostname')
        False  # Assuming 'nonexistent.hostname' cannot be resolved

    Notes
    -----
    - This function can be used as a preliminary check before attempting network connections to a hostname.
    - It handles exceptions internally and logs them for debugging purposes, ensuring the calling code
      can make decisions based on the boolean return value without handling exceptions directly.
    """
    try:
        dns.resolver.resolve(hostname)
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout) as err:
        # Optionally log or handle err here if needed
        logging.debug(f"Hostname resolution failed: {err}")
        return False


# ----------------------------------------------------------------------------
# Primary execution of the script
# ----------------------------------------------------------------------------
@app.command()
def main(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of either Panorama or firewall appliance",
            prompt="Hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Firewall appliance",
            prompt="Username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Password",
            hide_input=True,
        ),
    ],
    target_version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Target PAN-OS version to upgrade to",
            prompt="Target PAN-OS version",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
        ),
    ] = False,
    filter: Annotated[
        str,
        typer.Option(
            "--filter",
            "-f",
            help="Filter string - when connecting to Panorama, defines which devices we are to upgrade.",
            prompt="Filter string (only applicable for Panorama connections)",
        ),
    ] = "",
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
    Orchestrates the upgrade process for Palo Alto Networks PAN-OS devices.

    This script automates the upgrade of PAN-OS firewalls and Panorama management servers to a specified version.
    It encompasses various stages including connection establishment, device filtering (for Panorama), pre-upgrade
    checks, software download, and the upgrade process itself. The script supports a dry run mode to simulate the
    upgrade process without making changes. It is designed to be run from the command line and accepts various
    parameters to control its operation.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the Panorama or firewall device.
    username : str
        The administrative username for device authentication.
    password : str
        The administrative password for device authentication.
    target_version : str
        The target PAN-OS version to upgrade the device(s) to.
    dry_run : bool, optional
        If True, simulates the upgrade process without applying changes (default is False).
    filter : str, optional
        A filter string to select specific devices managed by Panorama for the upgrade (default is "").
    log_level : str, optional
        Specifies the logging level for the script's output (default is "info").

    Raises
    ------
    SystemExit
        The script will exit if it encounters critical errors during execution, such as connection failures,
        invalid filter strings, or errors during the upgrade process.

    Examples
    --------
    Upgrading a standalone firewall:
        $ python upgrade.py --hostname 192.168.1.1 --username admin --password secret --version 10.1.0

    Performing a dry run on a Panorama-managed device:
        $ python upgrade.py --hostname panorama.example.com --username admin --password secret --version 10.1.0 --dry-run --filter "serial=0123456789"

    Notes
    -----
    - The script uses threads to parallelize upgrades for multiple devices managed by Panorama.
    - It is recommended to back up the device configuration before running the script, especially for production environments.
    - The `--filter` option is applicable only when connecting to Panorama and must conform to the syntax expected by the `get_firewalls_from_panorama` function.
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

    # Create our connection to the firewall
    logging.debug(f"{get_emoji('start')} {hostname}: Connecting to PAN-OS device...")
    device = connect_to_host(
        hostname=hostname,
        api_username=username,
        api_password=password,
    )

    firewalls_to_upgrade = []
    if type(device) is Firewall:
        logging.info(
            f"{get_emoji('success')} {hostname}: Connection to firewall established"
        )
        firewalls_to_upgrade.append(device)

        # Using ThreadPoolExecutor to manage threads
        with ThreadPoolExecutor(max_workers=1) as executor:
            # Store future objects along with firewalls for reference
            future_to_firewall = {
                executor.submit(
                    upgrade_firewall,
                    fw,
                    target_version,
                    dry_run,
                ): fw
                for fw in firewalls_to_upgrade
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

    elif type(device) is Panorama:
        if not filter:
            logging.error(
                f"{get_emoji('error')} {hostname}: Specified device is Panorama, but no filter string was provided."
            )
            sys.exit(1)

        logging.info(
            f"{get_emoji('success')} {hostname}: Connection to Panorama established. Firewall connections will be proxied!"
        )
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
                    fw,
                    target_version,
                    dry_run,
                ): fw
                for fw in firewalls_to_upgrade
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
    if firewalls_to_revisit:
        logging.info(
            f"{get_emoji('start')} {hostname}: Revisiting firewalls that were active in an HA pair and had the same version as their peers."
        )

        # Using ThreadPoolExecutor to manage threads for revisiting firewalls
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_firewall = {
                executor.submit(upgrade_firewall, fw, target_version, dry_run): fw
                for fw in firewalls_to_revisit
            }

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

        with firewalls_to_revisit_lock:
            firewalls_to_revisit.clear()  # Clear the list after revisiting


if __name__ == "__main__":
    app()
