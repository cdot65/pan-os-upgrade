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
    <img src="images/logo.svg" alt="Logo">
    <h3 align="center">PAN-OS Automation Project</h3>
    <p align="center">
        Automating PAN-OS upgrades using Python
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
        <li>
            <a href="#about-the-project">About The Project</a>
            <ul>
                <li><a href="#built-with">Built With</a></li>
            </ul>
        </li>
        <li>
            <a href="#getting-started">Getting Started</a>
            <ul>
                <li><a href="#prerequisites">Prerequisites</a></li>
                <li><a href="#installation">Installation</a></li>
            </ul>
        </li>
        <li><a href="#usage">Usage</a></li>
        <li><a href="#contributing">Contributing</a></li>
        <li><a href="#license">License</a></li>
        <li><a href="#contact">Contact</a></li>
        <li><a href="#acknowledgments">Acknowledgments</a></li>
    </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

[![Project Screenshot][product-screenshot]](https://paloaltonetworks.com)

This project is a comprehensive Python-based solution for automating PAN-OS upgrades. It's designed to provide network administrators and security professionals with an efficient tool to manage upgrades, configurations, and system checks of Palo Alto Networks appliances.

Key Features:

* Automates routine tasks, reducing manual errors and saving time.
* Customizable scripts to fit various network environments and requirements.
* Extensive interaction with Palo Alto Networks appliances for operations like readiness checks, state snapshots, and report generation.

> Note: this script is targeted towards standalone and `active-passive` HA environments, no testing has been performed against `active-active` or clustered firewalls.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

This project is built with the following technologies:

* [Python](https://python.org/)
* [pan-os-python SDK](https://github.com/PaloAltoNetworks/pan-os-python)
* [panos-upgrade-assurance](https://github.com/PaloAltoNetworks/pan-os-upgrade-assurance)
* [Pydantic](https://docs.pydantic.dev/latest/)
* [xmltodict](https://pypi.org/project/xmltodict/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Prerequisites

* Python 3.x
* Access to a Palo Alto Networks firewall.
* Required Python packages: (found in [requirements.txt](https://github.com/cdot65/pan-os-upgrade/blob/main/requirements.txt) file).

## Getting Started

To get started with the PAN-OS upgrade project, you need to set up your environment and install the necessary dependencies.

### Installation

Clone the repository

```bash
git clone https://github.com/cdot65/pan-os-upgrade.git
cd pan-os-upgrade
```

Before running the script, ensure you have Python installed on your system. If you're new to Python, here's how you can set up a virtual environment, which allows us to install Python packages without having them conflict with our system's Python environment:

* Setting up a virtual environment

If you have Poetry on your machine, simply type `poetry install` and `poetry shell` to activate this project's virtual environment.

If Poetry is not installed, then you can build and activate the Python virtual enviornment manually.

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Once the virutal environment has been created and activated, install the required packages

```bash
pip install -r requirements.txt
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

### Define Variables Within .env

As an alternative to passing CLI arguments, which can be a security risk due to your console's history function, you can instead update the variables within the `.env` file of your project.

These environment variables will be used when CLI arguments are not provided, feel free to mix and match CLI arguments and hardcoded values within the .env file. Just note that if you're using an API key for authentication, leave the username and password blank.

> note: CLI arguments will take precedent of .env file

```env
# PAN-OS credientials if using an API key, leave username and password blank
PAN_USERNAME=admin
PAN_PASSWORD=paloalto123
API_KEY=

# hostname or IP address
HOSTNAME=firewall1.example.com

# target PAN-OS version
TARGET_VERSION=11.0.2-h3

# manage the levels of logging of the script debug, info, warning, error, critical
LOG_LEVEL=debug

# dry run will not perform the actual upgrade process
DRY_RUN=

```

Then execute your script as follows:

```bash
python upgrade.py
```

### Dry Run

To execute a dry run (which performs checks without upgrading):

   ```bash
   python upgrade.py --hostname 192.168.1.1 --username admin --password secret --version 10.0.0 --dry-run
   ```

For more details on the usage and examples, refer to the [documentation](https://cdot65.github.io/pan-os-upgrade/).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

Refer to the [documentation](https://github.com/cdot65/pan-os-upgrade) for more details on usage.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Output

The script generates several files containing the state of the firewall and readiness checks. These files are stored in the `assurance` directory with the following structure:

* `snapshots`: Contains the pre and post-upgrade network state snapshots in JSON format.
* `readiness_checks`: Contains the results of readiness checks in JSON format.
* `configurations`: Contains the backup of the firewall's configuration in XML format.

## Logging

Log messages are printed to the console and saved to a rotating log file located in the `logs` directory. The log level can be set via the `--log-level` argument.

<!-- TROUBLESHOOTING -->
## Troubleshooting

Encountered an issue? Here are some common problems and solutions:

* **Problem**: Script fails to connect to the PAN-OS device.
  * **Solution**: Check if the hostname and credentials are correct. Ensure network connectivity to the PAN-OS device.

* **Problem**: Error regarding missing dependencies.
  * **Solution**: Ensure all required packages are installed using `pip install -r requirements.txt`.

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
