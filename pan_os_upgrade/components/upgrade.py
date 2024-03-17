import json
import logging
import sys
import time
import yaml
from pathlib import Path
from threading import Lock
from typing import Union

# Palo Alto Networks pan-os-python imports
from panos.device import SystemSettings
from panos.errors import (
    PanDeviceError,
    PanDeviceXapiError,
)
from panos.firewall import Firewall
from panos.panorama import Panorama

# Palo Alto Networks panos-upgrade-assurance imports
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare

# Third-party library imports
from dynaconf import LazySettings

# Local imports
from pan_os_upgrade.components.assurance import (
    AssuranceOptions,
    generate_diff_report_pdf,
    perform_readiness_checks,
    perform_snapshot,
)
from pan_os_upgrade.components.device import (
    check_panorama_license,
    get_ha_status,
    perform_reboot,
)
from pan_os_upgrade.components.ha import (
    ha_sync_check_firewall,
    ha_sync_check_panorama,
    handle_firewall_ha,
    handle_panorama_ha,
)
from pan_os_upgrade.components.utilities import (
    backup_configuration,
    determine_upgrade,
    ensure_directory_exists,
    find_close_matches,
    get_emoji,
)


def check_ha_compatibility(
    ha_details: dict,
    hostname: str,
    current_major: int,
    current_minor: int,
    upgrade_major: int,
    upgrade_minor: int,
) -> bool:
    """
    Checks the compatibility of the target PAN-OS version with the current version in an HA pair.

    This function assesses whether upgrading a firewall in an HA pair to the target PAN-OS version is compatible
    with the current version running on the firewall. It compares the major and minor version numbers to determine
    if the upgrade spans more than one major release or if the minor version increment is too large within the same
    major version. The function logs warnings for potential compatibility issues and returns a boolean indicating
    whether the upgrade is compatible or not.

    Parameters
    ----------
    ha_details : dict
        A dictionary containing the HA configuration details of the firewall.
    hostname : str
        The hostname or IP address of the firewall for logging purposes.
    current_major : int
        The current major version number of PAN-OS running on the firewall.
    current_minor : int
        The current minor version number of PAN-OS running on the firewall.
    upgrade_major : int
        The target major version number of PAN-OS for the upgrade.
    upgrade_minor : int
        The target minor version number of PAN-OS for the upgrade.

    Returns
    -------
    bool
        True if the target PAN-OS version is compatible with the current version in the HA pair, False otherwise.

    Examples
    --------
    Check compatibility for an HA pair:
        >>> ha_details = {'enabled': True, 'group': '1', 'peer_ip': '192.168.1.2'}
        >>> compatible = check_ha_compatibility(ha_details, 'firewall1', 9, 1, 10, 0)
        >>> if compatible:
        ...     print("Upgrade is compatible")
        ... else:
        ...     print("Upgrade may cause compatibility issues")

    Check compatibility for a standalone firewall:
        >>> ha_details = {'enabled': False}
        >>> compatible = check_ha_compatibility(ha_details, 'firewall2', 8, 1, 9, 0)
        >>> if compatible:
        ...     print("Upgrade is compatible")
        ... else:
        ...     print("Upgrade may cause compatibility issues")

    Notes
    -----
    - The function checks for three scenarios that may cause compatibility issues in an HA pair:
      1. Upgrading to a version that is more than one major release apart.
      2. Upgrading within the same major version but the minor version increment is more than one.
      3. Upgrading to the next major version with a minor version higher than 0.
    - If the firewall is not in an HA pair, the function logs a success message and returns True.
    """
    is_ha_pair = ha_details["result"].get("enabled", False)

    if is_ha_pair:
        # Check if the major upgrade is more than one release apart
        if upgrade_major - current_major > 1:
            logging.warning(
                f"{get_emoji(action='warning')} {hostname}: Upgrading firewalls in an HA pair to a version that is more than one major release apart may cause compatibility issues."
            )
            return False

        # Check if the upgrade is within the same major version but the minor upgrade is more than one release apart
        elif upgrade_major == current_major and upgrade_minor - current_minor > 1:
            logging.warning(
                f"{get_emoji(action='warning')} {hostname}: Upgrading firewalls in an HA pair to a version that is more than one minor release apart may cause compatibility issues."
            )
            return False

        # Check if the upgrade spans exactly one major version but also increases the minor version
        elif upgrade_major - current_major == 1 and upgrade_minor > 0:
            logging.warning(
                f"{get_emoji(action='warning')} {hostname}: Upgrading firewalls in an HA pair to a version that spans more than one major release or increases the minor version beyond the first in the next major release may cause compatibility issues."
            )
            return False

    # Log compatibility check success
    logging.info(
        f"{get_emoji(action='success')} {hostname}: The target version is compatible with the current version."
    )
    return True


def perform_upgrade(
    hostname: str,
    settings_file: LazySettings,
    settings_file_path: Path,
    target_device: Union[Firewall, Panorama],
    target_version: str,
) -> bool:
    """
    Conducts the upgrade process for a Palo Alto Networks device to a specified version. This function handles
    downloading the necessary software version and executing the upgrade command. It is designed to work in both
    standalone and High Availability (HA) configurations, ensuring proper upgrade procedures are followed in each scenario.

    This function attempts the upgrade process up to a maximum number of retries defined in the settings file or default settings.
    If the software manager is busy, it waits for a specified interval before retrying. The function returns a boolean indicating
    the success or failure of the installation process.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target device.
    settings_file : LazySettings
        The LazySettings object containing configurations loaded from the settings file.
    settings_file_path : Path
        The filesystem path to the settings.yaml file, which contains custom configuration settings.
    target_device : Union[Firewall, Panorama]
        The device object representing the target Firewall or Panorama to be upgraded.
    target_version : str
        The target PAN-OS version to upgrade the device to.

    Returns
    -------
    bool
        True if the upgrade installation was successful, False otherwise.

    Raises
    ------
    SystemExit
        If a critical error occurs during the upgrade process, the script will exit.

    Examples
    --------
    Perform an upgrade on a standalone firewall:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> success = perform_upgrade('192.168.1.1', settings_file, Path('/path/to/settings.yaml'), firewall, '10.1.0')
        >>> if success:
        ...     print("Upgrade successful")
        ... else:
        ...     print("Upgrade failed")

    Perform an upgrade on a device in an HA setup (additional HA logic not shown here):
        >>> success = perform_upgrade('192.168.1.1', settings_file, Path('/path/to/settings.yaml'), ha_firewall, '10.1.0')
        >>> if success:
        ...     print("Upgrade successful")
        ... else:
        ...     print("Upgrade failed")

    Notes
    -----
    - The function uses settings from 'settings.yaml' to determine the maximum number of retry attempts and the interval
      between retries if the software manager is busy.
    - The upgrade process includes pre-upgrade checks to ensure the target device is ready for the upgrade.
    - In HA configurations, additional steps are required to ensure both devices in the HA pair are upgraded and synchronized.
    """

    # Initialize with default values
    max_retries = 3
    retry_interval = 60
    install_success = False
    attempt = 0

    # Override if settings.yaml exists and contains these settings
    if settings_file_path.exists():
        max_retries = settings_file.get("install.max_tries", max_retries)
        retry_interval = settings_file.get("install.retry_interval", retry_interval)

    logging.info(
        f"{get_emoji(action='start')} {hostname}: Performing upgrade to version {target_version}.\n"
        f"{get_emoji(action='report')} {hostname}: The install will take several minutes, check for status details within the GUI."
    )

    while attempt < max_retries:
        try:
            logging.info(
                f"{get_emoji(action='start')} {hostname}: Attempting upgrade to version {target_version} (Attempt {attempt + 1} of {max_retries})."
            )
            install_job = target_device.software.install(target_version, sync=True)

            if install_job["success"]:
                logging.info(
                    f"{get_emoji(action='success')} {hostname}: Upgrade completed successfully"
                )
                logging.debug(
                    f"{get_emoji(action='report')} {hostname}: Install Job {install_job}"
                )
                # Mark installation as successful
                install_success = True
                # Exit loop on successful upgrade
                break
            else:
                logging.error(
                    f"{get_emoji(action='error')} {hostname}: Upgrade job failed."
                )
                attempt += 1
                if attempt < max_retries:
                    logging.info(
                        f"{get_emoji(action='warning')} {hostname}: Retrying in {retry_interval} seconds."
                    )
                    time.sleep(retry_interval)

        except PanDeviceError as upgrade_error:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: Upgrade error: {upgrade_error}"
            )
            error_message = str(upgrade_error)
            if "software manager is currently in use" in error_message:
                attempt += 1
                if attempt < max_retries:
                    logging.info(
                        f"{get_emoji(action='warning')} {hostname}: Software manager is busy. Retrying in {retry_interval} seconds."
                    )
                    time.sleep(retry_interval)
            else:
                logging.error(
                    f"{get_emoji(action='stop')} {hostname}: Critical error during upgrade. Halting script."
                )
                sys.exit(1)

    # Return the installation success flag
    return install_success


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
            f"{get_emoji(action='success')} {hostname}: version {target_version} already on target device."
        )
        return True

    if (
        not target_device.software.versions[target_version]["downloaded"]
        or target_device.software.versions[target_version]["downloaded"]
        != "downloading"
    ):
        logging.info(
            f"{get_emoji(action='search')} {hostname}: version {target_version} is not on the target device"
        )

        start_time = time.time()

        try:
            logging.info(
                f"{get_emoji(action='start')} {hostname}: version {target_version} is beginning download"
            )
            target_device.software.download(target_version)
        except PanDeviceXapiError as download_error:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: Download Error {download_error}"
            )

            sys.exit(1)

        while True:
            target_device.software.info()
            dl_status = target_device.software.versions[target_version]["downloaded"]
            elapsed_time = int(time.time() - start_time)

            if dl_status is True:
                logging.info(
                    f"{get_emoji(action='success')} {hostname}: {target_version} downloaded in {elapsed_time} seconds",
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
                        f"{get_emoji(action='working')} {hostname}: Downloading version {target_version} - HA will sync image - Elapsed time: {elapsed_time} seconds"
                    )
                else:
                    logging.info(
                        f"{get_emoji(action='working')} {hostname}: {status_msg} - Elapsed time: {elapsed_time} seconds"
                    )
            else:
                logging.error(
                    f"{get_emoji(action='error')} {hostname}: Download failed after {elapsed_time} seconds"
                )
                return False

            time.sleep(30)

    else:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Error downloading {target_version}."
        )

        sys.exit(1)


def software_update_check(
    ha_details: dict,
    hostname: str,
    settings_file: LazySettings,
    settings_file_path: Path,
    target_device: Union[Firewall, Panorama],
    version: str,
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
        f"{get_emoji(action='working')} {hostname}: Refreshing running system information"
    )
    target_device.refresh_system_info()

    # check to see if the specified version is older than the current version
    determine_upgrade(
        hostname=hostname,
        target_device=target_device,
        target_maintenance=maintenance,
        target_major=major,
        target_minor=minor,
    )

    current_version = target_device.refresh_system_info().version
    current_parts = current_version.split(".")
    current_major, current_minor = map(int, current_parts[:2])
    upgrade_parts = version.split(".")
    upgrade_major, upgrade_minor = map(int, upgrade_parts[:2])

    if ha_details and ha_details["result"].get("enabled"):
        # Check if the target version is compatible with the current version and the HA setup
        if not check_ha_compatibility(
            ha_details,
            hostname,
            current_major,
            current_minor,
            upgrade_major,
            upgrade_minor,
        ):
            return False

    # retrieve available versions of PAN-OS
    logging.info(
        f"{get_emoji(action='working')} {hostname}: Refreshing list of available software versions"
    )
    target_device.software.check()
    available_versions = target_device.software.versions

    if version in available_versions:
        retry_count = settings_file.get("download.max_tries", 3)
        wait_time = settings_file.get("download.retry_interval", 60)

        logging.info(
            f"{get_emoji(action='success')} {hostname}: version {version} is available for download"
        )

        base_version_key = f"{major}.{minor}.0"
        if available_versions.get(base_version_key, {}).get("downloaded"):
            logging.info(
                f"{get_emoji(action='success')} {hostname}: Base image for {version} is already downloaded"
            )
            return True
        else:
            for attempt in range(retry_count):
                logging.error(
                    f"{get_emoji(action='error')} {hostname}: Base image for {version} is not downloaded. Attempting download."
                )
                downloaded = software_download(
                    target_device, hostname, base_version_key, ha_details
                )

                if downloaded:
                    logging.info(
                        f"{get_emoji(action='success')} {hostname}: Base image {base_version_key} downloaded successfully"
                    )
                    logging.info(
                        f"{get_emoji(action='success')} {hostname}: Pausing for {wait_time} seconds to let {base_version_key} image load into the software manager before downloading {version}"
                    )

                    # Wait before retrying to ensure the device has processed the downloaded base image
                    time.sleep(wait_time)

                    # Re-check the versions after waiting
                    target_device.software.check()
                    if version in target_device.software.versions:
                        # Proceed with the target version check again
                        return software_update_check(
                            ha_details=ha_details,
                            hostname=hostname,
                            settings_file=settings_file,
                            settings_file_path=settings_file_path,
                            target_device=target_device,
                            version=version,
                        )

                    else:
                        logging.info(
                            f"{get_emoji(action='report')} {hostname}: Waiting for device to load the new base image into software manager"
                        )
                        # Retry if the version is still not recognized
                        continue
                else:
                    if attempt < retry_count - 1:
                        logging.error(
                            f"{get_emoji(action='error')} {hostname}: Failed to download base image for version {version}. Retrying in {wait_time} seconds."
                        )
                        time.sleep(wait_time)
                    else:
                        logging.error(
                            f"{get_emoji(action='error')} {hostname}: Failed to download base image after {retry_count} attempts."
                        )
                        return False

    else:
        # If the version is not available, find and log close matches
        close_matches = find_close_matches(list(available_versions.keys()), version)
        close_matches_str = ", ".join(close_matches)
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Version {version} is not available for download. Closest matches: {close_matches_str}"
        )
        return False


def upgrade_firewall(
    dry_run: bool,
    firewall: Firewall,
    settings_file: LazySettings,
    settings_file_path: Path,
    target_version: str,
    target_devices_to_revisit: list = None,
    target_devices_to_revisit_lock: Lock = None,
) -> None:
    """
    Orchestrates the upgrade process for a specified Palo Alto Networks firewall to a target version. This function
    incorporates various steps including readiness checks, software download, upgrade execution, and system reboot,
    with special considerations for High Availability (HA) setups. It supports a dry-run option for process validation
    without applying changes.

    The function verifies the success of the software installation before proceeding with the reboot step. If the installation
    fails, the process halts, preventing unnecessary reboots and ensuring system stability.

    Parameters
    ----------
    dry_run : bool
        If True, simulates the upgrade process without making actual changes to the device.
    firewall : Firewall
        The Firewall object representing the device to be upgraded.
    settings_file : LazySettings
        Settings loaded from the 'settings.yaml' file for configuring the upgrade process.
    settings_file_path : Path
        The path to the 'settings.yaml' file.
    target_version : str
        The target PAN-OS version to upgrade the firewall to.
    target_devices_to_revisit : list, optional
        A list to append devices that need to be revisited, typically used in HA scenarios.
    target_devices_to_revisit_lock : Lock, optional
        A threading lock to synchronize access to the 'target_devices_to_revisit' list in multi-threaded environments.

    Raises
    ------
    SystemExit
        If a critical failure occurs during the upgrade process, the function will terminate the script.

    Examples
    --------
    To upgrade a firewall to version '10.1.0':
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> upgrade_firewall(False, firewall_instance, settings_file, Path('/path/to/settings.yaml'), '10.1.0')

    To perform a dry run of the upgrade process:
        >>> upgrade_firewall(True, firewall_instance, settings_file, Path('/path/to/settings.yaml'), '10.1.0')

    Notes
    -----
    - It's recommended to perform a dry run before the actual upgrade to validate the process.
    - The function ensures that the device is ready for the upgrade through a series of pre-upgrade checks.
    - In HA configurations, the upgrade process is coordinated between the HA peers to maintain synchronization.

    Workflow
    --------
    1. Perform pre-upgrade checks and readiness assessments.
    2. Download the target software version if it's not already present on the device.
    3. Attempt the software installation with a defined number of retries for transient errors.
    4. Verify the success of the software installation before proceeding.
    5. If the installation is successful and not in dry-run mode, reboot the device to complete the upgrade.
    6. After reboot, perform post-upgrade validations including configuration backup and system health checks.
    """

    # Refresh system information to ensure we have the latest data
    logging.debug(f"{get_emoji(action='start')} Refreshing system information.")
    firewall_details = SystemSettings.refreshall(firewall)[0]
    hostname = firewall_details.hostname
    logging.info(
        f"{get_emoji(action='report')} {hostname}: {firewall.serial} {firewall_details.ip_address}"
    )

    # Determine if the firewall is standalone, HA, or in a cluster
    logging.debug(
        f"{get_emoji(action='start')} {hostname}: Performing test to see if firewall is standalone, HA, or in a cluster."
    )
    deploy_info, ha_details = get_ha_status(
        hostname=hostname,
        target_device=firewall,
    )
    logging.info(f"{get_emoji(action='report')} {hostname}: HA mode: {deploy_info}")
    logging.debug(f"{get_emoji(action='report')} {hostname}: HA details: {ha_details}")

    # If firewall is part of HA pair, determine if it's active or passive
    if ha_details:
        proceed_with_upgrade, peer_firewall = handle_firewall_ha(
            dry_run=dry_run,
            hostname=hostname,
            settings_file=settings_file,
            settings_file_path=settings_file_path,
            target_device=firewall,
            target_devices_to_revisit=target_devices_to_revisit,
            target_devices_to_revisit_lock=target_devices_to_revisit_lock,
        )

        # gracefully exit the upgrade_firewall function if the firewall is not ready for an upgrade to target version
        if not proceed_with_upgrade:
            if peer_firewall:
                logging.info(
                    f"{get_emoji(action='start')} {hostname}: Switching control to the peer firewall for upgrade."
                )
                upgrade_firewall(peer_firewall, target_version, dry_run)
            else:
                return  # Exit the function without proceeding to upgrade

    # Check to see if the firewall is ready for an upgrade
    logging.debug(
        f"{get_emoji(action='start')} {hostname}: Checking to see if a PAN-OS upgrade is available."
    )
    update_available = software_update_check(
        ha_details=ha_details,
        hostname=hostname,
        settings_file=settings_file,
        settings_file_path=settings_file_path,
        target_device=firewall,
        version=target_version,
    )

    # gracefully exit if the firewall is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Not ready for upgrade to {target_version}.",
        )
        sys.exit(1)

    # Download the target version
    logging.info(
        f"{get_emoji(action='start')} {hostname}: Performing test to see if {target_version} is already downloaded."
    )
    image_downloaded = software_download(
        firewall,
        hostname,
        target_version,
        ha_details,
    )
    if deploy_info == "active" or deploy_info == "passive":
        logging.info(
            f"{get_emoji(action='success')} {hostname}: {target_version} has been downloaded and sync'd to HA peer."
        )
    else:
        logging.info(
            f"{get_emoji(action='success')} {hostname}: version {target_version} has been downloaded."
        )

    # Begin snapshots of the network state
    if not image_downloaded:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Image not downloaded, exiting."
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
        actions=selected_actions,
        file_path=f'assurance/snapshots/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
        firewall=firewall,
        hostname=hostname,
        settings_file_path=settings_file_path,
    )

    # Perform Readiness Checks
    perform_readiness_checks(
        file_path=f'assurance/readiness_checks/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
        firewall=firewall,
        hostname=hostname,
        settings_file_path=settings_file_path,
    )

    # Perform HA sync check, skipping standalone firewalls
    if ha_details:
        ha_sync_check_firewall(
            ha_details=ha_details,
            hostname=hostname,
        )

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji(action='start')} {hostname}: Performing backup of configuration to local filesystem."
    )
    backup_config = backup_configuration(
        file_path=f'assurance/configurations/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
        hostname=hostname,
        target_device=firewall,
    )
    logging.debug(f"{get_emoji(action='report')} {hostname}: {backup_config}")

    # Exit execution is dry_run is True
    if dry_run is True:
        logging.info(
            f"{get_emoji(action='success')} {hostname}: Dry run complete, exiting."
        )
        logging.info(f"{get_emoji(action='stop')} {hostname}: Halting script.")
        sys.exit(0)
    else:
        logging.info(
            f"{get_emoji(action='report')} {hostname}: Not a dry run, continue with upgrade."
        )

    # Perform the upgrade
    install_success = perform_upgrade(
        hostname=hostname,
        settings_file=settings_file,
        settings_file_path=settings_file_path,
        target_device=firewall,
        target_version=target_version,
    )

    # Perform the reboot if the installation was successful
    if install_success:
        perform_reboot(
            hostname=hostname,
            settings_file=settings_file,
            settings_file_path=settings_file_path,
            target_device=firewall,
            target_version=target_version,
        )

        # Back up configuration to local filesystem
        logging.info(
            f"{get_emoji(action='start')} {hostname}: Performing backup of configuration to local filesystem."
        )
        backup_config = backup_configuration(
            file_path=f'assurance/configurations/{hostname}/post/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
            hostname=hostname,
            target_device=firewall,
        )
        logging.debug(f"{get_emoji(action='report')} {hostname}: {backup_config}")

        # Wait for the device to become ready for the post upgrade snapshot
        logging.info(
            f"{get_emoji(action='working')} {hostname}: Waiting for the device to become ready for the post upgrade snapshot."
        )
        time.sleep(120)

        # Load settings if the file exists
        if settings_file_path.exists():
            with open(settings_file_path, "r") as file:
                settings = yaml.safe_load(file)

            # Check if snapshots are disabled in the settings
            if settings.get("snapshots", {}).get("disabled", False):
                logging.info(
                    f"{get_emoji(action='skipped')} {hostname}: Snapshots are disabled in the settings. Skipping snapshot for {hostname}."
                )
                # Early return, no snapshot performed
                return None

        # Perform the post-upgrade snapshot
        post_snapshot = perform_snapshot(
            actions=selected_actions,
            file_path=f'assurance/snapshots/{hostname}/post/{time.strftime("%Y-%m-%d_%H-%M-%S")}.json',
            firewall=firewall,
            hostname=hostname,
            settings_file_path=settings_file_path,
        )

        # initialize object storing both snapshots
        snapshot_compare = SnapshotCompare(
            left_snapshot=pre_snapshot.model_dump(),
            right_snapshot=post_snapshot.model_dump(),
        )

        pre_post_diff = snapshot_compare.compare_snapshots(selected_actions)

        logging.debug(
            f"{get_emoji(action='report')} {hostname}: Snapshot comparison before and after upgrade {pre_post_diff}"
        )

        folder_path = f"assurance/snapshots/{hostname}/diff"
        pdf_report = f'{folder_path}/{time.strftime("%Y-%m-%d_%H-%M-%S")}_report.pdf'
        ensure_directory_exists(file_path=pdf_report)

        # Generate the PDF report for the diff
        generate_diff_report_pdf(
            file_path=pdf_report,
            hostname=hostname,
            pre_post_diff=pre_post_diff,
            target_version=target_version,
        )

        logging.info(
            f"{get_emoji(action='save')} {hostname}: Snapshot comparison PDF report saved to {pdf_report}"
        )

        json_report = f'{folder_path}/{time.strftime("%Y-%m-%d_%H-%M-%S")}_report.json'

        # Write the file to the local filesystem as JSON
        with open(json_report, "w") as file:
            file.write(json.dumps(pre_post_diff))

        logging.debug(
            f"{get_emoji(action='save')} {hostname}: Snapshot comparison JSON report saved to {json_report}"
        )

    else:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Installation of the target version was not successful. Skipping reboot."
        )


def upgrade_panorama(
    dry_run: bool,
    panorama: Panorama,
    settings_file: LazySettings,
    settings_file_path: Path,
    target_devices_to_revisit: list,
    target_devices_to_revisit_lock: Lock,
    target_version: str,
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
    logging.debug(f"{get_emoji(action='start')} Refreshing system information.")
    panorama_details = SystemSettings.refreshall(panorama)[0]
    hostname = panorama_details.hostname
    logging.info(
        f"{get_emoji(action='report')} {hostname}: {panorama.serial} {panorama_details.ip_address}"
    )

    # Check Panorama license before proceeding with the upgrade
    logging.info(f"{get_emoji(action='start')} {hostname}: Checking Panorama license.")
    if not check_panorama_license(panorama):
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Panorama does not have an active license. Cannot proceed with the upgrade."
        )
        sys.exit(1)
    else:
        logging.info(
            f"{get_emoji(action='success')} {hostname}: Panorama license is valid."
        )

    # Determine if the Panorama is standalone, HA, or in a cluster
    logging.debug(
        f"{get_emoji(action='start')} {hostname}: Performing test to see if Panorama is standalone, HA, or in a cluster."
    )
    deploy_info, ha_details = get_ha_status(
        hostname=hostname,
        target_device=panorama,
    )
    logging.info(f"{get_emoji(action='report')} {hostname}: HA mode: {deploy_info}")
    logging.debug(f"{get_emoji(action='report')} {hostname}: HA details: {ha_details}")

    # If Panorama is part of HA pair, determine if it's active or passive
    if ha_details:
        proceed_with_upgrade, peer_panorama = handle_panorama_ha(
            dry_run=dry_run,
            hostname=hostname,
            settings_file=settings_file,
            settings_file_path=settings_file_path,
            target_device=panorama,
            target_devices_to_revisit=target_devices_to_revisit,
            target_devices_to_revisit_lock=target_devices_to_revisit_lock,
        )

        if not proceed_with_upgrade:
            if peer_panorama:
                logging.info(
                    f"{get_emoji(action='start')} {hostname}: Switching control to the peer Panorama for upgrade."
                )
                upgrade_panorama(
                    dry_run=dry_run,
                    panorama=peer_panorama,
                    target_version=target_version,
                )
            else:
                # Exit the function without proceeding to upgrade
                return

    # Check to see if the Panorama is ready for an upgrade
    logging.debug(
        f"{get_emoji(action='start')} {hostname}: Performing tests to validate Panorama's readiness."
    )
    update_available = software_update_check(
        ha_details=ha_details,
        hostname=hostname,
        settings_file=settings_file,
        settings_file_path=settings_file_path,
        target_device=panorama,
        version=target_version,
    )

    # gracefully exit if the Panorama is not ready for an upgrade to target version
    if not update_available:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Not ready for upgrade to {target_version}.",
        )
        sys.exit(1)

    # Download the target version
    logging.info(
        f"{get_emoji(action='start')} {hostname}: Performing test to see if {target_version} is already downloaded."
    )
    image_downloaded = software_download(
        panorama,
        hostname,
        target_version,
        ha_details,
    )
    if deploy_info == "primary-active" or deploy_info == "secondary-passive":
        logging.info(
            f"{get_emoji(action='success')} {hostname}: {target_version} has been downloaded and sync'd to HA peer."
        )
    else:
        logging.info(
            f"{get_emoji(action='success')} {hostname}: Panorama version {target_version} has been downloaded."
        )

    # Begin snapshots of the network state
    if not image_downloaded:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Image not downloaded, exiting."
        )

        sys.exit(1)

    # Determine strictness of HA sync check
    with target_devices_to_revisit_lock:
        is_panorama_to_revisit = panorama in target_devices_to_revisit

    # Print out list of Panorama appliances to revisit
    logging.debug(
        f"{get_emoji(action='report')} Panorama appliances to revisit: {target_devices_to_revisit}"
    )
    logging.debug(
        f"{get_emoji(action='report')} {hostname}: Is Panorama to revisit: {is_panorama_to_revisit}"
    )

    # Perform HA sync check, skipping standalone Panoramas
    if ha_details:
        ha_sync_check_panorama(
            ha_details=ha_details,
            hostname=hostname,
            strict_sync_check=False,
            # strict_sync_check=not is_panorama_to_revisit,
        )

    # Back up configuration to local filesystem
    logging.info(
        f"{get_emoji(action='start')} {hostname}: Performing backup of configuration to local filesystem."
    )
    backup_config = backup_configuration(
        file_path=f'assurance/configurations/{hostname}/pre/{time.strftime("%Y-%m-%d_%H-%M-%S")}.xml',
        hostname=hostname,
        target_device=panorama,
    )
    logging.debug(f"{get_emoji(action='report')} {hostname}: {backup_config}")

    # Exit execution is dry_run is True
    if dry_run is True:
        logging.info(
            f"{get_emoji(action='success')} {hostname}: Dry run complete, exiting."
        )
        logging.info(f"{get_emoji(action='stop')} {hostname}: Halting script.")
        sys.exit(0)
    else:
        logging.info(
            f"{get_emoji(action='start')} {hostname}: Not a dry run, continue with upgrade."
        )

    # Perform the upgrade
    perform_upgrade(
        hostname=hostname,
        settings_file=settings_file,
        settings_file_path=settings_file_path,
        target_device=panorama,
        target_version=target_version,
    )

    # Perform the reboot
    perform_reboot(
        hostname=hostname,
        settings_file=settings_file,
        settings_file_path=settings_file_path,
        target_device=panorama,
        target_version=target_version,
    )
