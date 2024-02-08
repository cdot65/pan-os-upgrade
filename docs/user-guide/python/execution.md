# Python Setup and Execution Guide for pan-os-upgrade

This guide provides comprehensive steps for configuring and executing the `pan-os-upgrade` package within a Python environment. It details command-line execution methods, including the new feature of targeting a Panorama appliance as a connection proxy.

## Configuring and Executing `pan-os-upgrade`

### Executing Without Command-Line Arguments

You can start the script interactively by simply issuing `pan-os-upgrade` from your current working directory. The interactive shell will prompt you to input the required arguments, including whether to target a standalone firewall or use Panorama as a proxy.

<div class="termy">

```console
pan-os-upgrade firewall
Firewall hostname or IP: houston.cdot.io
Firewall username: cdot
Firewall password:
Target version: 11.1.1
Dry Run? [Y/n]:
===================================================================
Welcome to the PAN-OS upgrade tool

You have selected to upgrade a single Firewall appliance.

No settings.yaml file was found. Default values will be used.
Create a settings.yaml file with 'pan-os-upgrade settings' command.
===================================================================
📝 houston: 007054000242050 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current version: 10.1.3
📝 houston: Target version: 11.1.1
✅ houston: Upgrade required from 10.1.3 to 11.1.1
🔧 houston: Refreshing list of available software versions
✅ houston: version 11.1.1 is available for download
❌ houston: Base image for 11.1.1 is not downloaded. Attempting download.
🔍 houston: version 11.1.0 is not on the target device
🚀 houston: version 11.1.0 is beginning download
Device 007054000242050 downloading version: 11.1.0
🔧 houston: Downloading version 11.1.0 - Elapsed time: 3 seconds
🔧 houston: Downloading version 11.1.0 - Elapsed time: 37 seconds
🔧 houston: Downloading version 11.1.0 - Elapsed time: 69 seconds
🔧 houston: Downloading version 11.1.0 - Elapsed time: 102 seconds
🔧 houston: Downloading version 11.1.0 - Elapsed time: 134 seconds
✅ houston: 11.1.0 downloaded in 167 seconds
✅ houston: Base image 11.1.0 downloaded successfully
✅ houston: Pausing for 60 seconds to let 11.1.0 image load into the software manager before downloading 11.1.1
📝 houston: Current version: 10.1.3
📝 houston: Target version: 11.1.1
✅ houston: Upgrade required from 10.1.3 to 11.1.1
🔧 houston: Refreshing list of available software versions
✅ houston: version 11.1.1 is available for download
✅ houston: Base image for 11.1.1 is already downloaded
🚀 houston: Performing test to see if 11.1.1 is already downloaded.
🔍 houston: version 11.1.1 is not on the target device
🚀 houston: version 11.1.1 is beginning download
Device 007054000242050 downloading version: 11.1.1
🔧 houston: Downloading version 11.1.1 - Elapsed time: 6 seconds
🔧 houston: Downloading version 11.1.1 - Elapsed time: 40 seconds
🔧 houston: Downloading version 11.1.1 - Elapsed time: 74 seconds
✅ houston: 11.1.1 downloaded in 110 seconds
✅ houston: version 11.1.1 has been downloaded.
🚀 houston: Performing snapshot of network state information.
🚀 houston: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ houston: Network snapshot created successfully on attempt 1.
💾 houston: Network state snapshot collected and saved to assurance/snapshots/houston/pre/2024-02-04_09-19-25.json
🚀 houston: Performing readiness checks to determine if firewall is ready for upgrade.
✅ houston: Passed Readiness Check: Check if active support is available
🟨 houston: Skipped Readiness Check: Check if a given ARP entry is available in the ARP table
✅ houston: Passed Readiness Check: Check if there are pending changes on device
🟨 houston: Skipped Readiness Check: Check if the certificates' keys meet minimum size requirements
🟨 houston: Skipped Readiness Check: Running Latest Content Version
✅ houston: Passed Readiness Check: Check if any Dynamic Update job is scheduled to run within the specified time window
✅ houston: Passed Readiness Check: No Expired Licenses
✅ houston: Passed Readiness Check: Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.
🟨 houston: Skipped Readiness Check: Checks HA pair status from the perspective of the current device
🟨 houston: Skipped Readiness Check: Check if a given IPsec tunnel is in active state
🟨 houston: Skipped Readiness Check: Check for any job with status different than FIN
🟨 houston: Skipped Readiness Check: Check if NTP is synchronized
🟨 houston: Skipped Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ houston: Passed Readiness Check: Check connectivity with the Panorama appliance
🟨 houston: Skipped Readiness Check: Check if a critical session is present in the sessions table
✅ houston: Readiness Checks completed
🚀 houston: Performing backup of configuration to local filesystem.
📝 houston: Not a dry run, continue with upgrade.
🚀 houston: Performing upgrade to version 11.1.1.
📝 houston: The install will take several minutes, check for status details within the GUI.
🚀 houston: Attempting upgrade to version 11.1.1 (Attempt 1 of 3).
Device 007054000242050 installing version: 11.1.1
❌ houston: Upgrade error: Device 007054000242050 attempt to install version 11.1.1 failed: ['Failed to install 11.1.1 with the following errors.\nSW version is 11.1.1\nThe software manager is currently in use. Please try again later.\nFailed to install   version  11.1.1  type  panos\n\n']
🟧 houston: Software manager is busy. Retrying in 60 seconds.
🚀 houston: Attempting upgrade to version 11.1.1 (Attempt 2 of 3).
Device 007054000242050 installing version: 11.1.1
✅ houston: Upgrade completed successfully
🚀 houston: Rebooting the target device.
📝 houston: Command succeeded with no output
🟧 houston: Retry attempt 1 due to error: URLError: reason: [Errno 60] Operation timed out
🟧 houston: Retry attempt 2 due to error: URLError: reason: [Errno 60] Operation timed out
🟧 houston: Retry attempt 3 due to error: URLError: reason: [Errno 61] Connection refused
🟧 houston: Retry attempt 4 due to error: URLError: reason: [Errno 61] Connection refused
🟧 houston: Retry attempt 5 due to error: URLError: reason: [Errno 61] Connection refused
🟧 houston: Retry attempt 6 due to error: URLError: code: 403 reason: API Error: Invalid Credential
🟧 houston: Retry attempt 7 due to error: URLError: code: 403 reason: API Error: Invalid Credential
🟧 houston: Retry attempt 8 due to error: URLError: code: 403 reason: API Error: Invalid Credential
📝 houston: Current device version: 11.1.1
✅ houston: Device rebooted to the target version successfully.
🚀 houston: Performing backup of configuration to local filesystem.
🔧 houston: Waiting for the device to become ready for the post upgrade snapshot.
🚀 houston: Performing snapshot of network state information.
🚀 houston: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ houston: Network snapshot created successfully on attempt 1.
💾 houston: Network state snapshot collected and saved to assurance/snapshots/houston/post/2024-02-04_09-44-21.json
💾 houston: Snapshot comparison PDF report saved to assurance/snapshots/houston/diff/2024-02-04_09-44-25_report.pdf
```

</div>

### Executing Using Command-Line Arguments

Alternatively, you can pass these details as command-line arguments. This method now includes an optional `--filter` argument for targeting devices managed by a Panorama appliance.

#### Direct Firewall Targeting

```bash
pan-os-upgrade firewall --hostname 192.168.255.1 --username admin --password secret --version 10.1.0
INFO - ✅ Connection to firewall established
... shortened output for brevity ...
```

#### Using Panorama as a Proxy

When using Panorama as a proxy, the `--filter` argument is necessary to specify the criteria for selecting the managed firewalls to upgrade.

```bash
pan-os-upgrade panorama --hostname panorama.cdot.io --filter 'hostname=houston' --username admin --password secret --version 10.1.0
✅ Connection to Panorama established. Firewall connections will be proxied!
... shortened output for brevity ...
```

### CLI Arguments vs. CLI Options

In the context of the `pan-os-upgrade` application, it's important to distinguish between CLI arguments and CLI options:

- **CLI Arguments** are the primary commands that determine the operation mode of the application. They are not prefixed by `--` or `-` and are essential for defining the core action the script should perform.
- **CLI Options**, on the other hand, are additional modifiers or settings that further customize the behavior of the CLI arguments. They typically come with a `--` prefix (or `-` for shorthand) and are optional.

#### CLI Arguments

The following are the main commands (CLI arguments) for the `pan-os-upgrade` application, each tailored for specific upgrade scenarios:

| CLI Argument | Description                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| `firewall`   | Targets an individual firewall for upgrade.                                                               |
| `panorama`   | Targets an individual Panorama appliance for upgrade.                                                     |
| `batch`      | Utilizes a Panorama appliance to orchestrate bulk upgrades of managed firewalls.                          |
| `settings`   | Creates a `settings.yaml` that will allow users to customize the script's default settings and behaviors. |

#### CLI Options

Below are the CLI options that can be used in conjunction with the above CLI arguments to customize the upgrade process:

| CLI Option   | Shorthand | Description                                                                             |
| ------------ | --------- | --------------------------------------------------------------------------------------- |
| `--dry-run`  | `-d`      | Executes all preparatory steps without applying the actual upgrade, useful for testing. |
| `--filter`   | `-f`      | Specifies criteria for selecting devices when performing batch upgrades via Panorama.   |
| `--hostname` | `-h`      | The IP address or DNS name of the target firewall or Panorama appliance.                |
| `--password` | `-p`      | The authentication password required for accessing the target device.                   |
| `--username` | `-u`      | The username for authentication with the target PAN-OS device.                          |
| `--version`  | `-v`      | Specifies the target PAN-OS version for the upgrade operation.                          |

Each CLI option has a specific role in tailoring the upgrade process, from defining the target device and authentication credentials to setting operational parameters like the target PAN-OS version and logging verbosity.

#### Option 1: Execute `pan-os-upgrade` without Command-Line Arguments

You can simply get started by issuing `pan-os-upgrade` from your current working directory, you will be guided to input the missing requirement arguments through an interactive shell.

<div class="termy">

```console
pan-os-upgrade batch
Panorama hostname or IP: panorama.cdot.io
Panorama username: cdot
Panorama password:
Firewall target version (ex: 10.1.2): 10.2.7-h3
Filter string (ex: hostname=Woodlands*) []: hostname=Woodlands*
Dry Run? [Y/n]:
===========================================================================
Welcome to the PAN-OS upgrade tool

You have selected to perform a batch upgrade of firewalls through Panorama.

No settings.yaml file was found. Default values will be used.
Create a settings.yaml file with 'pan-os-upgrade settings' command.
===========================================================================
✅ panorama.cdot.io: Connection to Panorama established. Firewall connections will be proxied!
📝 Woodlands-fw2: 007954000987652 192.168.255.44
📝 Woodlands-fw1: 007954000987651 192.168.255.43
📝 Woodlands-fw2: HA mode: active
📝 Woodlands-fw1: HA mode: passive
📝 Woodlands-fw2: Local state: active, Local version: 10.1.3, Peer version: 10.1.3
📝 Woodlands-fw2: Version comparison: equal
🔍 Woodlands-fw2: Detected active target device in HA pair running the same version as its peer. Added target device to revisit list.
📝 Woodlands-fw1: Local state: passive, Local version: 10.1.3, Peer version: 10.1.3
📝 Woodlands-fw1: Version comparison: equal
📝 Woodlands-fw1: Target device is passive
📝 Woodlands-fw1: Current version: 10.1.3
📝 Woodlands-fw1: Target version: 10.2.7-h3
✅ Woodlands-fw1: Upgrade required from 10.1.3 to 10.2.7-h3
🔧 Woodlands-fw1: Refreshing list of available software versions
✅ Woodlands-fw1: version 10.2.7-h3 is available for download
❌ Woodlands-fw1: Base image for 10.2.7-h3 is not downloaded. Attempting download.
🔍 Woodlands-fw1: version 10.2.0 is not on the target device
🚀 Woodlands-fw1: version 10.2.0 is beginning download
Device 007954000987651 downloading version: 10.2.0
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 3 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 35 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 66 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 98 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 129 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 160 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 192 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 223 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 257 seconds
🔧 Woodlands-fw1: Downloading version 10.2.0 - HA will sync image - Elapsed time: 289 seconds
✅ Woodlands-fw1: 10.2.0 downloaded in 321 seconds
✅ Woodlands-fw1: Base image 10.2.0 downloaded successfully
✅ Woodlands-fw1: Pausing for 60 seconds to let 10.2.0 image load into the software manager before downloading 10.2.7-h3
📝 Woodlands-fw1: Current version: 10.1.3
📝 Woodlands-fw1: Target version: 10.2.7-h3
✅ Woodlands-fw1: Upgrade required from 10.1.3 to 10.2.7-h3
🔧 Woodlands-fw1: Refreshing list of available software versions
✅ Woodlands-fw1: version 10.2.7-h3 is available for download
✅ Woodlands-fw1: Base image for 10.2.7-h3 is already downloaded
🚀 Woodlands-fw1: Performing test to see if 10.2.7-h3 is already downloaded.
🔍 Woodlands-fw1: version 10.2.7-h3 is not on the target device
🚀 Woodlands-fw1: version 10.2.7-h3 is beginning download
Device 007954000987651 downloading version: 10.2.7-h3
🔧 Woodlands-fw1: Downloading version 10.2.7-h3 - HA will sync image - Elapsed time: 3 seconds
🔧 Woodlands-fw1: Downloading version 10.2.7-h3 - HA will sync image - Elapsed time: 35 seconds
🔧 Woodlands-fw1: Downloading version 10.2.7-h3 - HA will sync image - Elapsed time: 67 seconds
🔧 Woodlands-fw1: Downloading version 10.2.7-h3 - HA will sync image - Elapsed time: 103 seconds
🔧 Woodlands-fw1: Downloading version 10.2.7-h3 - HA will sync image - Elapsed time: 135 seconds
🔧 Woodlands-fw1: Downloading version 10.2.7-h3 - HA will sync image - Elapsed time: 168 seconds
🔧 Woodlands-fw1: Downloading version 10.2.7-h3 - HA will sync image - Elapsed time: 201 seconds
✅ Woodlands-fw1: 10.2.7-h3 downloaded in 233 seconds
✅ Woodlands-fw1: 10.2.7-h3 has been downloaded and sync'd to HA peer.
🚀 Woodlands-fw1: Performing snapshot of network state information.
🚀 Woodlands-fw1: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ Woodlands-fw1: Network snapshot created successfully on attempt 1.
💾 Woodlands-fw1: Network state snapshot collected and saved to assurance/snapshots/Woodlands-fw1/pre/2024-02-04_09-15-40.json
🚀 Woodlands-fw1: Performing readiness checks to determine if firewall is ready for upgrade.
✅ Woodlands-fw1: Passed Readiness Check: Check if active support is available
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a given ARP entry is available in the ARP table
✅ Woodlands-fw1: Passed Readiness Check: Check if there are pending changes on device
🟨 Woodlands-fw1: Skipped Readiness Check: Check if the certificates' keys meet minimum size requirements
🟨 Woodlands-fw1: Skipped Readiness Check: Running Latest Content Version
✅ Woodlands-fw1: Passed Readiness Check: Check if any Dynamic Update job is scheduled to run within the specified time window
✅ Woodlands-fw1: Passed Readiness Check: No Expired Licenses
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.
✅ Woodlands-fw1: Passed Readiness Check: Checks HA pair status from the perspective of the current device
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a given IPsec tunnel is in active state
🟨 Woodlands-fw1: Skipped Readiness Check: Check for any job with status different than FIN
🟨 Woodlands-fw1: Skipped Readiness Check: Check if NTP is synchronized
🟨 Woodlands-fw1: Skipped Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ Woodlands-fw1: Passed Readiness Check: Check connectivity with the Panorama appliance
🟨 Woodlands-fw1: Skipped Readiness Check: Check if a critical session is present in the sessions table
✅ Woodlands-fw1: Readiness Checks completed
🚀 Woodlands-fw1: Checking if HA peer is in sync.
✅ Woodlands-fw1: HA peer sync test has been completed.
🚀 Woodlands-fw1: Performing backup of configuration to local filesystem.
📝 Woodlands-fw1: Not a dry run, continue with upgrade.
🚀 Woodlands-fw1: Performing upgrade to version 10.2.7-h3.
📝 Woodlands-fw1: The install will take several minutes, check for status details within the GUI.
🚀 Woodlands-fw1: Attempting upgrade to version 10.2.7-h3 (Attempt 1 of 3).
Device 007954000987651 installing version: 10.2.7-h3
✅ Woodlands-fw1: Upgrade completed successfully
🚀 Woodlands-fw1: Rebooting the target device.
📝 Woodlands-fw1: Command succeeded with no output
🟧 Woodlands-fw1: Retry attempt 1 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 2 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 3 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 4 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 5 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 6 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 7 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 8 due to error: 007954000987651 not connected
🟧 Woodlands-fw1: Retry attempt 9 due to error: 007954000987651 not connected
📝 Woodlands-fw1: Current device version: 10.2.7-h3
✅ Woodlands-fw1: Device rebooted to the target version successfully.
🚀 Woodlands-fw1: Performing backup of configuration to local filesystem.
🔧 Woodlands-fw1: Waiting for the device to become ready for the post upgrade snapshot.
🚀 Woodlands-fw1: Performing snapshot of network state information.
🚀 Woodlands-fw1: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ Woodlands-fw1: Network snapshot created successfully on attempt 1.
💾 Woodlands-fw1: Network state snapshot collected and saved to assurance/snapshots/Woodlands-fw1/post/2024-02-04_09-35-39.json
💾 Woodlands-fw1: Snapshot comparison PDF report saved to assurance/snapshots/Woodlands-fw1/diff/2024-02-04_09-35-40_report.pdf
🚀 panorama.cdot.io: Revisiting firewalls that were active in an HA pair and had the same version as their peers.
📝 Woodlands-fw2: 007954000987652 192.168.255.44
📝 Woodlands-fw2: HA mode: non-functional
📝 Woodlands-fw2: Local state: non-functional, Local version: 10.1.3, Peer version: 10.2.7-h3
Waiting for HA synchronization to complete on Woodlands-fw2. Attempt 1/3
HA synchronization complete on Woodlands-fw2. Proceeding with upgrade.
📝 Woodlands-fw2: Version comparison: older
📝 Woodlands-fw2: Target device is on an older version
📝 Woodlands-fw2: Current version: 10.1.3
📝 Woodlands-fw2: Target version: 10.2.7-h3
✅ Woodlands-fw2: Upgrade required from 10.1.3 to 10.2.7-h3
🔧 Woodlands-fw2: Refreshing list of available software versions
✅ Woodlands-fw2: version 10.2.7-h3 is available for download
✅ Woodlands-fw2: Base image for 10.2.7-h3 is already downloaded
🚀 Woodlands-fw2: Performing test to see if 10.2.7-h3 is already downloaded.
✅ Woodlands-fw2: version 10.2.7-h3 already on target device.
✅ Woodlands-fw2: version 10.2.7-h3 has been downloaded.
🚀 Woodlands-fw2: Performing snapshot of network state information.
🚀 Woodlands-fw2: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ Woodlands-fw2: Network snapshot created successfully on attempt 1.
💾 Woodlands-fw2: Network state snapshot collected and saved to assurance/snapshots/Woodlands-fw2/pre/2024-02-04_09-36-48.json
🚀 Woodlands-fw2: Performing readiness checks to determine if firewall is ready for upgrade.
✅ Woodlands-fw2: Passed Readiness Check: Check if active support is available
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a given ARP entry is available in the ARP table
✅ Woodlands-fw2: Passed Readiness Check: Check if there are pending changes on device
🟨 Woodlands-fw2: Skipped Readiness Check: Check if the certificates' keys meet minimum size requirements
🟨 Woodlands-fw2: Skipped Readiness Check: Running Latest Content Version
✅ Woodlands-fw2: Passed Readiness Check: Check if any Dynamic Update job is scheduled to run within the specified time window
✅ Woodlands-fw2: Passed Readiness Check: No Expired Licenses
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.
🟨 Woodlands-fw2: Skipped Readiness Check: Checks HA pair status from the perspective of the current device
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a given IPsec tunnel is in active state
🟨 Woodlands-fw2: Skipped Readiness Check: Check for any job with status different than FIN
🟨 Woodlands-fw2: Skipped Readiness Check: Check if NTP is synchronized
✅ Woodlands-fw2: Passed Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ Woodlands-fw2: Passed Readiness Check: Check connectivity with the Panorama appliance
🟨 Woodlands-fw2: Skipped Readiness Check: Check if a critical session is present in the sessions table
✅ Woodlands-fw2: Readiness Checks completed
🚀 Woodlands-fw2: Checking if HA peer is in sync.
🟧 Woodlands-fw2: HA peer state is not in sync. This will be noted, but the script will continue.
🚀 Woodlands-fw2: Performing backup of configuration to local filesystem.
📝 Woodlands-fw2: Not a dry run, continue with upgrade.
🚀 Woodlands-fw2: Performing upgrade to version 10.2.7-h3.
📝 Woodlands-fw2: The install will take several minutes, check for status details within the GUI.
🚀 Woodlands-fw2: Attempting upgrade to version 10.2.7-h3 (Attempt 1 of 3).
Device 007954000987652 installing version: 10.2.7-h3
✅ Woodlands-fw2: Upgrade completed successfully
🚀 Woodlands-fw2: Rebooting the target device.
📝 Woodlands-fw2: Command succeeded with no output
🟧 Woodlands-fw2: Retry attempt 1 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 2 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 3 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 4 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 5 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 6 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 7 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 8 due to error: 007954000987652 not connected
🟧 Woodlands-fw2: Retry attempt 9 due to error: 007954000987652 not connected
📝 Woodlands-fw2: Current device version: 10.2.7-h3
✅ Woodlands-fw2: Device rebooted to the target version successfully.
🚀 Woodlands-fw2: Performing backup of configuration to local filesystem.
🔧 Woodlands-fw2: Waiting for the device to become ready for the post upgrade snapshot.
🚀 Woodlands-fw2: Performing snapshot of network state information.
🚀 Woodlands-fw2: Attempting to capture network state snapshot (Attempt 1 of 3).
✅ Woodlands-fw2: Network snapshot created successfully on attempt 1.
💾 Woodlands-fw2: Network state snapshot collected and saved to assurance/snapshots/Woodlands-fw2/post/2024-02-04_09-57-36.json
💾 Woodlands-fw2: Snapshot comparison PDF report saved to assurance/snapshots/Woodlands-fw2/diff/2024-02-04_09-57-38_report.pdf
✅ panorama.cdot.io: Completed revisiting firewalls
```

</div>

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

## Advanced Settings

If you would like to change the default settings of `pan-os-upgrade` tool, you can run the `settings` CLI argument. This will walk you through a series of options to change.

### Readiness Checks

The following table lists the available readiness checks, their descriptions, and whether they are enabled by default. These checks are designed to ensure the device's readiness for an upgrade by validating its operational and configuration status.

| Readiness Check             | Description                                                                               | Enabled by Default |
| --------------------------- | ----------------------------------------------------------------------------------------- | :----------------: |
| `active_support`            | Check if active support is available                                                      |        Yes         |
| `arp_entry_exist`           | Check if a given ARP entry is available in the ARP table                                  |         No         |
| `candidate_config`          | Check if there are pending changes on device                                              |        Yes         |
| `certificates_requirements` | Check if the certificates' keys meet minimum size requirements                            |         No         |
| `content_version`           | Running Latest Content Version                                                            |        Yes         |
| `dynamic_updates`           | Check if any Dynamic Update job is scheduled to run within the specified time window      |        Yes         |
| `expired_licenses`          | No Expired Licenses                                                                       |        Yes         |
| `free_disk_space`           | Check if there is enough space on the `/opt/panrepo` volume for downloading a PanOS image |        Yes         |
| `ha`                        | Checks HA pair status from the perspective of the current device                          |        Yes         |
| `ip_sec_tunnel_status`      | Check if a given IPsec tunnel is in active state                                          |        Yes         |
| `jobs`                      | Check for any job with status different than FIN                                          |         No         |
| `ntp_sync`                  | Check if NTP is synchronized                                                              |         No         |
| `panorama`                  | Check connectivity with the Panorama appliance                                            |        Yes         |
| `planes_clock_sync`         | Check if the clock is synchronized between dataplane and management plane                 |        Yes         |
| `session_exist`             | Check if a critical session is present in the sessions table                              |         No         |

### State Snapshots

The following table lists the categories of state snapshots that can be captured to document essential data about the device's current state. These snapshots are crucial for diagnostics and verifying the device's operational status before proceeding with the upgrade.

| Snapshot          | Description                         | Enabled by Default |
| ----------------- | ----------------------------------- | :----------------: |
| `arp_table`       | Snapshot of the ARP Table           |        Yes         |
| `content_version` | Snapshot of the Content Version     |        Yes         |
| `ip_sec_tunnels`  | Snapshot of the IPsec Tunnels       |         No         |
| `license`         | Snapshot of the License Information |        Yes         |
| `nics`            | Snapshot of the Network Interfaces  |        Yes         |
| `routes`          | Snapshot of the Routing Table       |        Yes         |
| `session_stats`   | Snapshot of the Session Statistics  |         No         |

### Customizing Default Settings

The default settings for readiness checks and snapshots can be customized using the `pan-os-upgrade settings` subcommand. This interactive command guides you through a series of prompts to configure various aspects of the script's behavior, including which readiness checks and snapshots are enabled.

To override the default settings:

1. Run the `pan-os-upgrade settings` command.
2. Follow the prompts to enable or disable specific readiness checks and snapshots.
3. The resulting configurations are saved to a `settings.yaml` file in the current working directory.

    ```bash
    pan-os-upgrade settings
    ```

#### Note

The `settings.yaml` file created by this command can be edited manually for further customization.

<div class="termy">

```console
pan-os-upgrade settings
===============================================================================
Welcome to the PAN-OS upgrade settings menu

You'll be presented with configuration items, press enter for default settings.

This will create a `settings.yaml` file in your current working directory.
===============================================================================
Number of concurrent threads [10]: 35
Logging level [INFO]: debug
Path for log files [logs/upgrade.log]:
Maximum log file size (MB) [10]:
Number of upgrade logs to retain [10]:
Reboot retry interval (seconds) [60]:
Maximum reboot tries [30]: 45
Would you like to customize readiness checks? [y/N]:
Location to save readiness checks [assurance/readiness_checks/]:
Would you like to customize snapshots? [y/N]:
Location to save snapshots [assurance/snapshots/]:
Connection timeout (seconds) [30]:
Command timeout (seconds) [120]:
Configuration saved to /app/settings.yaml
```

</div>

Once you have a `settings.yaml` file in your current working directory, take a moment to review its contents to make sure all of the settings match your expectations.

Example `settings.yaml` file

```yaml
concurrency:
  threads: 34
logging:
  file_path: logs/upgrade.log
  level: INFO
  max_size: 10
  upgrade_log_count: 10
readiness_checks:
  checks: {}
  customize: false
  location: assurance/readiness_checks/
reboot:
  max_tries: 4
  retry_interval: 10
snapshots:
  customize: true
  location: assurance/snapshots/
  state:
    arp_table: true
    content_version: true
    ip_sec_tunnels: false
    license: false
    nics: true
    routes: true
    session_stats: false
timeout_settings:
  command_timeout: 120
  connection_timeout: 30
```

You will be able to confirm that the file was discovered by the message within the banner `Custom configuration loaded from: /path/to/your/settings.yaml`. If you do *not* see this message in the banner, then you can assume that your `settings.yaml` file was not properly discovered by the script.

<div class="termy">

```console
pan-os-upgrade firewall -v 10.2.5 -u cdot -h houston.cdot.io
Firewall password:
Dry Run? [Y/n]:
=========================================================
Welcome to the PAN-OS upgrade tool

You have selected to upgrade a single Firewall appliance.

Custom configuration loaded from:
/Users/cdot/development/pan-os-upgrade/settings.yaml
=========================================================
📝 houston: 007054000242050 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current version: 10.2.4-h4
📝 houston: Target version: 10.2.5
✅ houston: Upgrade required from 10.2.4-h4 to 10.2.5
... shortened for brevity ...
✅ houston: Device rebooted to the target version successfully.
```

</div>

## Output and Assurance Functions

This output will include detailed logs of the process, such as establishing a connection, checking versions, performing upgrades, and rebooting the firewall or firewalls, especially when using Panorama as a proxy.

## Assurance Functions

The script performs various assurance functions like readiness checks, snapshots, and configuration backups. These are stored in the `assurance/` directory, structured as follows:

- `snapshots/`: Contains pre and post-upgrade network state snapshots in JSON format.
- `readiness_checks/`: Holds results of readiness checks in JSON format.
- `configurations/`: Stores backups of the firewall's configuration in XML format.

### Log Files and Levels

Log entries are recorded in the `logs/` directory. The verbosity of logs can be controlled by creating a `settings.yaml` file with `pan-os-upgrade settings` CLI command. Available options being `debug`, `info`, `warning`, `error`, and `critical`.

## Next Steps

With `pan-os-upgrade` configured, you're ready to execute the upgrade process. This guide should have provided you with all the necessary information to use the tool effectively within a Python environment. For further assistance or advanced tips, refer to the [Python Troubleshooting Guide](troubleshooting.md).
