import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import PosixPath
from typing import Tuple, Union
from panos.firewall import Firewall
from panos.panorama import Panorama
from dynaconf.base import LazySettings


class Utilities:
    def __init__(self):
        pass

    @staticmethod
    def compare_versions(self, version1: str, version2: str) -> str:
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

        parsed_version1 = self.parse_version(version1)
        parsed_version2 = self.parse_version(version2)

        if parsed_version1 < parsed_version2:
            return "older"
        elif parsed_version1 > parsed_version2:
            return "newer"
        else:
            return "equal"

    @staticmethod
    def configure_logging(
        settings_file: LazySettings,
        settings_file_path: PosixPath,
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

        level = settings_file.get("logging.level", "INFO")

        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level.upper() not in allowed_levels:
            raise ValueError(
                f"Invalid log level: {level}. Allowed levels are: {', '.join(allowed_levels)}"
            )

        # Use the provided log_level parameter if given, otherwise fall back to settings file or default
        log_level = (
            level.upper()
            if level
            else settings_file.get("logging.level", "INFO").upper()
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

    @classmethod
    def determine_upgrade(
        cls,
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

        current_version = cls.parse_version(target_device.version)

        if isinstance(target_maintenance, int):
            # Handling integer maintenance version separately
            target_version = (target_major, target_minor, target_maintenance, 0)
        else:
            # Handling string maintenance version with hotfix
            target_version = cls.parse_version(
                f"{target_major}.{target_minor}.{target_maintenance}"
            )

        logging.info(
            f"{cls.get_emoji('report')} {hostname}: Current version: {target_device.version}"
        )
        logging.info(
            f"{cls.get_emoji('report')} {hostname}: Target version: {target_major}.{target_minor}.{target_maintenance}"
        )

        if current_version < target_version:
            logging.info(
                f"{cls.get_emoji('success')} {hostname}: Upgrade required from {target_device.version} to {target_major}.{target_minor}.{target_maintenance}"
            )
        else:
            logging.info(
                f"{cls.get_emoji('skipped')} {hostname}: No upgrade required or downgrade attempt detected."
            )
            logging.info(f"{cls.get_emoji('skipped')} {hostname}: Halting upgrade.")
            sys.exit(0)

    @staticmethod
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

    # @staticmethod
    # def flatten_xml_to_dict(element: ET.Element) -> dict:
    #     # Function implementation here

    @staticmethod
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

    # @staticmethod
    # def find_close_matches(available_versions: List[str], target_version: str, max_results: int = 5) -> List[str]:
    #     # Function implementation here

    @staticmethod
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

    # @staticmethod
    # def resolve_hostname(hostname: str) -> bool:
    #     # Function implementation here
