"""
upgrade.py: A script to automate the upgrade process of PAN-OS firewalls.

This module contains the functionality to perform automated upgrade procedures on Palo Alto Networks firewalls.
It includes handling for various PAN-OS operations, system settings management, error handling specific to PAN-OS,
and interactions with the panos-upgrade-assurance tool. The module is designed to be used as a standalone script or
integrated into larger automation workflows.

Imports:
    Standard Libraries:
        argparse: For parsing command-line arguments.
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
        BaseModel (pydantic): For creating Pydantic base models.

    Project-specific imports:
        SnapshotReport, ReadinessCheckReport (pan_os_upgrade.models): For handling snapshot and readiness check reports.
"""
# standard library imports
import argparse
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional, Tuple, Union

# trunk-ignore(bandit/B405)
import xml.etree.ElementTree as ET

# Palo Alto Networks PAN-OS imports
import panos
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

# Palo Alto Networks panos-upgrade-assurance imports
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy

# third party imports
import xmltodict
from pydantic import BaseModel

# project imports
from pan_os_upgrade.models import SnapshotReport, ReadinessCheckReport


# ----------------------------------------------------------------------------
# Define logging levels
# ----------------------------------------------------------------------------
# A dictionary mapping string representations of logging levels to their
# corresponding numeric values in the logging module.
#
# This dictionary is used to configure the logging level of the application
# based on user input or configuration settings. Each key is a string that
# represents a logging level, and the corresponding value is the numeric
# level from the logging module.
#
# Keys:
#     debug (str): Corresponds to logging.DEBUG, for detailed diagnostic information.
#     info (str): Corresponds to logging.INFO, for general informational messages.
#     warning (str): Corresponds to logging.WARNING, for warning messages about potential issues.
#     error (str): Corresponds to logging.ERROR, for error messages indicating a problem.
#     critical (str): Corresponds to logging.CRITICAL, for critical issues that may prevent program execution.
#
# Example:
#     To set the logging level to 'debug':
#     logger.setLevel(LOGGING_LEVELS['debug'])
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
# Define models
# ----------------------------------------------------------------------------
class Args(BaseModel):
    """
    Represents the command-line arguments for connecting and configuring a Firewall appliance.

    This class, utilizing Pydantic for data validation, ensures that the provided arguments meet
    the expected data types and formats. It serves as a structured way to define and access
    configuration settings and command-line options required for the operation of the upgrade script.

    Attributes
    ----------
    api_key : Optional[str]
        The API key used for authenticating with the Firewall appliance. If not provided,
        defaults to None. This field is optional and mutually exclusive with username/password authentication.

    dry_run : bool
        Indicates whether the script should perform a dry run without making actual changes.
        Defaults to False. Useful for testing and validation purposes.

    hostname : Optional[str]
        The hostname or IP address of the Firewall appliance. Required for establishing a connection.
        If not provided, defaults to None.

    log_level : str
        The logging level for the script's output. Valid options are 'debug', 'info', 'warning',
        'error', and 'critical'. Defaults to 'info'. This controls the verbosity of the script's logging.

    password : Optional[str]
        The password for authentication with the Firewall appliance. Required if using username/password
        authentication. Defaults to None.

    target_version : Optional[str]
        The target PAN-OS version for the upgrade. Specifies the version to which the appliance should be upgraded.
        If not provided, defaults to None.

    username : Optional[str]
        The username for authentication with the Firewall appliance. Required if using username/password
        authentication. Defaults to None.

    Example
    -------
    Creating an instance of Args with command-line parameters:
        >>> args = Args(api_key="yourapikey", hostname="192.168.1.1", target_version="10.0.1")
        >>> print(args.hostname)
        192.168.1.1
    """

    api_key: Optional[str] = None
    dry_run: bool = False
    hostname: Optional[str] = None
    log_level: str = "info"
    password: Optional[str] = None
    target_version: Optional[str] = None
    username: Optional[str] = None


# ----------------------------------------------------------------------------
# Setting up environment variables based on the .env file or CLI arguments
# ----------------------------------------------------------------------------
def load_environment_variables(file_path: str) -> None:
    """
    Load key-value pairs as environment variables from a specified file.

    This function processes a file line by line, setting each key-value pair as an environment variable.
    It ignores lines that start with a '#' as they are considered comments. The function is useful for
    initializing environment variables from a configuration file, typically named '.env'. This allows for
    dynamic configuration of the script based on external settings.

    Parameters
    ----------
    file_path : str
        The path to the file containing the environment variables. Each non-comment line in the file
        should be in the format 'KEY=VALUE'. Comment lines should start with '#'.

    Raises
    ------
    FileNotFoundError
        If the file specified by 'file_path' does not exist, a FileNotFoundError is raised.

    Examples
    --------
    Assuming a '.env' file with the following contents:
        # Example .env file
        PAN_USERNAME=admin
        PAN_PASSWORD=password123
        API_KEY=
        HOSTNAME=panorama.example.com
        TARGET_VERSION=10.1.1
        LOG_LEVEL=debug
        DRY_RUN=True

    Using the function to load these environment variables:
        >>> load_environment_variables('.env')
        # Environment variables are now set based on the contents of '.env'.
    """
    if os.path.exists(file_path):
        with open(file_path) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                key, value = line.strip().split("=", 1)
                os.environ[key] = value


# ----------------------------------------------------------------------------
# Handling CLI arguments
# ----------------------------------------------------------------------------
def parse_arguments() -> Args:
    """
    Parses command-line arguments for configuring the Firewall appliance interaction.

    This function sets up an argument parser to define and process command-line arguments necessary for the script's
    operation. It handles authentication details (like hostname, username, password, API key), operational flags (such as dry-run),
    and logging level. If required arguments are not provided via the command line, the function attempts to load them from a `.env` file.

    The function ensures mutual exclusivity between using an API key and a username/password combination for authentication.
    If crucial arguments like hostname or target version are missing, or if the authentication information is incomplete,
    the script logs an error and exits.

    Returns
    -------
    Args
        An instance of the Args class, populated with the parsed arguments and environment variables. It contains
        fields such as api_key, hostname, log_level, username, target_version, and password.

    Raises
    ------
    SystemExit
        - If essential arguments like hostname or target version are not provided either via CLI or in the .env file.
        - If neither an API key nor both username and password are provided for authentication.

    Example
    -------
    Command-line usage example:
        $ python upgrade.py --hostname 192.168.0.1 --username admin --password secret --version 10.0.0

    This would parse the arguments and return an Args instance with the specified values.
    """
    # Load environment variables first
    load_environment_variables(".env")

    parser = argparse.ArgumentParser(
        description="This script interacts with a Firewall appliance to perform readiness checks, "
        "snapshots, and configuration backups in before and after its upgrade. If arguments are not "
        "provided, the script will attempt to load them from a .env file.",
        epilog="For more information, visit https://cdot65.github.io/pan-os-upgrade.",
    )

    # Grouping authentication arguments
    auth_group = parser.add_argument_group("Authentication")
    auth_group.add_argument(
        "--hostname",
        dest="hostname",
        type=str,
        default=None,
        help="Hostname of the PAN-OS appliance",
    )
    auth_group.add_argument(
        "--api-key",
        dest="api_key",
        type=str,
        default=None,
        help="API Key for authentication with the Firewall appliance.",
    )
    auth_group.add_argument(
        "--username",
        dest="username",
        type=str,
        help="Username for authentication with the Firewall appliance.",
    )
    auth_group.add_argument(
        "--password",
        dest="password",
        type=str,
        help="Password for authentication.",
    )

    # Other arguments
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=os.getenv("DRY_RUN", "False").lower() == "true",
        help="Perform a dry run of all tests and downloads without performing the actual upgrade.",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=LOGGING_LEVELS.keys(),
        default=os.getenv("LOG_LEVEL", "info"),
        help="Set the logging output level",
    )
    parser.add_argument(
        "--version",
        dest="target_version",
        type=str,
        default=None,
        help="Target PAN-OS version to upgrade to",
    )

    args = parser.parse_args()

    # Load environment variables if necessary arguments are not provided
    if not all([args.api_key, args.hostname, args.username, args.password]):
        load_environment_variables(".env")

    # Create a new structure to store arguments with different variable names
    arguments = {
        "api_key": args.api_key or os.getenv("API_KEY"),
        "dry_run": args.dry_run or os.getenv("DRY_RUN"),
        "hostname": args.hostname or os.getenv("HOSTNAME"),
        "pan_username": args.username or os.getenv("PAN_USERNAME"),
        "pan_password": args.password or os.getenv("PAN_PASSWORD"),
        "target_version": args.target_version or os.getenv("TARGET_VERSION"),
        "log_level": args.log_level or os.getenv("LOG_LEVEL") or "info",
    }

    # Check for missing hostname
    if not arguments["hostname"]:
        logging.error(
            f"{get_emoji('error')} Hostname must be provided as a --hostname argument or in .env",
        )

        sys.exit(1)

    # Check for missing target version
    if not arguments["target_version"]:
        logging.error(
            f"{get_emoji('error')} Target version must be provided as a --version argument or in .env",
        )
        logging.error(f"{get_emoji('stop')} Halting script.")

        sys.exit(1)

    # Ensuring mutual exclusivity
    if arguments["api_key"]:
        arguments["pan_username"] = arguments["pan_password"] = None
    elif not (arguments["pan_username"] and arguments["pan_password"]):
        logging.error(
            f"{get_emoji('error')} Provide either API key --api-key argument or both --username and --password",
        )
        logging.error(f"{get_emoji('stop')} Halting script.")

        sys.exit(1)

    return arguments


# ----------------------------------------------------------------------------
# Setting up logging
# ----------------------------------------------------------------------------
def configure_logging(level: str) -> None:
    """
    Configures the logging system for the script with a specified logging level.

    This function sets up the global logging configuration for the script. It initializes a logger,
    sets the logging level based on the input, and adds two handlers: one for console output and
    another for file output. File logging uses a RotatingFileHandler to manage log file size and backups.

    Parameters
    ----------
    level : str
        The logging level to be set for the logger. Valid options are 'debug', 'info', 'warning',
        'error', and 'critical', as defined in the LOGGING_LEVELS dictionary. The function handles the
        input case-insensitively and defaults to 'info' if an invalid level is provided.

    Notes
    -----
    - Console Handler: Logs messages to the standard output.
    - File Handler: Logs messages to 'logs/upgrade.log'. The log file is rotated when it reaches 1MB,
      with up to three backup files being kept.
    """
    logging_level = getattr(logging, level.upper(), None)

    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging_level)

    # Create handlers (console and file handler)
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        "logs/upgrade.log",
        maxBytes=1024 * 1024,
        backupCount=3,
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
        console_format = logging.Formatter(
            "%(levelname)s - %(message)s",
        )
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
    Retrieves the emoji character associated with a given action keyword.

    This function maps a specified action keyword to its corresponding emoji character. The mapping
    is defined in a predefined dictionary, 'emoji_map'. If the specified action is not recognized,
    the function returns an empty string.

    Parameters
    ----------
    action : str
        The action keyword for which the emoji is desired. Supported actions include 'success',
        'warning', 'error', 'working', 'report', 'search', 'save', 'stop', and 'start'.

    Returns
    -------
    str
        The emoji character corresponding to the given action. Returns an empty string if the
        action is not recognized in the emoji_map.

    Examples
    --------
    >>> get_emoji('success')
    '✅'

    >>> get_emoji('error')
    '❌'

    >>> get_emoji('start')
    '🚀'
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
# Helper function to flip XML objects into Python dictionaries
# ----------------------------------------------------------------------------
def xml_to_dict(xml_object: ET.Element) -> dict:
    """
    Converts an XML object to a Python dictionary for easy manipulation and access.

    This function uses the 'xmltodict' library to convert an XML object into a Python dictionary.
    The conversion preserves the XML tree structure, representing elements as keys and their contents
    as values in the dictionary. This utility is especially useful for processing and handling XML data
    in Python, facilitating access to XML elements and attributes in a Pythonic manner.

    Parameters
    ----------
    xml_object : ET.Element
        The XML object to be converted. It should be an instance of ElementTree.Element, typically obtained
        from parsing XML data using the ElementTree API.

    Returns
    -------
    dict
        A dictionary representation of the provided XML object. The dictionary's structure mirrors the XML's
        structure, with tags as keys and their textual content as values.

    Example
    -------
    Converting an XML object to a dictionary:
        >>> xml_data = ET.Element('root', attrib={'id': '1'})
        >>> sub_element = ET.SubElement(xml_data, 'child')
        >>> sub_element.text = 'content'
        >>> xml_dict = xml_to_dict(xml_data)
        >>> print(xml_dict)
        {'root': {'@id': '1', 'child': 'content'}}
    """
    xml_string = ET.tostring(xml_object)
    xml_dict = xmltodict.parse(xml_string)
    return xml_dict


# ----------------------------------------------------------------------------
# Helper function to ensure the directories exist for our snapshots
# ----------------------------------------------------------------------------
def ensure_directory_exists(file_path: str):
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
):
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
# Setting up connection to the Firewall appliance
# ----------------------------------------------------------------------------
def connect_to_firewall(args: dict) -> Firewall:
    """
    Establishes a connection to a Firewall appliance using provided credentials.

    This function attempts to connect to a Firewall appliance, which can be authenticated either using an
    API key or a combination of a username and password. It ensures that the target device is indeed a
    Firewall and not a Panorama appliance. On successful connection, it returns a Firewall object. If the
    connection fails or if the target device is a Panorama appliance, the script logs an error and terminates.

    Parameters
    ----------
    args : dict
        A dictionary of arguments required for establishing the connection. Expected keys are:
        - 'api_key': The API key for authentication (optional if username and password are provided).
        - 'hostname': The hostname or IP address of the Firewall appliance.
        - 'pan_username': Username for authentication (required if API key is not provided).
        - 'pan_password': Password for authentication (required if API key is not provided).

    Returns
    -------
    Firewall
        An instance of the Firewall class representing the established connection to the Firewall appliance.

    Raises
    ------
    SystemExit
        - If the target device is a Panorama appliance.
        - If the connection to the Firewall appliance fails (e.g., due to timeout or incorrect credentials).

    Examples
    --------
    Connecting to a Firewall using an API key:
        >>> connect_to_firewall({'api_key': 'apikey123', 'hostname': '192.168.0.1'})
        <Firewall object>

    Connecting to a Firewall using username and password:
        >>> connect_to_firewall({'pan_username': 'admin', 'pan_password': 'password', 'hostname': '192.168.0.1'})
        <Firewall object>
    """
    try:
        # Build a connection using either an API key or username/password combination
        if args["api_key"]:
            target_device = PanDevice.create_from_device(
                args["hostname"],
                api_key=args["api_key"],
            )
        else:
            target_device = PanDevice.create_from_device(
                args["hostname"],
                args["pan_username"],
                args["pan_password"],
            )

        if isinstance(target_device, panos.panorama.Panorama):
            logging.error(
                f"{get_emoji('error')} You are targeting a Panorama appliance, please target a firewall."
            )

            sys.exit(1)

        return target_device

    except PanConnectionTimeout:
        logging.error(
            f"{get_emoji('error')} Connection to the firewall timed out. Please check the hostname and network connectivity."
        )

        sys.exit(1)

    except Exception as e:
        logging.error(
            f"{get_emoji('error')} An error occurred while connecting to the firewall: {e}"
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
    Determines if an upgrade to a specified PAN-OS version is necessary.

    This function compares the current PAN-OS version of the firewall against a target version
    specified by the major, minor, and maintenance/hotfix levels. It logs both the current and
    target versions, then assesses whether an upgrade is required. The function concludes that an
    upgrade is needed if the current version is lower than the target version. Conversely, if the
    current version is equal to or higher than the target version, it indicates that no upgrade is
    necessary or that a downgrade attempt has been made.

    Parameters
    ----------
    firewall : Firewall
        The Firewall instance whose PAN-OS version is to be compared.
    target_major : int
        The major version number of the target PAN-OS.
    target_minor : int
        The minor version number of the target PAN-OS.
    target_maintenance : Union[int, str]
        The maintenance version number of the target PAN-OS. Can be an integer or a string
        (including hotfix information).

    Raises
    ------
    SystemExit
        If the current PAN-OS version is equal to or higher than the target version, suggesting
        that no upgrade is needed or that a downgrade was attempted.

    Notes
    -----
    - The function uses a nested `parse_version` function to convert version strings to a tuple of
      integers for comparison.
    - The logging includes emojis for better visual distinction of the messages.
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
    target_version: str,
    ha_details: dict,
) -> bool:
    """
    Checks if the specified PAN-OS version is available and ready for download on the firewall.

    This function retrieves the current PAN-OS version of the firewall and lists available versions
    for upgrade. It compares these with the target version. If the target version is available and
    its base image is already downloaded on the firewall, the function logs this information and
    returns True. If the target version is not available or its base image is not downloaded, an
    error is logged, and the function returns False. The function also verifies that the target
    version is a newer version compared to the current one on the firewall.

    Parameters
    ----------
    firewall : Firewall
        The Firewall object representing the firewall to be checked.
    target_version : str
        The desired target PAN-OS version for the upgrade.
    ha_details : dict
        High-availability details of the firewall, used to determine if HA synchronization is required.

    Returns
    -------
    bool
        True if the target version is available and its base image is downloaded, False otherwise.

    Raises
    ------
    SystemExit
        If the target version is older than or equal to the current version, indicating no upgrade is
        needed or a downgrade was attempted.

    Example
    --------
    Checking if a specific PAN-OS version is available for download:
        >>> firewall = Firewall(hostname='192.168.0.1', api_key='apikey')
        >>> software_update_check(firewall, '10.1.0', ha_details={})
        True or False depending on the availability of the version
    """
    # parse target version
    target_major, target_minor, target_maintenance = target_version.split(".")

    # check to see if the target version is older than the current version
    determine_upgrade(firewall, target_major, target_minor, target_maintenance)

    # retrieve available versions of PAN-OS
    firewall.software.check()
    available_versions = firewall.software.versions
    logging.debug(f"Available PAN-OS versions: {available_versions}")

    # check to see if target version is available for upgrade
    if target_version in available_versions:
        logging.info(
            f"{get_emoji('success')} Target PAN-OS version {target_version} is available for download"
        )

        # validate the target version's base image is already downloaded
        if available_versions[f"{target_major}.{target_minor}.0"]["downloaded"]:
            logging.info(
                f"{get_emoji('success')} Base image for {target_version} is already downloaded"
            )
            return True

        else:
            logging.error(
                f"{get_emoji('error')} Base image for {target_version} is not downloaded"
            )
            return False
    else:
        logging.error(
            f"{get_emoji('error')} Target PAN-OS version {target_version} is not available for download"
        )
        return False


# ----------------------------------------------------------------------------
# Determine if the firewall is standalone, HA, or in a cluster
# ----------------------------------------------------------------------------
def get_ha_status(firewall: Firewall) -> Tuple[str, Optional[dict]]:
    """
    Determines the High-Availability (HA) status and configuration of a Firewall appliance.

    This function checks and logs the HA deployment status of the specified Firewall. It identifies
    whether the Firewall is in a standalone setup, part of an HA pair, or in a cluster configuration.
    Additional details about the HA configuration are also retrieved and logged if available.

    Parameters
    ----------
    firewall : Firewall
        The Firewall instance whose HA status is to be determined.

    Returns
    -------
    Tuple[str, Optional[dict]]
        A tuple containing:
        1. A string indicating the HA deployment type (e.g., 'standalone', 'active/passive', 'active/active').
        2. A dictionary with detailed HA configuration information, if available; otherwise, None.

    Example
    -------
    Retrieving HA status of a Firewall:
        >>> fw = Firewall(hostname='192.168.1.1', api_key='apikey')
        >>> ha_status, ha_details = get_ha_status(fw)
        >>> print(ha_status)
        'active/passive'
        >>> print(ha_details)
        {'ha_details': {...}}

    Notes
    -----
    - The function utilizes the 'show_highavailability_state' method of the Firewall class to fetch HA details.
    - The 'xml_to_dict' helper function is used to convert XML data into a more accessible dictionary format.
    """
    logging.debug(
        f"{get_emoji('start')} Getting {firewall.serial} deployment information..."
    )
    deployment_type = firewall.show_highavailability_state()
    logging.debug(f"{get_emoji('report')} Firewall deployment: {deployment_type[0]}")

    if deployment_type[1]:
        ha_details = xml_to_dict(deployment_type[1])
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
        >>> firewall = Firewall(hostname='192.168.0.1', api_key='apikey')
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
        The hostname of the firewall.
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
        >>> firewall = Firewall(hostname='192.168.1.1', api_key='apikey')
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
        >>> firewall = Firewall(hostname='192.168.1.1', api_key='apikey')
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
        >>> firewall = Firewall(hostname='192.168.1.1', api_key='apikey')
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
        >>> firewall = Firewall(hostname='192.168.1.1', api_key='apikey')
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
    max_retries: int = 3,  # Maximum number of retry attempts
    retry_interval: int = 60,  # Time to wait between retries (in seconds)
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
        >>> firewall = Firewall(hostname='192.168.1.1', api_key='apikey')
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
def perform_reboot(firewall: Firewall, ha_details: Optional[dict] = None) -> None:
    """
    Initiates and manages the reboot process for a specified firewall appliance.

    This function triggers a reboot of the firewall and monitors its status until it comes back online.
    If the firewall is part of an HA (High Availability) setup, it ensures synchronization with the HA peer
    post-reboot. The process includes robust handling of various states and potential errors during reboot,
    with detailed logging at each step.

    Parameters
    ----------
    firewall : Firewall
        The firewall instance to be rebooted.
    ha_details : Optional[dict], optional
        High Availability details for the firewall, if applicable, by default None.

    Raises
    ------
    SystemExit
        Exits the script if the reboot process encounters critical errors or timeouts.

    Notes
    -----
    - The function repeatedly checks the firewall's status and HA synchronization (if applicable) post-reboot.
    - Reboot completion is confirmed when the firewall is online and, in HA setups, synchronized with its peer.
    - The script terminates if the firewall doesn't come online or synchronize within 20 minutes.

    Example
    -------
    Rebooting a firewall and ensuring its operational status:
        >>> firewall = Firewall(hostname='192.168.1.1', api_key='apikey')
        >>> perform_reboot(firewall)
        # The firewall undergoes a reboot and the script monitors until it's back online.
    """

    reboot_start_time = time.time()
    rebooted = False

    logging.info(f"{get_emoji('start')} Rebooting the firewall...")
    reboot_job = firewall.op(
        "<request><restart><system/></restart></request>", cmd_xml=False
    )
    reboot_job_result = xml_to_dict(reboot_job)
    logging.info(f"{get_emoji('report')} {reboot_job_result['response']['result']}")

    while not rebooted:
        try:
            deploy_info, current_ha_details = get_ha_status(firewall)
            if current_ha_details and deploy_info in ["active", "passive"]:
                if (
                    current_ha_details["response"]["result"]["group"]["running-sync"]
                    == "synchronized"
                ):
                    logging.info(
                        f"{get_emoji('success')} Firewall rebooted and synchronized with its HA peer in {int(time.time() - reboot_start_time)} seconds"
                    )
                    rebooted = True
                else:
                    logging.info(
                        f"{get_emoji('working')} Firewall rebooted but not yet synchronized with its peer. Will try again in 30 seconds."
                    )
                    time.sleep(30)
            elif current_ha_details and deploy_info == "disabled":
                logging.info(
                    f"{get_emoji('success')} Firewall rebooted in {int(time.time() - reboot_start_time)} seconds"
                )
                rebooted = True
            else:
                logging.info(
                    f"{get_emoji('working')} Firewall is responding to requests but hasn't finished its reboot process..."
                )
                time.sleep(30)

        except (PanXapiError, PanConnectionTimeout, PanURLError):
            logging.info(f"{get_emoji('working')} Firewall is rebooting...")
            time.sleep(30)

        # Check if 20 minutes have passed
        if time.time() - reboot_start_time > 1200:  # 20 minutes in seconds
            logging.error(
                f"{get_emoji('error')} Firewall did not become available and/or establish a Connected sync state with its HA peer after 20 minutes. Please check the firewall status manually."
            )
            break


# ----------------------------------------------------------------------------
# Primary execution of the script
# ----------------------------------------------------------------------------
def main() -> None:
    """
    Main entry point for executing the firewall upgrade script.

    This function orchestrates the entire process of upgrading a PAN-OS firewall. It includes various stages,
    such as parsing command-line arguments, establishing a connection with the firewall, assessing readiness
    for upgrade, and executing the upgrade process. The function is designed to handle both dry run and actual
    upgrade scenarios, providing comprehensive logging throughout.

    Steps:
    1. Create necessary directories for logs and snapshots.
    2. Configure logging based on user-defined log level.
    3. Establish a connection to the firewall and refresh its system info.
    4. Determine firewall's deployment status and readiness for upgrade.
    5. Download required PAN-OS version if not present.
    6. Perform pre-upgrade snapshots and readiness checks.
    7. Back up current firewall configuration.
    8. Proceed with upgrade and reboot if not a dry run.

    Exits the script in cases such as:
    - Firewall not ready for the intended upgrade.
    - Critical issues that prevent script continuation.
    - Successful completion of a dry run.
    - HA peer state is not synchronized (for HA setups).

    Example Usage:
    ```bash
    python upgrade.py --hostname 192.168.1.1 --username admin --password secret --version 10.2.7
    ```
    This command will start the upgrade process for the firewall at '192.168.1.1' to version '10.2.7'.
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
    args = parse_arguments()
    configure_logging(args["log_level"])

    # Create our connection to the firewall
    logging.debug(f"{get_emoji('start')} Connecting to PAN-OS firewall...")
    firewall = connect_to_firewall(args)
    logging.info(f"{get_emoji('success')} Connection to firewall established")

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
    update_available = software_update_check(
        firewall, args["target_version"], ha_details
    )
    logging.debug(f"{get_emoji('report')} Firewall readiness check complete")

    # gracefully exit if the firewall is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"{get_emoji('error')} Firewall is not ready for upgrade to {args['target_version']}.",
        )

        sys.exit(1)

    # Download the target PAN-OS version
    logging.info(
        f"{get_emoji('start')} Performing test to see if {args['target_version']} is already downloaded..."
    )
    image_downloaded = software_download(firewall, args["target_version"], ha_details)
    if deploy_info == "active" or deploy_info == "passive":
        logging.info(
            f"{get_emoji('success')} {args['target_version']} has been downloaded and sync'd to HA peer."
        )
    else:
        logging.info(
            f"{get_emoji('success')} PAN-OS version {args['target_version']} has been downloaded."
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
        if ha_details["response"]["result"]["group"]["running-sync"] == "synchronized":
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
    if args["dry_run"] is True:
        logging.info(f"{get_emoji('success')} Dry run complete, exiting...")
        logging.info(f"{get_emoji('stop')} Halting script.")
        sys.exit(0)
    else:
        logging.info(f"{get_emoji('start')} Not a dry run, continue with upgrade...")

    # Perform the upgrade
    perform_upgrade(
        firewall=firewall,
        hostname=firewall_details.hostname,
        target_version=args["target_version"],
        ha_details=ha_details,
    )

    # Perform the reboot
    perform_reboot(firewall=firewall, ha_details=ha_details)


if __name__ == "__main__":
    main()
