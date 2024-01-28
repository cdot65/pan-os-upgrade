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
        <a href="https://cdot65.github.io/pan-os-upgrade"><strong>Documentation Website »</strong></a>
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
        <li><a href="#usage">Usage</a></li>
        <li><a href="#contributing">Contributing</a></li>
        <li><a href="#license">License</a></li>
        <li><a href="#contact">Contact</a></li>
        <li><a href="#acknowledgments">Acknowledgments</a></li>
    </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

This project is a comprehensive Python-based solution for automating PAN-OS upgrades. It's designed to provide network administrators and security professionals with an efficient tool to manage upgrades, configurations, and system checks of Palo Alto Networks appliances.

Project Link: [https://github.com/cdot65/pan-os-upgrade](https://github.com/cdot65/pan-os-upgrade)
Documentation: [https://cdot65.github.io/pan-os-upgrade/](https://cdot65.github.io/pan-os-upgrade/)

### Key Features

- **Three Unique Upgrade Workflows Supported**:
  - `firewall`: targets and upgrades an individual firewall
  - `panorama`: targets and upgrades an individual Panorama appliance
  - `batch`: targets a Panorama appliance and upgrades firewalls in batch
    - The script will support up to ten simultaneous upgrades
- **Automation of Routine Tasks**: Reduces manual errors and saves time by automating upgrades, configurations, and system checks.
- **Support for Direct and Proxy Connections**: Connect directly to firewalls or through a Panorama appliance, with support for targeting specific devices using filters.
- **Active/Passive High Availability (HA) Workflow**: Fully supports upgrading devices in active/passive HA configurations, ensuring both members are properly upgraded and synchronized.
- **Multi-threading for Efficiency**: Utilizes multi-threading to parallelize upgrades, especially beneficial when upgrading multiple devices through Panorama, enhancing performance and reducing overall upgrade time.
- **Customizable and Extensible**: Execution of the script can be tailored to fit diverse network environments and requirements, offering flexibility for various deployment scenarios.
- **Comprehensive PAN-OS Interactions**: Facilitates extensive interactions with Palo Alto Networks appliances for operations like readiness checks, state snapshots, and report generation.

> **Note**: While this script is optimized for standalone and active/passive HA environments, it has not been tested against active/active or clustered firewalls.

Example Execution

<div class="termy">

```console
pan-os-upgrade batch
Panorama hostname or IP: panorama.cdot.io
Panorama username: cdot
Panorama password:
Firewall target version (ex: 10.1.2): 10.2.3
Filter string (ex: hostname=Woodlands*) []: hostname=Woodlands*
Dry Run? [y/N]:
===========================================================================
Welcome to the PAN-OS upgrade tool

You have selected to perform a batch upgrade of firewalls through Panorama.

No settings.yaml file was found. Default values will be used.
Create a settings.yaml file with 'pan-os-upgrade settings' command.
===========================================================================
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

<!-- USAGE -->
## Usage

There are two primary methods to utilize the `pan-os-upgrade` tool: through a Python virtual environment or via a Docker container.

Please refer to the dedicated documentation website to understand how to use this tool.

Documentation Site: [https://cdot65.github.io/pan-os-upgrade/](https://cdot65.github.io/pan-os-upgrade/)

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
