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
    <img src="https://github.com/cdot65/pan-os-upgrade/blob/main/images/logo.svg?raw=true" alt="Logo">
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

Key Features:

* Automates routine tasks, reducing manual errors and saving time.
* Customizable scripts to fit various network environments and requirements.
* Extensive interaction with Palo Alto Networks appliances for operations like readiness checks, state snapshots, and report generation.

> Note: this script is targeted towards standalone and `active-passive` HA environments, no testing has been performed against `active-active` or clustered firewalls.

Example Screenshot

![Example Screenshot](https://github.com/cdot65/pan-os-upgrade/blob/main/images/screenshot.jpg?raw=true)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

This guide will help you set up the `pan-os-upgrade` library in your environment, especially focusing on users who are new to Python and virtual environments.

### Prerequisites

* Python 3.8 or newer.
* Access to a Palo Alto Networks firewall.
* An active internet connection to download the package from PyPI.

### Installation

The `pan-os-upgrade` library is available on PyPI and can be installed within a Python virtual environment. A virtual environment is a self-contained directory that contains a Python installation for a particular version of Python, plus a number of additional packages.

#### Using `python3 -m venv` (Recommended for Beginners)

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

### Using Poetry (Advanced Users)

Poetry is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.

1. Install Poetry:

    Follow [the official instructions](https://python-poetry.org/docs/) to install Poetry on your system.

2. Create a New Project using Poetry:

    ```bash
    poetry new panos_project
    cd panos_project
    ```

3. Add `pan-os-upgrade` as a Dependency:

    ```bash
    poetry add pan-os-upgrade
    ```

    This command will create a virtual environment and install the `pan-os-upgrade` package along with its dependencies.

4. Activate the Poetry Shell:

    To activate the virtual environment created by Poetry, use:

    ```bash
    poetry shell
    ```

### Setting Up Your Environment

After setting up the virtual environment and installing the package, you can configure your environment to use the library. This can be done using command-line arguments or an .env file.

#### Option 1: Using an .env File

Create a `.env` file in your local directory and fill it with your firewall's details:

```env
# PAN-OS credentials - use either API key or username/password combination
PAN_USERNAME=admin
PAN_PASSWORD=paloalto123
API_KEY=

# Hostname or IP address of the firewall
HOSTNAME=firewall1.example.com

# Target PAN-OS version for the upgrade
TARGET_VERSION=11.0.2-h3

# Logging level (e.g., debug, info, warning, error, critical)
LOG_LEVEL=debug

# Set to true for a dry run
DRY_RUN=false
```

#### Option 2: Using Command-Line Arguments

Alternatively, you can pass these details as command-line arguments when running the script:

```bash
pan-os-upgrade --hostname 192.168.1.1 --username admin --password secret --version 10.1.0
```

For a dry run:

```bash
pan-os-upgrade --hostname 192.168.1.1 --username admin --password secret --version 10.1.0 --dry-run
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

The script can be run from the command line with various options. It requires at least the hostname (or IP address) and the target PAN-OS version for the firewall. Authentication can be done via API key or username and password.

### CLI Arguments Description

* `--api-key`: API Key for authentication
* `--dry-run`: Perform a dry run of all tests and downloads without performing the actual upgrade.
* `--hostname`: Hostname or IP address of the PAN-OS firewall.
* `--log-level`: Set the logging output level (e.g., debug, info, warning).
* `--password`: Password for authentication.
* `--username`: Username for authentication.
* `--version`: Target PAN-OS version to upgrade to.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

Refer to the [documentation](https://github.com/cdot65/pan-os-upgrade) for more details on usage.

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

For more troubleshooting tips, visit our [FAQ section](#).

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request or open an issue with the tag "enhancement". Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [Contributing Guidelines](#) for detailed instructions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

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
[product-screenshot]: https://github.com/cdot65/pan-os-upgrade/blob/main/images/screenshot.jpg
