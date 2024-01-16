# standard library imports
import argparse
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Tuple, Union

# Palo Alto Networks PAN-OS imports
import panos
from panos.base import PanDevice
from panos.device import SystemSettings
from panos.errors import PanDeviceXapiError
from panos.firewall import Firewall

# Palo Alto Networks panos-upgrade-assurance imports
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy

# third party imports
import defusedxml.ElementTree as ET
import xmltodict
from pydantic import BaseModel

# project imports
from models import AssuranceReport


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
    Configuration options for the panos-upgrade-assurance process.

    This class encapsulates various configurations used in the upgrade assurance process for PAN-OS appliances.
    It includes definitions for readiness checks, state snapshots, and reports, which are crucial in the upgrade
    process of PAN-OS appliances.

    Attributes
    ----------
    READINESS_CHECKS : list of str
        A list of readiness checks to be performed on the PAN-OS appliance. These checks assess system and
        network parameters like active support status, ARP entry existence, candidate configuration, etc.

    STATE_SNAPSHOTS : list of str
        A list of state snapshot types to capture from the PAN-OS appliance. These snapshots record critical
        data regarding the appliance's current state, such as ARP table, content version, IPsec tunnels, etc.

    REPORTS : list of str
        A list of report types that can be generated for the PAN-OS appliance. These reports provide detailed
        information on various aspects of the appliance, including ARP table, content version, IPsec tunnels,
        license details, and more.

    READINESS_CHECK_DESCRIPTIONS : dict
        A dictionary mapping each readiness check to its description, log level, and whether to exit on failure.
        This provides a more detailed context for each check, allowing for tailored logging and error handling.
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

    READINESS_CHECK_DESCRIPTIONS = {
        "candidate_config": {
            "description": "No Pending Configuration Changes",
            "log_level": "error",
            "exit_on_failure": True,
        },
        "content_version": {
            "description": "Running Latest Content Version",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "expired_licenses": {
            "description": "No Expired Licenses",
            "log_level": "warning",
            "exit_on_failure": False,
        },
        "ha": {
            "description": "HA Status",
            "log_level": "info",
            "exit_on_failure": False,
        },
    }


# ----------------------------------------------------------------------------
# Define models
# ----------------------------------------------------------------------------
class Args(BaseModel):
    """
    A model representing the arguments needed for connecting to and
    configuring the Firewall appliance.

    This class uses Pydantic (or similar) for data validation, ensuring that
    the provided data types and formats meet the expected criteria for each
    field.

    Attributes
    ----------
    api_key : str, optional
        API key for authentication with the Firewall appliance.
        Default is None.
    hostname : str, optional
        Hostname or IP address of the Firewall appliance.
        Default is None.
    log_level : str, optional
        The logging level for the script.
        Accepted values are 'debug', 'info', 'warning', 'error', and 'critical'
        Default is 'info'.
    password : str, optional
        Password for authentication with the Firewall appliance.
        Default is None.
    target_version : str, optional
        The target PAN-OS version to upgrade to.
        Default is None.
    username : str, optional
        Username for authentication with the Firewall appliance.
        Default is None.
    """

    api_key: str = None
    hostname: str = None
    log_level: str = "info"
    password: str = None
    target_version: str = None
    username: str = None


# ----------------------------------------------------------------------------
# Setting up environment variables based on the .env file or CLI arguments
# ----------------------------------------------------------------------------
def load_environment_variables(file_path: str) -> None:
    """
    Load environment variables from a given file.

    Reads a file line by line, checking for non-commented and non-empty lines. Each line is split into a key-value pair
    and set as an environment variable. Lines beginning with '#' are treated as comments and ignored.

    Parameters
    ----------
    file_path : str
        The file path of the environment variables file. The file should contain key-value pairs in the format KEY=VALUE.
        Lines starting with '#' are treated as comments and are ignored.

    Raises
    ------
    FileNotFoundError
        If the file at the given file_path does not exist, this error is raised.

    Example
    -------
    Given a file named '.env' with the following content:
    ```
    # PAN-OS credentials if using an API key, leave user and password blank
    PAN_USERNAME=admin
    PAN_PASSWORD=password123
    API_KEY=
    HOSTNAME=panorama.example.com
    TARGET_VERSION=
    LOG_LEVEL=debug
    ```
    Calling `load_environment_variables('.env')` will set the environment variables
    PAN_USERNAME, PAN_PASSWORD, API_KEY, HOSTNAME, TARGET_VERSION, and LOG_LEVEL.
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
    Parse command-line arguments for interacting with a Firewall appliance.

    Sets up an argument parser for the script, defining command-line arguments for configuration.
    Supports log level, hostname, username, password, API key, and target PAN-OS version.
    If necessary arguments are not provided, attempts to load them from a `.env` file.

    Ensures mutual exclusivity between API key and username/password combinations. If neither
    CLI arguments nor .env file configurations provide the necessary information, the script
    exits and displays an error.

    Returns
    -------
    Args
        An instance of the Args model class populated with the parsed arguments or environment
        variables. Contains fields for API key, hostname, log level, username, target version, and password.

    Raises
    ------
    SystemExit
        If the hostname or target version is not provided either as CLI arguments or in the .env file,
        or if neither the API key nor both username and password are provided.
    """
    parser = argparse.ArgumentParser(
        description="Script to interact with Firewall appliance."
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        type=str,
        default=None,
        help="API Key for authentication",
    )
    parser.add_argument(
        "--hostname",
        dest="hostname",
        type=str,
        default=None,
        help="Hostname of the PAN-OS appliance",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=LOGGING_LEVELS.keys(),
        default="info",
        help="Set the logging output level",
    )
    parser.add_argument(
        "--password",
        dest="password",
        type=str,
        default=None,
        help="Password for authentication",
    )
    parser.add_argument(
        "--username",
        dest="username",
        type=str,
        default=None,
        help="Username for authentication",
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
        "hostname": args.hostname or os.getenv("HOSTNAME"),
        "pan_username": args.username or os.getenv("PAN_USERNAME"),
        "pan_password": args.password or os.getenv("PAN_PASSWORD"),
        "target_version": args.target_version or os.getenv("TARGET_VERSION"),
        "log_level": args.log_level or os.getenv("LOG_LEVEL"),
    }

    # Check for missing hostname
    if not arguments["hostname"]:
        logging.error(
            "Error: Hostname must be provided as a --hostname argument or in .env",
        )
        sys.exit(1)

    # Check for missing target version
    if not arguments["target_version"]:
        logging.error(
            "Error: Target version must be provided as a --version argument or in .env",
        )
        sys.exit(1)

    # Ensuring mutual exclusivity
    if arguments["api_key"]:
        arguments["pan_username"] = arguments["pan_password"] = None
    elif not (arguments["pan_username"] and arguments["pan_password"]):
        logging.error(
            "Error: Provide either API key --api-key argument or both --username and --password",
            file=sys.stderr,
        )
        sys.exit(1)

    return arguments


# ----------------------------------------------------------------------------
# Setting up logging
# ----------------------------------------------------------------------------
def configure_logging(level: str) -> None:
    """
    Configure the logging for the script.

    Sets up logging with a specified level. It initializes a logger, sets its level based on the input,
    and adds two handlers: one for console output and another for file output. The file output is managed
    with a RotatingFileHandler, which keeps up to three backups and a maximum file size of 1MB each.

    Parameters
    ----------
    level : str
        A string representing the desired logging level. Valid values are defined in the LOGGING_LEVELS
        dictionary and include 'debug', 'info', 'warning', 'error', and 'critical'. The input is
        case-insensitive. If an invalid level is provided, it defaults to 'info'.

    Notes
    -----
    The logging configuration includes:
    - A console handler that logs messages to the standard output.
    - A file handler that logs messages to 'logs/upgrade.log', with log rotation.
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
    console_format = logging.Formatter(
        "%(name)s - %(levelname)s - %(message)s",
    )
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


# ----------------------------------------------------------------------------
# Helper function to flip XML objects into Python dictionaries
# ----------------------------------------------------------------------------
def xml_to_dict(xml_object) -> dict:
    """
    Convert an XML object into a Python dictionary.

    This function takes an XML object, typically obtained from parsing XML data, and converts it into a Python dictionary
    for easier access and manipulation. The conversion is done using the xmltodict library, which transforms the XML tree
    structure into a dictionary format, maintaining elements as keys and their contents as values. This is particularly useful
    for processing and interacting with XML data in a more Pythonic way.

    Parameters
    ----------
    xml_object : ET.Element
        An XML object to convert into a Python dictionary. This is typically an ElementTree Element.

    Returns
    -------
    dict
        A Python dictionary representation of the XML object. The structure of the dictionary corresponds to the structure
        of the XML, with tags as keys and their contents as values.
    """
    xml_string = ET.tostring(xml_object)
    xml_dict = xmltodict.parse(xml_string)
    return xml_dict


# ----------------------------------------------------------------------------
# Helper function to ensure the directories exist for our snapshots
# ----------------------------------------------------------------------------
def ensure_directory_exists(file_path: str):
    """
    Ensure that the directory for the given file path exists.

    Creates the directory (and any necessary parent directories) if it does not already exist.

    Parameters
    ----------
    file_path : str
        The file path for which to ensure the directory exists.
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
    test_result = result.get(
        test_name, {"state": False, "reason": "Test not performed"}
    )
    log_message = f'{test_info["description"]} - {test_result["reason"]}'

    if test_result["state"]:
        logging.info(f"Passed Readiness Check: {test_info['description']}")
    else:
        if test_info["log_level"] == "error":
            logging.error(f"{log_message}")
            if test_info["exit_on_failure"]:
                sys.exit(1)
        elif test_info["log_level"] == "warning":
            logging.warning(f"{log_message}")
        else:
            logging.info(log_message)


# ----------------------------------------------------------------------------
# Setting up connection to the Firewall appliance
# ----------------------------------------------------------------------------
def connect_to_firewall(args: dict) -> Firewall:
    """
    Establish a connection to the Firewall appliance.

    Connects to a Firewall appliance using credentials provided in 'args'. The connection
    can be established either using an API key or a combination of username and password.
    This function ensures the target device is a Firewall and not a Panorama appliance.

    If the connection is successful, it returns an instance of the Firewall class. If the
    target device is a Panorama appliance or if the connection fails, the script logs an
    error message and exits.

    Parameters
    ----------
    args : dict
        A dictionary containing the arguments for connecting to the Firewall appliance.
        Keys should include 'api_key', 'hostname', 'pan_username', and 'pan_password'.

    Returns
    -------
    Firewall
        An instance of the Firewall class representing the connection to the Firewall appliance.

    Raises
    ------
    SystemExit
        If the target device is a Panorama appliance or if the required credentials are not provided.
    """
    # Conditional connection logic
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
            "You are targeting a Panorama appliance, please target a firewall."
        )
        sys.exit(1)

    return target_device


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
    Determine if an upgrade is needed based on the target and current PAN-OS versions.

    Compares the major, minor, maintenance, and hotfix versions of the current PAN-OS on the firewall
    with the specified target version. Logs the current and target versions and decides if an upgrade
    is required. If the current version is lower than the target version, it logs that an upgrade is
    required. If the current version is equal to or higher than the target version, it logs that no
    upgrade is needed or a downgrade was attempted.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the firewall to be checked.
    target_major : int
        The major version of the target PAN-OS.
    target_minor : int
        The minor version of the target PAN-OS.
    target_maintenance : Union[int, str]
        The maintenance (and optionally hotfix) version of the target PAN-OS. Can be an integer or a
        string (to include hotfix information).

    Raises
    ------
    SystemExit
        If the current version is equal to or higher than the target version, indicating no upgrade
        is needed or a downgrade was attempted.
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

    logging.info(f"Current PAN-OS version: {firewall.version}")
    logging.info(
        f"Target PAN-OS version: {target_major}.{target_minor}.{target_maintenance}"
    )

    upgrade_needed = current_version < target_version
    if upgrade_needed:
        logging.info(
            f"Confirmed that moving from {firewall.version} to {target_major}.{target_minor}.{target_maintenance} is an upgrade"
        )
        return

    else:
        logging.error("Upgrade is not required or a downgrade was attempted.")
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
    Check if a specific PAN-OS software version is available for the firewall.

    Retrieves the current PAN-OS version of the firewall and available versions for upgrade.
    Logs the current version and available versions. If the target version is available and
    its base image is already downloaded, it logs this information and returns True. If the
    target version is not available or its base image is not downloaded, it logs an error and
    returns False. Additionally, it checks if the target version is newer than the current version.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the firewall to check.
    target_version : str
        The target PAN-OS version to check availability for.
    ha_details : dict
        A dictionary containing high-availability details of the firewall.

    Returns
    -------
    bool
        True if the target version is available for upgrade and its base image is downloaded.
        False if the target version is not available or its base image is not downloaded.

    Raises
    ------
    SystemExit
        If the target version is older than or equal to the current version, indicating no
        upgrade is needed or a downgrade was attempted.
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
            f"Target PAN-OS version {target_version} is available for download"
        )

        # validate the target version's base image is already downloaded
        if available_versions[f"{target_major}.{target_minor}.0"]["downloaded"]:
            logging.info(f"Base image for {target_version} is already downloaded")
            return True

        else:
            logging.error(f"Base image for {target_version} is not downloaded")
            return False
    else:
        logging.error(
            f"Target PAN-OS version {target_version} is not available for download"
        )
        return False


# ----------------------------------------------------------------------------
# Determine if the firewall is standalone, HA, or in a cluster
# ----------------------------------------------------------------------------
def get_ha_status(firewall: Firewall) -> Tuple:
    """
    Determine the high-availability (HA) status of a Firewall appliance.

    Retrieves and logs the HA deployment information of the specified Firewall. This function checks
    whether the Firewall is standalone, part of an HA pair, or in a cluster configuration. It also
    extracts additional HA details if available.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the firewall to check.

    Returns
    -------
    tuple
        A tuple containing two elements:
        1. A string indicating the deployment type (e.g., 'standalone', 'active/passive', 'active/active').
        2. A dictionary with detailed HA information if available, or None otherwise.

    Example
    -------
    >>> fw = Firewall(hostname='192.168.1.1', api_key='apikey')
    >>> get_ha_status(fw)
    ('active/passive', {'ha_details': ...})
    """
    logging.debug(f"Getting {firewall.serial} deployment information...")
    deployment_type = firewall.show_highavailability_state()
    logging.debug(f"Firewall deployment: {deployment_type[0]}")

    if deployment_type[1]:
        ha_details = xml_to_dict(deployment_type[1])
        logging.debug(f"Firewall deployment details: {ha_details}")
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
    Initiate and monitor the download of a specific PAN-OS software version for the firewall.

    Starts the download process for the specified target PAN-OS version on the provided firewall instance.
    Continuously checks and logs the download progress. If the download is successful, returns True.
    If the download process encounters an error or fails, the function logs the appropriate message
    and returns False. In case of exceptions during the download process, the script exits.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the firewall on which the software is to be downloaded.
    target_version : str
        The target PAN-OS version to be downloaded.
    ha_details : dict
        High-availability details of the firewall, used to determine if HA synchronization is required.

    Returns
    -------
    bool
        True if the target version is successfully downloaded, False if the download fails or an error occurs.

    Raises
    ------
    SystemExit
        If an exception occurs during the download process or if the script encounters a critical error.

    Notes
    -----
    The function checks if the target version is already downloaded before initiating the download.
    It also provides logging about the HA state if relevant HA details are provided.
    """

    if firewall.software.versions[target_version]["downloaded"]:
        logging.info(f"PAN-OS version {target_version} already on firewall.")
        return True

    if (
        not firewall.software.versions[target_version]["downloaded"]
        or firewall.software.versions[target_version]["downloaded"] != "downloading"
    ):
        logging.info(f"PAN-OS version {target_version} is not on the firewall")

        start_time = time.time()

        try:
            logging.info(f"PAN-OS version {target_version} is beginning download")
            firewall.software.download(target_version)
        except PanDeviceXapiError as download_error:
            logging.error(download_error)
            sys.exit(1)

        while True:
            firewall.software.info()
            dl_status = firewall.software.versions[target_version]["downloaded"]
            elapsed_time = int(time.time() - start_time)

            if dl_status is True:
                logging.info(
                    f"{target_version} downloaded in {elapsed_time} seconds",
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
                        f"{status_msg} - HA will sync image - Elapsed time: {elapsed_time} seconds"
                    )
                else:
                    logging.info(f"{status_msg} - Elapsed time: {elapsed_time} seconds")
            else:
                logging.error(f"Download failed after {elapsed_time} seconds")
                return False

            time.sleep(30)

    else:
        logging.error(f"Error downloading {target_version}.")
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
) -> Union[AssuranceReport, None]:
    """
    Execute operational tasks on the Firewall and return the results or generate reports.

    Handles various operational tasks on the Firewall based on 'operation_type', such as
    performing readiness checks, capturing state snapshots, or generating reports. The function
    operates according to the specified 'actions' and 'config'. If the operation is successful,
    it returns the results or an AssuranceReport object. If an invalid operation type or action
    is specified, or an error occurs, the function logs an error and returns None.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class representing the firewall to operate on.
    hostname : str
        Hostname of the firewall.
    operation_type : str
        Type of operation to be executed, e.g., 'readiness_check', 'state_snapshot', 'report'.
    actions : List[str]
        List of specific actions to be performed within the operation type.
    config : Dict[str, Union[str, int, float, bool]]
        Configuration settings for the specified action.

    Returns
    -------
    Union[AssuranceReport, None]
        The results of the operation as an AssuranceReport object, or None if an invalid
        operation type or action is specified, or if an error occurs.

    Raises
    ------
    SystemExit
        If an invalid action is provided for the specified operation type or if an exception
        occurs during the execution of the operation.

    Notes
    -----
    - 'readiness_check' verifies the firewall's readiness for upgrade tasks.
    - 'state_snapshot' captures the current state of the firewall.
    - 'report' generates a report based on the specified action. Implementation details for
      report generation should be completed as per requirements.
    """
    # setup Firewall client
    proxy_firewall = FirewallProxy(firewall)
    checks_firewall = CheckFirewall(proxy_firewall)

    results = None

    if operation_type == "readiness_check":
        for action in actions:
            if action not in AssuranceOptions.READINESS_CHECKS:
                logging.error(f"Invalid action for readiness check: {action}")
                sys.exit(1)

        try:
            logging.info("Checking if firewall is ready for upgrade...")
            result = checks_firewall.run_readiness_checks(actions)

            for (
                test_name,
                test_info,
            ) in AssuranceOptions.READINESS_CHECK_DESCRIPTIONS.items():
                check_readiness_and_log(result, test_name, test_info)

        except Exception as e:
            logging.error(f"Error running readiness checks: {e}")
            return

    elif operation_type == "state_snapshot":
        # validate each type of action
        for action in actions:
            if action not in AssuranceOptions.STATE_SNAPSHOTS:
                logging.error(f"Invalid action for state snapshot: {action}")
                return

        # take snapshots
        try:
            logging.debug("Running snapshots...")
            results = checks_firewall.run_snapshots(snapshots_config=actions)
            logging.debug(results)

            if results:
                # Pass the results to the AssuranceReport model
                return AssuranceReport(hostname=hostname, **results)
            else:
                return None

        except Exception as e:
            logging.error("Error running snapshots: %s", e)
            return

    elif operation_type == "report":
        for action in actions:
            if action not in AssuranceOptions.REPORTS:
                logging.error(f"Invalid action for report: {action}")
                return
            logging.info(f"Generating report: {action}")
            # result = getattr(Report(firewall), action)(**config)

    else:
        logging.error(f"Invalid operation type: {operation_type}")
        return

    return results


# ----------------------------------------------------------------------------
# Primary execution of the script
# ----------------------------------------------------------------------------
def main() -> None:
    """
    Main function of the script, serving as the entry point.

    Handles CLI arguments, configures logging, and establishes a connection to the Firewall appliance.
    Performs a series of operations, including refreshing system information, checking for software updates,
    downloading the target PAN-OS version, and collecting network state information for upgrade assurance.
    It conducts readiness checks and takes a pre-upgrade snapshot of the network state. Logs progress and
    status throughout the process.

    The function gracefully exits with an error if conditions for the upgrade are not met or if any critical
    issues are encountered during execution. It enters a debug mode upon successful completion of all operations.

    Operations:
    - Connects to the Firewall and refreshes system information.
    - Determines deployment status (standalone, HA, cluster).
    - Assesses readiness for upgrade and downloads the target PAN-OS version.
    - Collects network state information and performs readiness checks.

    Raises
    ------
    SystemExit
        If the firewall is not ready for an upgrade to the target version, or
        if there are other critical issues preventing the continuation of the script.
    """
    args = parse_arguments()
    configure_logging(args["log_level"])

    # Create our connection to the firewall
    logging.debug("Connecting to PAN-OS firewall...")
    firewall = connect_to_firewall(args)
    logging.info("Connection established")

    # Refresh system information to ensure we have the latest data
    logging.debug("Refreshing system information...")
    firewall_details = SystemSettings.refreshall(firewall)[0]
    logging.info(
        f"{firewall.serial} {firewall_details.hostname} {firewall_details.ip_address}"
    )

    # Determine if the firewall is standalone, HA, or in a cluster
    logging.debug("Checking if firewall is standalone, HA, or in a cluster...")
    deploy_info, ha_details = get_ha_status(firewall)
    logging.info(f"Firewall HA mode: {deploy_info}")
    logging.debug(f"Firewall HA details: {ha_details}")

    # Check to see if the firewall is ready for an upgrade
    logging.debug("Checking firewall readiness...")
    update_available = software_update_check(
        firewall, args["target_version"], ha_details
    )
    logging.debug("Firewall readiness check complete")

    # gracefully exit if the firewall is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"Firewall is not ready for upgrade to {args['target_version']}.",
        )
        sys.exit(1)

    # Download the target PAN-OS version
    logging.info(f"Checking if {args['target_version']} is downloaded...")
    image_downloaded = software_download(firewall, args["target_version"], ha_details)
    if deploy_info == "active" or deploy_info == "passive":
        logging.info(
            f"{args['target_version']} has been downloaded and sync'd to HA peer."
        )
    else:
        logging.info(f"{args['target_version']} has been downloaded.")

    # Begin Snapshotting the network state
    if image_downloaded:
        # Execute the pre-upgrade snapshot
        logging.info("Taking a pre-upgrade snapshot of network state information...")
        assurance_report = run_assurance(
            firewall,
            firewall_details.hostname,
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

        # Check if an assurance report was successfully created
        if assurance_report:
            # Do something with the assurance report, e.g., log it, save it, etc.
            logging.info("Assurance Report created successfully")
            assurance_report_json = assurance_report.model_dump_json(indent=4)
            logging.debug(assurance_report_json)

            # Ensure directory exists before writing the file
            file_path = f'assurance/snapshots/{firewall_details.hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json'
            ensure_directory_exists(file_path)

            with open(file_path, "w") as file:
                file.write(assurance_report_json)

        else:
            logging.error("Failed to create Assurance Report")

        logging.info(
            f"Pre-Upgrade network state snapshot collected from {firewall_details.hostname}, saved to {file_path}"
        )

        # Execute Readiness Checks
        logging.info("Checking device to see if its ready for an upgrade...")
        readiness_check = run_assurance(
            firewall,
            firewall_details.hostname,
            operation_type="readiness_check",
            actions=[
                "candidate_config",
                "content_version",
                "expired_licenses",
                "ha",
            ],
            config={},
        )

        # Check if an readiness check was successfully created
        if readiness_check:
            # Do something with the readiness check, e.g., log it, save it, etc.
            logging.info("Readiness Checks completed")
            logging.info(readiness_check)


if __name__ == "__main__":
    main()
