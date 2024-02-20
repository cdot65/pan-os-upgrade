"""
upgrade.py: Automating the Upgrade Process for Palo Alto Networks Devices with PDF Reporting

This script automates the upgrade process for Palo Alto Networks Firewalls and Panorama appliances, offering a seamless and efficient way to perform upgrades with enhanced reporting capabilities. Leveraging Typer for a command-line interface, users can specify parameters directly. The script supports upgrading standalone firewalls, Panorama appliances, and batch upgrading firewalls managed by Panorama. A unique feature is the integration with reportlab for generating comprehensive PDF reports summarizing pre- and post-upgrade snapshots, providing a visual and detailed comparison of device states before and after upgrades. Additionally, a settings command generates a `settings.yaml` file, allowing users to override default script settings.

Features
--------
- **Automated Upgrades**: Streamlines the upgrade process for firewalls and Panorama appliances, reducing manual intervention.
- **Enhanced Reporting**: Utilizes reportlab to generate detailed PDF reports of pre and post-upgrade snapshots, aiding in the verification of upgrade success and system integrity.
- **Comprehensive Error Handling**: Incorporates extensive error handling to address common and unforeseen issues during upgrades.
- **Integration with panos-upgrade-assurance**: Uses the panos-upgrade-assurance tool for pre and post-upgrade checks, ensuring device readiness.
- **Flexible Configuration**: Enables customization of the upgrade process via a `settings.yaml` file, allowing adjustments to readiness checks, snapshot configurations, and more.

Imports
-------
Standard Libraries:
    - concurrent, threading: For parallel processing and multi-threading.
    - ipaddress: For IP address manipulation.
    - logging: For detailed logging throughout the upgrade process.
    - os, sys: For file and directory operations interfacing with the operating system.
    - time, re: For time-related functions and regular expression operations.
    - yaml: For YAML file parsing and settings configuration.
    - RemoteDisconnected, RotatingFileHandler: For HTTP connection management and log file rotation.
    - Path, Lock, typing: For file path utilities, synchronization primitives, and type annotations.

External Libraries:
    - xml.etree.ElementTree (ET): For XML tree structure manipulation, crucial for parsing PAN-OS API responses.
    - dns.resolver: For DNS lookups and hostname resolution.
    - Dynaconf: For dynamic configuration and settings management.
    - typer: For command-line interface creation, enhancing user interaction.
    - reportlab: For PDF report generation, detailing upgrade snapshots comparisons.

Palo Alto Networks libraries:
    - panos: For direct API interaction with Palo Alto Networks devices.
    - PanDevice, SystemSettings: For base PAN-OS device operations and system settings management.
    - Firewall, Panorama: For firewall and Panorama-specific operations.
    - Error handling modules: For specialized error management in PAN-OS environments.

panos-upgrade-assurance package:
    - CheckFirewall, FirewallProxy: For readiness checks and serving as intermediaries to firewalls.

Project-specific imports:
    - SnapshotReport, ReadinessCheckReport: For structured management of snapshot and readiness check reports.
    - ManagedDevice, ManagedDevices: For device information and collections management models.

Subcommands
-----------
- `firewall`: Triggers the upgrade process for an individual firewall device.
- `inventory`: Creates an `inventory.yaml` file based on selected firewalls.
- `panorama`: Initiates the upgrade for a Panorama appliance.
- `batch`: Executes batch upgrades for firewalls managed by a Panorama appliance.
- `settings`: Creates a `settings.yaml` file for script settings customization.

Usage
-----
The script is executed with various subcommands and options to customize the upgrade process. For example, to upgrade a firewall:

    python upgrade.py firewall --hostname <firewall_ip> --username <user> --password <password> --version <target_version>

For a batch upgrade of firewalls through Panorama:

    python upgrade.py batch --hostname <panorama_ip> --username <user> --password <password> --version <target_version>

To generate a `settings.yaml` file for customization:

    python upgrade.py settings

Notes
-----
- Ensure network connectivity and valid credentials before starting the upgrade process.
- The `settings.yaml` file allows for the customization of various aspects of the upgrade process, including the selection of readiness checks and snapshot configurations.
"""

# standard library imports
import logging
import sys
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing_extensions import Annotated

# Palo Alto Networks imports
from panos.firewall import Firewall

# third party imports
import typer
from colorama import init, Fore
from dynaconf import Dynaconf

# project imports
from pan_os_upgrade.components.assurance import AssuranceOptions
from pan_os_upgrade.components.device import (
    common_setup,
    get_firewalls_from_panorama,
    threaded_get_firewall_details,
)
from pan_os_upgrade.components.upgrade import (
    upgrade_firewall,
    upgrade_panorama,
)
from pan_os_upgrade.components.utilities import (
    console_welcome_banner,
    create_firewall_mapping,
    get_emoji,
    ip_callback,
    select_devices_from_table,
)


# Define Typer command-line interface
app = typer.Typer(help="PAN-OS Upgrade script")

# Define the path to the settings file
SETTINGS_FILE_PATH = Path.cwd() / "settings.yaml"
INVENTORY_FILE_PATH = Path.cwd() / "inventory.yaml"

# Initialize Dynaconf settings object conditionally based on the existence of settings.yaml
if SETTINGS_FILE_PATH.exists():
    SETTINGS_FILE = Dynaconf(settings_files=[str(SETTINGS_FILE_PATH)])
else:
    SETTINGS_FILE = Dynaconf()

# Initialize colorama
init()

# Global list and lock for storing HA active firewalls and Panorama to revisit
target_devices_to_revisit = []
target_devices_to_revisit_lock = Lock()

# Define logging levels
LOGGING_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


# Subcommand for upgrading a firewall
@app.command()
def firewall(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of either Panorama or firewall appliance",
            prompt="Firewall hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Firewall appliance",
            prompt="Firewall username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Firewall password",
            hide_input=True,
        ),
    ],
    target_version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Target version to upgrade to",
            prompt="Target version",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Dry Run?",
        ),
    ] = True,
):
    """
    Launches the upgrade process for a Palo Alto Networks firewall, facilitating a comprehensive and controlled upgrade workflow.

    This command orchestrates the steps required for upgrading a firewall appliance, encompassing initial validations, environment setup, and execution of the upgrade process. It is capable of operating in a 'dry run' mode, which simulates the upgrade process without applying any changes, allowing for validation of upgrade prerequisites and assessment of potential issues. The command leverages a series of internal functions to prepare the environment, verify connectivity, ensure compatibility with the target version, and, if all checks pass, proceed with the upgrade.

    Parameters
    ----------
    hostname : str
        The IP address or DNS hostname of the firewall to be upgraded. Must be accessible from the execution environment.
    username : str
        The administrative username for the firewall, used for API or CLI authentication.
    password : str
        The corresponding password for the provided administrative username.
    target_version : str
        The version of PAN-OS to which the firewall is to be upgraded. Must be a valid and supported version for the device.
    dry_run : bool, optional
        When set to True, the function performs all preparatory and validation steps without executing the actual upgrade, defaulting to False.

    Examples
    --------
    Executing an upgrade to version 9.1.0:
        $ python upgrade.py firewall --hostname 192.168.1.1 --username admin --password secure123 --version 9.1.0

    Performing a dry run for version 9.1.0:
        $ python upgrade.py firewall --hostname 192.168.1.1 --username admin --password secure123 --version 9.1.0 --dry-run

    Notes
    -----
    - Prior to executing the upgrade, ensure that the firewall is in a stable state and that there is a reliable network connection to the device.
    - The 'dry run' mode is highly recommended for a preliminary assessment to identify any potential issues that might impede the upgrade process.
    - Default settings for the upgrade process, such as log levels and file paths, can be overridden by providing a `settings.yaml` file, if supported by the implementation of `common_setup` and other called functions within this command.
    """

    # Display the custom banner for firewall upgrade
    if SETTINGS_FILE_PATH.exists():
        banner = console_welcome_banner(
            config_path=SETTINGS_FILE_PATH,
            mode="firewall",
        )
    else:
        banner = console_welcome_banner(mode="firewall")
    typer.echo(banner)

    # Perform common setup tasks, return a connected device
    device = common_setup(
        hostname=hostname,
        username=username,
        password=password,
        settings_file=SETTINGS_FILE,
        settings_file_path=SETTINGS_FILE_PATH,
    )

    # Perform upgrade
    upgrade_firewall(
        dry_run=dry_run,
        firewall=device,
        settings_file=SETTINGS_FILE,
        settings_file_path=SETTINGS_FILE_PATH,
        target_version=target_version,
    )


# Subcommand for upgrading Panorama
@app.command()
def panorama(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of Panorama appliance",
            prompt="Panorama hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Panorama appliance",
            prompt="Panorama username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Panorama password",
            hide_input=True,
        ),
    ],
    target_version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Target Panorama version to upgrade to",
            prompt="Target Panorama version",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Dry Run?",
        ),
    ] = True,
):
    """
    Manages the upgrade process for a Panorama management platform, orchestrating the sequence of actions required for a successful upgrade.

    This command facilitates the upgrade of a Panorama appliance by executing a series of preparatory actions, including validation of connectivity, compatibility checks with the target version, and the actual upgrade process. The dry run mode allows operators to simulate the upgrade steps without making any modifications to the Panorama appliance. The command leverages internal utility functions to ensure the environment is correctly configured, to establish a connection to the Panorama, and to conduct the upgrade according to the parameters specified.

    Parameters
    ----------
    hostname : str
        The network address of the Panorama appliance, either as an IP address or a DNS-resolvable hostname.
    username : str
        The administrative username required for authentication on the Panorama appliance.
    password : str
        The corresponding password for the specified administrative username.
    target_version : str
        The target version of PAN-OS to which the Panorama appliance is to be upgraded.
    dry_run : bool, optional
        A boolean flag indicating whether to simulate the upgrade process without applying changes, defaulting to False.

    Examples
    --------
    Directly upgrading a Panorama appliance:
        $ python upgrade.py panorama --hostname panorama.example.com --username admin --password secure123 --version 10.0.0

    Conducting a dry run for the upgrade process:
        $ python upgrade.py panorama --hostname panorama.example.com --username admin --password secure123 --version 10.0.0 --dry-run

    Notes
    -----
    - It is critical to ensure that the Panorama appliance is accessible and that the provided credentials are correct before initiating the upgrade process.
    - Utilizing the dry run mode is strongly recommended for validating the upgrade path and identifying any potential obstacles without risking the operational state of the Panorama appliance.
    - Settings for the upgrade process, such as logging levels and file paths, may be overridden by a `settings.yaml` file if present and detected by the implementation of `common_setup` and other invoked functions within this command.
    """

    # Display the custom banner for panorama upgrade
    if SETTINGS_FILE_PATH.exists():
        banner = console_welcome_banner(
            config_path=SETTINGS_FILE_PATH,
            mode="panorama",
        )
    else:
        banner = console_welcome_banner(mode="panorama")
    typer.echo(banner)

    # Perform common setup tasks, return a connected device
    device = common_setup(
        hostname=hostname,
        username=username,
        password=password,
        settings_file=SETTINGS_FILE,
        settings_file_path=SETTINGS_FILE_PATH,
    )

    # Perform upgrade
    upgrade_panorama(
        dry_run=dry_run,
        panorama=device,
        settings_file=SETTINGS_FILE,
        settings_file_path=SETTINGS_FILE_PATH,
        target_devices_to_revisit=target_devices_to_revisit,
        target_devices_to_revisit_lock=target_devices_to_revisit_lock,
        target_version=target_version,
    )


# Subcommand for batch upgrades using Panorama as a communication proxy
@app.command()
def batch(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of Panorama appliance",
            prompt="Panorama hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Panorama appliance",
            prompt="Panorama username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Panorama password",
            hide_input=True,
        ),
    ],
    target_version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Target version to upgrade firewalls to",
            prompt="Firewall target version (ex: 10.1.2)",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Dry Run?",
            is_flag=True,
        ),
    ] = True,
):
    """
    Orchestrates a batch upgrade process for firewalls under Panorama's management. This command leverages Panorama
    to coordinate upgrades across multiple devices, streamlining the process. The user has the option to perform a
    dry run to validate the upgrade steps without applying changes, and to specify the target PAN-OS version for the
    upgrade.

    The process begins by establishing a secure connection to Panorama using provided credentials. Firewalls managed
    by Panorama are then enumerated, and a subset may be selected for upgrade based on criteria defined in an
    'inventory.yaml' file or interactively during execution. The 'inventory.yaml' file, if present, pre-selects
    devices for upgrade, bypassing manual selection.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the Panorama appliance to connect to.
    username : str
        The username for authenticating with Panorama.
    password : str
        The password for the provided username, used for authentication.
    target_version : str
        The version of PAN-OS to which the firewalls should be upgraded.
    dry_run : bool, optional
        If set, the command simulates the upgrade process without making any changes to the devices. Defaults to True, meaning dry run is enabled by default.

    Examples
    --------
    Initiating a batch upgrade process with specified parameters:
        $ python upgrade.py batch --hostname 192.168.1.1 --username admin --password secret --version 10.2.7-h3 --dry-run

    Notes
    -----
    - The command streamlines firewall upgrades by automating repetitive tasks and consolidating operations through Panorama.
    - The dry run feature is useful for validating the upgrade plan and ensuring readiness without impacting production systems.
    - The presence of an 'inventory.yaml' file can automate device selection, facilitating integration into larger automated workflows.
    - It's recommended to back up device configurations and have a rollback plan in place before proceeding with actual upgrades.
    - Customization options, such as setting logging preferences, can be specified through a 'settings.yaml' file if the script supports reading from such a file, allowing for more granular control over the upgrade process.
    """

    # Create the custom banner for batch firewall upgrades
    if SETTINGS_FILE_PATH.exists():
        if INVENTORY_FILE_PATH.exists():
            banner = console_welcome_banner(
                config_path=SETTINGS_FILE_PATH,
                inventory_path=INVENTORY_FILE_PATH,
                mode="batch",
            )
        else:
            banner = console_welcome_banner(
                config_path=SETTINGS_FILE_PATH,
                mode="batch",
            )

    elif INVENTORY_FILE_PATH.exists():
        banner = console_welcome_banner(
            inventory_path=INVENTORY_FILE_PATH,
            mode="batch",
        )

    else:
        banner = console_welcome_banner(mode="batch")

    # Display the custom banner for batch firewall upgrades
    typer.echo(banner)

    # Perform common setup tasks, return a connected device
    device = common_setup(
        hostname=hostname,
        username=username,
        password=password,
        settings_file=SETTINGS_FILE,
        settings_file_path=SETTINGS_FILE_PATH,
    )

    # Exit script if device is Firewall (batch upgrade is only supported when connecting to Panorama)
    if type(device) is Firewall:
        logging.info(
            f"{get_emoji(action='error')} {hostname}: Batch upgrade is only supported when connecting to Panorama."
        )
        sys.exit(1)

    # Report the successful connection to Panorama
    logging.info(
        f"{get_emoji(action='success')} {hostname}: Connection to Panorama established. Firewall connections will be proxied!"
    )

    # Get firewalls connected to Panorama
    logging.info(
        f"{get_emoji(action='working')} {hostname}: Retrieving a list of all firewalls connected to Panorama..."
    )
    all_firewalls = get_firewalls_from_panorama(panorama=device)

    # Retrieve additional information about all of the firewalls
    logging.info(
        f"{get_emoji(action='working')} {hostname}: Retrieving detailed information of each firewall..."
    )
    firewalls_info = threaded_get_firewall_details(firewalls=all_firewalls)

    # Create a mapping of firewalls for selection
    firewall_mapping = create_firewall_mapping(
        all_firewalls=all_firewalls,
        firewalls_info=firewalls_info,
    )

    # Check if inventory.yaml exists and if it does, read the selected devices
    if INVENTORY_FILE_PATH.exists():
        with open(INVENTORY_FILE_PATH, "r") as file:
            inventory_data = yaml.safe_load(file)
            user_selected_hostnames = inventory_data.get("firewalls_to_upgrade", [])

    # If inventory.yaml does not exist, then prompt the user to select devices
    else:
        # Present a table of firewalls with detailed system information for selection
        user_selected_hostnames = select_devices_from_table(
            firewall_mapping=firewall_mapping
        )

    # Extracting the Firewall objects from the filtered mapping
    firewall_objects_for_upgrade = [
        firewall_mapping[hostname]["object"]
        for hostname in user_selected_hostnames
        if hostname in firewall_mapping
    ]
    logging.info(
        f"{get_emoji(action='working')} {hostname}: Selected {len(firewall_objects_for_upgrade)} firewalls from inventory.yaml for upgrade."
    )

    # Now, firewall_objects_for_upgrade should contain the actual Firewall objects
    # Proceed with the upgrade for the selected devices
    if not firewall_objects_for_upgrade:
        typer.echo("No devices selected for upgrade.")
        raise typer.Exit()

    typer.echo(
        f"{get_emoji(action='report')} {hostname}: Upgrading {len(firewall_objects_for_upgrade)} devices to version {target_version}..."
    )

    firewall_list = "\n".join(
        [
            f"  - {firewall_mapping[hostname]['hostname']} ({firewall_mapping[hostname]['ip-address']})"
            for hostname in user_selected_hostnames
        ]
    )

    typer.echo(
        f"{get_emoji(action='report')} {hostname}: Please confirm the selected firewalls:\n{firewall_list}"
    )

    # Asking for user confirmation before proceeding
    if dry_run:
        typer.echo(
            f"{get_emoji(action='warning')} {hostname}: Dry run mode is enabled, upgrade workflow will be skipped."
        )
        confirmation = typer.confirm(
            "Do you want to proceed with the dry run?", abort=True
        )
    else:
        typer.echo(
            f"{get_emoji(action='warning')} {hostname}: Dry run mode is disabled, upgrade workflow will be executed."
        )
        confirmation = typer.confirm(
            f"{get_emoji(action='report')} {hostname}: Do you want to proceed with the upgrade?",
            abort=True,
        )
        typer.echo(f"{get_emoji(action='start')} Proceeding with the upgrade...")

    if confirmation:
        typer.echo(f"{get_emoji(action='start')} Proceeding with the upgrade...")

        # Using ThreadPoolExecutor to manage threads
        threads = SETTINGS_FILE.get("concurrency.threads", 10)
        logging.info(
            f"{get_emoji(action='working')} {hostname}: Using {threads} threads."
        )

        # Using ThreadPoolExecutor to manage threads for upgrading firewalls
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Store future objects along with firewalls for reference
            future_to_firewall = {
                executor.submit(
                    upgrade_firewall,
                    dry_run=dry_run,
                    firewall=target_device,
                    settings_file=SETTINGS_FILE,
                    settings_file_path=SETTINGS_FILE_PATH,
                    target_devices_to_revisit=target_devices_to_revisit,
                    target_devices_to_revisit_lock=target_devices_to_revisit_lock,
                    target_version=target_version,
                ): target_device
                for target_device in firewall_objects_for_upgrade
            }

            # Process completed tasks
            for future in as_completed(future_to_firewall):
                firewall = future_to_firewall[future]
                try:
                    future.result()
                except Exception as exc:
                    logging.error(
                        f"{get_emoji(action='error')} {hostname}: Firewall {firewall.hostname} generated an exception: {exc}"
                    )

        # Revisit the firewalls that were skipped in the initial pass
        if target_devices_to_revisit:
            logging.info(
                f"{get_emoji(action='start')} {hostname}: Revisiting firewalls that were active in an HA pair and had the same version as their peers."
            )

            # Using ThreadPoolExecutor to manage threads for revisiting firewalls
            threads = SETTINGS_FILE.get("concurrency.threads", 10)
            logging.debug(
                f"{get_emoji(action='working')} {hostname}: Using {threads} threads."
            )
            with ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_firewall = {
                    executor.submit(
                        upgrade_firewall,
                        dry_run=dry_run,
                        firewall=target_device,
                        settings_file=SETTINGS_FILE,
                        settings_file_path=SETTINGS_FILE_PATH,
                        target_devices_to_revisit=target_devices_to_revisit,
                        target_devices_to_revisit_lock=target_devices_to_revisit_lock,
                        target_version=target_version,
                    ): target_device
                    for target_device in target_devices_to_revisit
                }

                # Process completed tasks
                for future in as_completed(future_to_firewall):
                    firewall = future_to_firewall[future]
                    try:
                        future.result()
                        logging.info(
                            f"{get_emoji(action='success')} {hostname}: Completed revisiting firewalls"
                        )
                    except Exception as exc:
                        logging.error(
                            f"{get_emoji(action='error')} {hostname}: Exception while revisiting firewalls: {exc}"
                        )

            # Clear the list after revisiting
            with target_devices_to_revisit_lock:
                target_devices_to_revisit.clear()
    else:
        typer.echo("Upgrade cancelled.")


# Subcommand for generating an inventory.yaml file
@app.command()
def inventory(
    hostname: Annotated[
        str,
        typer.Option(
            "--hostname",
            "-h",
            help="Hostname or IP address of Panorama appliance",
            prompt="Panorama hostname or IP",
            callback=ip_callback,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Username for authentication with the Panorama appliance",
            prompt="Panorama username",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Perform a dry run of all tests and downloads without performing the actual upgrade",
            prompt="Panorama password",
            hide_input=True,
        ),
    ],
):
    """
    Interactively generates an inventory file listing devices managed by a Panorama appliance,
    allowing the user to select which devices to include for potential upgrade. The inventory
    process involves connecting to Panorama, retrieving a list of managed firewalls, and presenting
    the user with a table of devices. The user can then select specific devices to include in the
    inventory file. This file serves as input for subsequent upgrade operations, ensuring that
    upgrades are targeted and organized.

    Parameters
    ----------
    hostname : str
        The hostname or IP address of the Panorama appliance. This is the address used to establish
        a connection for querying managed devices.
    username : str
        The username for authentication with the Panorama appliance. It is required to have sufficient
        permissions to retrieve device information.
    password : str
        The password associated with the username for authentication purposes. Input is hidden to protect
        sensitive information.

    Raises
    ------
    typer.Exit
        Exits the script if the command is invoked for an individual firewall rather than a Panorama appliance,
        as this functionality is specific to Panorama-managed environments.

    Examples
    --------
    Generating an inventory file from the command line:
        >>> typer run inventory --hostname 192.168.1.1 --username admin --password admin
        # This command initiates the inventory process, connecting to the Panorama at 192.168.1.1, and
        # interactively allows the user to select devices to include in the inventory file.

    Notes
    -----
    - The inventory process is an interactive session that requires the user to select devices from a
      presented table. The selections are then saved to 'inventory.yaml'.
    - This function is part of a Typer application that includes multiple subcommands for managing device
      upgrades. It is designed to be used in the context of a larger upgrade workflow.
    - The inventory file generated by this function can be customized or extended by editing 'inventory.yaml'
      directly, allowing for manual inclusion or exclusion of devices as needed.
    """

    # Display the custom banner for inventory
    banner = console_welcome_banner(mode="inventory")
    typer.echo(banner)

    device = common_setup(
        hostname=hostname,
        username=username,
        password=password,
        settings_file=SETTINGS_FILE,
        settings_file_path=SETTINGS_FILE_PATH,
    )

    if type(device) is Firewall:
        logging.error(
            "Inventory command is only supported when connecting to Panorama."
        )
        raise typer.Exit()

    # Report the successful connection to Panorama
    logging.info(
        f"{get_emoji(action='success')} {hostname}: Connection to Panorama established."
    )

    # Get firewalls connected to Panorama
    logging.info(
        f"{get_emoji(action='working')} {hostname}: Retrieving a list of all firewalls connected to Panorama..."
    )
    all_firewalls = get_firewalls_from_panorama(panorama=device)

    # Retrieve additional information about all of the firewalls
    logging.info(
        f"{get_emoji(action='working')} {hostname}: Retrieving detailed information of each firewall..."
    )
    firewalls_info = threaded_get_firewall_details(firewalls=all_firewalls)

    # Create a mapping of firewalls for selection
    firewall_mapping = create_firewall_mapping(
        all_firewalls=all_firewalls,
        firewalls_info=firewalls_info,
    )

    user_selected_hostnames = select_devices_from_table(
        firewall_mapping=firewall_mapping
    )

    with open("inventory.yaml", "w") as file:
        yaml.dump(
            {
                "firewalls_to_upgrade": [
                    hostname for hostname in user_selected_hostnames
                ]
            },
            file,
            default_flow_style=False,
        )

    typer.echo(Fore.GREEN + "Selected devices saved to inventory.yaml" + Fore.RESET)


# Subcommand for creating a settings.yaml file to override default settings
@app.command()
def settings():
    """
    Generates a settings.yaml file allowing customization of script configurations.

    This interactive command guides the user through a series of prompts to configure various aspects of the script's behavior, including concurrency, logging, reboot strategies, readiness checks, snapshots, and timeout settings. Each configuration section allows the user to specify preferences, such as the number of concurrent threads, logging levels, and file paths, among others. Customization of readiness checks and snapshots is also offered, enabling selective execution based on user requirements. The resulting configurations are saved to a 'settings.yaml' file in the current working directory, which the script can subsequently use to override default settings.

    Configuration Sections
    ----------------------
    - Concurrency: Defines the number of concurrent operations, particularly useful for batch operations.
    - Logging: Sets logging preferences including verbosity level, file path, maximum size, and log retention count.
    - Reboot: Configures retry intervals and maximum attempts for device reboots during the upgrade process.
    - Readiness Checks: Allows customization of pre-upgrade readiness checks to run.
    - Snapshots: Enables configuration of pre and post-upgrade snapshots for comparison and rollback purposes.
    - Timeout Settings: Determines timeout values for device connections and command executions.

    Notes
    -----
    - This command is part of the setup process and is intended to be run prior to executing upgrade commands.
    - The 'settings.yaml' file created by this command can be edited manually for further customization.
    - Default values are provided for each configuration option, with the option to accept the default or provide a custom value.
    """

    # Display the custom banner for settings
    banner = console_welcome_banner(mode="settings")
    typer.echo(banner)

    config_file_path = Path.cwd() / "settings.yaml"

    # Add confirmation prompts for disabling features
    disable_readiness_checks = typer.confirm(
        "Would you like to disable all readiness checks?", default=False
    )
    disable_snapshots = typer.confirm(
        "Would you like to disable all snapshots?", default=False
    )

    config_data = {
        "concurrency": {
            "threads": typer.prompt(
                "Number of concurrent threads",
                default=10,
                type=int,
            ),
        },
        "download": {
            "retry_interval": typer.prompt(
                "PAN-OS download retry interval (seconds)",
                default=60,
                type=int,
            ),
            "max_tries": typer.prompt(
                "PAN-OS maximum download tries",
                default=3,
                type=int,
            ),
        },
        "install": {
            "retry_interval": typer.prompt(
                "PAN-OS install retry interval (seconds)",
                default=60,
                type=int,
            ),
            "max_tries": typer.prompt(
                "PAN-OS maximum install attempts",
                default=3,
                type=int,
            ),
        },
        "logging": {
            "level": typer.prompt("Logging level", default="INFO"),
            "file_path": typer.prompt("Path for log files", default="logs/upgrade.log"),
            "max_size": typer.prompt(
                "Maximum log file size (MB)",
                default=10,
                type=int,
            ),
            "upgrade_log_count": typer.prompt(
                "Number of upgrade logs to retain",
                default=10,
                type=int,
            ),
        },
        "reboot": {
            "retry_interval": typer.prompt(
                "Device reboot retry interval (seconds)",
                default=60,
                type=int,
            ),
            "max_tries": typer.prompt(
                "Device maximum reboot tries",
                default=30,
                type=int,
            ),
        },
        "readiness_checks": {
            "disabled": disable_readiness_checks,
            "customize": (
                False
                if disable_readiness_checks
                else typer.confirm(
                    "Would you like to customize readiness checks?", default=False
                )
            ),
            "checks": {},
            "location": (
                "assurance/readiness_checks/" if not disable_readiness_checks else None
            ),
        },
        "snapshots": {
            "disabled": disable_snapshots,
            "customize": (
                False
                if disable_snapshots
                else typer.confirm(
                    "Would you like to customize snapshots?", default=False
                )
            ),
            "state": {},
            "location": "assurance/snapshots/" if not disable_snapshots else None,
            "retry_interval": 60 if not disable_snapshots else None,
            "max_tries": 3 if not disable_snapshots else None,
        },
        "timeout_settings": {
            "connection_timeout": typer.prompt(
                "Connection timeout (seconds)",
                default=30,
                type=int,
            ),
            "command_timeout": typer.prompt(
                "Command timeout (seconds)",
                default=120,
                type=int,
            ),
        },
    }

    # Modify the conditional sections to check for the disabled state
    if not disable_readiness_checks and config_data["readiness_checks"]["customize"]:
        for check, info in AssuranceOptions.READINESS_CHECKS.items():
            config_data["readiness_checks"]["checks"][check] = typer.confirm(
                f"Enable {info['description']}?", default=info["enabled_by_default"]
            )

    if not disable_snapshots and config_data["snapshots"]["customize"]:
        for snapshot_name, snapshot_info in AssuranceOptions.STATE_SNAPSHOTS.items():
            config_data["snapshots"]["state"][snapshot_name] = typer.confirm(
                f"Enable {snapshot_info['description']}?",
                default=snapshot_info["enabled_by_default"],
            )

    with open(config_file_path, "w") as f:
        yaml.dump(
            config_data,
            f,
            default_flow_style=False,
            sort_keys=True,
        )

    typer.echo(f"Configuration saved to {config_file_path}")


if __name__ == "__main__":
    app()
