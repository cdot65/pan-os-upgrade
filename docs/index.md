---
hide:
    - navigation
---

<style>
.md-content .md-typeset h1 { display: none; }
</style>

<p align="center">
    <a href="https://paloaltonetworks.com"><img src="https://github.com/cdot65/pan-os-upgrade/blob/main/docs/images/logo.svg?raw=true" alt="PaloAltoNetworks"></a>
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

<a href="https://github.com/cdot65/pan-os-upgrade" target="_blank">pan-os-upgrade</a> is a modern Python CLI tool that provides a comprehensive automated workflow for PAN-OS firewalls. It offers two primary methods of execution: through a Python virtual environment or via a Docker container, catering to various operational requirements and preferences.

## Python Virtual Environment Workflow

This approach involves setting up a Python virtual environment and running `pan-os-upgrade` within this isolated environment, ensuring compatibility and preventing any conflicts with system-wide Python installations.

### Python Key Features

- Easy and isolated Python environment setup.
- Full control over the Python version and dependencies.
- Ideal for users familiar with Python and virtual environments.

### Python Getting Started

Install `pan-os-upgrade` via pip in a Python virtual environment and configure it using command-line arguments or an interactive shell. Detailed instructions can be found in the [User Guide](user-guide/python/getting-started.md).

## Docker Container Workflow

Running `pan-os-upgrade` in a Docker container encapsulates the tool and its dependencies in an isolated environment, simplifying setup and ensuring consistency across different systems.

### Docker Key Features

- Simplified setup process with Docker.
- Consistent runtime environment regardless of the host system.
- Suitable for users who prefer Docker or require containerized environments.

### Docker Getting Started

Pull the `pan-os-upgrade` Docker image, run the container with mounted directories for outputs, and interact with the tool in an isolated environment. More information is available in the [User Guide](user-guide/docker/getting-started.md).

---

Visit the [User Guide](user-guide/introduction.md) for detailed insights into setting up and running `pan-os-upgrade` using either Python or Docker workflows.

---

## Example

<div class="termy">

```console
$ pan-os-upgrade --hostname 192.168.255.211 --version 10.2.0-h2 --username admin --password paloalto#1
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

For more examples and usage scenarios, refer to the [Documentation](https://cdot65.github.io/pan-os-upgrade/).

---

### Release Notes

Updates with each release are tracked at [Release Notes](about/release-notes.md).

### Contributing

Contributions are welcome and greatly appreciated. Visit the [Contributing](about/contributing.md) page for guidelines on how to contribute.

### License

This project is licensed under the Apache 2.0 License - see the [License](about/license.md) page for details.
