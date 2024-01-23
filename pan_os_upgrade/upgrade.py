"""
upgrade.py: A script to automate the upgrade process of PAN-OS firewalls.

This module contains functionality to perform automated upgrade procedures on Palo Alto Networks firewalls.
It handles various PAN-OS operations, system settings management, error handling specific to PAN-OS,
and interactions with the panos-upgrade-assurance tool. The script is intended for use as a standalone utility or
as part of larger automation workflows. It uses the Typer library for command-line interface creation, replacing
the previous argparse implementation. Authentication is now exclusively username/password-based, with no option for
API key authentication. Additionally, the script no longer searches for settings in a .env file but accepts necessary
parameters directly via command-line arguments.

Imports:
    Standard Libraries:
        ipaddress: For handling IP addresses.
        logging: For providing a logging interface.
        os: For interacting with the operating system.
        sys: For accessing system-specific parameters and functions.
        time: For time-related functions.
        RotatingFileHandler (logging.handlers): For handling log file rotation.

    External Libraries:
        xml.etree.ElementTree (ET): For XML tree manipulation.
        panos: For interacting with Palo Alto Networks devices.
        PanDevice, SystemSettings (panos.base, panos.device): For base PAN-OS device operations.
        PanConnectionTimeout, PanDeviceError, PanDeviceXapiError, PanURLError, PanXapiError (panos.errors):
            For handling specific PAN-OS errors.
        Firewall (panos.firewall): For handling firewall-specific operations.

    panos-upgrade-assurance package:
        CheckFirewall, FirewallProxy (panos_upgrade_assurance): For performing checks and acting as a proxy to the firewall.

    Third-party libraries:
        xmltodict: For converting XML data to Python dictionaries.
        typer: For building command-line interface applications.
        BaseModel (pydantic): For creating Pydantic base models.

    Project-specific imports:
        SnapshotReport, ReadinessCheckReport (pan_os_upgrade.models): For handling snapshot and readiness check reports.
"""
# standard library imports
import ipaddress
import logging
import os
import sys
import time
import re
from logging.handlers import RotatingFileHandler
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
# Setting up logging
# ----------------------------------------------------------------------------
def configure_logging(level: str, encoding: str = "utf-8") -> None:
    """
    Sets up the logging configuration for the script with the specified logging level and encoding.

    This function initializes the global logger, sets the specified logging level, and configures two handlers:
    one for console output and another for file output. It uses RotatingFileHandler for file logging to manage
    file size and maintain backups.

    Parameters
    ----------
    level : str
        The desired logging level (e.g., 'debug', 'info', 'warning', 'error', 'critical').
        The input is case-insensitive. If an invalid level is provided, it defaults to 'info'.

    encoding : str, optional
        The encoding format for the file-based log handler, by default 'utf-8'.

    Notes
    -----
    - The Console Handler outputs log messages to the standard output.
    - The File Handler logs messages to 'logs/upgrade.log'. This file is rotated when it reaches 1MB in size,
      maintaining up to three backup files.
    - The logging level influences the verbosity of the log messages. An invalid level defaults to 'info',
      ensuring a baseline of logging.
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


def get_emoji(action: str) -> str:
    """
    Retrieves an emoji character corresponding to a specific action keyword.

    This function is used to enhance the visual appeal and readability of log messages or console outputs.
    It maps predefined action keywords to their corresponding emoji characters.

    Parameters
    ----------
    action : str
        An action keyword for which an emoji is required. Supported keywords include 'success',
        'warning', 'error', 'working', 'report', 'search', 'save', 'stop', and 'start'.

    Returns
    -------
    str
        The emoji character associated with the action keyword. If the keyword is not recognized,
        returns an empty string.

    Examples
    --------
    >>> get_emoji('success')
    '✅'  # Indicates a successful operation

    >>> get_emoji('error')
    '❌'  # Indicates an error

    >>> get_emoji('start')
    '🚀'  # Indicates the start of a process
    """
    emoji_map = {
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "working": "⚙️",
        "report": "📝",
        "search": "🔍",
        "save": "💾",
        "stop": "🛑",
        "start": "🚀",
    }
    return emoji_map.get(action, "")


# ----------------------------------------------------------------------------
# Helper function to validate either the DNS hostname or IP address
# ----------------------------------------------------------------------------
def resolve_hostname(hostname: str) -> bool:
    """
    Checks if a given hostname can be resolved via DNS query.

    This function attempts to resolve the specified hostname using DNS. It queries the DNS servers
    that the operating system is configured to use. The function is designed to return a boolean
    value indicating whether the hostname could be successfully resolved or not.

    Parameters
    ----------
    hostname : str
        The hostname (e.g., 'example.com') to be resolved.

    Returns
    -------
    bool
        Returns True if the hostname can be resolved, False otherwise.

    Raises
    ------
    None
        This function does not raise any exceptions. It handles all exceptions internally and
        returns False in case of any issues during the resolution process.
    """
    try:
        dns.resolver.resolve(hostname)
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout) as err:
        # Optionally log or handle err here if needed
        logging.debug(f"Hostname resolution failed: {err}")
        return False


def ip_callback(value: str) -> str:
    """
    Validates the input as a valid IP address or a resolvable hostname.

    This function first attempts to resolve the hostname via DNS query. If it fails,
    it utilizes the ip_address function from the ipaddress standard library module to
    validate the provided input as an IP address. It is designed to be used as a callback
    function for Typer command-line argument parsing, ensuring that only valid IP addresses
    or resolvable hostnames are accepted as input.

    Parameters
    ----------
    value : str
        A string representing the IP address or hostname to be validated.

    Returns
    -------
    str
        The validated IP address string or hostname.

    Raises
    ------
    typer.BadParameter
        If the input string is not a valid IP address or a resolvable hostname, a typer.BadParameter
        exception is raised with an appropriate error message.
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


# ----------------------------------------------------------------------------
# Helper function to ensure the directories exist for our snapshots
# ----------------------------------------------------------------------------
def ensure_directory_exists(file_path: str) -> None:
    """
    Ensures the existence of the directory for a specified file path, creating it if necessary.

    This function checks if the directory for a given file path exists. If it does not exist, the function
    creates the directory along with any necessary parent directories. This is particularly useful for
    ensuring that the file system is prepared for file operations that require specific directory structures.

    Parameters
    ----------
    file_path : str
        The file path whose directory needs to be verified and potentially created. The function extracts
        the directory part of the file path to check its existence.

    Example
    -------
    Ensuring a directory exists for a file path:
        >>> file_path = '/path/to/directory/file.txt'
        >>> ensure_directory_exists(file_path)
        # If '/path/to/directory/' does not exist, it is created.
    """
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


# ----------------------------------------------------------------------------
# Helper function to check readiness and log the result
# ----------------------------------------------------------------------------
def check_readiness_and_log(
    result: dict,
    test_name: str,
    test_info: dict,
) -> None:
    """
    Evaluates and logs the results of a specified readiness test.

    This function assesses the outcome of a particular readiness test by examining its result.
    It logs the outcome using varying log levels (info, warning, error), determined by the
    test's importance and its result. If a test is marked as critical and fails, the script
    may terminate execution.

    Parameters
    ----------
    result : dict
        A dictionary where each key corresponds to a readiness test name. The value is another dictionary
        containing two keys: 'state' (a boolean indicating the test's success or failure) and 'reason'
        (a string explaining the outcome).

    test_name : str
        The name of the test to evaluate. This name should correspond to a key in the 'result' dictionary.

    test_info : dict
        Information about the test, including its description, log level (info, warning, error), and a flag
        indicating whether to exit the script upon test failure (exit_on_failure).

    Notes
    -----
    - The function utilizes the `get_emoji` helper function to add appropriate emojis to log messages,
      enhancing readability and user experience.
    - If 'state' in the test result is True, the test is logged as passed. Otherwise, it is either
      logged as failed or skipped, based on the specified log level in 'test_info'.

    Raises
    ------
    SystemExit
        If a critical test (marked with "exit_on_failure": True) fails, the script will raise SystemExit.
    """
    test_result = result.get(
        test_name, {"state": False, "reason": "Test not performed"}
    )
    log_message = f'{test_info["description"]} - {test_result["reason"]}'

    if test_result["state"]:
        logging.info(
            f"{get_emoji('success')} Passed Readiness Check: {test_info['description']}"
        )
    else:
        if test_info["log_level"] == "error":
            logging.error(f"{get_emoji('error')} {log_message}")
            if test_info["exit_on_failure"]:
                logging.error(f"{get_emoji('stop')} Halting script.")

                sys.exit(1)
        elif test_info["log_level"] == "warning":
            logging.debug(
                f"{get_emoji('report')} Skipped Readiness Check: {test_info['description']}"
            )
        else:
            logging.debug(log_message)


# ----------------------------------------------------------------------------
# Setting up connection to either Panorama or PAN-OS firewall appliance
# ----------------------------------------------------------------------------
def connect_to_host(
    hostname: str,
    api_username: str,
    api_password: str,
) -> PanDevice:
    """
    Establishes a connection to a Panorama or PAN-OS firewall appliance using provided credentials.

    This function uses the hostname, username, and password to attempt a connection to a target appliance,
    which can be either a Panorama management server or a PAN-OS firewall. It identifies the type of
    appliance based on the provided credentials and hostname. Upon successful connection, it returns an
    appropriate PanDevice object (either Panorama or Firewall).

    Parameters
    ----------
    hostname : str
        The DNS Hostname or IP address of the target appliance.
    api_username : str
        Username for authentication.
    api_password : str
        Password for authentication.

    Returns
    -------
    PanDevice
        An instance of PanDevice (either Panorama or Firewall), representing the established connection.

    Raises
    ------
    SystemExit
        If the connection attempt fails, such as due to a timeout, incorrect credentials, or other errors.

    Example
    --------
    Connecting to a Panorama management server:
        >>> connect_to_host('panorama.example.com', 'admin', 'password')
        <Panorama object>

    Connecting to a PAN-OS firewall:
        >>> connect_to_host('192.168.0.1', 'admin', 'password')
        <Firewall object>
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
            f"{get_emoji('error')} Connection to the {hostname} appliance timed out. Please check the DNS hostname or IP address and network connectivity."
        )

        sys.exit(1)

    except Exception as e:
        logging.error(
            f"{get_emoji('error')} An error occurred while connecting to the {hostname} appliance: {e}"
        )

        sys.exit(1)


# ----------------------------------------------------------------------------
# Determine if an upgrade is suitable
# ----------------------------------------------------------------------------
def determine_upgrade(
    firewall: Firewall,
    target_major: int,
    target_minor: int,
    target_maintenance: Union[int, str],
) -> None:
    """
    Determines the necessity of an upgrade for a firewall to a specific PAN-OS version.

    This function assesses if upgrading the firewall's PAN-OS version is required by comparing its current
    version with the specified target version. The target version is defined by major, minor, and maintenance
    version numbers, where the maintenance version can also include hotfix information. The function logs
    the current and target versions, and establishes the need for an upgrade if the current version is lower
    than the target. If the current version is equal to or higher than the target, it suggests that an upgrade
    is unnecessary or a downgrade is being attempted, leading to termination of the script.

    Parameters
    ----------
    firewall : Firewall
        The instance of the Firewall whose PAN-OS version is being evaluated.
    target_major : int
        Major version number of the target PAN-OS.
    target_minor : int
        Minor version number of the target PAN-OS.
    target_maintenance : Union[int, str]
        Maintenance or hotfix version number of the target PAN-OS, can be an integer or string.

    Raises
    ------
    SystemExit
        Exits the script if the target version is not an upgrade, indicating either a downgrade attempt
        or that the current version already meets or exceeds the target version.

    Notes
    -----
    - Parses the PAN-OS version strings into tuples of integers for accurate comparison.
    - Utilizes emojis in logging for clear and user-friendly status indication.
    """

    def parse_version(version: str) -> Tuple[int, int, int, int]:
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

    current_version = parse_version(firewall.version)

    if isinstance(target_maintenance, int):
        # Handling integer maintenance version separately
        target_version = (target_major, target_minor, target_maintenance, 0)
    else:
        # Handling string maintenance version with hotfix
        target_version = parse_version(
            f"{target_major}.{target_minor}.{target_maintenance}"
        )

    logging.info(f"{get_emoji('report')} Current PAN-OS version: {firewall.version}")
    logging.info(
        f"{get_emoji('report')} Target PAN-OS version: {target_major}.{target_minor}.{target_maintenance}"
    )

    upgrade_needed = current_version < target_version
    if upgrade_needed:
        logging.info(
            f"{get_emoji('success')} Confirmed that moving from {firewall.version} to {target_major}.{target_minor}.{target_maintenance} is an upgrade"
        )
        return

    else:
        logging.error(
            f"{get_emoji('error')} Upgrade is not required or a downgrade was attempted."
        )
        logging.error(f"{get_emoji('stop')} Halting script.")

        sys.exit(1)


# ----------------------------------------------------------------------------
# Determine the firewall's PAN-OS version and any available updates
# ----------------------------------------------------------------------------
def software_update_check(
    firewall: Firewall,
    version: str,
    ha_details: dict,
) -> bool:
    """
    Verifies the availability and readiness of a specified PAN-OS version for upgrade on a firewall.

    This function checks if the target PAN-OS version is available for upgrade on the specified firewall.
    It first refreshes the firewall's system information to ensure current data, then uses the
    `determine_upgrade` function to validate if the target version is an upgrade compared to the current
    version. It checks the list of available PAN-OS versions and verifies if the base image for the
    target version is downloaded. The function returns True if the target version is available and the
    base image is downloaded, and False if the version is not available, the base image is not downloaded,
    or a downgrade attempt is identified.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance to be checked for software update availability.
    version : str
        The target PAN-OS version intended for the upgrade.
    ha_details : dict
        High-availability (HA) details of the firewall. Used to assess if HA synchronization is required for the update.

    Returns
    -------
    bool
        True if the target PAN-OS version is available and ready for upgrade, False otherwise.

    Raises
    ------
    SystemExit
        Exits the script if a downgrade attempt is identified or if the target version is not suitable for an upgrade.

    Example
    --------
    >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
    >>> software_update_check(firewall, '10.1.0', ha_details={})
    True  # If the version 10.1.0 is available and ready for upgrade
    """
    # parse version
    major, minor, maintenance = version.split(".")

    # Make sure we know about the system details - if we have connected via Panorama, this can be null without this.
    logging.debug("Refreshing running system information")
    firewall.refresh_system_info()

    # check to see if the specified version is older than the current version
    determine_upgrade(firewall, major, minor, maintenance)

    # retrieve available versions of PAN-OS
    firewall.software.check()
    available_versions = firewall.software.versions
    logging.debug(f"Available PAN-OS versions: {available_versions}")

    # check to see if specified version is available for upgrade
    if version in available_versions:
        logging.info(
            f"{get_emoji('success')} PAN-OS version {version} is available for download"
        )

        # validate the specified version's base image is already downloaded
        if available_versions[f"{major}.{minor}.0"]["downloaded"]:
            logging.info(
                f"{get_emoji('success')} Base image for {version} is already downloaded"
            )
            return True

        else:
            logging.error(
                f"{get_emoji('error')} Base image for {version} is not downloaded"
            )
            return False
    else:
        logging.error(
            f"{get_emoji('error')} PAN-OS version {version} is not available for download"
        )
        return False


# ----------------------------------------------------------------------------
# Determine if the firewall is standalone, HA, or in a cluster
# ----------------------------------------------------------------------------
def get_ha_status(firewall: Firewall) -> Tuple[str, Optional[dict]]:
    """
    Determines the High-Availability (HA) deployment status and configuration of a specified Firewall appliance.

    This function queries a firewall to determine its HA deployment status. It can identify if the firewall
    operates in a standalone mode, as part of an HA pair (either active/passive or active/active), or within
    a cluster configuration. It fetches and logs both the deployment status and, if applicable, detailed
    configuration information about the HA setup.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the firewall whose HA status is to be assessed.

    Returns
    -------
    Tuple[str, Optional[dict]]
        A tuple containing two elements:
        - A string indicating the HA deployment type (e.g., 'standalone', 'active/passive', 'active/active').
        - An optional dictionary with detailed HA configuration information. The dictionary is provided if
          the firewall is part of an HA setup; otherwise, None is returned.

    Example
    -------
    >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
    >>> ha_status, ha_details = get_ha_status(firewall)
    >>> print(ha_status)  # Example output: 'active/passive'
    >>> print(ha_details) # Example output: {'ha_details': {...}}

    Notes
    -----
    - This function uses the 'show_highavailability_state' method from the Firewall class to retrieve HA status.
    - For processing the XML response, it employs the 'flatten_xml_to_dict' helper function to translate the
      data into a Python dictionary, providing a more accessible format for further operations or analysis.
    """
    logging.debug(
        f"{get_emoji('start')} Getting {firewall.serial} deployment information..."
    )
    deployment_type = firewall.show_highavailability_state()
    logging.debug(f"{get_emoji('report')} Firewall deployment: {deployment_type[0]}")

    if deployment_type[1]:
        ha_details = flatten_xml_to_dict(deployment_type[1])
        logging.debug(
            f"{get_emoji('report')} Firewall deployment details: {ha_details}"
        )
        return deployment_type[0], ha_details
    else:
        return deployment_type[0], None


# ----------------------------------------------------------------------------
# Download the target PAN-OS version
# ----------------------------------------------------------------------------
def software_download(
    firewall: Firewall,
    target_version: str,
    ha_details: dict,
) -> bool:
    """
    Initiates and monitors the download of a specified PAN-OS software version on the firewall.

    This function starts the download process for the given target PAN-OS version on the specified
    firewall. It continually checks and logs the download's progress. If the download is successful,
    it returns True. If the download process encounters errors or fails, these are logged, and the
    function returns False. Exceptions during the download process lead to script termination.

    Parameters
    ----------
    firewall : Firewall
        The Firewall instance on which the software is to be downloaded.
    target_version : str
        The PAN-OS version targeted for download.
    ha_details : dict
        High-availability details of the firewall, determining if HA synchronization is needed.

    Returns
    -------
    bool
        True if the download is successful, False if the download fails or encounters an error.

    Raises
    ------
    SystemExit
        Raised if an exception occurs during the download process or if a critical error is encountered.

    Example
    --------
    Initiating a PAN-OS version download:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> software_download(firewall, '10.1.0', ha_details={})
        True or False depending on the success of the download

    Notes
    -----
    - Before initiating the download, the function checks if the target version is already available on the firewall.
    - It uses the 'download' method of the Firewall's software attribute to perform the download.
    - The function sleeps for 30 seconds between each status check to allow time for the download to progress.
    """

    if firewall.software.versions[target_version]["downloaded"]:
        logging.info(
            f"{get_emoji('success')} PAN-OS version {target_version} already on firewall."
        )
        return True

    if (
        not firewall.software.versions[target_version]["downloaded"]
        or firewall.software.versions[target_version]["downloaded"] != "downloading"
    ):
        logging.info(
            f"{get_emoji('search')} PAN-OS version {target_version} is not on the firewall"
        )

        start_time = time.time()

        try:
            logging.info(
                f"{get_emoji('start')} PAN-OS version {target_version} is beginning download"
            )
            firewall.software.download(target_version)
        except PanDeviceXapiError as download_error:
            logging.error(f"{get_emoji('error')} {download_error}")

            sys.exit(1)

        while True:
            firewall.software.info()
            dl_status = firewall.software.versions[target_version]["downloaded"]
            elapsed_time = int(time.time() - start_time)

            if dl_status is True:
                logging.info(
                    f"{get_emoji('success')} {target_version} downloaded in {elapsed_time} seconds",
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
                        f"{get_emoji('working')} {status_msg} - HA will sync image - Elapsed time: {elapsed_time} seconds"
                    )
                else:
                    logging.info(f"{status_msg} - Elapsed time: {elapsed_time} seconds")
            else:
                logging.error(
                    f"{get_emoji('error')} Download failed after {elapsed_time} seconds"
                )
                return False

            time.sleep(30)

    else:
        logging.error(f"{get_emoji('error')} Error downloading {target_version}.")

        sys.exit(1)


# ----------------------------------------------------------------------------
# Handle panos-upgrade-assurance operations
# ----------------------------------------------------------------------------
def run_assurance(
    firewall: Firewall,
    hostname: str,
    operation_type: str,
    actions: List[str],
    config: Dict[str, Union[str, int, float, bool]],
) -> Union[SnapshotReport, ReadinessCheckReport, None]:
    """
    Executes specified operational tasks on the firewall and returns the results or reports.

    This function handles different operational tasks on the firewall based on the provided
    'operation_type'. It supports operations like performing readiness checks, capturing state
    snapshots, and generating reports. The operation is executed according to the 'actions' and
    'config' specified. Successful operations return results or a report object. Invalid operations
    or errors during execution result in logging an error and returning None.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance on which to perform the operations.
    hostname : str
        The ip address or dns hostname of the firewall.
    operation_type : str
        The type of operation to perform (e.g., 'readiness_check', 'state_snapshot', 'report').
    actions : List[str]
        A list of actions to be performed for the specified operation type.
    config : Dict[str, Union[str, int, float, bool]]
        Configuration settings for the specified actions.

    Returns
    -------
    Union[SnapshotReport, ReadinessCheckReport, None]
        The results of the operation as a report object, or None if the operation type or action is invalid, or an error occurs.

    Raises
    ------
    SystemExit
        Raised if an invalid action is specified for the operation type or if an exception occurs during execution.

    Example
    --------
    Performing a state snapshot operation:
        >>> firewall = Firewall(hostname='192.168.1.1', 'admin', 'password')
        >>> run_assurance(firewall, 'firewall1', 'state_snapshot', ['arp_table', 'ip_sec_tunnels'], {})
        SnapshotReport object or None

    Notes
    -----
    - The 'readiness_check' operation verifies the firewall's readiness for upgrade-related tasks.
    - The 'state_snapshot' operation captures the current state of the firewall.
    - The 'report' operation generates a report based on the specified actions. This is pending implementation.
    """
    # setup Firewall client
    proxy_firewall = FirewallProxy(firewall)
    checks_firewall = CheckFirewall(proxy_firewall)

    results = None

    if operation_type == "readiness_check":
        for action in actions:
            if action not in AssuranceOptions.READINESS_CHECKS.keys():
                logging.error(
                    f"{get_emoji('error')} Invalid action for readiness check: {action}"
                )

                sys.exit(1)

        try:
            logging.info(
                f"{get_emoji('start')} Performing readiness checks to determine if firewall is ready for upgrade..."
            )
            result = checks_firewall.run_readiness_checks(actions)

            for (
                test_name,
                test_info,
            ) in AssuranceOptions.READINESS_CHECKS.items():
                check_readiness_and_log(result, test_name, test_info)

            return ReadinessCheckReport(**result)

        except Exception as e:
            logging.error(f"{get_emoji('error')} Error running readiness checks: {e}")

            return None

    elif operation_type == "state_snapshot":
        # validate each type of action
        for action in actions:
            if action not in AssuranceOptions.STATE_SNAPSHOTS:
                logging.error(
                    f"{get_emoji('error')} Invalid action for state snapshot: {action}"
                )
                return

        # take snapshots
        try:
            logging.debug("Running snapshots...")
            results = checks_firewall.run_snapshots(snapshots_config=actions)
            logging.debug(results)

            if results:
                # Pass the results to the SnapshotReport model
                return SnapshotReport(hostname=hostname, **results)
            else:
                return None

        except Exception as e:
            logging.error(f"{get_emoji('error')} Error running snapshots: %s", e)
            return

    elif operation_type == "report":
        for action in actions:
            if action not in AssuranceOptions.REPORTS:
                logging.error(
                    f"{get_emoji('error')} Invalid action for report: {action}"
                )
                return
            logging.info(f"{get_emoji('report')} Generating report: {action}")
            # result = getattr(Report(firewall), action)(**config)

    else:
        logging.error(f"{get_emoji('error')} Invalid operation type: {operation_type}")
        return

    return results


# ----------------------------------------------------------------------------
# Perform the snapshot of the network state
# ----------------------------------------------------------------------------
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
        f"{get_emoji('start')} Performing snapshot of network state information..."
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
        logging.info(f"{get_emoji('success')} Network snapshot created successfully")
        network_snapshot_json = network_snapshot.model_dump_json(indent=4)
        logging.debug(network_snapshot_json)

        ensure_directory_exists(file_path)

        with open(file_path, "w") as file:
            file.write(network_snapshot_json)

        logging.debug(
            f"{get_emoji('save')} Network state snapshot collected from {hostname}, saved to {file_path}"
        )
    else:
        logging.error(f"{get_emoji('error')} Failed to create snapshot")


# ----------------------------------------------------------------------------
# Perform the readiness checks
# ----------------------------------------------------------------------------
def perform_readiness_checks(
    firewall: Firewall,
    hostname: str,
    file_path: str,
) -> None:
    """
    Executes readiness checks on a specified firewall and saves the results as a JSON file.

    This function initiates a series of readiness checks on the firewall to assess its state before
    proceeding with operations like upgrades. The checks cover aspects like configuration status,
    content version, license validity, HA status, and more. The results of these checks are logged,
    and a detailed report is generated and saved to the provided file path.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance on which to perform the readiness checks.
    hostname : str
        Hostname of the firewall, used primarily for logging purposes.
    file_path : str
        Path to the file where the readiness check report JSON will be saved.

    Notes
    -----
    - Utilizes the `run_assurance` function to perform the readiness checks.
    - Ensures the existence of the directory where the report file will be saved.
    - Logs the outcome of the readiness checks and saves the report in JSON format.
    - Logs an error message if the readiness check creation fails.

    Example
    --------
    Conducting readiness checks:
        >>> firewall = Firewall(hostname='192.168.1.1', 'username', 'password')
        >>> perform_readiness_checks(firewall, 'firewall1', '/path/to/readiness_report.json')
        # Readiness report is saved to the specified path.
    """

    logging.debug(
        f"{get_emoji('start')} Performing readiness checks of target firewall..."
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
        logging.info(f"{get_emoji('success')} Readiness Checks completed")
        readiness_check_report_json = readiness_check.model_dump_json(indent=4)
        logging.debug(readiness_check_report_json)

        ensure_directory_exists(file_path)

        with open(file_path, "w") as file:
            file.write(readiness_check_report_json)

        logging.debug(
            f"{get_emoji('save')} Readiness checks completed for {hostname}, saved to {file_path}"
        )
    else:
        logging.error(f"{get_emoji('error')} Failed to create readiness check")


# ----------------------------------------------------------------------------
# Back up the configuration
# ----------------------------------------------------------------------------
def backup_configuration(
    firewall: Firewall,
    file_path: str,
) -> bool:
    """
    Backs up the current running configuration of a specified firewall to a local file.

    This function retrieves the running configuration from the firewall and saves it as an XML file
    at the specified file path. It checks the validity of the retrieved XML data and logs the success
    or failure of the backup process.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance from which the configuration is to be backed up.
    file_path : str
        The path where the configuration backup file will be saved.

    Returns
    -------
    bool
        Returns True if the backup is successfully created, False otherwise.

    Raises
    ------
    Exception
        Raises an exception if any error occurs during the backup process.

    Notes
    -----
    - The function verifies the XML structure of the retrieved configuration.
    - Ensures the directory for the backup file exists.
    - The backup file is saved in XML format.

    Example
    --------
    Backing up the firewall configuration:
        >>> firewall = Firewall(hostname='192.168.1.1', 'admin', 'password')
        >>> backup_configuration(firewall, '/path/to/config_backup.xml')
        # Configuration is backed up to the specified file.
    """

    try:
        # Run operational command to retrieve configuration
        config_xml = firewall.op("show config running")
        if config_xml is None:
            logging.error(
                f"{get_emoji('error')} Failed to retrieve running configuration."
            )
            return False

        # Check XML structure
        if (
            config_xml.tag != "response"
            or len(config_xml) == 0
            or config_xml[0].tag != "result"
        ):
            logging.error(
                f"{get_emoji('error')} Unexpected XML structure in configuration data."
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
            f"{get_emoji('save')} Configuration backed up successfully to {file_path}"
        )
        return True

    except Exception as e:
        logging.error(f"{get_emoji('error')} Error backing up configuration: {e}")
        return False


# ----------------------------------------------------------------------------
# Perform the upgrade process
# ----------------------------------------------------------------------------
def perform_upgrade(
    firewall: Firewall,
    hostname: str,
    target_version: str,
    ha_details: Optional[dict] = None,
    max_retries: int = 3,
    retry_interval: int = 60,
) -> None:
    """
    Initiates and manages the upgrade process of a firewall to a specified PAN-OS version.

    This function attempts to upgrade the firewall to the given PAN-OS version, handling potential issues
    and retrying if necessary. It deals with High Availability (HA) considerations and ensures that the
    upgrade process is robust against temporary failures or busy states. The function logs each step of the
    process and exits the script if critical errors occur.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance to be upgraded.
    hostname : str
        The hostname of the firewall, used for logging purposes.
    target_version : str
        The target PAN-OS version for the upgrade.
    ha_details : Optional[dict], optional
        High Availability details of the firewall, by default None.
    max_retries : int, optional
        The maximum number of retry attempts for the upgrade, by default 3.
    retry_interval : int, optional
        The interval (in seconds) to wait between retry attempts, by default 60.

    Raises
    ------
    SystemExit
        Exits the script if the upgrade job fails, if HA synchronization issues occur,
        or if critical errors are encountered during the upgrade process.

    Notes
    -----
    - The function handles retries based on the 'max_retries' and 'retry_interval' parameters.
    - In case of 'software manager is currently in use' errors, retries are attempted.
    - Critical errors during the upgrade process lead to script termination.

    Example
    -------
    Upgrading a firewall to a specific PAN-OS version:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> perform_upgrade(firewall, '192.168.1.1', '10.2.0', max_retries=2, retry_interval=30)
        # The firewall is upgraded to PAN-OS version 10.2.0, with retries if necessary.
    """

    logging.info(
        f"{get_emoji('start')} Performing upgrade on {hostname} to version {target_version}..."
    )

    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(
                f"{get_emoji('start')} Attempting upgrade {hostname} to version {target_version} (Attempt {attempt + 1} of {max_retries})..."
            )
            install_job = firewall.software.install(target_version, sync=True)

            if install_job["success"]:
                logging.info(
                    f"{get_emoji('success')} {hostname} upgrade completed successfully"
                )
                logging.debug(f"{get_emoji('report')} {install_job}")
                break  # Exit loop on successful upgrade
            else:
                logging.error(f"{get_emoji('error')} {hostname} upgrade job failed.")
                attempt += 1
                if attempt < max_retries:
                    logging.info(
                        f"{get_emoji('warning')} Retrying in {retry_interval} seconds..."
                    )
                    time.sleep(retry_interval)

        except PanDeviceError as upgrade_error:
            logging.error(
                f"{get_emoji('error')} {hostname} upgrade error: {upgrade_error}"
            )
            error_message = str(upgrade_error)
            if "software manager is currently in use" in error_message:
                attempt += 1
                if attempt < max_retries:
                    logging.info(
                        f"{get_emoji('warning')} Software manager is busy. Retrying in {retry_interval} seconds..."
                    )
                    time.sleep(retry_interval)
            else:
                logging.error(
                    f"{get_emoji('stop')} Critical error during upgrade. Halting script."
                )
                sys.exit(1)


# ----------------------------------------------------------------------------
# Perform the reboot process
# ----------------------------------------------------------------------------
def perform_reboot(
    firewall: Firewall,
    target_version: str,
    ha_details: Optional[dict] = None,
) -> None:
    """
    Initiates and oversees the reboot process of a firewall, ensuring it reaches the specified target version.

    This function triggers a reboot of the specified firewall and monitors its status throughout the process.
    In HA (High Availability) setups, it confirms synchronization with the HA peer post-reboot. The function
    includes robust handling of various states and errors, with detailed logging. It verifies the firewall
    reaches the target PAN-OS version upon reboot completion.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance to be rebooted.
    target_version : str
        The target PAN-OS version to confirm after reboot.
    ha_details : Optional[dict], optional
        High Availability details of the firewall, if applicable. Default is None.

    Raises
    ------
    SystemExit
        Exits the script if the firewall fails to reboot to the target version, if HA synchronization issues
        occur, or if critical errors are encountered during the reboot process.

    Notes
    -----
    - The function checks the firewall's version and HA synchronization status (if applicable) post-reboot.
    - Confirms that the firewall has successfully rebooted to the target PAN-OS version.
    - Script terminates if the firewall doesn't reach the target version or synchronize (in HA setups) within
      20 minutes.

    Example
    -------
    Rebooting a firewall to a specific PAN-OS version:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> perform_reboot(firewall, '10.2.0')
        # The firewall undergoes a reboot and the script monitors until it reaches the target version 10.2.0.
    """

    reboot_start_time = time.time()
    rebooted = False

    # Check if HA details are available
    if ha_details:
        logging.info(f"{get_emoji('start')} Rebooting the passive HA firewall...")

    # Reboot standalone firewall
    else:
        logging.info(f"{get_emoji('start')} Rebooting the standalone firewall...")

    reboot_job = firewall.op(
        "<request><restart><system/></restart></request>", cmd_xml=False
    )
    reboot_job_result = flatten_xml_to_dict(reboot_job)
    logging.info(f"{get_emoji('report')} {reboot_job_result['result']}")

    # Wait for the firewall reboot process to initiate before checking status
    time.sleep(60)

    while not rebooted:
        # Check if HA details are available
        if ha_details:
            try:
                deploy_info, current_ha_details = get_ha_status(firewall)
                logging.debug(
                    f"{get_emoji('report')} deploy_info: {deploy_info}",
                )
                logging.debug(
                    f"{get_emoji('report')} current_ha_details: {current_ha_details}",
                )

                if current_ha_details and deploy_info in ["active", "passive"]:
                    if (
                        current_ha_details["result"]["group"]["running-sync"]
                        == "synchronized"
                    ):
                        logging.info(
                            f"{get_emoji('success')} HA passive firewall rebooted and synchronized with its peer in {int(time.time() - reboot_start_time)} seconds"
                        )
                        rebooted = True
                    else:
                        logging.info(
                            f"{get_emoji('working')} HA passive firewall rebooted but not yet synchronized with its peer. Will try again in 30 seconds."
                        )
                        time.sleep(60)
            except (PanXapiError, PanConnectionTimeout, PanURLError):
                logging.info(f"{get_emoji('working')} Firewall is rebooting...")
                time.sleep(60)

        # Reboot standalone firewall
        else:
            try:
                firewall.refresh_system_info()
                logging.info(
                    f"{get_emoji('report')} Firewall version: {firewall.version}"
                )

                if firewall.version == target_version:
                    logging.info(
                        f"{get_emoji('success')} Firewall rebooted in {int(time.time() - reboot_start_time)} seconds"
                    )
                    rebooted = True
                else:
                    logging.error(
                        f"{get_emoji('stop')} Firewall rebooted but running the target version. Please try again."
                    )
                    sys.exit(1)
            except (PanXapiError, PanConnectionTimeout, PanURLError):
                logging.info(f"{get_emoji('working')} Firewall is rebooting...")
                time.sleep(60)

        # Check if 20 minutes have passed
        if time.time() - reboot_start_time > 1200:  # 20 minutes in seconds
            logging.error(
                f"{get_emoji('error')} Firewall did not become available and/or establish a Connected sync state with its HA peer after 20 minutes. Please check the firewall status manually."
            )
            break


# ----------------------------------------------------------------------------
# Helper function to convert XML ET.Element into a Python dictionary
# ----------------------------------------------------------------------------
def flatten_xml_to_dict(element: ET.Element) -> dict:
    """
    Converts a given XML element to a dictionary, flattening the XML structure.

    This function recursively processes an XML element, converting it and its children into a dictionary format.
    The conversion flattens the XML structure, making it easier to adapt to model definitions. It treats elements
    containing only text as leaf nodes, directly mapping their tags to their text content. For elements with child
    elements, it continues the recursion. The function handles multiple occurrences of the same tag by aggregating
    them into a list. Specifically, it always treats elements with the tag 'entry' as lists, reflecting their
    common usage pattern in PAN-OS XML API responses.

    Parameters
    ----------
    element : ET.Element
        The XML element to be converted. This should be an instance of ElementTree.Element, typically obtained
        from parsing XML data using the ElementTree API.

    Returns
    -------
    dict
        A dictionary representation of the XML element. The dictionary mirrors the structure of the XML,
        with tags as keys and text content or nested dictionaries as values. Elements with the same tag
        are aggregated into a list.

    Notes
    -----
    - This function is designed to work with PAN-OS XML API responses, which often use the 'entry' tag
      to denote list items.
    - The function does not preserve attributes of XML elements; it focuses solely on tags and text content.

    Example
    -------
    Converting an XML element with nested children to a dictionary:
        >>> xml_string = "<root><child>value</child><child><subchild>subvalue</subchild></child></root>"
        >>> xml_element = ET.fromstring(xml_string)
        >>> flatten_xml_to_dict(xml_element)
        {'child': ['value', {'subchild': 'subvalue'}]}
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


def model_from_api_response(
    element: Union[ET.Element, ET.ElementTree],
    model: type[FromAPIResponseMixin],
) -> FromAPIResponseMixin:
    """
    Converts an XML Element, typically from an API response, into a specified Pydantic model.

    This function facilitates the transformation of XML data into a structured Pydantic model.
    It first flattens the XML Element into a dictionary and then maps this dictionary to the
    specified Pydantic model. This approach simplifies the handling of complex XML structures
    often returned by APIs, enabling easier manipulation and access to the data within Python.

    Parameters
    ----------
    element : Union[ET.Element, ET.ElementTree]
        The XML Element or ElementTree to be converted. This is typically obtained from parsing
        XML data returned by an API call.

    model : type[FromAPIResponseMixin]
        The Pydantic model class into which the XML data will be converted. This model must
        inherit from the FromAPIResponseMixin, indicating it can handle data derived from
        API responses.

    Returns
    -------
    FromAPIResponseMixin
        An instance of the specified Pydantic model, populated with data extracted from the
        provided XML Element.

    Example
    -------
    Converting an XML response to a Pydantic model:
        >>> xml_element = ET.fromstring('<response><data>value</data></response>')
        >>> MyModel = type('MyModel', (FromAPIResponseMixin, BaseModel), {})
        >>> model_instance = model_from_api_response(xml_element, MyModel)
        # 'model_instance' is now an instance of 'MyModel' with data from 'xml_element'.
    """
    result_dict = flatten_xml_to_dict(element)
    return model.from_api_response(result_dict)


def get_managed_devices(panorama: Panorama, **filters) -> list[ManagedDevice]:
    """
    Retrieves a filtered list of managed devices from a specified Panorama appliance.

    This function queries a Panorama appliance for its managed devices and filters the results
    based on the provided keyword arguments. Each keyword argument must correspond to an
    attribute of the `ManagedDevice` model. The function applies regex matching for each
    filter, returning only those devices that match all specified filters.

    Parameters
    ----------
    panorama : Panorama
        An instance of the Panorama class, representing the Panorama appliance to query.

    filters : **kwargs
        Keyword argument filters to apply. Each keyword should correspond to an attribute
        of the `ManagedDevice` model class. The value for each keyword is a regex pattern
        to match against the corresponding attribute.

    Returns
    -------
    list[ManagedDevice]
        A list of `ManagedDevice` instances that match the specified filters.

    Example
    -------
    Retrieving devices from Panorama with specific hostname and model filters:
        >>> panorama = Panorama('192.168.1.1', 'admin', 'password')
        >>> managed_devices = get_managed_devices(panorama, hostname='^PA-220$', model='.*220.*')
        # Returns a list of `ManagedDevice` instances for devices with hostnames matching 'PA-220'
        # and model containing '220'.
    """
    managed_devices = model_from_api_response(
        panorama.op("show devices all"), ManagedDevices
    )
    devices = managed_devices.devices
    for filter_key, filter_value in filters.items():
        devices = [d for d in devices if re.match(filter_value, getattr(d, filter_key))]

    return devices


def get_firewalls_from_panorama(panorama: Panorama, **filters) -> list[Firewall]:
    """
    Retrieves a list of Firewall objects associated with a Panorama appliance, filtered by specified criteria.

    This function queries a Panorama appliance for its managed firewalls and filters the results based on the
    provided keyword arguments. The firewalls that match the specified filters are then instantiated as `Firewall`
    objects. These firewall objects are also attached to the Panorama instance, allowing API calls to be proxied
    through the Panorama.

    Parameters
    ----------
    panorama : Panorama
        An instance of the Panorama class, representing the Panorama appliance to query.

    filters : **kwargs
        Keyword argument filters to apply. Each keyword should correspond to an attribute of the `ManagedDevice`
        model class. The value for each keyword is a regex pattern to match against the corresponding attribute.

    Returns
    -------
    list[Firewall]
        A list of `Firewall` instances that match the specified filters.

    Example
    -------
    Getting firewalls from Panorama with specific model filters:
        >>> panorama = Panorama('192.168.1.1', 'admin', 'password')
        >>> firewalls = get_firewalls_from_panorama(panorama, model='.*220.*')
        # Returns a list of `Firewall` instances for firewalls with models containing '220'.
    """
    firewalls = []
    for managed_device in get_managed_devices(panorama, **filters):
        firewall = Firewall(serial=managed_device.serial)
        firewalls.append(firewall)
        panorama.add(firewall)

    return firewalls


def upgrade_single_firewall(
    firewall: Firewall,
    target_version: str,
    dry_run: bool,
) -> None:
    """
    Manages the upgrade process for a single firewall appliance to a specified PAN-OS version.

    This function orchestrates a series of steps to upgrade a firewall, including readiness checks,
    software download, configuration backup, and the actual upgrade and reboot processes. It supports a
    'dry run' mode to simulate the upgrade process without applying changes. The function is designed to handle
    both standalone firewalls and firewalls in a High Availability (HA) setup.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the firewall to be upgraded.
    target_version : str
        The target PAN-OS version to upgrade the firewall to.
    dry_run : bool
        If True, the function will simulate the upgrade process without making any changes.
        If False, the function will proceed with the actual upgrade.

    Steps
    -----
    1. Refresh system information to ensure latest data is available.
    2. Determine if the firewall is standalone, part of HA, or in a cluster.
    3. Check firewall readiness for the specified target version.
    4. Download the target PAN-OS version if not already present.
    5. Perform pre-upgrade snapshots and readiness checks.
    6. Backup current configuration to the local filesystem.
    7. Proceed with upgrade and reboot if not a dry run.

    Notes
    -----
    - The script gracefully exits if the firewall is not ready for the upgrade.
    - In HA setups, the script checks for synchronization status of the HA pair.
    - In dry run mode, the script simulates the upgrade process without performing the actual upgrade.

    Example
    -------
    Upgrading a firewall to a specific PAN-OS version:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> upgrade_single_firewall(firewall, '10.1.0', dry_run=False)
        # This will upgrade the firewall to PAN-OS version 10.1.0.
    """
    # Refresh system information to ensure we have the latest data
    logging.debug(f"{get_emoji('start')} Refreshing system information...")
    firewall_details = SystemSettings.refreshall(firewall)[0]
    logging.info(
        f"{get_emoji('report')} {firewall.serial} {firewall_details.hostname} {firewall_details.ip_address}"
    )

    # Determine if the firewall is standalone, HA, or in a cluster
    logging.debug(
        f"{get_emoji('start')} Performing test to see if firewall is standalone, HA, or in a cluster..."
    )
    deploy_info, ha_details = get_ha_status(firewall)
    logging.info(f"{get_emoji('report')} Firewall HA mode: {deploy_info}")
    logging.debug(f"{get_emoji('report')} Firewall HA details: {ha_details}")

    # Check to see if the firewall is ready for an upgrade
    logging.debug(
        f"{get_emoji('start')} Performing test to validate firewall's readiness..."
    )
    update_available = software_update_check(firewall, target_version, ha_details)
    logging.debug(f"{get_emoji('report')} Firewall readiness check complete")

    # gracefully exit if the firewall is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"{get_emoji('error')} Firewall is not ready for upgrade to {target_version}.",
        )

        sys.exit(1)

    # Download the target PAN-OS version
    logging.info(
        f"{get_emoji('start')} Performing test to see if {target_version} is already downloaded..."
    )
    image_downloaded = software_download(firewall, target_version, ha_details)
    if deploy_info == "active" or deploy_info == "passive":
        logging.info(
            f"{get_emoji('success')} {target_version} has been downloaded and sync'd to HA peer."
        )
    else:
        logging.info(
            f"{get_emoji('success')} PAN-OS version {target_version} has been downloaded."
        )

    # Begin snapshots of the network state
    if not image_downloaded:
        logging.error(f"{get_emoji('error')} Image not downloaded, exiting...")

        sys.exit(1)

    # Perform the pre-upgrade snapshot
    perform_snapshot(
        firewall,
        firewall_details.hostname,
        f'assurance/snapshots/{firewall_details.hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
    )

    # Perform Readiness Checks
    perform_readiness_checks(
        firewall,
        firewall_details.hostname,
        f'assurance/readiness_checks/{firewall_details.hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
    )

    # If the firewall is in an HA pair, check the HA peer to ensure sync has been enabled
    if ha_details:
        logging.info(
            f"{get_emoji('start')} Performing test to see if HA peer is in sync..."
        )
        if ha_details["result"]["group"]["running-sync"] == "synchronized":
            logging.info(f"{get_emoji('success')} HA peer sync test has been completed")
        else:
            logging.error(
                f"{get_emoji('error')} HA peer state is not in sync, please try again"
            )
            logging.error(f"{get_emoji('stop')} Halting script.")

            sys.exit(1)

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji('start')} Performing backup of {firewall_details.hostname}'s configuration to local filesystem..."
    )
    backup_config = backup_configuration(
        firewall,
        f'assurance/configurations/{firewall_details.hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
    )
    logging.debug(f"{get_emoji('report')} {backup_config}")

    # Exit execution is dry_run is True
    if dry_run is True:
        logging.info(f"{get_emoji('success')} Dry run complete, exiting...")
        logging.info(f"{get_emoji('stop')} Halting script.")
        sys.exit(0)
    else:
        logging.info(f"{get_emoji('start')} Not a dry run, continue with upgrade...")

    # Perform the upgrade
    perform_upgrade(
        firewall=firewall,
        hostname=firewall_details.hostname,
        target_version=target_version,
        ha_details=ha_details,
    )

    # Perform the reboot
    perform_reboot(
        firewall=firewall,
        target_version=target_version,
        ha_details=ha_details,
    )


def filter_string_to_dict(filter_string: str) -> dict:
    """
    Converts a string containing comma-separated key-value pairs into a dictionary.

    This utility function parses a string where each key-value pair is separated by a comma, and
    each key is separated from its value by an equal sign ('='). It's useful for converting filter
    strings into dictionary formats, commonly used in configurations and queries.

    Parameters
    ----------
    filter_string : str
        The string to be parsed into key-value pairs. It should follow the format 'key1=value1,key2=value2,...'.
        If the string is empty or improperly formatted, an empty dictionary is returned.

    Returns
    -------
    dict
        A dictionary with keys and values derived from the `filter_string`. Keys are the substrings before each '='
        character, and values are the corresponding substrings after the '=' character.

    Examples
    --------
    Converting a filter string to a dictionary:
        >>> filter_string_to_dict("hostname=test,serial=11111")
        {'hostname': 'test', 'serial': '11111'}

    Handling an empty or improperly formatted string:
        >>> filter_string_to_dict("")
        {}
        >>> filter_string_to_dict("invalid_format_string")
        {}

    Notes
    -----
    - The function does not perform validation on the key-value pairs. It's assumed that the input string is
      correctly formatted.
    - In case of duplicate keys, the last occurrence of the key in the string will determine its value in the
      resulting dictionary.
    """
    result = {}
    for substr in filter_string.split(","):
        k, v = substr.split("=")
        result[k] = v

    return result


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
        ),
    ] = "",
    log_level: Annotated[
        str,
        typer.Option("--log-level", "-l", help="Set the logging output level"),
    ] = "info",
):
    """
    Orchestrates the upgrade process for PAN-OS firewalls, including both standalone and HA configurations.

    This script automates the process of upgrading Palo Alto Networks firewalls to a specified PAN-OS version. It
    supports both standalone firewalls and those managed by Panorama. The script can perform a full upgrade process
    or a dry run, which includes all pre-upgrade checks without applying the actual upgrade. It handles various
    aspects like readiness checks, configuration backup, software download, and reboot procedures.

    Parameters
    ----------
    hostname : str
        Hostname or IP address of the Panorama or firewall appliance.
    username : str
        Username for authentication with the appliance.
    password : str
        Password for authentication.
    target_version : str
        Target PAN-OS version for the upgrade.
    dry_run : bool, optional
        If True, performs a dry run without executing the actual upgrade (default is False).
    filter : str, optional
        When connecting to Panorama, defines the filter criteria for selecting devices to upgrade (default is "").
    log_level : str, optional
        Sets the logging level for script execution (default is "info").

    Workflow
    --------
    1. Initializes necessary directories and logging configuration.
    2. Establishes a connection to the specified Panorama or firewall appliance.
    3. If connected to Panorama, filters and retrieves the list of firewalls to upgrade.
    4. Sequentially processes each firewall, performing readiness checks, downloading necessary software, and executing the upgrade and reboot steps.

    Exits
    ------
    - On critical errors that prevent continuation of the script.
    - After successfully completing a dry run.
    - If the firewall is not ready for the intended upgrade.
    - If HA synchronization issues are detected in HA configurations.

    Example Usage
    --------------
    Upgrading a firewall to version '10.2.7':
    ```bash
    python upgrade.py --hostname 192.168.1.1 --username admin --password secret --version 10.2.7
    ```
    Upgrading a firewall to version '10.2.7' by using Panorama appliance as a proxy:
    ```bash
    python upgrade.py --hostname panorama.cdot.io --filter "hostname=houston" --username admin --password secret --version 10.2.7
    ```

    Notes
    -----
    - The script operates serially on each identified firewall.
    - Currently, the script is not HA-aware, meaning it does not handle upgrades of both firewalls in an HA pair simultaneously.
    - The script includes extensive logging, providing detailed feedback throughout the upgrade process.
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
    logging.debug(f"{get_emoji('start')} Connecting to PAN-OS device...")
    device = connect_to_host(
        hostname=hostname,
        api_username=username,
        api_password=password,
    )

    firewalls_to_upgrade = []
    if type(device) is Firewall:
        logging.info(f"{get_emoji('success')} Connection to firewall established")
        firewalls_to_upgrade.append(device)
    elif type(device) is Panorama:
        if not filter:
            logging.error(
                f"{get_emoji('error')} Specified device is Panorama, but no filter string was provided."
            )
            sys.exit(1)

        logging.info(
            f"{get_emoji('success')} Connection to Panorama established. Firewall connections will be proxied!"
        )
        firewalls_to_upgrade = get_firewalls_from_panorama(
            device, **filter_string_to_dict(filter)
        )

    # Run the upgrade process for each identified firewall. Note this runs serially, i.e one after the other.
    # This is also not yet "HA aware".
    for firewall in firewalls_to_upgrade:
        upgrade_single_firewall(firewall, target_version, dry_run)


if __name__ == "__main__":
    app()
