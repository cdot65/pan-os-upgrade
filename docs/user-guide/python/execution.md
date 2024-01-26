# Python Setup and Execution Guide for pan-os-upgrade

This guide provides comprehensive steps for configuring and executing the `pan-os-upgrade` package within a Python environment. It details command-line execution methods, including the new feature of targeting a Panorama appliance as a connection proxy.

## Configuring and Executing `pan-os-upgrade`

### Executing Without Command-Line Arguments

You can start the script interactively by simply issuing `pan-os-upgrade` from your current working directory. The interactive shell will prompt you to input the required arguments, including whether to target a standalone firewall or use Panorama as a proxy.

<div class="termy">

```console
$ pan-os-upgrade firewall
Firewall hostname or IP: houston.cdot.io
Firewall username: cdot
Firewall password:
Target version: 10.2.4-h4
Dry Run? [y/N]: N
📝 houston: 007054000242050 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current version: 10.2.4-h3
📝 houston: Target version: 10.2.4-h4
✅ houston: Upgrade required from 10.2.4-h3 to 10.2.4-h4
✅ houston: version 10.2.4-h4 is available for download
✅ houston: Base image for 10.2.4-h4 is already downloaded
🚀 houston: Performing test to see if 10.2.4-h4 is already downloaded...
✅ houston: version 10.2.4-h4 already on target device.
✅ houston: version 10.2.4-h4 has been downloaded.
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
🚀 houston: Performing upgrade to version 10.2.4-h4...
🚀 houston: Attempting upgrade to version 10.2.4-h4 (Attempt 1 of 3)...
Device 007054000242050 installing version: 10.2.4-h4
✅ houston: Upgrade completed successfully
🚀 houston: Rebooting the standalone target device...
📝 houston: Command succeeded with no output
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
📝 houston: Target device version: 10.2.4-h4
✅ houston: Target device rebooted in 448 seconds
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
$ pan-os-upgrade batch
Panorama hostname or IP: panorama.cdot.io
Panorama username: cdot
Panorama password:
Firewall target version (ex: 10.1.2): 10.2.3
Filter string (ex: hostname=Woodlands*) []: hostname=Woodlands*
Dry Run? [y/N]:
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

### CLI Arguments vs. CLI Options

In the context of the `pan-os-upgrade` application, it's important to distinguish between CLI arguments and CLI options:

- **CLI Arguments** are the primary commands that determine the operation mode of the application. They are not prefixed by `--` or `-` and are essential for defining the core action the script should perform.
- **CLI Options**, on the other hand, are additional modifiers or settings that further customize the behavior of the CLI arguments. They typically come with a `--` prefix (or `-` for shorthand) and are optional.

#### CLI Arguments

The following are the main commands (CLI arguments) for the `pan-os-upgrade` application, each tailored for specific upgrade scenarios:

| CLI Argument | Description                                                                                                                                                                                         |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `firewall`   | Targets an individual firewall for upgrade. This command requires subsequent CLI options to specify the firewall details and desired actions.                                                       |
| `panorama`   | Targets an individual Panorama appliance for upgrade, necessitating further CLI options for execution details.                                                                                      |
| `batch`      | Utilizes a Panorama appliance to orchestrate bulk upgrades of managed firewalls, supporting up to ten concurrent operations. Requires additional CLI options for filtering and execution specifics. |

#### CLI Options

Below are the CLI options that can be used in conjunction with the above CLI arguments to customize the upgrade process:

| CLI Option    | Shorthand | Type    | Description                                                                                                                               |
| ------------- | --------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `--dry-run`   | `-d`      | Boolean | Executes all preparatory steps without applying the actual upgrade, useful for testing and verification purposes.                         |
| `--filter`    | `-f`      | String  | Specifies criteria for selecting devices when performing batch upgrades via Panorama, such as device hostname patterns or serial numbers. |
| `--hostname`  | `-h`      | String  | The IP address or DNS name of the target firewall or Panorama appliance.                                                                  |
| `--log-level` | `-l`      | String  | Determines the verbosity of log output, with levels including debug, info, and warning among others.                                      |
| `--password`  | `-p`      | String  | The authentication password required for accessing the target device.                                                                     |
| `--username`  | `-u`      | String  | The username for authentication with the target PAN-OS device.                                                                            |
| `--version`   | `-v`      | String  | Specifies the target PAN-OS version for the upgrade operation.                                                                            |

Each CLI option has a specific role in tailoring the upgrade process, from defining the target device and authentication credentials to setting operational parameters like the target PAN-OS version and logging verbosity.

#### Option 1: Execute `pan-os-upgrade` without Command-Line Arguments

You can simply get started by issuing `pan-os-upgrade` from your current working directory, you will be guided to input the missing requirement arguments through an interactive shell.

<div class="termy">

```console
$ pan-os-upgrade firewall
Firewall hostname or IP: houston.cdot.io
Firewall username: cdot
Firewall password:
Target version: 10.2.4-h4
Dry Run? [y/N]: N
📝 houston: 007054000242050 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current version: 10.2.4-h3
📝 houston: Target version: 10.2.4-h4
✅ houston: Upgrade required from 10.2.4-h3 to 10.2.4-h4
✅ houston: version 10.2.4-h4 is available for download
✅ houston: Base image for 10.2.4-h4 is already downloaded
🚀 houston: Performing test to see if 10.2.4-h4 is already downloaded...
✅ houston: version 10.2.4-h4 already on target device.
✅ houston: version 10.2.4-h4 has been downloaded.
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
🚀 houston: Performing upgrade to version 10.2.4-h4...
🚀 houston: Attempting upgrade to version 10.2.4-h4 (Attempt 1 of 3)...
Device 007054000242050 installing version: 10.2.4-h4
✅ houston: Upgrade completed successfully
🚀 houston: Rebooting the standalone target device...
📝 houston: Command succeeded with no output
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
🔧 houston: Target device is rebooting...
📝 houston: Target device version: 10.2.4-h4
✅ houston: Target device rebooted in 448 seconds
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
