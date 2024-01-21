---
hide:
  - navigation
---

<style>
.md-content .md-typeset h1 { display: none; }
</style>

<p align="center">
  <a href="https://paloaltonetworks.com"><img src="https://github.com/cdot65/pan-os-upgrade/blob/main/images/logo.svg?raw=true" alt="PaloAltoNetworks"></a>
</p>
<p align="center">
    <em><code>pan-os-upgrade</code>, a Python CLI tool to help automate the upgrade process for PAN-OS firewalls using Typer</em>
</p>
<p align="center">
<a href="https://github.com/cdot65/pan-os-upgrade/graphs/contributors" target="_blank">
    <img src="https://img.shields.io/github/contributors/cdot65/pan-os-upgrade.svg?style=for-the-badge" alt="Contributors">
</a>
<a href="https://github.com/cdot65/pan-os-upgrade/network/members" target="_blank">
    <img src="https://img.shields.io/github/forks/cdot65/pan-os-upgrade.svg?style=for-the-badge" alt="Forks">
</a>
<a href="https://github.com/cdot65/pan-os-upgrade/stargazers" target="_blank">
    <img src="https://img.shields.io/github/stars/cdot65/pan-os-upgrade.svg?style=for-the-badge" alt="Stars">
</a>
<a href="https://github.com/cdot65/pan-os-upgrade/issues" target="_blank">
    <img src="https://img.shields.io/github/issues/cdot65/pan-os-upgrade.svg?style=for-the-badge" alt="Issues">
</a>
</p>

---

**Documentation**: <a href="https://cdot65.github.io/pan-os-upgrade/" target="_blank">https://cdot65.github.io/pan-os-upgrade/</a>

**Source Code**: <a href="https://github.com/cdot65/pan-os-upgrade" target="_blank">https://github.com/cdot65/pan-os-upgrade</a>

---

<a href="https://github.com/cdot65/pan-os-upgrade" target="_blank">pan-os-upgrade</a> is a modern Python CLI tool that provides a comprehensive automated workflow for PAN-OS firewalls.

The key features of the `pan-os-upgrade` library are:

* **Easy to Use**: Designed with simplicity in mind, the `pan-os-upgrade` script offers an intuitive interface, minimizing the need for extensive documentation perusal. Users can quickly learn to use the tool, saving valuable time and effort.

* **Resilient**: Built with robust error handling and recovery mechanisms, the script can gracefully manage various nuances and mechanical intricacies of firewall upgrades. This resilience ensures reliable operations even in complex network environments.

* **Robust Workflow Coverage**: Capable of handling a wide range of upgrade workflows, the script is adaptable to different network configurations and requirements. This flexibility makes it suitable for various scenarios, from standalone setups to complex HA environments.

* **Strong Typing**: Employing Python’s strong typing features, the script enhances code clarity and reduces the likelihood of type-related bugs. This approach contributes to the overall stability and reliability of the upgrade process.

* **Data Modeling with Pydantic**: Utilizing Pydantic for data validation, the `pan-os-upgrade` script ensures that input and output data are accurately modeled. This feature significantly reduces bugs and enhances the predictability of operations, leading to smoother upgrade experiences.

## Requirements

Python 3.8+

`pan-os-upgrade` stands on the shoulders of giants:

* <a href="https://github.com/PaloAltoNetworks/pan-os-python" target="_blank">pan-os-python</a> for handling all interactions with PAN-OS firewalls.
* <a href="https://github.com/PaloAltoNetworks/pan-os-upgrade-assurance" target="_blank">panos-upgrade-assurance</a> for performing Readiness Checks, Snapshots, Health Checks, and Reporting.
* <a href="https://docs.pydantic.dev/latest/">Pydantic</a> for handling the data modeling and validation.
* <a href="https://typer.tiangolo.com/">Typer</a> for handling the data modeling and validation.

## Installation

<div class="termy">

```console
$ pip install pan-os-upgrade

---> 100%
```

</div>

## Example

<div class="termy">

```console
$ pan-os-upgrade --ip-address 192.168.255.211 --version 10.2.0-h2 --username admin --password paloalto#1
INFO - ✅ Connection to firewall established
INFO - 📝 007054000123456 houston 192.168.255.211
INFO - 📝 Firewall HA mode: disabled
INFO - 📝 Current PAN-OS version: 10.2.0
INFO - 📝 Target PAN-OS version: 10.2.0-h2
INFO - ✅ Confirmed that moving from 10.2.0 to 10.2.0-h2 is an upgrade
INFO - ✅ Target PAN-OS version 10.2.0-h2 is available for download
INFO - ✅ Base image for 10.2.0-h2 is already downloaded
INFO - 🚀 Performing test to see if 10.2.0-h2 is already downloaded...
INFO - 🔍 PAN-OS version 10.2.0-h2 is not on the firewall
INFO - 🚀 PAN-OS version 10.2.0-h2 is beginning download
INFO - Device 007054000123456 downloading version: 10.2.0-h2
INFO - ⚙️ Downloading PAN-OS version 10.2.0-h2 - Elapsed time: 4 seconds
INFO - ⚙️ Downloading PAN-OS version 10.2.0-h2 - Elapsed time: 36 seconds
INFO - ⚙️ Downloading PAN-OS version 10.2.0-h2 - Elapsed time: 71 seconds
INFO - ✅ 10.2.0-h2 downloaded in 103 seconds
INFO - ✅ PAN-OS version 10.2.0-h2 has been downloaded.
INFO - 🚀 Performing snapshot of network state information...
INFO - ✅ Network snapshot created successfully
INFO - 🚀 Performing readiness checks to determine if firewall is ready for upgrade...
INFO - ✅ Passed Readiness Check: Check if there are pending changes on device
INFO - ✅ Passed Readiness Check: No Expired Licenses
INFO - ✅ Passed Readiness Check: Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.
INFO - ✅ Passed Readiness Check: Check if NTP is synchronized
INFO - ✅ Passed Readiness Check: Check connectivity with the Panorama appliance
INFO - ✅ Readiness Checks completed
INFO - 🚀 Performing backup of houston's configuration to local filesystem...
INFO - 🚀 Not a dry run, continue with upgrade...
INFO - 🚀 Performing upgrade on houston to version 10.2.0-h2...
INFO - 🚀 Attempting upgrade houston to version 10.2.0-h2 (Attempt 1 of 3)...
INFO - Device 007054000123456 installing version: 10.2.0-h2
INFO - ✅ houston upgrade completed successfully
INFO - 🚀 Rebooting the firewall...
INFO - 📝 Command succeeded with no output
INFO - ⚙️ Firewall is responding to requests but hasn't finished its reboot process...
INFO - ⚙️ Firewall is rebooting...
INFO - ⚙️ Firewall is rebooting...
INFO - ⚙️ Firewall is rebooting...
INFO - ⚙️ Firewall is rebooting...
INFO - ⚙️ Firewall is rebooting...
INFO - ⚙️ Firewall is rebooting...
INFO - ⚙️ Firewall is rebooting...
INFO - ⚙️ Firewall is responding to requests but hasn't finished its reboot process...
INFO - ⚙️ Firewall is responding to requests but hasn't finished its reboot process...
INFO - ✅ Firewall upgraded and rebooted in 343 seconds

```

</div>

## Next Steps

### Getting Started

Visit the [User Guide](user-guide/introduction.md) for detailed insights into getting up and running.

### API Documentation

Visit the [Developer Documentation](reference/pan_os_upgrade.md) reference page for detailed documentation on the library's code.

### Contributing

Visit the [Contributing](about/contributing.md) page to understand how you can contribute to the project.

### License

Visit the [License](about/license.md) for information about the project's licensing.
