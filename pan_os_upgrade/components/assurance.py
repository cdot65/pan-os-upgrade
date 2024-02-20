import importlib.resources as pkg_resources
import logging
import sys
import time
import yaml
from pathlib import Path
from typing import List, Optional, Union

from panos.firewall import Firewall
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Line

from pan_os_upgrade.models import (
    SnapshotReport,
    ReadinessCheckReport,
)
from pan_os_upgrade.components.utilities import (
    ensure_directory_exists,
    get_emoji,
)


# Define panos-upgrade-assurance options
class AssuranceOptions:
    """
    Centralizes configuration options for readiness checks, reports, and state snapshots in the upgrade assurance process.

    This class provides a structured approach to define and access various configuration options related to the upgrade
    assurance process for Palo Alto Networks devices. It outlines available readiness checks, types of reports, and
    categories of state snapshots that can be utilized during the device upgrade process. These configurations are
    designed to be flexible, allowing customization through an external `settings.yaml` file to cater to specific
    operational needs and preferences.

    Attributes
    ----------
    READINESS_CHECKS : dict
        A dictionary mapping the names of readiness checks to their attributes, which include descriptions, associated
        log levels, and flags to indicate whether to exit the process upon check failure. These checks are designed to
        ensure a device's readiness for an upgrade by validating its operational and configuration status.
    REPORTS : dict
        A dictionary enumerating the types of reports that can be generated to offer insights into the device's state
        before and after an upgrade. These reports encompass aspects like ARP tables, content versions, IPsec tunnels,
        licenses, network interfaces, routing tables, and session statistics.
    STATE_SNAPSHOTS : dict
        A dictionary listing the categories of state snapshots that can be captured to document essential data about
        the device's current state. These snapshots are crucial for diagnostics and verifying the device's operational
        status before proceeding with the upgrade.

    Examples
    --------
    Accessing the log level for the 'active_support' readiness check:
        >>> log_level = AssuranceOptions.READINESS_CHECKS['active_support']['log_level']
        >>> print(log_level)
        'warning'

    Iterating through all available report types:
        >>> for report_type in AssuranceOptions.REPORTS:
        ...     print(report_type)
        'arp_table'
        'content_version'
        ...

    Notes
    -----
    - The configurations for readiness checks, report types, and state snapshots provided in this class can be selectively
      enabled or customized through the `settings.yaml` file. This allows users to adapt the upgrade assurance process
      to their specific requirements and scenarios.
    - Default settings are predefined within this class; however, they can be overridden by specifying custom configurations
      in the `settings.yaml` file, thus enhancing the script's flexibility and adaptability to different upgrade contexts.
    """

    READINESS_CHECKS = {
        "active_support": {
            "description": "Check if active support is available",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "arp_entry_exist": {
            "description": "Check if a given ARP entry is available in the ARP table",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "candidate_config": {
            "description": "Check if there are pending changes on device",
            "log_level": "error",
            "exit_on_failure": True,
            "enabled_by_default": True,
        },
        "certificates_requirements": {
            "description": "Check if the certificates' keys meet minimum size requirements",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "content_version": {
            "description": "Running Latest Content Version",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "dynamic_updates": {
            "description": "Check if any Dynamic Update job is scheduled to run within the specified time window",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "expired_licenses": {
            "description": "No Expired Licenses",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "free_disk_space": {
            "description": "Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "ha": {
            "description": "Checks HA pair status from the perspective of the current device",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "ip_sec_tunnel_status": {
            "description": "Check if a given IPsec tunnel is in active state",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "jobs": {
            "description": "Check for any job with status different than FIN",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "ntp_sync": {
            "description": "Check if NTP is synchronized",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
        "planes_clock_sync": {
            "description": "Check if the clock is synchronized between dataplane and management plane",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "panorama": {
            "description": "Check connectivity with the Panorama appliance",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": True,
        },
        "session_exist": {
            "description": "Check if a critical session is present in the sessions table",
            "log_level": "warning",
            "exit_on_failure": False,
            "enabled_by_default": False,
        },
    }

    # This is a placeholder for the report types, currently no reports are executed
    REPORTS = {
        "arp_table": {
            "enabled_by_default": True,
            "description": "ARP Table",
        },
        "content_version": {
            "enabled_by_default": True,
            "description": "App Content Version",
        },
        "ip_sec_tunnels": {
            "enabled_by_default": True,
            "description": "IPsec VPN tunnels",
        },
        "license": {
            "enabled_by_default": True,
            "description": "License Information",
        },
        "nics": {
            "enabled_by_default": True,
            "description": "Network Interfaces",
        },
        "routes": {
            "enabled_by_default": False,
            "description": "Route Table",
        },
        "session_stats": {
            "enabled_by_default": True,
            "description": "Session Stats",
        },
    }

    STATE_SNAPSHOTS = {
        "arp_table": {
            "enabled_by_default": False,
            "description": "Snapshot of the ARP Table",
        },
        "content_version": {
            "enabled_by_default": True,
            "description": "Snapshot of the Content Version",
        },
        "ip_sec_tunnels": {
            "enabled_by_default": False,
            "description": "Snapshot of the IPsec Tunnels",
        },
        "license": {
            "enabled_by_default": True,
            "description": "Snapshot of the License Information",
        },
        "nics": {
            "enabled_by_default": True,
            "description": "Snapshot of the Network Interfaces",
        },
        "routes": {
            "enabled_by_default": False,
            "description": "Snapshot of the Routing Table",
        },
        "session_stats": {
            "enabled_by_default": False,
            "description": "Snapshot of the Session Statistics",
        },
    }


def check_readiness_and_log(
    hostname: str,
    result: dict,
    test_info: dict,
    test_name: str,
) -> None:
    """
    Analyzes and logs the outcomes of readiness checks for a firewall or Panorama device, emphasizing failures that
    could impact the upgrade process. This function is integral to the pre-upgrade validation phase, ensuring that
    each device meets the necessary criteria before proceeding with an upgrade. It logs detailed results for each
    readiness check, using severity levels appropriate to the outcome of each test. Critical failures, identified by
    the 'exit_on_failure' flag in the test metadata, will cause the script to terminate, preventing potentially
    hazardous upgrade attempts.

    Parameters
    ----------
    result : dict
        The results of the readiness checks, structured as a dictionary where each key represents a test name and its
        value is a dictionary detailing the test's outcome ('state') and an explanation ('reason').
    hostname : str
        The hostname or IP address of the device being tested, utilized for logging context.
    test_name : str
        The identifier for the specific readiness check being logged, which should match a key in the 'result' dictionary.
    test_info : dict
        A dictionary containing metadata about the readiness check, including a descriptive label ('description'), the
        severity level for logging ('log_level'), and a flag indicating whether failure of this test should halt script
        execution ('exit_on_failure').

    Raises
    ------
    SystemExit
        If a test marked as critical (where 'exit_on_failure' is True) fails, the script will exit to avert an unsafe upgrade.

    Examples
    --------
    Handling a failed readiness check that is critical for upgrade:
        >>> result = {'connectivity_check': {'state': False, 'reason': 'Network unreachable'}}
        >>> test_info = {'description': 'Connectivity Check', 'log_level': 'error', 'exit_on_failure': True}
        >>> check_readiness_and_log(result, 'firewall01', 'connectivity_check', test_info)
        # This logs an error for the failed connectivity check and exits the script to prevent proceeding with the upgrade.

    Notes
    -----
    - This function is pivotal in ensuring that devices are fully prepared for an upgrade by rigorously logging the
      outcomes of various readiness checks.
    - The structured approach to logging facilitates easy identification and troubleshooting of potential issues prior
      to initiating the upgrade process.
    - Flexibility in defining the log level and criticality of each test allows for nuanced logging that reflects the
      importance and implications of each readiness check.
    """

    test_result = result.get(
        test_name, {"state": False, "reason": "Skipped Readiness Check"}
    )

    # Use .get() with a default value for 'reason' to avoid KeyError
    reason = test_result.get("reason", "No reason provided")
    log_message = f'{reason}: {test_info["description"]}'

    if test_result["state"]:
        logging.info(
            f"{get_emoji(action='success')} {hostname}: Passed Readiness Check: {test_info['description']}"
        )
    else:
        if test_info["log_level"] == "error":
            logging.error(f"{get_emoji(action='error')} {hostname}: {log_message}")
            if test_info["exit_on_failure"]:
                logging.error(f"{get_emoji(action='stop')} {hostname}: Halting script.")

                sys.exit(1)
        elif test_info["log_level"] == "warning":
            logging.info(
                f"{get_emoji(action='skipped')} {hostname}: Skipped Readiness Check: {test_info['description']}"
            )
        else:
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Log Message {log_message}"
            )


def generate_diff_report_pdf(
    file_path: str,
    hostname: str,
    pre_post_diff: dict,
    target_version: str,
) -> None:
    """
    Creates a PDF report detailing the differences observed in the network state of a device before and after an
    upgrade. The report organizes the changes into sections and highlights modifications, deletions, and additions in
    the device's configuration and operational state. It serves as a comprehensive document for reviewing the impact
    of the upgrade and verifying the changes made.

    The function employs a structured format to present the data, with a header section that includes the device's
    hostname and the target firmware version. This aids in quick identification of the report's context. The body of
    the report systematically lists the differences, categorized by the type of change, making it easy to assess the
    extent and nature of the modifications.

    Parameters
    ----------
    pre_post_diff : dict
        The differences between the pre-upgrade and post-upgrade states, structured as a nested dictionary. Each key
        represents a category (e.g., 'interfaces', 'policies'), with sub-keys detailing the specific changes (e.g.,
        'added', 'removed', 'modified').
    file_path : str
        The destination path for the generated PDF report, including the file name and extension.
    hostname : str
        The hostname of the device for which the upgrade was performed, used to personalize the report.
    target_version : str
        The version of the firmware to which the device was upgraded, included for reference in the report's header.

    Raises
    ------
    IOError
        If the PDF file cannot be created or written to the specified path, possibly due to issues like inadequate
        file permissions, non-existent directory paths, or insufficient disk space.

    Examples
    --------
    Generating a PDF report to document configuration changes after an upgrade:
        >>> pre_post_diff = {
        ...     'interfaces': {
        ...         'added': ['Ethernet1/3'],
        ...         'removed': ['Ethernet1/4'],
        ...         'modified': {'Ethernet1/1': {'before': '192.168.1.1', 'after': '192.168.1.2'}}
        ...     }
        ... }
        >>> generate_diff_report_pdf(pre_post_diff, '/tmp/device_upgrade_report.pdf', 'device123', '10.0.0')
        # This will create a PDF report at '/tmp/device_upgrade_report.pdf' summarizing the changes made during the upgrade to version 10.0.0.

    Notes
    -----
    - The report aims to provide a clear and concise summary of changes, facilitating audits and documentation of the
      upgrade process.
    - The PDF format ensures the report is accessible and easily distributable for review by various stakeholders.
    - Configuration for the PDF generation, such as layout and styling, can be customized through a `settings.yaml`
      file if the `settings_file_path` variable is utilized in the function, allowing for adaptation to specific
      reporting standards or preferences.
    """

    pdf = SimpleDocTemplate(file_path, pagesize=letter)
    content = []
    styles = getSampleStyleSheet()

    # Accessing logo.png using importlib.resources, creating a custom banner with logo and styling
    logo_path = pkg_resources.files("pan_os_upgrade.assets").joinpath("logo.png")
    img = Image(str(logo_path), width=71, height=51)  # Use the string path directly
    img.hAlign = "LEFT"
    content.append(img)

    banner_style = styles["Title"]
    banner_style.fontSize = 24
    banner_style.textColor = colors.HexColor("#333333")
    banner_style.alignment = 1  # Center alignment
    banner_content = Paragraph(
        f"<b>{hostname} Upgrade {target_version} Diff Report</b>",
        banner_style,
    )
    content.append(Spacer(1, 12))
    content.append(banner_content)
    content.append(Spacer(1, 20))

    # Line separator
    d = Drawing(500, 1)
    line = Line(0, 0, 500, 0)
    line.strokeColor = colors.HexColor("#F04E23")
    line.strokeWidth = 2
    d.add(line)
    content.append(d)
    content.append(Spacer(1, 20))

    for section, details in pre_post_diff.items():
        # Section title with background color
        section_style = styles["Heading2"]
        section_style.backColor = colors.HexColor("#EEEEEE")
        section_content = Paragraph(section.replace("_", " ").title(), section_style)
        content.append(section_content)
        content.append(Spacer(1, 12))

        for sub_section, sub_details in details.items():
            if sub_section == "passed":
                # Overall status of the section
                status = "Passed" if sub_details else "Failed"
                status_style = styles["BodyText"]
                status_style.textColor = colors.green if sub_details else colors.red
                status_content = Paragraph(
                    f"Overall Status: <b>{status}</b>", status_style
                )
                content.append(status_content)
            else:
                # Sub-section details
                sub_section_title = sub_section.replace("_", " ").title()
                passed = "Passed" if sub_details["passed"] else "Failed"
                passed_style = styles["BodyText"]
                passed_style.textColor = (
                    colors.green if sub_details["passed"] else colors.red
                )
                content.append(
                    Paragraph(
                        f"{sub_section_title} (Status: <b>{passed}</b>)", passed_style
                    )
                )

                keys = (
                    sub_details.get("missing_keys", [])
                    + sub_details.get("added_keys", [])
                    + list(sub_details.get("changed_raw", {}).keys())
                )

                # Format keys for display
                if keys:
                    for key in keys:
                        key_content = Paragraph(f"- {key}", styles["BodyText"])
                        content.append(key_content)
                else:
                    content.append(
                        Paragraph("No changes detected.", styles["BodyText"])
                    )

            content.append(Spacer(1, 12))

        # Add some space after each section
        content.append(Spacer(1, 20))

    # Build the PDF
    pdf.build(content)


def perform_readiness_checks(
    file_path: str,
    firewall: Firewall,
    hostname: str,
    settings_file_path: Path,
) -> None:
    """
    Conducts a set of predefined readiness checks on a specified Palo Alto Networks Firewall to verify its
    preparedness for an upgrade operation.

    This function systematically executes a series of checks on the specified firewall, evaluating various
    aspects such as configuration status, licensing validity, software version compatibility, and more, to
    ascertain its readiness for an upgrade. The outcomes of these checks are meticulously compiled into a
    detailed JSON report, which is then saved to the specified file path. The scope of checks performed can
    be tailored through configurations in the `settings.yaml` file, providing the flexibility to adapt the
    checks to specific operational needs or preferences.

    Parameters
    ----------
    firewall : Firewall
        An instance of the Firewall class, properly initialized with necessary authentication details and
        network connectivity to the target firewall device.
    hostname : str
        A string representing the hostname or IP address of the firewall, utilized for logging and
        identification purposes within the process.
    file_path : str
        The designated file path where the JSON-formatted report summarizing the results of the readiness
        checks will be stored. The function ensures the existence of the specified directory, creating it
        if necessary.

    Raises
    ------
    IOError
        Signals an issue with writing the readiness report to the specified file path, potentially due to
        file access restrictions or insufficient disk space, warranting further investigation.

    Examples
    --------
    Executing readiness checks for a firewall and saving the results:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> perform_readiness_checks(firewall_instance, 'firewall1', '/path/to/firewall1_readiness_report.json')
        # This command initiates the readiness checks on the specified firewall and saves the generated report
        # to the given file path.

    Notes
    -----
    - The execution of readiness checks is a pivotal preliminary step in the upgrade process, designed to
      uncover and address potential impediments, thereby facilitating a seamless and successful upgrade.
    - The set of checks to be conducted can be customized via the `settings.yaml` file. If this file is
      present and contains specific configurations under the `readiness_checks.customize` key, those
      configurations will dictate the checks to be performed. In the absence of such custom configurations,
      a default set of checks, determined by the `enabled_by_default` attribute within the AssuranceOptions
      class, will be applied.
    """

    # Load settings if the file exists
    if settings_file_path.exists():
        with open(settings_file_path, "r") as file:
            settings = yaml.safe_load(file)

        # Check if readiness checks are disabled in the settings
        if settings.get("readiness_checks", {}).get("disabled", False):
            logging.info(
                f"{get_emoji(action='skipped')} {hostname}: Readiness checks are disabled in the settings. Skipping readiness checks for {hostname}."
            )
            # Early return, no readiness checks performed
            return

        # Determine readiness checks to perform based on settings
        if settings.get("readiness_checks", {}).get("customize", False):
            # Extract checks where value is True
            selected_checks = [
                check
                for check, enabled in settings.get("readiness_checks", {})
                .get("checks", {})
                .items()
                if enabled
            ]
        else:
            # Select checks based on 'enabled_by_default' attribute from AssuranceOptions class
            selected_checks = [
                check
                for check, attrs in AssuranceOptions.READINESS_CHECKS.items()
                if attrs.get("enabled_by_default", False)
            ]
    else:
        # Select checks based on 'enabled_by_default' attribute from AssuranceOptions class
        selected_checks = [
            check
            for check, attrs in AssuranceOptions.READINESS_CHECKS.items()
            if attrs.get("enabled_by_default", False)
        ]

    logging.info(
        f"{get_emoji(action='start')} {hostname}: Performing readiness checks of target firewall."
    )

    readiness_check = run_assurance(
        actions=selected_checks,
        firewall=firewall,
        hostname=hostname,
        operation_type="readiness_check",
    )

    # Check if a readiness check was successfully created
    if isinstance(readiness_check, ReadinessCheckReport):
        logging.info(
            f"{get_emoji(action='success')} {hostname}: Readiness Checks completed"
        )
        readiness_check_report_json = readiness_check.model_dump_json(indent=4)
        logging.debug(
            f"{get_emoji(action='save')} {hostname}: Readiness Check Report: {readiness_check_report_json}"
        )

        ensure_directory_exists(file_path=file_path)

        with open(file_path, "w") as file:
            file.write(readiness_check_report_json)

        logging.debug(
            f"{get_emoji(action='save')} {hostname}: Readiness checks completed for {hostname}, saved to {file_path}"
        )
    else:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Failed to create readiness check"
        )


def perform_snapshot(
    file_path: str,
    firewall: Firewall,
    hostname: str,
    settings_file_path: Path,
    actions: Optional[List[str]] = None,
) -> SnapshotReport:
    """
    Captures and saves a comprehensive snapshot of a specified firewall's current state, focusing on key areas such
    as ARP tables, content versions, IPsec tunnel statuses, licensing, network interfaces, routing tables, and session
    statistics. The snapshot is saved in JSON format at a specified file path. This functionality is particularly useful
    for conducting pre- and post-change analyses, such as upgrade assessments or troubleshooting tasks.

    The snapshot content can be customized through the 'actions' parameter, allowing for a focused analysis on specified
    areas of interest. The function also supports customization of retry logic and intervals for capturing snapshots via
    a 'settings.yaml' file, providing flexibility for various operational requirements.

    Parameters
    ----------
    firewall : Firewall
        The Firewall object representing the device from which the snapshot will be captured. This object should be
        initialized and authenticated prior to calling this function.
    hostname : str
        The hostname or IP address of the firewall. This is used for identification and logging purposes throughout the
        snapshot process.
    file_path : str
        The filesystem path where the snapshot JSON file will be saved. If the specified directory does not exist, it will
        be created.
    actions : Optional[List[str]], optional
        A list of specific data points to be included in the snapshot. This allows for customization of the snapshot's
        content based on operational needs. If not specified, a default set of data points will be captured.

    Returns
    -------
    SnapshotReport
        An object containing detailed information about the firewall's state at the time of the snapshot. This includes
        both the data specified in the 'actions' parameter and metadata about the snapshot process itself.

    Raises
    ------
    IOError
        If there are issues with writing the snapshot data to the filesystem, such as problems creating the file or insufficient
        disk space, an IOError will be raised.

    Examples
    --------
    Taking a snapshot focusing on specific network elements:
        >>> firewall_instance = Firewall(hostname='192.168.1.1', api_username='admin', api_password='admin')
        >>> actions = ['arp_table', 'routes', 'session_stats']
        >>> snapshot_report = perform_snapshot(firewall_instance, 'fw1', '/path/to/snapshot.json', actions=actions)
        # This creates a snapshot containing ARP tables, routing tables, and session statistics for the firewall
        # identified as 'fw1' and saves it to '/path/to/snapshot.json'.

    Notes
    -----
    - The function is designed to be minimally invasive, allowing snapshots to be taken without impacting the operational
      performance of the network or the firewall.
    - The 'actions' parameter provides a means to tailor the snapshot to specific requirements, enhancing the function's
      utility for a wide range of diagnostic and compliance purposes.
    - Retry parameters, such as the maximum number of attempts and the interval between attempts, can be customized through
      a 'settings.yaml' file, allowing the function's behavior to be adapted to different network environments and operational
      policies.
    """

    # Load settings if the file exists
    if settings_file_path.exists():
        with open(settings_file_path, "r") as file:
            settings = yaml.safe_load(file)

        # Check if snapshots are disabled in the settings
        if settings.get("snapshots", {}).get("disabled", False):
            logging.info(
                f"{get_emoji(action='skipped')} {hostname}: Snapshots are disabled in the settings. Skipping snapshot for {hostname}."
            )
            return None  # Early return, no snapshot performed
        # Override default values with settings if snapshots are not disabled
        max_retries = settings.get("snapshots", {}).get("max_tries", 3)
        retry_interval = settings.get("snapshots", {}).get("retry_interval", 60)
    else:
        # Default values if settings.yaml does not exist or does not contain snapshot settings
        max_retries = 3
        retry_interval = 60

    logging.info(
        f"{get_emoji(action='start')} {hostname}: Performing snapshot of network state information."
    )
    attempt = 0
    snapshot = None

    while attempt < max_retries and snapshot is None:
        try:
            logging.info(
                f"{get_emoji(action='start')} {hostname}: Attempting to capture network state snapshot (Attempt {attempt + 1} of {max_retries})."
            )

            # Take snapshots
            snapshot = run_assurance(
                actions=actions,
                firewall=firewall,
                hostname=hostname,
                operation_type="state_snapshot",
            )

            if snapshot is not None and isinstance(snapshot, SnapshotReport):
                logging.info(
                    f"{get_emoji(action='success')} {hostname}: Network snapshot created successfully on attempt {attempt + 1}."
                )

                # Save the snapshot to the specified file path as JSON
                ensure_directory_exists(file_path=file_path)
                with open(file_path, "w") as file:
                    file.write(snapshot.model_dump_json(indent=4))

                logging.info(
                    f"{get_emoji(action='save')} {hostname}: Network state snapshot collected and saved to {file_path}"
                )

                return snapshot

        # Catch specific and general exceptions
        except (AttributeError, IOError, Exception) as error:
            logging.warning(
                f"{get_emoji(action='warning')} {hostname}: Snapshot attempt failed with error: {error}. Retrying after {retry_interval} seconds."
            )
            time.sleep(retry_interval)
            attempt += 1

    if snapshot is None:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Failed to create snapshot after {max_retries} attempts."
        )


def run_assurance(
    actions: List[str],
    firewall: Firewall,
    hostname: str,
    operation_type: str,
) -> Union[SnapshotReport, ReadinessCheckReport, None]:
    """
    Executes specified operational tasks, such as readiness checks or state snapshots, on a firewall based on the given
    operation type. This function is a versatile tool for conducting various operational checks or capturing the current
    state of the firewall for analysis. It uses a list of actions relevant to the chosen operation type and additional
    configuration parameters to customize the execution. Depending on the operation's success and type, it returns a
    report object or None in case of failure or if the operation type is invalid.

    Parameters
    ----------
    firewall : Firewall
        The Firewall object representing the device on which the assurance operations will be performed. This object
        must be initialized and authenticated prior to use.
    hostname : str
        The hostname or IP address of the firewall. This is used for identification and logging purposes.
    operation_type : str
        A string specifying the type of operation to perform. Supported types include 'readiness_check' and 'state_snapshot'.
    actions : List[str]
        A list of actions to be performed as part of the operation. The valid actions depend on the operation type.
    config : Dict[str, Union[str, int, float, bool]]
        A dictionary of additional configuration options that customize the operation. These might include thresholds,
        specific elements to check, or other operation-specific parameters.

    Returns
    -------
    Union[SnapshotReport, ReadinessCheckReport, None]
        Depending on the operation type, returns a SnapshotReport, ReadinessCheckReport, or None if the operation fails
        or the operation type is invalid.

    Raises
    ------
    SystemExit
        Exits the script if an invalid action is specified for the given operation type or if an unrecoverable error
        occurs during the operation execution.

    Examples
    --------
    Executing readiness checks before a firewall upgrade:
        >>> firewall = Firewall(hostname='192.168.1.1', api_username='admin', api_password='password')
        >>> result = run_assurance(firewall, '192.168.1.1', 'readiness_check', ['pending_changes', 'system_health'], {})
        # This might return a ReadinessCheckReport object with the results of the specified checks.

    Capturing the current state of a firewall for analysis:
        >>> result = run_assurance(firewall, '192.168.1.1', 'state_snapshot', ['arp_table', 'routes'], {})
        # This might return a SnapshotReport object with the current state information of the specified elements.

    Notes
    -----
    - The 'operation_type' parameter is key to defining the nature of the operation, making this function adaptable to
      a wide range of firewall management and diagnostic tasks.
    - This function is designed for extensibility, allowing new operation types and associated actions to be added as
      operational needs evolve.
    - Some operational parameters can be dynamically adjusted by providing a 'settings.yaml' file if the function
      utilizes a 'settings_file_path' to load these settings, offering greater control and customization of the operations.
    """

    # setup Firewall client
    proxy_firewall = FirewallProxy(firewall)
    checks_firewall = CheckFirewall(proxy_firewall)

    results = None

    if operation_type == "readiness_check":
        for action in actions:
            if action not in AssuranceOptions.READINESS_CHECKS.keys():
                logging.error(
                    f"{get_emoji(action='error')} {hostname}: Invalid action for readiness check: {action}"
                )

                sys.exit(1)

        try:
            logging.info(
                f"{get_emoji(action='start')} {hostname}: Performing readiness checks to determine if firewall is ready for upgrade."
            )
            result = checks_firewall.run_readiness_checks(actions)

            for (
                test_name,
                test_info,
            ) in AssuranceOptions.READINESS_CHECKS.items():
                check_readiness_and_log(
                    hostname=hostname,
                    result=result,
                    test_info=test_info,
                    test_name=test_name,
                )

            return ReadinessCheckReport(**result)

        except Exception as e:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: Error running readiness checks: {e}"
            )

            return None

    elif operation_type == "state_snapshot":
        # validate each type of action
        for action in actions:
            if action not in AssuranceOptions.STATE_SNAPSHOTS.keys():
                logging.error(
                    f"{get_emoji(action='error')} {hostname}: Invalid action for state snapshot: {action}"
                )
                return

        # take snapshots
        try:
            logging.debug(
                f"{get_emoji(action='start')} {hostname}: Performing snapshots."
            )
            results = checks_firewall.run_snapshots(snapshots_config=actions)
            logging.debug(
                f"{get_emoji(action='report')} {hostname}: Snapshot results {results}"
            )

            if results:
                # Pass the results to the SnapshotReport model
                return SnapshotReport(hostname=hostname, **results)
            else:
                return None

        except Exception as e:
            logging.error(
                f"{get_emoji(action='error')} {hostname}: Error running snapshots: %s",
                e,
            )
            return

    elif operation_type == "report":
        for action in actions:
            if action not in AssuranceOptions.REPORTS.keys():
                logging.error(
                    f"{get_emoji(action='error')} {hostname}: Invalid action for report: {action}"
                )
                return
            logging.info(
                f"{get_emoji(action='report')} {hostname}: Generating report: {action}"
            )
            # result = getattr(Report(firewall), action)(**config)

    else:
        logging.error(
            f"{get_emoji(action='error')} {hostname}: Invalid operation type: {operation_type}"
        )
        return

    return results
