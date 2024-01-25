# Python Setup and Execution Guide for pan-os-upgrade

This guide provides comprehensive steps for configuring and executing the `pan-os-upgrade` package within a Python environment. It details command-line execution methods, including the new feature of targeting a Panorama appliance as a connection proxy.

## Configuring and Executing `pan-os-upgrade`

### Executing Without Command-Line Arguments

You can start the script interactively by simply issuing `pan-os-upgrade` from your current working directory. The interactive shell will prompt you to input the required arguments, including whether to target a standalone firewall or use Panorama as a proxy.

<div class="termy">

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
✅ houston: PAN-OS version 10.2.4 already on firewall.
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

</div>

### Executing Using Command-Line Arguments

Alternatively, you can pass these details as command-line arguments. This method now includes an optional `--filter` argument for targeting devices managed by a Panorama appliance.

#### Direct Firewall Targeting

```bash
$ pan-os-upgrade --hostname 192.168.255.1 --username admin --password secret --version 10.1.0
INFO - ✅ Connection to firewall established
... shortened output for brevity ...
```

#### Using Panorama as a Proxy

When using Panorama as a proxy, the `--filter` argument is necessary to specify the criteria for selecting the managed firewalls to upgrade.

```bash
$ pan-os-upgrade --hostname panorama.cdot.io --filter 'hostname=houston' --username admin --password secret --version 10.1.0
✅ Connection to Panorama established. Firewall connections will be proxied!
... shortened output for brevity ...
```

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

### CLI Arguments Description

When using command-line arguments, the following options are available:

| Argument      | Description                                                          | Required    |
| ------------- | -------------------------------------------------------------------- | ----------- |
| `--hostname`  | Hostname or IP address of the target PAN-OS firewall or Panorama.    | Yes         |
| `--username`  | Username for authentication with the firewall.                       | Yes         |
| `--password`  | Password for authentication with the firewall.                       | Yes         |
| `--version`   | Target PAN-OS version to upgrade to.                                 | Yes         |
| `--dry-run`   | Perform a dry run of all tests and downloads without actual upgrade. | No          |
| `--log-level` | Set the logging output level (e.g., debug, info, warning).           | No          |
| `--filter`    | Filter criteria for selecting devices when using Panorama.           | Conditional |

Note: The use of an API key and `.env` file for configuration is no longer supported.

## Output and Assurance Functions

This output will include detailed logs of the process, such as establishing a connection, checking versions, performing upgrades, and rebooting the firewall or firewalls, especially when using Panorama as a proxy.

## Assurance Functions

The script performs various assurance functions like readiness checks, snapshots, and configuration backups. These are stored in the `assurance/` directory, structured as follows:

- `snapshots/`: Contains pre and post-upgrade network state snapshots in JSON format.
- `readiness_checks/`: Holds results of readiness checks in JSON format.
- `configurations/`: Stores backups of the firewall's configuration in XML format.

### Log Files and Levels

Log entries are recorded in the `logs/` directory. The verbosity of logs can be controlled with the `--log-level` argument, with available options being `debug`, `info`, `warning`, `error`, and `critical`.

## Next Steps

With `pan-os-upgrade` configured, you're ready to execute the upgrade process. This guide should have provided you with all the necessary information to use the tool effectively within a Python environment. For further assistance or advanced tips, refer to the [Python Troubleshooting Guide](troubleshooting.md).
