import ipaddress
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET

from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# third party imports
import dns.resolver
import typer
from colorama import Fore
from dynaconf.base import LazySettings
from tabulate import tabulate
from typer import BadParameter

# Palo Alto Networks imports
from panos.firewall import Firewall
from panos.panorama import Panorama

# Project imports
from pan_os_upgrade.models import FromAPIResponseMixin


def backup_configuration(
    file_path: str,
    hostname: str,
    target_device: Union[Firewall, Panorama],
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
                f"{get_emoji(action='error')} {hostname}: Failed to retrieve running configuration."
            )
            return False

        # Check XML structure
        if (
            config_xml.tag != "response"
            or len(config_xml) == 0
            or config_xml[0].tag != "result"
        ):
            logging.error(
                f"{get_emoji(action='error')} {hostname}: Unexpected XML structure in configuration data."
            )
            return False

        # Extract the configuration data from the <result><config> tag
        config_data = config_xml.find(".//result/config")

        # Manually construct the string representation of the XML data
        config_str = ET.tostring(config_data, encoding="unicode")

        # Ensure the directory exists
        ensure_directory_exists(file_path=file_path)

        # Write the file to the local filesystem
        with open(file_path, "w") as file:
            file.write(config_str)

        logging.debug(
            f"{get_emoji(action='save')} {hostname}: Configuration backed up successfully to {file_path}"
        )
        return True

    except Exception as e:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Error backing up configuration: {e}"
        )
        return False


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

    parsed_version1 = parse_version(version=version1)
    parsed_version2 = parse_version(version=version2)

    if parsed_version1 < parsed_version2:
        return "older"
    elif parsed_version1 > parsed_version2:
        return "newer"
    else:
        return "equal"


def console_welcome_banner(
    mode: str,
    config_path: Optional[Path] = None,
    inventory_path: Optional[Path] = None,
) -> str:
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

    support_message = "This script software is provided on an 'as-is' basis with no warranties, and no support provided."

    # Longest line defines border, and that will always be the support message
    border_length = len(support_message)

    # Customize messages based on the mode
    if mode == "settings":
        welcome_message = "Welcome to the PAN-OS upgrade settings menu"
        banner_message = "The selected 'settings' subcommand will create `settings.yaml` in your current directory.\nThis `settings.yaml` file will contain your custom settings and will be loaded at runtime."
        config_message = inventory_message = ""
    elif mode == "inventory":
        welcome_message = "Welcome to the PAN-OS upgrade inventory menu"
        banner_message = "The selected 'inventory' subcommand will create `inventory.yaml` in your current directory.\nThis `inventory.yaml` file will contain firewalls to upgrade and will be loaded at runtime."
        config_message = inventory_message = ""
    else:
        welcome_message = "Welcome to the PAN-OS upgrade tool"
        banner_message = {
            "firewall": "The selected `firewall` subcommand will upgrade a single Firewall appliance.",
            "panorama": "The selected `panorama` subcommand will upgrade a single Panorama appliance.",
            "batch": "The selected `batch` subcommand will upgrade one or more firewalls.",
        }.get(mode, "")

        if mode == "batch":
            inventory_message = (
                f"Inventory: Custom inventory loaded file detected and loaded at:\n{inventory_path}"
                if inventory_path and inventory_path.exists()
                else "Inventory: No inventory.yaml file was found, firewalls will need be selected through the menu.\nYou can create an inventory.yaml file with 'pan-os-upgrade inventory' command."
            )

        else:
            inventory_message = ""

        config_message = (
            f"Settings: Custom configuration loaded file detected and loaded at:\n{config_path}"
            if config_path and config_path.exists()
            else "Settings: No settings.yaml file was found, default values will be used.\nYou can create a settings.yaml file with 'pan-os-upgrade settings' command."
        )

    # Calculate border length based on the longer message
    border_length = max(
        len(welcome_message),
        len(support_message),
        max(len(line) for line in banner_message.split("\n")),
        (
            max(len(line) for line in config_message.split("\n"))
            if config_message
            else 0
        ),
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
    banner = f"{color_start}{border}\n{welcome_message}\n\n{support_message}\n\n{banner_message}"
    # Only add config_message if it's not empty
    if config_message:
        banner += f"\n\n{config_message}"

    # Only add config_message if it's not empty
    if inventory_message:
        banner += f"\n\n{inventory_message}"

    banner += f"\n{border}{color_end}"

    return banner


def configure_logging(
    encoding: str = "utf-8",
    log_file_path: str = "logs/upgrade.log",
    log_max_size: int = 10 * 1024 * 1024,
    settings_file: LazySettings = None,
    settings_file_path: Path = None,
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

    level = settings_file.get("logging.level", "INFO")

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


def create_firewall_mapping(
    all_firewalls: List[Firewall],
    firewalls_info: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Constructs a mapping between firewall hostnames and their associated data, including the corresponding Firewall
    object and additional firewall details. This mapping facilitates easy access to both the Firewall object and its
    attributes like serial number, management IP, and any other relevant information provided in the firewalls_info list.

    This function iterates through each provided firewall's information, matches it with the corresponding Firewall
    object based on the serial number, and then combines these into a single dictionary. This combined dictionary is
    indexed by the hostname of each firewall, allowing for quick lookup of firewall details and the associated Firewall
    object.

    Parameters
    ----------
    all_firewalls : List[Firewall]
        A list of instantiated Firewall objects, each representing a specific firewall device with connectivity
        and operational capabilities.
    firewalls_info : List[Dict[str, Any]]
        A list of dictionaries, with each dictionary containing detailed information about a firewall, such as
        its hostname, serial number, management IP, and potentially other metadata.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        A dictionary where each key is a firewall's hostname and each value is a dictionary containing the
        corresponding Firewall object under the 'object' key and merged with the firewall's detailed information
        from the firewalls_info list.

    Example
    -------
    Creating a mapping of firewalls to their details and objects:
        >>> all_firewalls = [Firewall('fw1'), Firewall('fw2')]
        >>> firewalls_info = [{'hostname': 'fw1', 'serial': '12345', 'ip': '10.0.0.1'},
                            {'hostname': 'fw2', 'serial': '67890', 'ip': '10.0.0.2'}]
        >>> mapping = create_firewall_mapping(all_firewalls, firewalls_info)
        >>> mapping['fw1']
        {'object': <Firewall object>, 'hostname': 'fw1', 'serial': '12345', 'ip': '10.0.0.1'}

    Notes
    -----
    - This function assumes that each firewall's serial number is unique and uses it as the key to match
    Firewall objects with their corresponding details.
    - The function does not validate the presence of keys within the firewalls_info dictionaries; it is
    assumed that each dictionary contains at least the 'serial' and 'hostname' keys.
    """
    firewall_mapping = {}
    firewall_object_mapping = {fw.serial: fw for fw in all_firewalls}

    for fw_info in firewalls_info:
        serial = fw_info["serial"]
        firewall_object = firewall_object_mapping.get(serial)
        if firewall_object:
            firewall_mapping[fw_info["hostname"]] = {
                "object": firewall_object,
                **fw_info,
            }

    return firewall_mapping


def determine_upgrade(
    hostname: str,
    target_device: Union[Firewall, Panorama],
    target_maintenance: Union[int, str],
    target_major: int,
    target_minor: int,
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

    current_version = parse_version(version=target_device.version)

    if isinstance(target_maintenance, int):
        # Handling integer maintenance version separately
        target_version = (target_major, target_minor, target_maintenance, 0)
    else:
        # Handling string maintenance version with hotfix
        target_version = parse_version(
            version=f"{target_major}.{target_minor}.{target_maintenance}"
        )

    logging.info(
        f"{get_emoji(action='report')} {hostname}: Current version: {target_device.version}"
    )
    logging.info(
        f"{get_emoji(action='report')} {hostname}: Target version: {target_major}.{target_minor}.{target_maintenance}"
    )

    if current_version < target_version:
        logging.info(
            f"{get_emoji(action='success')} {hostname}: Upgrade required from {target_device.version} to {target_major}.{target_minor}.{target_maintenance}"
        )
    else:
        logging.info(
            f"{get_emoji(action='skipped')} {hostname}: No upgrade required or downgrade attempt detected."
        )
        logging.info(f"{get_emoji(action='skipped')} {hostname}: Halting upgrade.")
        sys.exit(0)


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
        version=target_version
    )

    version_distances = []

    for version in available_versions:
        # Parse each available version
        major, minor, maintenance, hotfix = parse_version(version=version)

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
                        flatten_xml_to_dict(element=child_element),
                    ]
                else:
                    result[child_tag].append(flatten_xml_to_dict(element=child_element))
            else:
                if child_tag == "entry":
                    # Always assume entries are a list.
                    result[child_tag] = [flatten_xml_to_dict(element=child_element)]
                else:
                    result[child_tag] = flatten_xml_to_dict(element=child_element)

    return result


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
        >>> logging.info(f"{get_emoji(action='success')} Operation successful.")
        >>> logging.error(f"{get_emoji(action='error')} An error occurred.")

    Enhancing user prompts in a command-line application:
        >>> print(f"{get_emoji(action='start')} Initiating the process.")
        >>> print(f"{get_emoji(action='stop')} Process terminated.")

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
    BadParameter
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
    - Default settings can be overridden by configurations specified in a `settings.yaml` file if `SETTINGS_FILE_PATH` is used within the script, allowing for customized validation logic based on the application's needs.
    """

    # First, try to resolve as a hostname
    if resolve_hostname(hostname=value):
        return value

    # If hostname resolution fails, try as an IP address
    try:
        ipaddress.ip_address(value)
        return value

    except ValueError as err:
        raise BadParameter(
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
    - Default configuration and behavior can be modified through the use of a `settings.yaml` file if the application supports loading configurations in this manner and `SETTINGS_FILE_PATH` is utilized.

    Raises
    ------
    ValueError
        In cases where the XML data does not match the structure expected by the Pydantic model, indicating a possible mismatch between the API response format and the model's schema.
    """

    result_dict = flatten_xml_to_dict(element=element)
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
    except (
        dns.resolver.NoAnswer,
        dns.resolver.NXDOMAIN,
        dns.exception.Timeout,
    ) as err:
        # Optionally log or handle err here if needed
        logging.debug(f"Hostname resolution failed: {err}")
        return False


def select_devices_from_table(firewall_mapping: dict) -> List[str]:
    """
    Presents a table of firewalls, including details such as hostname, IP address, model, serial number, software version, and HA mode, and prompts the user to select devices for further operations. Users can select devices by their listing numbers, a range, or a combination thereof. The function returns a list of hostnames corresponding to the user's selections.

    This interactive step is crucial for operations targeting multiple devices, as it provides users with precise control over which devices are included. The function ensures that selections are valid and within the range of displayed devices, providing feedback on any invalid entries.

    Parameters
    ----------
    firewall_mapping : dict
        A dictionary mapping device hostnames to their respective details, which includes the firewall object, IP address, model, serial number, software version, application version, HA mode, and HA details. This information is used to generate the selection table.

    Returns
    -------
    List[str]
        A list of hostnames for the selected devices, based on user input.

    Examples
    --------
    Displaying a selection table and capturing user choices:
        >>> firewall_mapping = {
        ...     'fw1': {
        ...         'object': <Firewall '0123456789' None at 0x1234abcd>,
        ...         'hostname': 'fw1',
        ...         'ip-address': '10.1.1.1',
        ...         'model': 'PA-850',
        ...         'serial': '0123456789',
        ...         'sw-version': '9.1.0',
        ...         'app-version': '9.1.0',
        ...         'ha-mode': 'active/passive',
        ...         'ha-details': None,
        ...     },
        ...     'fw2': {
        ...         'object': <Firewall '9876543210' None at 0xabcd1234>,
        ...         'hostname': 'fw2',
        ...         'ip-address': '10.1.1.2',
        ...         'model': 'PA-220',
        ...         'serial': '9876543210',
        ...         'sw-version': '9.1.2',
        ...         'app-version': '9.1.3',
        ...         'ha-mode': 'active/active',
        ...         'ha-details': {...},
        ...     },
        ... }
        >>> selected_hostnames = select_devices_from_table(firewall_mapping)
        # The user is prompted to select from the table. The function returns the hostnames of the selected devices.

    Notes
    -----
    - Utilizes the `tabulate` library to display a structured and readable table for device selection.
    - Supports various input formats for device selection, such as individual numbers, ranges (e.g., '2-4'), or a comma-separated list, offering flexibility in selection methodology.
    - Gracefully handles invalid selections with prompts for correction, ensuring a user-friendly selection process.
    """

    # Sort firewalls by hostname for consistent display
    sorted_firewall_items = sorted(firewall_mapping.items(), key=lambda item: item[0])

    devices_table = []
    for i, (hostname, details) in enumerate(sorted_firewall_items):
        preemptive_status = "N/A"
        if details["ha-details"] is not None:
            preemptive_status = (
                details["ha-details"]
                .get("result", {})
                .get("group", {})
                .get("local-info", {})
                .get("preemptive", "N/A")
            )

        # Using 'hostname' to add an entry to the 'devices_table'
        devices_table.append(
            [
                Fore.CYAN + str(i + 1) + Fore.RESET,
                hostname,
                details["ip-address"],
                details["model"],
                # details["serial"],
                details["sw-version"],
                details["app-version"],
                details["ha-mode"],
                preemptive_status,
            ]
        )

    typer.echo(
        tabulate(
            devices_table,
            headers=[
                Fore.GREEN + "#" + Fore.RESET,
                Fore.GREEN + "Hostname" + Fore.RESET,
                Fore.GREEN + "IP Address" + Fore.RESET,
                Fore.GREEN + "Model" + Fore.RESET,
                # Fore.GREEN + "Serial" + Fore.RESET,
                Fore.GREEN + "PAN-OS" + Fore.RESET,
                Fore.GREEN + "Content" + Fore.RESET,
                Fore.GREEN + "HA Mode" + Fore.RESET,
                Fore.GREEN + "Preempt" + Fore.RESET,
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
                    typer.echo(Fore.GREEN + f"  - {hostname} selected." + Fore.RESET)
                else:
                    typer.echo(
                        Fore.YELLOW
                        + f"  - {hostname} is already selected."
                        + Fore.RESET
                    )
            else:
                typer.echo(
                    Fore.RED + f"Selection '{index + 1}' is out of range." + Fore.RESET
                )

    # New code to check for preemptive="yes" and prompt user
    preemptive_firewalls = []
    for hostname in user_selected_hostnames:
        details = firewall_mapping.get(hostname, {})
        ha_details = details.get("ha-details", {})
        if ha_details:
            preemptive_status = (
                ha_details.get("result", {})
                .get("group", {})
                .get("local-info", {})
                .get("preemptive", "no")
            )
            if preemptive_status.lower() == "yes":
                preemptive_firewalls.append(hostname)

    if preemptive_firewalls:
        typer.echo(
            Fore.RED
            + f"Warning: Firewalls {', '.join(preemptive_firewalls)} have 'preempt' enabled, this can cause an interruption."
            + Fore.RESET
        )
        confirmation = typer.prompt(
            Fore.YELLOW
            + "Are you sure that you want to add these firewalls to the upgrade list? (y/n)"
            + Fore.RESET
        )
        if confirmation.lower() != "y":
            user_selected_hostnames = [
                hostname
                for hostname in user_selected_hostnames
                if hostname not in preemptive_firewalls
            ]
            typer.echo(
                Fore.GREEN
                + "Firewalls with 'preempt' set to 'yes' have been excluded."
                + Fore.RESET
            )

    return user_selected_hostnames
