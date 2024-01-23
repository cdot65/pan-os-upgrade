# Python Setup and Execution Guide for pan-os-upgrade

This guide provides comprehensive steps for configuring and executing the `pan-os-upgrade` package within a Python environment. It details command-line execution methods, including the new feature of targeting a Panorama appliance as a connection proxy.

## Configuring and Executing `pan-os-upgrade`

### Executing Without Command-Line Arguments

You can start the script interactively by simply issuing `pan-os-upgrade` from your current working directory. The interactive shell will prompt you to input the required arguments, including whether to target a standalone firewall or use Panorama as a proxy.

<div class="termy">

```console
$ pan-os-upgrade
Hostname or IP: 192.168.255.1
Username: admin
Password:
Target PAN-OS version: 11.1.1
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
INFO - ⚙️ Firewall is responding to requests but hasn't finished its reboot process...
INFO - ✅ Firewall upgraded and rebooted in 542 seconds
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
$ pan-os-upgrade --filter 'hostname=houston'
Hostname or IP: panorama.cdot.io
Username: cdot
Password:
Target PAN-OS version: 10.2.3-h2
✅ Connection to Panorama established. Firewall connections will be proxied!
📝 007054000123456 houston 192.168.255.211
📝 Firewall HA mode: disabled
📝 Current PAN-OS version: 10.2.3
📝 Target PAN-OS version: 10.2.3-h2
✅ Confirmed that moving from 10.2.3 to 10.2.3-h2 is an upgrade
✅ PAN-OS version 10.2.3-h2 is available for download
✅ Base image for 10.2.3-h2 is already downloaded
🚀 Performing test to see if 10.2.3-h2 is already downloaded...
🔍 PAN-OS version 10.2.3-h2 is not on the firewall
🚀 PAN-OS version 10.2.3-h2 is beginning download
Device 007054000123456 downloading version: 10.2.3-h2
Downloading PAN-OS version 10.2.3-h2 - Elapsed time: 8 seconds
Downloading PAN-OS version 10.2.3-h2 - Elapsed time: 42 seconds
Downloading PAN-OS version 10.2.3-h2 - Elapsed time: 75 seconds
Downloading PAN-OS version 10.2.3-h2 - Elapsed time: 110 seconds
Downloading PAN-OS version 10.2.3-h2 - Elapsed time: 151 seconds
✅ 10.2.3-h2 downloaded in 182 seconds
✅ PAN-OS version 10.2.3-h2 has been downloaded.
🚀 Performing snapshot of network state information...
✅ Network snapshot created successfully
🚀 Performing readiness checks to determine if firewall is ready for upgrade...
✅ Passed Readiness Check: Check if there are pending changes on device
✅ Passed Readiness Check: No Expired Licenses
✅ Passed Readiness Check: Check if NTP is synchronized
✅ Passed Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ Passed Readiness Check: Check connectivity with the Panorama appliance
✅ Readiness Checks completed
🚀 Performing backup of houston's configuration to local filesystem...
🚀 Not a dry run, continue with upgrade...
🚀 Performing upgrade on houston to version 10.2.3-h2...
🚀 Attempting upgrade houston to version 10.2.3-h2 (Attempt 1 of 3)...
Device 007054000123456 installing version: 10.2.3-h2
✅ houston upgrade completed successfully
🚀 Rebooting the standalone firewall...
📝 Command succeeded with no output
⚙️ Firewall is rebooting...
⚙️ Firewall is rebooting...
⚙️ Firewall is rebooting...
⚙️ Firewall is rebooting...
⚙️ Firewall is rebooting...
⚙️ Firewall is rebooting...
⚙️ Firewall is rebooting...
📝 Firewall version: 10.2.3-h2
✅ Firewall rebooted in 484 seconds
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
