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
$ pan-os-upgrade
Hostname or IP: panorama.cdot.io
Username: cdot
Password:
Target PAN-OS version: 10.2.2-h2
Filter string (only applicable for Panorama) []: hostname=Woodlands*
✅ panorama.cdot.io: Connection to Panorama established. Firewall connections will be proxied!
📝 Woodlands-fw1: 007954000123451 192.168.255.43
📝 Woodlands-fw2: 007954000123452 192.168.255.44
📝 Woodlands-fw1: HA mode: passive
📝 Woodlands-fw2: HA mode: active
🔍 Woodlands-fw2: Detected active firewall in HA pair running the same version as its peer. Added firewall to revisit list.
📝 Woodlands-fw1: Current PAN-OS version: 10.2.2
📝 Woodlands-fw1: Target PAN-OS version: 10.2.2-h2
✅ Woodlands-fw1: Upgrade required from 10.2.2 to 10.2.2-h2
✅ Woodlands-fw1: PAN-OS version 10.2.2-h2 is available for download
✅ Woodlands-fw1: Base image for 10.2.2-h2 is already downloaded
🚀 Woodlands-fw1: Performing test to see if 10.2.2-h2 is already downloaded...
🔍 Woodlands-fw1: PAN-OS version 10.2.2-h2 is not on the firewall
🚀 Woodlands-fw1: PAN-OS version 10.2.2-h2 is beginning download
Device 007954000123451 downloading version: 10.2.2-h2
🔧 Woodlands-fw1: Downloading PAN-OS version 10.2.2-h2 - HA will sync image - Elapsed time: 5 seconds
🔧 Woodlands-fw1: Downloading PAN-OS version 10.2.2-h2 - HA will sync image - Elapsed time: 37 seconds
🔧 Woodlands-fw1: Downloading PAN-OS version 10.2.2-h2 - HA will sync image - Elapsed time: 68 seconds
🔧 Woodlands-fw1: Downloading PAN-OS version 10.2.2-h2 - HA will sync image - Elapsed time: 100 seconds
🔧 Woodlands-fw1: Downloading PAN-OS version 10.2.2-h2 - HA will sync image - Elapsed time: 133 seconds
🔧 Woodlands-fw1: Downloading PAN-OS version 10.2.2-h2 - HA will sync image - Elapsed time: 167 seconds
✅ Woodlands-fw1: 10.2.2-h2 downloaded in 199 seconds
✅ Woodlands-fw1: 10.2.2-h2 has been downloaded and sync'd to HA peer.
🚀 Woodlands-fw1: Performing snapshot of network state information...
✅ Woodlands-fw1: Network snapshot created successfully
🚀 Woodlands-fw1: Performing readiness checks to determine if firewall is ready for upgrade...
✅ Woodlands-fw1: Passed Readiness Check: Check if there are pending changes on device
✅ Woodlands-fw1: Passed Readiness Check: No Expired Licenses
✅ Woodlands-fw1: Passed Readiness Check: Checks HA pair status from the perspective of the current device
✅ Woodlands-fw1: Passed Readiness Check: Check if NTP is synchronized
✅ Woodlands-fw1: Passed Readiness Check: Check connectivity with the Panorama appliance
✅ Woodlands-fw1: Readiness Checks completed
🚀 Woodlands-fw1: Checking if HA peer is in sync...
✅ Woodlands-fw1: HA peer sync test has been completed.
🚀 Woodlands-fw1: Performing backup of configuration to local filesystem...
🚀 Woodlands-fw1: Not a dry run, continue with upgrade...
🚀 Woodlands-fw1: Performing upgrade to version 10.2.2-h2...
🚀 Woodlands-fw1: Attempting upgrade to version 10.2.2-h2 (Attempt 1 of 3)...
Device 007954000123451 installing version: 10.2.2-h2
✅ Woodlands-fw1: Upgrade completed successfully
🚀 Woodlands-fw1: Rebooting the passive HA firewall...
📝 Woodlands-fw1: Command succeeded with no output
🔧 Woodlands-fw1: Firewall is rebooting...
🔧 Woodlands-fw1: Firewall is rebooting...
🔧 Woodlands-fw1: Firewall is rebooting...
🔧 Woodlands-fw1: Firewall is rebooting...
🔧 Woodlands-fw1: Firewall is rebooting...
🔧 Woodlands-fw1: Firewall is rebooting...
🔧 Woodlands-fw1: Firewall is rebooting...
✅ Woodlands-fw1: HA passive firewall rebooted and synchronized with its peer in 499 seconds
🚀 panorama.cdot.io: Revisiting firewalls that were active in an HA pair and had the same version as their peers.
📝 Woodlands-fw2: 007954000123452 192.168.255.44
📝 Woodlands-fw2: HA mode: active
❌ Woodlands-fw2: Error suspending active firewall HA state: argument of type 'NoneType' is not iterable
📝 Woodlands-fw2: Current PAN-OS version: 10.2.2
📝 Woodlands-fw2: Target PAN-OS version: 10.2.2-h2
✅ Woodlands-fw2: Upgrade required from 10.2.2 to 10.2.2-h2
✅ Woodlands-fw2: PAN-OS version 10.2.2-h2 is available for download
✅ Woodlands-fw2: Base image for 10.2.2-h2 is already downloaded
🚀 Woodlands-fw2: Performing test to see if 10.2.2-h2 is already downloaded...
✅ Woodlands-fw2: PAN-OS version 10.2.2-h2 already on firewall.
✅ Woodlands-fw2: 10.2.2-h2 has been downloaded and sync'd to HA peer.
🚀 Woodlands-fw2: Performing snapshot of network state information...
✅ Woodlands-fw2: Network snapshot created successfully
🚀 Woodlands-fw2: Performing readiness checks to determine if firewall is ready for upgrade...
✅ Woodlands-fw2: Passed Readiness Check: Check if there are pending changes on device
✅ Woodlands-fw2: Passed Readiness Check: No Expired Licenses
✅ Woodlands-fw2: Passed Readiness Check: Check if NTP is synchronized
✅ Woodlands-fw2: Passed Readiness Check: Check connectivity with the Panorama appliance
✅ Woodlands-fw2: Readiness Checks completed
🚀 Woodlands-fw2: Checking if HA peer is in sync...
✅ Woodlands-fw2: HA peer sync test has been completed.
🚀 Woodlands-fw2: Performing backup of configuration to local filesystem...
🚀 Woodlands-fw2: Not a dry run, continue with upgrade...
🚀 Woodlands-fw2: Performing upgrade to version 10.2.2-h2...
🚀 Woodlands-fw2: Attempting upgrade to version 10.2.2-h2 (Attempt 1 of 3)...
Device 007954000123452 installing version: 10.2.2-h2
✅ Woodlands-fw2: Upgrade completed successfully
🚀 Woodlands-fw2: Rebooting the passive HA firewall...
📝 Woodlands-fw2: Command succeeded with no output
🔧 Woodlands-fw2: Firewall is rebooting...
🔧 Woodlands-fw2: Firewall is rebooting...
🔧 Woodlands-fw2: Firewall is rebooting...
🔧 Woodlands-fw2: Firewall is rebooting...
🔧 Woodlands-fw2: Firewall is rebooting...
🔧 Woodlands-fw2: Firewall is rebooting...
🔧 Woodlands-fw2: Firewall is rebooting...
✅ Woodlands-fw2: HA passive firewall rebooted and synchronized with its peer in 483 seconds
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

* Python 3.8 or newer.
* Access to a Palo Alto Networks firewall.
* An active internet connection to download the package from PyPI.

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

#### Setting Up Your Environment

After setting up the virtual environment and installing the package, you can configure your environment to use the library. This can be done using command-line arguments or using the interactive shell.

##### Option 1: Execute `pan-os-upgrade` without Command-Line Arguments

You can simply get started by issuing `pan-os-upgrade` from your current working directory, you will be guided to input the missing requirement arguments through an interactive shell.

```console
$ pan-os-upgrade
Hostname or IP: houston.cdot.io
Username: cdot
Password:
Target PAN-OS version: 10.2.4
Filter string (only applicable for Panorama connections) []:
✅ houston.cdot.io: Connection to firewall established
📝 houston: 007954000123453 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current PAN-OS version: 10.2.3-h4
📝 houston: Target PAN-OS version: 10.2.4
✅ houston: Upgrade required from 10.2.3-h4 to 10.2.4
✅ houston: PAN-OS version 10.2.4 is available for download
✅ houston: Base image for 10.2.4 is already downloaded
🚀 houston: Performing test to see if 10.2.4 is already downloaded...
🔍 houston: PAN-OS version 10.2.4 is not on the firewall
🚀 houston: PAN-OS version 10.2.4 is beginning download
Device 007954000123453 downloading version: 10.2.4
🔧 houston: Downloading PAN-OS version 10.2.4 - Elapsed time: 11 seconds
🔧 houston: Downloading PAN-OS version 10.2.4 - Elapsed time: 48 seconds
🔧 houston: Downloading PAN-OS version 10.2.4 - Elapsed time: 84 seconds
✅ houston: 10.2.4 downloaded in 118 seconds
✅ houston: PAN-OS version 10.2.4 has been downloaded.
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
🚀 houston: Performing upgrade to version 10.2.4...
🚀 houston: Attempting upgrade to version 10.2.4 (Attempt 1 of 3)...
Device 007954000123453 installing version: 10.2.4
✅ houston: Upgrade completed successfully
🚀 houston: Rebooting the standalone firewall...
📝 houston: Command succeeded with no output
🔧 houston: Firewall is rebooting...
🔧 houston: Firewall is rebooting...
🔧 houston: Firewall is rebooting...
🔧 houston: Firewall is rebooting...
🔧 houston: Firewall is rebooting...
🔧 houston: Firewall is rebooting...
📝 houston: Firewall version: 10.2.4
✅ houston: Firewall rebooted in 516 seconds
```

As an alternative to targeting firewalls directly, you can target a Panorama appliance to act as the communication proxy. If you'd like to go down this path, make sure that you add an extra CLI option of `--filter` and pass a string representation of your filter.

As of version 0.2.5, the available filters are:

| filter type | description                                       | example                             |
| ----------- | ------------------------------------------------- | ----------------------------------- |
| hostname    | use the firewall's hostname as selection criteria | `--filter "hostname=Woodlands*"`    |
| serial      | use the firewall's serial as selection criteria   | `--filter "serial=007054000123456"` |

```console
$ pan-os-upgrade
Hostname or IP: panorama.cdot.io
Username: cdot
Password:
Target PAN-OS version: 10.2.2-h2
Filter string (only applicable for Panorama connections) []: hostname=Woodlands*
✅ panorama.cdot.io: Connection to Panorama established. Firewall connections will be proxied!
📝 Woodlands-fw1: 007954000123451 192.168.255.43
📝 Woodlands-fw2: 007954000123452 192.168.255.44
📝 Woodlands-fw1: HA mode: passive
📝 Woodlands-fw2: HA mode: active
🔍 Woodlands-fw2: Detected active firewall in HA pair running the same version as its peer. Added firewall to revisit list.
📝 Woodlands-fw1: Current PAN-OS version: 10.2.2
📝 Woodlands-fw1: Target PAN-OS version: 10.2.2-h2
✅ Woodlands-fw1: Upgrade required from 10.2.2 to 10.2.2-h2
✅ Woodlands-fw1: PAN-OS version 10.2.2-h2 is available for download
✅ Woodlands-fw1: Base image for 10.2.2-h2 is already downloaded
🚀 Woodlands-fw1: Performing test to see if 10.2.2-h2 is already downloaded...
🔍 Woodlands-fw1: PAN-OS version 10.2.2-h2 is not on the firewall
🚀 Woodlands-fw1: PAN-OS version 10.2.2-h2 is beginning download
Device 007954000123451 downloading version: 10.2.2-h2
🔧 Woodlands-fw1: Downloading PAN-OS version 10.2.2-h2 - HA will sync image - Elapsed time: 5 seconds
... shortened for brevity ...
```

##### Option 2: Execute `pan-os-upgrade` Using Command-Line Arguments

Alternatively, you can pass these details as command-line arguments when running the script:

```bash
pan-os-upgrade --hostname 192.168.1.1 --username admin --password secret --version 10.1.0
```

For a dry run:

```bash
pan-os-upgrade --hostname 192.168.1.1 --username admin --password secret --version 10.1.0 --dry-run
```

If you're targeting a Panorama appliance to act as a proxy for communications to the firewall, make sure you also pass a filter pattern:

```bash
pan-os-upgrade --hostname panorama.cdot.io --username admin --password secret --version 10.1.0 --filter "hostname=houston"
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Running with Docker

Alternatively, you can run `pan-os-upgrade` as a Docker container. This method ensures that the tool runs in an isolated environment with all its dependencies packaged together.

#### Docker Prerequisites

* Docker installed on your system. You can download it from [Docker's official site](https://www.docker.com/products/docker-desktop).

#### Pulling the Docker Image

First, pull the `pan-os-upgrade` image from GitHub Packages:

```bash
docker pull ghcr.io/cdot65/pan-os-upgrade:latest
```

#### Running the Container

To run the container and mount local directories for `assurance` and `logs`, use the following commands:

On macOS and Linux:

```bash
docker run -v $(pwd)/assurance:/app/assurance -v $(pwd)/logs:/app/logs -it pan-os-upgrade
```

On Windows:

```bash
docker run -v %CD%/assurance:/app/assurance -v %CD%/logs:/app/logs -it pan-os-upgrade
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
pan-os-upgrade --help
```

### CLI Arguments Description

| cli argument  | shorthand | type        | description                                                                         |
| ------------- | --------- | ----------- | ----------------------------------------------------------------------------------- |
| `--dry-run`   | `-d`      | n/a         | Perform a dry run of all tests and downloads without performing the actual upgrade. |
| `--filter`    | `-f`      | conditional | Filter criteria for selecting devices when using Panorama.                          |
| `--hostname`  | `-h`      | text        | Hostname or IP address of target firewall.                                          |
| `--log-level` | `-l`      | text        | Set the logging output level (e.g., debug, info, warning).                          |
| `--password`  | `-p`      | text        | Password for authentication.                                                        |
| `--username`  | `-u`      | text        | Username for authentication.                                                        |
| `--version`   | `-v`      | text        | Target PAN-OS version to upgrade to.                                                |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

Refer to the [documentation](https://cdot65.github.io/pan-os-upgrade/) for more details on usage.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- OUTPUT -->
## Output

The script generates several files containing the state of the firewall and readiness checks. These files are stored in the `assurance` directory with the following structure:

* `snapshots`: Contains the pre and post-upgrade network state snapshots in JSON format.
* `readiness_checks`: Contains the results of readiness checks in JSON format.
* `configurations`: Contains the backup of the firewall's configuration in XML format.

<!-- LOGGING -->
## Logging

Log messages are printed to the console and saved to a rotating log file located in the `logs` directory. The log level can be set via the `--log-level` argument.

<!-- TROUBLESHOOTING -->
## Troubleshooting

Encountered an issue? Here are some common problems and solutions:

* **Problem**: Script fails to connect to the PAN-OS device.
  * **Solution**: Check if the hostname and credentials are correct. Ensure network connectivity to the PAN-OS device.

* **Problem**: Script hangs during execution.
  * **Solution**: Check the firewall and network settings. Ensure the PAN-OS device is responding correctly.

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
