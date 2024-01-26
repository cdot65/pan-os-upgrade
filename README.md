<a name="readme-top"></a>

<!-- PROJECT SHIELDS -->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
    <img src="https://github.com/cdot65/pan-os-upgrade/blob/main/docs/images/logo.svg?raw=true" alt="Logo">
    <h3 align="center">PAN-OS Automation Project</h3>
    <p align="center">
        Streamlining Palo Alto Networks Firewall Upgrades with Python Automation
        <br />
        <a href="https://github.com/cdot65/pan-os-upgrade"><strong>Explore the docs »</strong></a>
        <br />
        <br />
        <a href="https://github.com/cdot65/pan-os-upgrade">View Demo</a>
        <a href="https://github.com/cdot65/pan-os-upgrade/issues">Report Bug</a>
        <a href="https://github.com/cdot65/pan-os-upgrade/issues">Request Feature</a>
    </p>
</div>
<!-- TABLE OF CONTENTS -->
<details>
    <summary>Table of Contents</summary>
    <ol>
        <li><a href="#about-the-project">About The Project</a></li>
        <li><a href="#getting-started">Getting Started</a></li>
        <li><a href="#usage">Usage</a></li>
        <li><a href="#output">Output</a></li>
        <li><a href="#logging">Logging</a></li>
        <li><a href="#contributing">Contributing</a></li>
        <li><a href="#license">License</a></li>
        <li><a href="#contact">Contact</a></li>
        <li><a href="#acknowledgments">Acknowledgments</a></li>
    </ol>
</details>
<!-- ABOUT THE PROJECT -->

## About The Project

This project is a comprehensive Python-based solution for automating PAN-OS upgrades. It's designed to provide network administrators and security professionals with an efficient tool to manage upgrades, configurations, and system checks of Palo Alto Networks appliances.

### Key Features

- **Three Unique Workflows Supported**:
  - `firewall`: targets and upgrades an individual firewall
  - `panorama`: targets and upgrades an individual Panorama appliance
  - `batch`: targets a Panorama appliance and upgrades firewalls in batch
    - The script will support up to ten simultaneous upgrades
- **Automation of Routine Tasks**: Reduces manual errors and saves time by automating upgrades, configurations, and system checks.
- **Support for Direct and Proxy Connections**: Connect directly to firewalls or through a Panorama appliance, with support for targeting specific devices using filters.
- **Active/Passive High Availability (HA) Workflow**: Fully supports upgrading devices in active/passive HA configurations, ensuring both members are properly upgraded and synchronized.
- **Multi-threading for Efficiency**: Utilizes multi-threading to parallelize upgrades, especially beneficial when upgrading multiple devices through Panorama, enhancing performance and reducing overall upgrade time.
- **Customizable and Extensible**: Scripts can be tailored to fit diverse network environments and requirements, offering flexibility for various deployment scenarios.
- **Comprehensive PAN-OS Interactions**: Facilitates extensive interactions with Palo Alto Networks appliances for operations like readiness checks, state snapshots, and report generation.

> **Note**: While this script is optimized for standalone and active/passive HA environments, it has not been tested against active/active or clustered firewalls.

Example Execution

<div class="termy">

```console
$ pan-os-upgrade batch
Panorama hostname or IP: panorama.cdot.io
Panorama username: cdot
Panorama password:
Firewall target version (ex: 10.1.2): 10.2.3
Filter string (ex: hostname=Woodlands*) []: hostname=Woodlands*
Dry Run? [y/N]:
✅ panorama.cdot.io: Connection to Panorama established. Firewall connections will be proxied!
📝 Woodlands-fw2: 007954000123452 192.168.255.44
📝 Woodlands-fw1: 007954000123451 192.168.255.43
📝 Woodlands-fw2: HA mode: passive
📝 Woodlands-fw1: HA mode: active
🔍 Woodlands-fw1: Detected active target device in HA pair running the same version as its peer. Added target device to revisit list.
📝 Woodlands-fw2: Current version: 10.2.2-h2
📝 Woodlands-fw2: Target version: 10.2.3
✅ Woodlands-fw2: Upgrade required from 10.2.2-h2 to 10.2.3
✅ Woodlands-fw2: version 10.2.3 is available for download
✅ Woodlands-fw2: Base image for 10.2.3 is already downloaded
🚀 Woodlands-fw2: Performing test to see if 10.2.3 is already downloaded...
✅ Woodlands-fw2: version 10.2.3 already on target device.
✅ Woodlands-fw2: 10.2.3 has been downloaded and sync'd to HA peer.
🚀 Woodlands-fw2: Performing snapshot of network state information...
✅ Woodlands-fw2: Network snapshot created successfully
🚀 Woodlands-fw2: Performing readiness checks to determine if firewall is ready for upgrade...
✅ Woodlands-fw2: Passed Readiness Check: Check if there are pending changes on device
✅ Woodlands-fw2: Passed Readiness Check: No Expired Licenses
✅ Woodlands-fw2: Passed Readiness Check: Checks HA pair status from the perspective of the current device
✅ Woodlands-fw2: Passed Readiness Check: Check if NTP is synchronized
✅ Woodlands-fw2: Passed Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ Woodlands-fw2: Passed Readiness Check: Check connectivity with the Panorama appliance
✅ Woodlands-fw2: Readiness Checks completed
🚀 Woodlands-fw2: Checking if HA peer is in sync...
✅ Woodlands-fw2: HA peer sync test has been completed.
🚀 Woodlands-fw2: Performing backup of configuration to local filesystem...
🚀 Woodlands-fw2: Not a dry run, continue with upgrade...
🚀 Woodlands-fw2: Performing upgrade to version 10.2.3...
🚀 Woodlands-fw2: Attempting upgrade to version 10.2.3 (Attempt 1 of 3)...
Device 007954000123452 installing version: 10.2.3
✅ Woodlands-fw2: Upgrade completed successfully
🚀 Woodlands-fw2: Rebooting the passive HA target device...
📝 Woodlands-fw2: Command succeeded with no output
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: Target device is rebooting...
🔧 Woodlands-fw2: HA passive target device rebooted but not yet synchronized with its peer. Will try again in 60 seconds.
🔧 Woodlands-fw2: HA passive target device rebooted but not yet synchronized with its peer. Will try again in 60 seconds.
🔧 Woodlands-fw2: HA passive target device rebooted but not yet synchronized with its peer. Will try again in 60 seconds.
🔧 Woodlands-fw2: HA passive target device rebooted but not yet synchronized with its peer. Will try again in 60 seconds.
🟧 Woodlands-fw2: HA passive target device rebooted but did not complete a configuration sync with the active after 5 attempts.
🚀 panorama.cdot.io: Revisiting firewalls that were active in an HA pair and had the same version as their peers.
📝 Woodlands-fw1: 007954000123451 192.168.255.43
📝 Woodlands-fw1: HA mode: active
❌ Woodlands-fw1: Error suspending active target device HA state: argument of type 'NoneType' is not iterable
📝 Woodlands-fw1: Current version: 10.2.2-h2
📝 Woodlands-fw1: Target version: 10.2.3
✅ Woodlands-fw1: Upgrade required from 10.2.2-h2 to 10.2.3
✅ Woodlands-fw1: version 10.2.3 is available for download
✅ Woodlands-fw1: Base image for 10.2.3 is already downloaded
🚀 Woodlands-fw1: Performing test to see if 10.2.3 is already downloaded...
✅ Woodlands-fw1: version 10.2.3 already on target device.
✅ Woodlands-fw1: 10.2.3 has been downloaded and sync'd to HA peer.
🚀 Woodlands-fw1: Performing snapshot of network state information...
✅ Woodlands-fw1: Network snapshot created successfully
🚀 Woodlands-fw1: Performing readiness checks to determine if firewall is ready for upgrade...
✅ Woodlands-fw1: Passed Readiness Check: Check if there are pending changes on device
✅ Woodlands-fw1: Passed Readiness Check: No Expired Licenses
✅ Woodlands-fw1: Passed Readiness Check: Check if NTP is synchronized
✅ Woodlands-fw1: Passed Readiness Check: Check connectivity with the Panorama appliance
✅ Woodlands-fw1: Readiness Checks completed
🚀 Woodlands-fw1: Checking if HA peer is in sync...
🟧 Woodlands-fw1: HA peer state is not in sync. This will be noted, but the script will continue.
🚀 Woodlands-fw1: Performing backup of configuration to local filesystem...
🚀 Woodlands-fw1: Not a dry run, continue with upgrade...
🚀 Woodlands-fw1: Performing upgrade to version 10.2.3...
🚀 Woodlands-fw1: Attempting upgrade to version 10.2.3 (Attempt 1 of 3)...
Device 007954000123451 installing version: 10.2.3
✅ Woodlands-fw1: Upgrade completed successfully
🚀 Woodlands-fw1: Rebooting the passive HA target device...
📝 Woodlands-fw1: Command succeeded with no output
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
🔧 Woodlands-fw1: Target device is rebooting...
✅ Woodlands-fw1: HA passive target device rebooted and synchronized with its peer in 631 seconds
✅ panorama.cdot.io: Completed revisiting firewalls
```

</div>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

There are two primary methods to utilize the `pan-os-upgrade` tool: through a Python virtual environment or via a Docker container. Both methods are outlined below to cater to different preferences or requirements.

### Running with Python Virtual Environment

This approach involves setting up a Python virtual environment on your local machine and running the `pan-os-upgrade` tool within this isolated environment.

#### Python Prerequisites

- Python 3.8 or newer.
- Access to a Palo Alto Networks firewall or Panorama appliance.
- An active internet connection to download the package from PyPI.

#### Installation

The `pan-os-upgrade` library is available on PyPI and can be installed within a Python virtual environment. A virtual environment is a self-contained directory that contains a Python installation for a particular version of Python, plus a number of additional packages.

##### Creating a Python Virtual Environment

The steps below highlight the process for creating, activating, and installing `pan-os-upgrade` into a Python virtual environment. If you're new to Python, it may be beneficial to understand why this is such an important step, [here is a good writeup](https://realpython.com/python-virtual-environments-a-primer/) to prime yourself.

1. Create a Virtual Environment:

    ```bash
    python3 -m venv panos_env
    ```

    This command creates a new directory panos_env which contains a copy of the Python interpreter, the standard library, and various supporting files.

2. Activate the Virtual Environment:

    On Windows:

    ```bash
    panos_env\Scripts\activate
    ```

    On macOS and Linux:

    ```bash
    source panos_env/bin/activate
    ```

    After activation, your command line will indicate that you are now in the virtual environment.

3. Install `pan-os-upgrade`:

    Within the activated environment, use pip to install the package:

    ```bash
    pip install pan-os-upgrade
    ```

### CLI Arguments vs. CLI Options

In the context of the `pan-os-upgrade` application, it's important to distinguish between CLI arguments and CLI options:

- **CLI Arguments** are the primary commands that determine the operation mode of the application. They are not prefixed by `--` or `-` and are essential for defining the core action the script should perform.
- **CLI Options**, on the other hand, are additional modifiers or settings that further customize the behavior of the CLI arguments. They typically come with a `--` prefix (or `-` for shorthand) and are optional.

#### CLI Arguments

The following are the main commands (CLI arguments) for the `pan-os-upgrade` application, each tailored for specific upgrade scenarios:

| CLI Argument | Description                                                                                                                                                                                         |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `firewall`   | Targets an individual firewall for upgrade. This command requires subsequent CLI options to specify the firewall details and desired actions.                                                       |
| `panorama`   | Targets an individual Panorama appliance for upgrade, necessitating further CLI options for execution details.                                                                                      |
| `batch`      | Utilizes a Panorama appliance to orchestrate bulk upgrades of managed firewalls, supporting up to ten concurrent operations. Requires additional CLI options for filtering and execution specifics. |

#### CLI Options

Below are the CLI options that can be used in conjunction with the above CLI arguments to customize the upgrade process:

| CLI Option    | Shorthand | Type    | Description                                                                                                                               |
| ------------- | --------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `--dry-run`   | `-d`      | Boolean | Executes all preparatory steps without applying the actual upgrade, useful for testing and verification purposes.                         |
| `--filter`    | `-f`      | String  | Specifies criteria for selecting devices when performing batch upgrades via Panorama, such as device hostname patterns or serial numbers. |
| `--hostname`  | `-h`      | String  | The IP address or DNS name of the target firewall or Panorama appliance.                                                                  |
| `--log-level` | `-l`      | String  | Determines the verbosity of log output, with levels including debug, info, and warning among others.                                      |
| `--password`  | `-p`      | String  | The authentication password required for accessing the target device.                                                                     |
| `--username`  | `-u`      | String  | The username for authentication with the target PAN-OS device.                                                                            |
| `--version`   | `-v`      | String  | Specifies the target PAN-OS version for the upgrade operation.                                                                            |

Each CLI option has a specific role in tailoring the upgrade process, from defining the target device and authentication credentials to setting operational parameters like the target PAN-OS version and logging verbosity.

#### Option 1: Execute `pan-os-upgrade` without Command-Line Arguments

You can simply get started by issuing `pan-os-upgrade` from your current working directory, you will be guided to input the missing requirement arguments through an interactive shell.

```console
$ pan-os-upgrade firewall
Firewall hostname or IP: houston.cdot.io
Firewall username: cdot
Firewall password:
Target version: 10.2.4-h4
Dry Run? [y/N]: N
📝 houston: 007054000242050 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current version: 10.2.4-h3
📝 houston: Target version: 10.2.4-h4
✅ houston: Upgrade required from 10.2.4-h3 to 10.2.4-h4
✅ houston: version 10.2.4-h4 is available for download
✅ houston: Base image for 10.2.4-h4 is already downloaded
🚀 houston: Performing test to see if 10.2.4-h4 is already downloaded...
✅ houston: version 10.2.4-h4 already on target device.
✅ houston: version 10.2.4-h4 has been downloaded.
🚀 houston: Performing snapshot of network state information...
✅ houston: Network snapshot created successfully
🚀 houston: Performing readiness checks to determine if firewall is ready for upgrade...
✅ houston: Passed Readiness Check: Check if there are pending changes on device
✅ houston: Passed Readiness Check: No Expired Licenses
✅ houston: Passed Readiness Check: Check if NTP is synchronized
✅ houston: Passed Readiness Check: Check connectivity with the Panorama appliance
✅ houston: Readiness Checks completed
🚀 houston: Performing backup of configuration to local filesystem...
🚀 houston: Not a dry run, continue with upgrade...
🚀 houston: Performing upgrade to version 10.2.4-h4...
🚀 houston: Attempting upgrade to version 10.2.4-h4 (Attempt 1 of 3)...
Device 007054000242050 installing version: 10.2.4-h4
✅ houston: Upgrade completed successfully
🚀 houston: Rebooting the standalone target device...
📝 houston: Command succeeded with no output
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
📝 houston: Target device version: 10.2.4-h4
✅ houston: Target device rebooted in 448 seconds
```

##### Option 2: Execute `pan-os-upgrade` Using Command-Line Arguments

Alternatively, you can pass these details as command-line arguments when running the script.

> Note: You *can* pass your password as a CLI option with either `--password` or `-p`, but make sure you understand the risk of having your password in your terminal's history.

```bash
pan-os-upgrade firewall --hostname 192.168.1.1 --username admin --password secret --version 10.1.0
```

For a dry run:

```bash
pan-os-upgrade firewall --hostname 192.168.1.1 --username admin --password secret --version 10.1.0 --dry-run
```

If you're targeting a Panorama appliance to act as a proxy for communications to the firewall, make sure you include a filter pattern:

```bash
pan-os-upgrade batch --hostname panorama.cdot.io --username admin --password secret --version 10.1.0 --filter "hostname=Woodlands*"
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Running with Docker

Alternatively, you can run `pan-os-upgrade` as a Docker container. This method ensures that the tool runs in an isolated environment with all its dependencies packaged together.

#### Docker Prerequisites

- Docker installed on your system. You can download it from [Docker's official site](https://www.docker.com/products/docker-desktop).

#### Pulling the Docker Image

First, pull the `pan-os-upgrade` image from GitHub Packages:

```bash
docker pull ghcr.io/cdot65/pan-os-upgrade:latest
```

#### Running the Container

To run the container and mount local directories for `assurance` and `logs`, use the following commands:

On macOS and Linux:

```bash
docker run -v $(pwd)/assurance:/app/assurance -v $(pwd)/logs:/app/logs -it pan-os-upgrade firewall
```

On Windows:

```bash
docker run -v %CD%/assurance:/app/assurance -v %CD%/logs:/app/logs -it pan-os-upgrade panorama
```

These commands mount the current directory's `assurance` and `logs` subdirectories to the corresponding directories in the container. If these directories don't exist on your host, Docker will create them.

#### Interactive Mode

The container will start in interactive mode, prompting you for the necessary input like IP address, username, password, and target PAN-OS version.

#### Accessing Logs and Output

After the container stops, you can find the logs and other output files in the `assurance` and `logs` directories of your current working directory on your host machine.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

The script can be run from the command line with various options.

You can view all arguments by passing the `--help` flag:

```bash
$ pan-os-upgrade --help

 Usage: upgrade.py [OPTIONS] COMMAND [ARGS]...

 PAN-OS Upgrade script

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                                                            │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                                     │
│ --help                        Show this message and exit.                                                                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ batch         Executes a batch upgrade of firewalls managed by a Panorama appliance based on specified criteria.                                   │
│ firewall      Initiates the upgrade process for a specified firewall appliance.                                                                    │
│ panorama      Initiates the upgrade process for a specified Panorama appliance.                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

Refer to the [documentation](https://cdot65.github.io/pan-os-upgrade/) for more details on usage.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- OUTPUT -->
## Output

The script generates several files containing the state of the firewall and readiness checks. These files are stored in the `assurance` directory with the following structure:

- `snapshots`: Contains the pre and post-upgrade network state snapshots in JSON format.
- `readiness_checks`: Contains the results of readiness checks in JSON format.
- `configurations`: Contains the backup of the firewall's configuration in XML format.

<!-- LOGGING -->
## Logging

Log messages are printed to the console and saved to a rotating log file located in the `logs` directory. The log level can be set via the `--log-level` argument.

<!-- TROUBLESHOOTING -->
## Troubleshooting

Encountered an issue? Here are some common problems and solutions:

- **Problem**: Script fails to connect to the PAN-OS device.
  - **Solution**: Check if the hostname and credentials are correct. Ensure network connectivity to the PAN-OS device.

- **Problem**: Script hangs during execution.
  - **Solution**: Check the firewall and network settings. Ensure the PAN-OS device is responding correctly.

For more troubleshooting tips, visit our [FAQ section](https://cdot65.github.io/pan-os-upgrade/).

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request or open an issue with the tag "enhancement". Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [Contributing Guidelines](https://cdot65.github.io/pan-os-upgrade/about/contributing/) for detailed instructions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](https://cdot65.github.io/pan-os-upgrade/about/license/) file for details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

Email Address - cremsburg.dev at gmail.com

Project Link: [https://github.com/cdot65/pan-os-upgrade](https://github.com/cdot65/pan-os-upgrade)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Palo Alto Networks](https://www.paloaltonetworks.com/)
* [Python.org](https://python.org/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/cdot65/pan-os-upgrade.svg?style=for-the-badge
[contributors-url]: https://github.com/cdot65/pan-os-upgrade/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/cdot65/pan-os-upgrade.svg?style=for-the-badge
[forks-url]: https://github.com/cdot65/pan-os-upgrade/network/members
[stars-shield]: https://img.shields.io/github/stars/cdot65/pan-os-upgrade.svg?style=for-the-badge
[stars-url]: https://github.com/cdot65/pan-os-upgrade/stargazers
[issues-shield]: https://img.shields.io/github/issues/cdot65/pan-os-upgrade.svg?style=for-the-badge
[issues-url]: https://github.com/cdot65/pan-os-upgrade/issues
[license-shield]: https://img.shields.io/github/license/cdot65/pan-os-upgrade.svg?style=for-the-badge
[license-url]: https://github.com/cdot65/pan-os-upgrade/blob/main/LICENSE
