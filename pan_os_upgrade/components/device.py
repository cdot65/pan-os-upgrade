# standard library imports
import copy
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import RemoteDisconnected
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Third-party imports
from dynaconf.base import LazySettings

# Palo Alto Networks SDK imports
from panos.base import PanDevice
from panos.errors import (
    PanConnectionTimeout,
    PanURLError,
    PanXapiError,
)
from panos.firewall import Firewall
from panos.panorama import Panorama

# Project imports
from pan_os_upgrade.components.utilities import (
    configure_logging,
    ensure_directory_exists,
    get_emoji,
    flatten_xml_to_dict,
    model_from_api_response,
)
from pan_os_upgrade.models import ManagedDevice, ManagedDevices


# Common setup for all subcommands
def common_setup(
    hostname: str,
    username: str,
    password: str,
    settings_file: LazySettings,
    settings_file_path: Path,
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
    - Logging configuration affects the entire application's logging behavior; the log level can be overridden by `settings.yaml` if `SETTINGS_FILE_PATH` is detected in the function.
    - A successful device connection is critical for the function to return; otherwise, it may raise exceptions based on connection issues.

    The ability to override default settings with `settings.yaml` is supported for the log level configuration in this function if `SETTINGS_FILE_PATH` is utilized within `configure_logging`.
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
        ensure_directory_exists(file_path=os.path.join(dir, "dummy_file"))

    # Configure logging right after directory setup
    configure_logging(
        settings_file=settings_file,
        settings_file_path=settings_file_path,
    )

    # Connect to the device
    device = connect_to_host(
        hostname=hostname,
        username=username,
        password=password,
    )
    return device


def connect_to_host(
    hostname: str,
    username: str,
    password: str,
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
            hostname=hostname,
            api_username=username,
            api_password=password,
        )
        logging.info(
            f"{get_emoji(action='start')} {hostname}: Connection to the appliance successful."
        )

        return target_device

    except PanConnectionTimeout:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Connection to the appliance timed out. Please check the DNS hostname or IP address and network connectivity."
        )

        sys.exit(1)

    except Exception as e:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: An error occurred while connecting to the appliance: {e}"
        )

        sys.exit(1)


def check_panorama_license(panorama: Panorama) -> bool:
    try:

        # Perform the operational command to retrieve license info
        response = panorama.op("request license info")

        licenses_element = response.find(".//licenses")

        if licenses_element is None or len(licenses_element) == 0:
            return False

        # Check if any license entry has expired
        for entry in licenses_element.findall(".//entry"):
            if entry.find("expired").text == "yes":
                return False

        return True

    except Exception as e:
        logging.error(f"Error checking Panorama license: {e}")
        return False


def get_firewall_details(
    firewall: Firewall,
) -> Dict[str, Any]:
    """
    Retrieves detailed system and High Availability (HA) status information from a specified firewall device and organizes it into a dictionary.

    This function establishes communication with the firewall to collect critical system details and HA status, such as hostname, IP address, model, serial number, software version, application version, and HA configuration. It is designed to assist in diagnostics, inventory management, operational monitoring, and checking the HA status by providing a comprehensive overview of the firewall's current operational state, configuration, and HA status.

    Parameters
    ----------
    firewall : Firewall
        The Firewall instance from which to fetch system information and HA status. This object must be initialized with the necessary authentication credentials and network details to enable API communication with the firewall.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing key elements of the firewall's system information, such as hostname, IP address, model, serial number, software version, application version, and HA status. If an error occurs during information retrieval, the function returns a dictionary with the data available up to the point of failure and marks the status as "Offline or Unavailable".

    Example
    -------
    Fetching system and HA status information for a firewall:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> firewall_info = get_firewall_details(firewall_instance)
        >>> print(firewall_info)
        {'hostname': 'fw-hostname', 'ip-address': '192.168.1.1', 'model': 'PA-850', 'serial': '0123456789',
        'sw-version': '10.0.0', 'app-version': '8200-1234', 'ha-mode': 'active/passive', 'ha-details': {...}}

    Notes
    -----
    - The function is aimed at scenarios requiring firewall configuration, status monitoring, and HA status checks.
    - Error handling is in place to ensure that, in the event the firewall is unreachable or if any issues occur during data retrieval, partial or default information is returned. This allows for graceful degradation of functionality and ensures operational continuity.
    """
    # Ensure a safe operation by working with a copy of the firewall object
    fw_copy = copy.deepcopy(firewall)

    try:
        # Attempt to retrieve system information from the firewall
        info = fw_copy.show_system_info()
        system_info = {
            "hostname": info["system"]["hostname"],
            "ip-address": info["system"]["ip-address"],
            "model": info["system"]["model"],
            "serial": info["system"]["serial"],
            "sw-version": info["system"]["sw-version"],
            "app-version": info["system"]["app-version"],
        }
    except Exception as e:
        # Log and return default values in case of an error for system info
        logging.error(f"Error retrieving system info for {fw_copy.serial}: {str(e)}")
        system_info = {
            "hostname": fw_copy.hostname or "Unknown",
            "ip-address": "N/A",
            "model": "N/A",
            "serial": fw_copy.serial,
            "sw-version": "N/A",
            "app-version": "N/A",
            "status": "Offline or Unavailable",
        }

    try:
        # Retrieve HA status and details
        deploy_info, ha_details = get_ha_status(
            hostname=system_info.get("hostname", ""),
            target_device=firewall,
        )
        ha_info = {
            "ha-mode": deploy_info,
            "ha-details": ha_details,
        }
    except Exception as e:
        # Log and return default values in case of an error for HA info
        logging.error(f"Error retrieving HA info for {fw_copy.serial}: {str(e)}")
        ha_info = {
            "ha-mode": "N/A",
            "ha-details": None,
        }

    # Merge system info and HA info into a single dictionary
    firewall_info = {**system_info, **ha_info}
    return firewall_info


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
    for managed_device in get_managed_devices(panorama=panorama):
        firewall = Firewall(serial=managed_device.serial)
        firewalls.append(firewall)
        panorama.add(firewall)

    return firewalls


def get_ha_status(
    hostname: str,
    target_device: Union[Firewall, Panorama],
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
        f"{get_emoji(action='start')} {hostname}: Getting {target_device.serial} deployment information."
    )
    deployment_type = target_device.show_highavailability_state()
    logging.debug(
        f"{get_emoji(action='report')} {hostname}: Target device deployment: {deployment_type[0]}"
    )

    if deployment_type[1]:
        ha_details = flatten_xml_to_dict(element=deployment_type[1])
        logging.debug(
            f"{get_emoji(action='report')} {hostname}: Target device deployment details: {ha_details}"
        )
        return deployment_type[0], ha_details
    else:
        return deployment_type[0], None


def get_managed_devices(panorama: Panorama) -> list[ManagedDevice]:
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
        panorama.op("show devices connected"), ManagedDevices
    )
    devices = managed_devices.devices

    return devices


def perform_reboot(
    hostname: str,
    settings_file: LazySettings,
    settings_file_path: Path,
    target_device: Union[Firewall, Panorama],
    target_version: str,
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

    logging.info(
        f"{get_emoji(action='start')} {hostname}: Rebooting the target device."
    )

    # Initiate reboot
    target_device.op(
        "<request><restart><system/></restart></request>",
        cmd_xml=False,
    )

    # Wait for the target device reboot process to initiate before checking status
    time.sleep(initial_sleep_duration)

    while not rebooted and attempt < max_retries:
        try:
            # Refresh system information to check if the device is back online
            target_device.refresh_system_info()
            current_version = target_device.version
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Current device version: {current_version}"
            )

            # Check if the device has rebooted to the target version
            if current_version == target_version:
                logging.info(
                    f"{get_emoji(action='success')} {hostname}: Device rebooted to the target version successfully."
                )
                rebooted = True
            else:
                logging.error(
                    f"{get_emoji(action='error')} {hostname}: Device rebooted but not to the target version."
                )
                sys.exit(1)

        except (
            PanXapiError,
            PanConnectionTimeout,
            PanURLError,
            RemoteDisconnected,
        ) as e:
            logging.warning(
                f"{get_emoji(action='warning')} {hostname}: Retry attempt {attempt + 1} due to error: {e}"
            )
            attempt += 1
            time.sleep(retry_interval)

    if not rebooted:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Failed to reboot to the target version after {max_retries} attempts."
        )
        sys.exit(1)


def threaded_get_firewall_details(firewalls: List[Firewall]) -> List[Dict[str, Any]]:
    """
    Retrieves detailed system information for a list of firewalls using concurrent executions to improve efficiency.

    This function iterates over a list of Firewall objects, fetching system information for each one in parallel to
    minimize total execution time. It utilizes a thread pool to handle concurrent requests, making it well-suited for
    scenarios where information from multiple devices needs to be aggregated swiftly. The collected information includes,
    but is not limited to, software version, system uptime, and serial numbers, structured as a dictionary for each firewall.

    Parameters
    ----------
    firewalls : List[Firewall]
        A list of Firewall objects, each representing a device from which system information is to be fetched. These
        objects should be initialized with the necessary connection details.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, with each dictionary containing system information for a respective firewall. The
        structure and content of these dictionaries depend on the implementation of the `get_firewall_details` function
        but typically include keys such as 'hostname', 'version', 'serial number', etc.

    Example
    -------
    Fetching information for a list of firewall objects:
        >>> firewalls = [Firewall('192.168.1.1', api_key='apikey1'), Firewall('192.168.1.2', api_key='apikey2')]
        >>> info = threaded_get_firewall_details(firewalls)
        # This returns a list of dictionaries, each containing information about a firewall.

    Notes
    -----
    - This function leverages concurrent threads to fetch data, significantly reducing the total time required to
    obtain information from multiple devices.
    - The actual data fetched and the structure of the returned dictionaries are determined by the `get_firewall_details`
    function, which this function depends on.
    """
    firewalls_info = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Creating a future for each firewall info fetch task
        future_to_firewall_info = {
            executor.submit(get_firewall_details, fw): fw for fw in firewalls
        }

        # Iterating over completed fetch tasks and collecting their results
        for future in as_completed(future_to_firewall_info):
            firewall_info = future.result()
            firewalls_info.append(firewall_info)

    return firewalls_info
