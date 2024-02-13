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
    <em><code>pan-os-upgrade</code>, a Python CLI tool to help automate the upgrade process for PAN-OS firewalls</em>
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
<a href="https://github.com/cdot65/pan-os-upgrade/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/github/license/cdot65/pan-os-upgrade.svg?style=for-the-badge" alt="License">
</a>
</p>

---

**Documentation**: <a href="https://cdot65.github.io/pan-os-upgrade/" target="_blank">https://cdot65.github.io/pan-os-upgrade/</a>

**Source Code**: <a href="https://github.com/cdot65/pan-os-upgrade" target="_blank">https://github.com/cdot65/pan-os-upgrade</a>

---

<a href="https://github.com/cdot65/pan-os-upgrade" target="_blank">pan-os-upgrade</a> is a modern Python CLI tool that provides a comprehensive automated workflow for PAN-OS firewalls. It offers two primary methods of execution: through a Python virtual environment or via a Docker container, catering to various operational requirements and preferences.

## Key Features

- **Three Unique Upgrade Workflows Supported**:
  - `firewall`: targets and upgrades an individual firewall
  - `panorama`: targets and upgrades an individual Panorama appliance
  - `batch`: targets a Panorama appliance and upgrades firewalls in batch
- **Automation of Routine Tasks**: Reduces manual errors and saves time by automating upgrades, configurations, and system checks.
- **Support for Direct and Proxy Connections**: Connect directly to firewalls or through a Panorama appliance, with support for targeting specific devices using filters.
- **Pre/Post Diff**: Network snapshots are taken before and after the upgrade process, providing a PDF report of changes within the network environment after the upgrade completes.
- **Active/Passive High Availability (HA) Workflow**: Fully supports upgrading devices in active/passive HA configurations, ensuring both members are properly upgraded and synchronized.
- **Multi-threading for Efficiency**: Utilizes multi-threading to parallelize upgrades, especially beneficial when upgrading multiple devices through Panorama, enhancing performance and reducing overall upgrade time.
- **Customizable and Extensible**: Execution of the script can be tailored to fit diverse network environments and requirements, offering flexibility for various deployment scenarios.
- **Comprehensive PAN-OS Interactions**: Facilitates extensive interactions with Palo Alto Networks appliances for operations like readiness checks, state snapshots, and report generation.

---

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
pan-os-upgrade batch
Panorama hostname or IP: panorama.cdot.io
Panorama username: officehours
Panorama password:
Firewall target version (ex: 10.1.2): 10.1.3-h2
Dry Run? [Y/n]: n
===========================================================================
Welcome to the PAN-OS upgrade tool

You have selected to perform a batch upgrade of firewalls through Panorama.

No settings.yaml file was found, the script's default values will be used.
Create a settings.yaml file with 'pan-os-upgrade settings' command.

No inventory.yaml file was found, getting firewalls connected to Panorama.
Create an inventory.yaml file with 'pan-os-upgrade inventory' command.
===========================================================================
✅ panorama.cdot.io: Connection to Panorama established. Firewall connections will be proxied!
🔧 panorama.cdot.io: Retrieving a list of all firewalls connected to Panorama...
🔧 panorama.cdot.io: Retrieving detailed information of each firewall...
╒═════╤═══════════════╤═════════════════╤═════════╤═════════════════╤══════════════╤═══════════════╕
│   # │ Hostname      │ IP Address      │ Model   │          Serial │ SW Version   │ App Version   │
╞═════╪═══════════════╪═════════════════╪═════════╪═════════════════╪══════════════╪═══════════════╡
│   1 │ Woodlands-fw1 │ 192.168.255.43  │ PA-VM   │ 007954000123451 │ 10.1.3       │ 8729-8157     │
├─────┼───────────────┼─────────────────┼─────────┼─────────────────┼──────────────┼───────────────┤
│   2 │ Woodlands-fw2 │ 192.168.255.44  │ PA-VM   │ 007954000123452 │ 10.1.3       │ 8729-8157     │
├─────┼───────────────┼─────────────────┼─────────┼─────────────────┼──────────────┼───────────────┤
│   3 │ houston       │ 192.168.255.211 │ PA-VM   │ 007954000123453 │ 10.1.3       │ 8797-8498     │
╘═════╧═══════════════╧═════════════════╧═════════╧═════════════════╧══════════════╧═══════════════╛
You can select devices by entering their numbers, ranges, or separated by commas.
Examples: '1', '2-4', '1,3,5-7'.
Type 'done' on a new line when finished.

Enter your selection(s): 1,2
Woodlands-fw1 selected.
Woodlands-fw2 selected.
Enter your selection(s): done
📝 panorama.cdot.io: Upgrading 2 devices to version 10.1.3-h2...
📝 panorama.cdot.io: Please confirm the selected firewalls:
  - Woodlands-fw1 (192.168.255.43)
  - Woodlands-fw2 (192.168.255.44)
🟧 panorama.cdot.io: Dry run mode is disabled, upgrade workflow will be executed.
Do you want to proceed with the upgrade? [y/N]: y
🚀 Proceeding with the upgrade...
🚀 Proceeding with the upgrade...
🔧 panorama.cdot.io: Using 10 threads.
📝 Woodlands-fw1: 007954000123451 192.168.255.43
📝 Woodlands-fw2: 007954000123452 192.168.255.44
📝 Woodlands-fw1: HA mode: active
📝 Woodlands-fw2: HA mode: passive
📝 Woodlands-fw1: Local state: active, Local version: 10.1.3, Peer version: 10.1.3
📝 Woodlands-fw1: Version comparison: equal
🔍 Woodlands-fw1: Detected active target device in HA pair running the same version as its peer. Added target device to revisit list.
📝 Woodlands-fw2: Local state: passive, Local version: 10.1.3, Peer version: 10.1.3
📝 Woodlands-fw2: Version comparison: equal
📝 Woodlands-fw2: Target device is passive
📝 Woodlands-fw2: Current version: 10.1.3
📝 Woodlands-fw2: Target version: 10.1.3-h2
✅ Woodlands-fw2: Upgrade required from 10.1.3 to 10.1.3-h2
🔧 Woodlands-fw2: Refreshing list of available software versions
✅ Woodlands-fw2: version 10.1.3-h2 is available for download
✅ Woodlands-fw2: Base image for 10.1.3-h2 is already downloaded
🚀 Woodlands-fw2: Performing test to see if 10.1.3-h2 is already downloaded.
✅ Woodlands-fw2: version 10.1.3-h2 already on target device.
✅ Woodlands-fw2: 10.1.3-h2 has been downloaded and sync'd to HA peer.
🚀 Woodlands-fw2: Performing snapshot of network state information.
🚀 Woodlands-fw2: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ Woodlands-fw2: Network snapshot created successfully on attempt 1.
💾 Woodlands-fw2: Network state snapshot collected and saved to assurance/snapshots/Woodlands-fw2/pre/2024-02-13_14-18-09.json
🚀 Woodlands-fw2: Performing readiness checks of target firewall.
🚀 Woodlands-fw2: Performing readiness checks to determine if firewall is ready for upgrade.
✅ Woodlands-fw2: Passed Readiness Check: Check if active support is available
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a given ARP entry is available in the ARP table
✅ Woodlands-fw2: Passed Readiness Check: Check if there are pending changes on device
🟨 Woodlands-fw2: Skipped Readiness Check: Check if the certificates' keys meet minimum size requirements
🟨 Woodlands-fw2: Skipped Readiness Check: Running Latest Content Version
✅ Woodlands-fw2: Passed Readiness Check: Check if any Dynamic Update job is scheduled to run within the specified time window
✅ Woodlands-fw2: Passed Readiness Check: No Expired Licenses
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.
✅ Woodlands-fw2: Passed Readiness Check: Checks HA pair status from the perspective of the current device
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a given IPsec tunnel is in active state
🟨 Woodlands-fw2: Skipped Readiness Check: Check for any job with status different than FIN
🟨 Woodlands-fw2: Skipped Readiness Check: Check if NTP is synchronized
✅ Woodlands-fw2: Passed Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ Woodlands-fw2: Passed Readiness Check: Check connectivity with the Panorama appliance
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a critical session is present in the sessions table
✅ Woodlands-fw2: Readiness Checks completed
🚀 Woodlands-fw2: Checking if HA peer is in sync.
✅ Woodlands-fw2: HA peer sync test has been completed.
🚀 Woodlands-fw2: Performing backup of configuration to local filesystem.
📝 Woodlands-fw2: Not a dry run, continue with upgrade.
🚀 Woodlands-fw2: Performing upgrade to version 10.1.3-h2.
📝 Woodlands-fw2: The install will take several minutes, check for status details within the GUI.
🚀 Woodlands-fw2: Attempting upgrade to version 10.1.3-h2 (Attempt 1 of 3).
Device 007954000123452 installing version: 10.1.3-h2
✅ Woodlands-fw2: Upgrade completed successfully
🚀 Woodlands-fw2: Rebooting the target device.
📝 Woodlands-fw2: Command succeeded with no output
🟧 Woodlands-fw2: Retry attempt 1 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 2 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 3 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 4 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 5 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 6 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 7 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 8 due to error: 007954000123452 not connected
🟧 Woodlands-fw2: Retry attempt 9 due to error: 007954000123452 not connected
📝 Woodlands-fw2: Current device version: 10.1.3-h2
✅ Woodlands-fw2: Device rebooted to the target version successfully.
🚀 Woodlands-fw2: Performing backup of configuration to local filesystem.
🔧 Woodlands-fw2: Waiting for the device to become ready for the post upgrade snapshot.
🚀 panorama.cdot.io: Revisiting firewalls that were active in an HA pair and had the same version as their peers.
📝 Woodlands-fw1: 007954000123451 192.168.255.43
📝 Woodlands-fw1: HA mode: active
📝 Woodlands-fw1: Local state: active, Local version: 10.1.3, Peer version: 10.1.3-h2
Waiting for HA synchronization to complete on Woodlands-fw1. Attempt 1/3
HA synchronization complete on Woodlands-fw1. Proceeding with upgrade.
📝 Woodlands-fw1: Version comparison: older
📝 Woodlands-fw1: Target device is on an older version
📝 Woodlands-fw1: Suspending HA state of active
🟧 Woodlands-fw1: Error received when suspending active target device HA state: argument of type 'NoneType' is not iterable
📝 Woodlands-fw1: Current version: 10.1.3
📝 Woodlands-fw1: Target version: 10.1.3-h2
✅ Woodlands-fw1: Upgrade required from 10.1.3 to 10.1.3-h2
🔧 Woodlands-fw1: Refreshing list of available software versions
✅ Woodlands-fw1: version 10.1.3-h2 is available for download
✅ Woodlands-fw1: Base image for 10.1.3-h2 is already downloaded
🚀 Woodlands-fw1: Performing test to see if 10.1.3-h2 is already downloaded.
✅ Woodlands-fw1: version 10.1.3-h2 already on target device.
✅ Woodlands-fw1: 10.1.3-h2 has been downloaded and sync'd to HA peer.
🚀 Woodlands-fw1: Performing snapshot of network state information.
🚀 Woodlands-fw1: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ Woodlands-fw1: Network snapshot created successfully on attempt 1.
💾 Woodlands-fw1: Network state snapshot collected and saved to assurance/snapshots/Woodlands-fw1/pre/2024-02-13_14-37-49.json
🚀 Woodlands-fw1: Performing readiness checks of target firewall.
🚀 Woodlands-fw1: Performing readiness checks to determine if firewall is ready for upgrade.
✅ Woodlands-fw1: Passed Readiness Check: Check if active support is available
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a given ARP entry is available in the ARP table
✅ Woodlands-fw1: Passed Readiness Check: Check if there are pending changes on device
🟨 Woodlands-fw1: Skipped Readiness Check: Check if the certificates' keys meet minimum size requirements
🟨 Woodlands-fw1: Skipped Readiness Check: Running Latest Content Version
✅ Woodlands-fw1: Passed Readiness Check: Check if any Dynamic Update job is scheduled to run within the specified time window
✅ Woodlands-fw1: Passed Readiness Check: No Expired Licenses
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.
🟨 Woodlands-fw1: Skipped Readiness Check: Checks HA pair status from the perspective of the current device
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a given IPsec tunnel is in active state
🟨 Woodlands-fw1: Skipped Readiness Check: Check for any job with status different than FIN
🟨 Woodlands-fw1: Skipped Readiness Check: Check if NTP is synchronized
✅ Woodlands-fw1: Passed Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ Woodlands-fw1: Passed Readiness Check: Check connectivity with the Panorama appliance
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a critical session is present in the sessions table
✅ Woodlands-fw1: Readiness Checks completed
🚀 Woodlands-fw1: Checking if HA peer is in sync.
✅ Woodlands-fw1: HA peer sync test has been completed.
🚀 Woodlands-fw1: Performing backup of configuration to local filesystem.
📝 Woodlands-fw1: Not a dry run, continue with upgrade.
🚀 Woodlands-fw1: Performing upgrade to version 10.1.3-h2.
📝 Woodlands-fw1: The install will take several minutes, check for status details within the GUI.
🚀 Woodlands-fw1: Attempting upgrade to version 10.1.3-h2 (Attempt 1 of 3).
Device 007954000123451 installing version: 10.1.3-h2
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
