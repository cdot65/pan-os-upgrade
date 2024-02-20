import logging
import sys
import time
from threading import Lock
from typing import Optional, Tuple, Union
from panos.firewall import Firewall
from panos.panorama import Panorama

from dynaconf import LazySettings
from pathlib import Path
from pan_os_upgrade.components.device import get_ha_status
from pan_os_upgrade.components.utilities import (
    compare_versions,
    get_emoji,
)


def ha_sync_check_firewall(
    ha_details: dict,
    hostname: str,
    strict_sync_check: bool = False,
) -> bool:
    """
    Checks the synchronization status between High Availability (HA) peers of a Palo Alto Networks device.

    Ensuring HA peers are synchronized is vital before executing operations that might impact the device's state,
    such as firmware upgrades or configuration changes. This function evaluates the HA synchronization status using
    provided HA details. It offers an option to enforce a strict synchronization check, where failure to sync
    results in script termination, ensuring operations proceed only in a fully synchronized HA environment.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target device, used for logging purposes to identify the device under evaluation.
    ha_details : dict
        A dictionary containing HA information for the device, specifically the synchronization status with its HA peer.
    strict_sync_check : bool, optional
        If True (default), the function will exit the script upon detecting unsynchronized HA peers to prevent potential
        disruptions. If False, the script logs a warning but continues execution, suitable for less critical operations.

    Returns
    -------
    bool
        Returns True if the HA peers are confirmed to be synchronized, indicating readiness for sensitive operations.
        Returns False if the HA peers are not synchronized, with subsequent actions dependent on the `strict_sync_check` parameter.

    Raises
    ------
    SystemExit
        Triggered if `strict_sync_check` is True and the HA peers are found to be unsynchronized, halting the script to avoid
        potential issues in an unsynchronized HA environment.

    Example
    -------
    >>> ha_details = {'result': {'group': {'running-sync': 'synchronized'}}}
    >>> ha_sync_check_firewall('firewall1', ha_details)
    True  # Indicates that the HA peers are synchronized

    >>> ha_sync_check_firewall('firewall1', ha_details, strict_sync_check=False)
    False  # HA peers are unsynchronized, but script continues due to lenient check

    Notes
    -----
    - In HA configurations, maintaining synchronization between peers is critical to ensure consistent state and behavior
    across devices.
    - This function is particularly useful in automated workflows and scripts where actions need to be conditional on the
    synchronization state of HA peers to maintain system integrity and prevent split-brain scenarios.
    - The option to override strict synchronization checks allows for flexibility in operations where immediate consistency
    between HA peers may not be as critical.
    """

    logging.info(
        f"{get_emoji(action='start')} {hostname}: Checking if HA peer is in sync."
    )
    if ha_details and ha_details["result"]["group"]["running-sync"] == "synchronized":
        logging.info(
            f"{get_emoji(action='success')} {hostname}: HA peer sync test has been completed."
        )
        return True
    else:
        if strict_sync_check:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: HA peer state is not in sync, please try again."
            )
            logging.error(f"{get_emoji(action='stop')} {hostname}: Halting script.")
            sys.exit(1)
        else:
            logging.warning(
                f"{get_emoji(action='warning')} {hostname}: HA peer state is not in sync. This will be noted, but the script will continue."
            )
            return False


def ha_sync_check_panorama(
    ha_details: dict,
    hostname: str,
    strict_sync_check: bool = False,
) -> bool:
    """
    Checks the synchronization status between High Availability (HA) peers of a Palo Alto Networks device.

    Ensuring HA peers are synchronized is vital before executing operations that might impact the device's state,
    such as firmware upgrades or configuration changes. This function evaluates the HA synchronization status using
    provided HA details. It offers an option to enforce a strict synchronization check, where failure to sync
    results in script termination, ensuring operations proceed only in a fully synchronized HA environment.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the target device, used for logging purposes to identify the device under evaluation.
    ha_details : dict
        A dictionary containing HA information for the device, specifically the synchronization status with its HA peer.
    strict_sync_check : bool, optional
        If True (default), the function will exit the script upon detecting unsynchronized HA peers to prevent potential
        disruptions. If False, the script logs a warning but continues execution, suitable for less critical operations.

    Returns
    -------
    bool
        Returns True if the HA peers are confirmed to be synchronized, indicating readiness for sensitive operations.
        Returns False if the HA peers are not synchronized, with subsequent actions dependent on the `strict_sync_check` parameter.

    Raises
    ------
    SystemExit
        Triggered if `strict_sync_check` is True and the HA peers are found to be unsynchronized, halting the script to avoid
        potential issues in an unsynchronized HA environment.

    Example
    -------
    >>> ha_details = {'result': {'group': {'running-sync': 'synchronized'}}}
    >>> ha_sync_check_firewall('firewall1', ha_details)
    True  # Indicates that the HA peers are synchronized

    >>> ha_sync_check_firewall('firewall1', ha_details, strict_sync_check=False)
    False  # HA peers are unsynchronized, but script continues due to lenient check

    Notes
    -----
    - In HA configurations, maintaining synchronization between peers is critical to ensure consistent state and behavior
    across devices.
    - This function is particularly useful in automated workflows and scripts where actions need to be conditional on the
    synchronization state of HA peers to maintain system integrity and prevent split-brain scenarios.
    - The option to override strict synchronization checks allows for flexibility in operations where immediate consistency
    between HA peers may not be as critical.
    """

    logging.info(
        f"{get_emoji(action='start')} {hostname}: Checking if HA peer is in sync."
    )
    if ha_details and ha_details["result"]["running-sync"] == "synchronized":
        logging.info(
            f"{get_emoji(action='success')} {hostname}: HA peer sync test has been completed."
        )
        return True
    else:
        if strict_sync_check:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: HA peer state is not in sync, please try again."
            )
            logging.error(f"{get_emoji(action='stop')} {hostname}: Halting script.")
            sys.exit(1)
        else:
            logging.warning(
                f"{get_emoji(action='warning')} {hostname}: HA peer state is not in sync. This will be noted, but the script will continue."
            )
            return False


def handle_firewall_ha(
    dry_run: bool,
    hostname: str,
    settings_file: LazySettings,
    settings_file_path: Path,
    target_device: Firewall,
    target_devices_to_revisit,
    target_devices_to_revisit_lock,
) -> Tuple[bool, Optional[Firewall]]:
    """
    Determines and handles High Availability (HA) logic for the target device during the upgrade process.

    This function assesses the HA configuration of the specified target device to decide the appropriate course of action for
    the upgrade. It considers the device's role in an HA setup (active, passive, or standalone) and uses the 'dry_run' flag to
    determine whether to simulate or execute the upgrade. Based on the device's HA status and synchronization state with its
    HA peer, the function guides whether to proceed with the upgrade and performs HA-specific preparations if necessary.

    Parameters
    ----------
    target_device: Firewall
        The device being evaluated for upgrade. It must be an instance of Firewall and might be part of
        an HA configuration.
    hostname : str
        The hostname or IP address of the target device for identification and logging purposes.
    dry_run : bool
        A flag indicating whether to simulate the upgrade process (True) without making actual changes or to proceed with
        the upgrade (False).

    Returns
    -------
    Tuple[bool, Optional[Firewall]]
        A tuple where the first element is a boolean indicating whether the upgrade process should continue, and the second
        element is an optional device instance representing the HA peer if relevant and applicable.

    Example
    -------
    >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
    >>> proceed, ha_peer = handle_firewall_ha(firewall, '192.168.1.1', dry_run=False)
    >>> print(proceed)  # Indicates whether the upgrade should continue
    >>> if ha_peer:
    ...     print(ha_peer)  # The HA peer device instance if applicable

    Notes
    -----
    - This function is crucial for managing the upgrade process in HA environments to ensure consistency and minimize
    downtime.
    - It incorporates checks for synchronization states and versions between HA peers, ensuring upgrades are conducted
    safely and effectively.
    - The 'dry_run' option allows administrators to validate the upgrade logic without impacting the actual device
    configuration or operation.
    - Settings such as retry counts and intervals for HA synchronization checks can be customized via the 'settings.yaml'
    file, providing flexibility for different network environments and requirements.
    """

    deploy_info, ha_details = get_ha_status(
        hostname=hostname,
        target_device=target_device,
    )

    # If the target device is not part of an HA configuration, proceed with the upgrade
    if not ha_details:
        return True, None

    logging.debug(
        f"{get_emoji(action='report')} {hostname}: Deployment info: {deploy_info}"
    )
    logging.debug(f"{get_emoji(action='report')} {hostname}: HA details: {ha_details}")

    local_state = ha_details["result"]["group"]["local-info"]["state"]
    local_version = ha_details["result"]["group"]["local-info"]["build-rel"]
    peer_version = ha_details["result"]["group"]["peer-info"]["build-rel"]

    logging.info(
        f"{get_emoji(action='report')} {hostname}: Local state: {local_state}, Local version: {local_version}, Peer version: {peer_version}"
    )

    # Check if the firewall is in the revisit list
    with target_devices_to_revisit_lock:
        is_device_to_revisit = target_device in target_devices_to_revisit

    if is_device_to_revisit:
        # Initialize with default values
        max_retries = 3
        retry_interval = 60

        # Override if settings.yaml exists and contains these settings
        if settings_file_path.exists():
            max_retries = settings_file.get("ha_sync.max_tries", max_retries)
            retry_interval = settings_file.get("ha_sync.retry_interval", retry_interval)

        for attempt in range(max_retries):
            logging.info(
                f"Waiting for HA synchronization to complete on {hostname}. Attempt {attempt + 1}/{max_retries}"
            )
            # Wait for HA synchronization
            time.sleep(retry_interval)

            # Re-fetch the HA status to get the latest state
            deploy_info, ha_details = get_ha_status(
                hostname=hostname,
                target_device=target_device,
            )
            local_version = ha_details["result"]["group"]["local-info"]["build-rel"]
            peer_version = ha_details["result"]["group"]["peer-info"]["build-rel"]

            if peer_version != local_version:
                logging.info(
                    f"HA synchronization complete on {hostname}. Proceeding with upgrade."
                )
                break
            else:
                logging.info(
                    f"HA synchronization still in progress on {hostname}. Rechecking after wait period."
                )

    version_comparison = compare_versions(
        version1=local_version,
        version2=peer_version,
    )
    logging.info(
        f"{get_emoji(action='report')} {hostname}: Version comparison: {version_comparison}"
    )

    # If the active and passive target devices are running the same version
    if version_comparison == "equal":
        if local_state == "active":
            # Add the active target device to the list and exit the upgrade process
            with target_devices_to_revisit_lock:
                target_devices_to_revisit.append(target_device)
            logging.info(
                f"{get_emoji(action='search')} {hostname}: Detected active target device in HA pair running the same version as its peer. Added target device to revisit list."
            )
            return False, None

        elif local_state == "passive":
            # Continue with upgrade process on the passive target device
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Target device is passive",
            )
            return True, None

        elif local_state == "initial":
            # Continue with upgrade process on the initial target device
            logging.info(
                f"{get_emoji(action='warning')} {hostname}: Target device is in initial HA state",
            )
            return True, None

    elif version_comparison == "older":
        logging.info(
            f"{get_emoji(action='report')} {hostname}: Target device is on an older version"
        )
        # Suspend HA state of active if the passive is on a later release
        if local_state == "active" and not dry_run:
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Suspending HA state of active"
            )
            suspend_ha_active(
                target_device,
                hostname,
            )
        return True, None

    elif version_comparison == "newer":
        logging.info(
            f"{get_emoji(action='report')} {hostname}: Target device is on a newer version"
        )
        # Suspend HA state of passive if the active is on a later release
        if local_state == "passive" and not dry_run:
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Suspending HA state of passive"
            )
            suspend_ha_passive(
                target_device,
                hostname,
            )
        return True, None

    return False, None


def handle_panorama_ha(
    dry_run: bool,
    hostname: str,
    settings_file: LazySettings,
    settings_file_path: Path,
    target_device: Panorama,
    target_devices_to_revisit: list,
    target_devices_to_revisit_lock: Lock,
) -> Tuple[bool, Optional[Panorama]]:
    """
    Determines and handles High Availability (HA) logic for the Panorama device during the upgrade process.

    This function assesses the HA configuration of the specified Panorama device to decide the appropriate course of action for
    the upgrade. It considers the device's role in an HA setup (primary-active, secondary-passive) and uses the 'dry_run' flag to
    determine whether to simulate or execute the upgrade. Based on the device's HA status and synchronization state with its
    HA peer, the function guides whether to proceed with the upgrade and performs HA-specific preparations if necessary.

    Parameters
    ----------
    target_device: Panorama
        The device being evaluated for upgrade. It must be an instance of Panorama and might be part of
        an HA configuration.
    hostname : str
        The hostname or IP address of the target device for identification and logging purposes.
    dry_run : bool
        A flag indicating whether to simulate the upgrade process (True) without making actual changes or to proceed with
        the upgrade (False).

    Returns
    -------
    Tuple[bool, Optional[Panorama]]
        A tuple where the first element is a boolean indicating whether the upgrade process should continue, and the second
        element is an optional device instance representing the HA peer if relevant and applicable.

    Example
    -------
    >>> panorama = Panorama(hostname='192.168.1.1', api_username='admin', api_password='admin')
    >>> proceed, ha_peer = handle_panorama_ha(firewall, '192.168.1.1', dry_run=False)
    >>> print(proceed)  # Indicates whether the upgrade should continue
    >>> if ha_peer:
    ...     print(ha_peer)  # The HA peer device instance if applicable

    Notes
    -----
    - This function is crucial for managing the upgrade process in HA environments to ensure consistency and minimize
    downtime.
    - It incorporates checks for synchronization states and versions between HA peers, ensuring upgrades are conducted
    safely and effectively.
    - The 'dry_run' option allows administrators to validate the upgrade logic without impacting the actual device
    configuration or operation.
    - Settings such as retry counts and intervals for HA synchronization checks can be customized via the 'settings.yaml'
    file, providing flexibility for different network environments and requirements.
    """

    deploy_info, ha_details = get_ha_status(
        hostname=hostname,
        target_device=target_device,
    )

    # If the target device is not part of an HA configuration, proceed with the upgrade
    if not ha_details:
        return True, None

    logging.debug(
        f"{get_emoji(action='report')} {hostname}: Deployment info: {deploy_info}"
    )
    logging.debug(f"{get_emoji(action='report')} {hostname}: HA details: {ha_details}")

    local_state = ha_details["result"]["local-info"]["state"]
    local_version = ha_details["result"]["local-info"]["build-rel"]
    # peer_state = ha_details["result"]["peer-info"]["state"]
    peer_version = ha_details["result"]["peer-info"]["build-rel"]

    logging.info(
        f"{get_emoji(action='report')} {hostname}: Local state: {local_state}, Local version: {local_version}, Peer version: {peer_version}"
    )

    # Check if the firewall is in the revisit list
    with target_devices_to_revisit_lock:
        is_device_to_revisit = target_device in target_devices_to_revisit

    if is_device_to_revisit:
        # Initialize with default values
        max_retries = 3
        retry_interval = 60

        # Override if settings.yaml exists and contains these settings
        if settings_file_path.exists():
            max_retries = settings_file.get("ha_sync.max_tries", max_retries)
            retry_interval = settings_file.get("ha_sync.retry_interval", retry_interval)

        for attempt in range(max_retries):
            logging.info(
                f"Waiting for HA synchronization to complete on {hostname}. Attempt {attempt + 1}/{max_retries}"
            )
            # Wait for HA synchronization
            time.sleep(retry_interval)

            # Re-fetch the HA status to get the latest state
            deploy_info, ha_details = get_ha_status(
                hostname=hostname,
                target_device=target_device,
            )
            local_version = ha_details["result"]["local-info"]["build-rel"]
            peer_version = ha_details["result"]["peer-info"]["build-rel"]

            if peer_version != local_version:
                logging.info(
                    f"HA synchronization complete on {hostname}. Proceeding with upgrade."
                )
                break
            else:
                logging.info(
                    f"HA synchronization still in progress on {hostname}. Rechecking after wait period."
                )

    version_comparison = compare_versions(
        version1=local_version,
        version2=peer_version,
    )
    logging.info(
        f"{get_emoji(action='report')} {hostname}: Version comparison: {version_comparison}"
    )

    # If the active and passive target devices are running the same version
    if version_comparison == "equal":
        if local_state == "primary-active":
            # Add the active target device to the list and exit the upgrade process
            with target_devices_to_revisit_lock:
                target_devices_to_revisit.append(target_device)
            logging.info(
                f"{get_emoji(action='search')} {hostname}: Detected primary-active target device in HA pair running the same version as its peer. Added target device to revisit list."
            )
            return False, None

        elif local_state == "secondary-passive":
            # Continue with upgrade process on the secondary-passive target device
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Target device is secondary-passive",
            )
            return True, None

        elif (
            local_state == "secondary-suspended"
            or local_state == "secondary-non-functional"
        ):
            # Continue with upgrade process on the secondary-suspended or secondary-non-functional target device
            logging.info(
                f"{get_emoji(action='warning')} {hostname}: Target device is {local_state}",
            )
            return True, None

    elif version_comparison == "older":
        logging.info(
            f"{get_emoji(action='report')} {hostname}: Target device is on an older version"
        )
        # Suspend HA state of active if the primary-active is on a later release
        if local_state == "primary-active" and not dry_run:
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Suspending HA state of primary-active"
            )
            suspend_ha_active(
                target_device,
                hostname,
            )
        return True, None

    elif version_comparison == "newer":
        logging.info(
            f"{get_emoji(action='report')} {hostname}: Target device is on a newer version"
        )
        # Suspend HA state of secondary-passive if the primary-active is on a later release
        if local_state == "primary-active" and not dry_run:
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Suspending HA state of primary-active"
            )
            suspend_ha_passive(
                target_device,
                hostname,
            )
        return True, None

    return False, None


def suspend_ha_active(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> bool:
    """
    Temporarily disables High Availability (HA) functionality on an active device within an HA configuration.

    In an HA setup, it may be necessary to suspend HA functionality on the active device to perform system upgrades or maintenance tasks without triggering failover to the passive device. This function sends an operational command to the target device to suspend HA, ensuring that the device remains in an active but non-failover state. It checks the command's success through the device's response and provides appropriate logging for the operation's outcome.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device on which HA functionality is to be suspended. This must be an active device in an HA pair and can be either a Firewall or a Panorama appliance.
    hostname : str
        The hostname or IP address of the target device. This is used primarily for identification and logging purposes.

    Returns
    -------
    bool
        True if the command to suspend HA is successfully issued and acknowledged by the target device, indicating that HA functionality has been suspended. False if the command fails or the device response indicates an error.

    Raises
    ------
    Exception
        If the operational command to suspend HA fails or an unexpected response is received from the device, an exception is raised detailing the error encountered.

    Example
    -------
    Suspending HA functionality on an active device in an HA pair:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> success = suspend_ha_active(firewall, '192.168.1.1')
        >>> if success:
        ...     print("HA suspension successful.")
        ... else:
        ...     print("HA suspension failed.")

    Notes
    -----
    - Suspending HA on the active device is a significant operation that should be performed with caution, particularly in a production environment, to avoid unintended service disruptions.
    - Ensure that the procedure for resuming HA functionality is planned and understood before suspending HA, as this will be necessary to restore full HA operational capabilities.
    """

    try:
        suspension_response = target_device.op(
            "<request><high-availability><state><suspend/></state></high-availability></request>",
            cmd_xml=False,
        )
        if "success" in suspension_response.text:
            logging.info(
                f"{get_emoji(action='success')} {hostname}: Active target device HA state suspended."
            )
            return True
        else:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: Failed to suspend active target device HA state."
            )
            return False
    except Exception as e:
        logging.warning(
            f"{get_emoji(action='warning')} {hostname}: Error received when suspending active target device HA state: {e}"
        )
        return False


def suspend_ha_passive(
    target_device: Union[Firewall, Panorama],
    hostname: str,
) -> bool:
    """
    Temporarily disables High Availability (HA) functionality on the passive device within an HA pair.

    In an HA environment, it may become necessary to suspend HA functionality on the passive device to facilitate system upgrades or maintenance, ensuring the device does not unexpectedly become active. This function issues a command to the target device to suspend its HA functionality. The success of this operation is determined by the response from the device, and the outcome is logged for administrative review.

    Parameters
    ----------
    target_device : Union[Firewall, Panorama]
        The device on which HA functionality is to be suspended. This must be a passive device in an HA pair and can be either a Firewall or a Panorama appliance.
    hostname : str
        The hostname or IP address of the device. Used for identification and logging.

    Returns
    -------
    bool
        True if the HA suspension command is successfully executed, indicating that HA functionality on the passive device has been temporarily disabled. False if the command execution fails or if the device response indicates an error.

    Raises
    ------
    Exception
        If the operational command to suspend HA fails or an unexpected response is received, an exception is logged detailing the encountered issue.

    Example
    -------
    Suspending HA on the passive device in an HA configuration:
        >>> panorama = Panorama(hostname='panorama.example.com', api_username='admin', api_password='admin')
        >>> success = suspend_ha_passive(panorama, 'panorama.example.com')
        >>> print("HA suspension successful" if success else "HA suspension failed")

    Notes
    -----
    - Suspending HA on a passive device is a critical operation that should be carefully planned and executed, particularly in live environments, to avoid unintended failovers or service disruptions.
    - Coordination with network management and understanding the process to resume HA functionality are essential to ensure the continuity of services and network redundancy.
    """

    try:
        suspension_response = target_device.op(
            "<request><high-availability><state><suspend/></state></high-availability></request>",
            cmd_xml=False,
        )
        if "success" in suspension_response.text:
            logging.info(
                f"{get_emoji(action='success')} {hostname}: Passive target device HA state suspended."
            )
            return True
        else:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: Failed to suspend passive target device HA state."
            )
            return False
    except Exception as e:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Error suspending passive target device HA state: {e}"
        )
        return False
