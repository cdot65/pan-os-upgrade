# Docker Execution for pan-os-upgrade

Run `pan-os-upgrade` in Docker for a consistent setup across systems. This guide details the steps for Docker configuration and execution, including Panorama proxy connections.

## Pulling the Docker Image

Pull the `pan-os-upgrade` image from GitHub Packages:

<div class="termy">

```console
docker pull ghcr.io/cdot65/pan-os-upgrade:latest
```

</div>

## Docker Setup

Before executing the tool, ensure your Docker environment is correctly set up.

### Prepare Directories

Create `assurance` and `logs` directories in your working directory to store outputs and logs:

<div class="termy">

```console
mkdir assurance logs
```

</div>

If you plan on customizing the settings of the script, create an empty `settings.yaml` in your working directory. This file will be filled out correctly when you run the `settings` argument when running the container image (see the `Advanced Setttings` section):

<div class="termy">

```console
touch settings.yaml
```

</div>

### Run Docker Container

Before we get the execution, let's take a moment to review the flags that we need to pass at runtime.

#### Docker CLI flags

| flag   | description                                                             | required? |
| ------ | ----------------------------------------------------------------------- | --------- |
| -v     | mount files / folders from your local computer into the container       | yes       |
| -it    | let Docker know that you need an interactive session with the container | yes       |
| --rm   | remove the container after it completes its execution, good for hygiene | no        |
| --name | assign a name to the container instance                                 | no        |

##### Volume Mounts

We will need to create at least two volume mounts with Docker, this workflow allows us to have our local files available within the Docker container. When a Docker container completes its execution, the default behavior is to stop the container and this will prevent us from viewing the logs, snapshots, configuration backups, and readiness checks.

##### Interactive Teletype

Since we are using a CLI tool that requires interaction from us during its execution, we also need to flag the container to work in an interactive teletype session.

##### Optional Flags

If you'd like, you can assign a name to your container. This can help you create a friendly name for the container instance that will help you revisit it, should that prove necessary.

If you decide to assign your container a name that be common across multiple executions, you will want to also pass the `--rm` flag to remove the container after its execution completes. This is a good practice to reduce the amount of duplicate containers, but will prevent you from revisiting a specific container instance later on; this shouldn't be an issue since all logs, snapshots, checks, and backups are available in your host's current directory, thanks to the volume mounts.

#### Example Execution on macOS and Linux

In this example we will upgrade a firewall directly by using the `firewall` argument when executing the container. The `$(pwd)` on macOS and Linux is a shortcut for `full path to your current working directory`; feel free to simply run `pwd` from your terminal to get an understanding of the response.

<div class="termy">

```console
docker run \
-v $(pwd)/assurance:/app/assurance \
-v $(pwd)/logs:/app/logs \
-it \
ghcr.io/cdot65/pan-os-upgrade:latest firewall
Firewall password:
===================================================================
Welcome to the PAN-OS upgrade tool

You have selected to upgrade a single Firewall appliance.

No settings.yaml file was found. Default values will be used.
Create a settings.yaml file with 'pan-os-upgrade settings' command.
===================================================================
📝 houston: 007054000242050 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current version: 10.2.5
📝 houston: Target version: 10.2.6
✅ houston: Upgrade required from 10.2.5 to 10.2.6
✅ houston: version 10.2.6 is available for download
✅ houston: Base image for 10.2.6 is already downloaded
🚀 houston: Performing test to see if 10.2.6 is already downloaded...
🔍 houston: version 10.2.6 is not on the target device
🚀 houston: version 10.2.6 is beginning download
Device 007054000242050 downloading version: 10.2.6
🔧 houston: Downloading version 10.2.6 - Elapsed time: 5 seconds
🔧 houston: Downloading version 10.2.6 - Elapsed time: 41 seconds
🔧 houston: Downloading version 10.2.6 - Elapsed time: 76 seconds
✅ houston: 10.2.6 downloaded in 109 seconds
✅ houston: version 10.2.6 has been downloaded.
🚀 houston: Performing snapshot of network state information...
✅ houston: Network snapshot created successfully
🚀 houston: Performing readiness checks to determine if firewall is ready for upgrade...
✅ houston: Passed Readiness Check: Check if there are pending changes on device
✅ houston: Passed Readiness Check: No Expired Licenses
✅ houston: Passed Readiness Check: Check if NTP is synchronized
✅ houston: Passed Readiness Check: Check if the clock is synchronized between dataplane and management plane
✅ houston: Passed Readiness Check: Check connectivity with the Panorama appliance
✅ houston: Readiness Checks completed
🚀 houston: Performing backup of configuration to local filesystem...
✅ houston: Dry run complete, exiting...
🛑 houston: Halting script.
```

</div>

In the example I am using the `\` at execution to allow me to split the flags on separate lines, this is completely optional but I have found that it helps me review all flags without going cross-eyed. You can absolutely execute all commands on a single line

<div class="termy">

```console
docker run -v $(pwd)/assurance:/app/assurance -v $(pwd)/logs:/app/logs -it ghcr.io/cdot65/pan-os-upgrade:latest firewall
```

</div>

#### Example Execution on Windows

The volume mount flags need to point to a different shortcut to reference your current working directory on Windows:

<div class="termy">

```console
docker run -v %CD%/assurance:/app/assurance -v %CD%/logs:/app/logs -it ghcr.io/cdot65/pan-os-upgrade:latest panorama
```

</div>

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

| CLI Option   | Shorthand | Type    | Description                                                                             |
| ------------ | --------- | ------- | --------------------------------------------------------------------------------------- |
| `--dry-run`  | `-d`      | Boolean | Executes all preparatory steps without applying the actual upgrade, useful for testing. |
| `--filter`   | `-f`      | String  | Specifies criteria for selecting devices when performing batch upgrades via Panorama.   |
| `--hostname` | `-h`      | String  | The IP address or DNS name of the target firewall or Panorama appliance.                |
| `--password` | `-p`      | String  | The authentication password required for accessing the target device.                   |
| `--username` | `-u`      | String  | The username for authentication with the target PAN-OS device.                          |
| `--version`  | `-v`      | String  | Specifies the target PAN-OS version for the upgrade operation.                          |

Each CLI option has a specific role in tailoring the upgrade process, from defining the target device and authentication credentials to setting operational parameters like the target PAN-OS version and logging verbosity.

## Interacting with the Docker Container

The container runs interactively, prompting you for details like IP address, username, password, and target PAN-OS version. If connecting to firewalls through Panorama as a proxy, you will also be prompted to provide a `--filter` option to specify the criteria for selecting the managed firewalls to upgrade.

<div class="termy">

```console
$ docker run \
-v $(pwd)/assurance:/app/assurance \
-v $(pwd)/logs:/app/logs \
-it \
ghcr.io/cdot65/pan-os-upgrade:latest batch

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

## Advanced Settings

If you would like to change the default settings of `pan-os-upgrade` tool, you can create a `settings.yaml` file and run the `settings` CLI argument. This will walk you through a series of options to change.

Create the empty `settings.yaml` file within your current working directory

<div class="termy">

```console
touch settings.yaml
```

</div>

> Note: Make sure that you created an empty `settings.yaml` file *before* you run the `settings` CLI argument, or else Docker will create `settings.yaml` as a folder instead of a file.

<div class="termy">

```console
❯ docker run \
-v $(pwd)/settings.yaml:/app/settings.yaml \
-it \
ghcr.io/cdot65/pan-os-upgrade:latest settings
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

Once you have a `settings.yaml` file in your current working directory, and you have reviewed its contents to make sure all of the settings match your expectations, then we must add it to the list of volume mounts in order to make the file accessible by the script within the container.

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

You will be able to confirm that the file was discovered by the message within the banner `Custom configuration loaded from: /app/settings.yaml`. If you do *not* see this message in the banner, then you can assume that your `settings.yaml` file was not properly mounted to the container.

<div class="termy">

```console
$ docker run \
-v $(pwd)/assurance:/app/assurance \
-v $(pwd)/logs:/app/logs \
-v $(pwd)/settings.yaml:/app/settings.yaml \
-it \
ghcr.io/cdot65/pan-os-upgrade:latest firewall -v 10.2.5 -u cdot -h houston.cdot.io
Firewall password:
Dry Run? [y/N]:
=========================================================
Welcome to the PAN-OS upgrade tool

You have selected to upgrade a single Firewall appliance.

Custom configuration loaded from:
/app/settings.yaml
=========================================================
📝 houston: 007054000242050 192.168.255.211
📝 houston: HA mode: disabled
📝 houston: Current version: 10.2.4-h4
📝 houston: Target version: 10.2.5
✅ houston: Upgrade required from 10.2.4-h4 to 10.2.5
... shortened for brevity ...
🟧 houston: Retry attempt 4 due to error: URLError: reason: [Errno 111] Connection refused
📝 houston: Current device version: 10.2.5
✅ houston: Device rebooted to the target version successfully.
```

</div>

## Troubleshooting Panorama Proxy Connections

When using Panorama as a connection proxy:

- Ensure the `--filter` option is correctly formatted and corresponds to the criteria for selecting firewalls.
- Verify network connectivity between the Docker container and the Panorama appliance.
- Check the Panorama and firewall configurations to ensure proper communication and permissions.

## Output and Logs

After running the container, you'll find all necessary outputs and logs in the `assurance` and `logs` directories on your host machine.

## Next Steps

With `pan-os-upgrade` successfully executed using Docker, check the outputs and logs for insights into the upgrade process. For detailed troubleshooting steps or further assistance, refer to the [Troubleshooting Guide](troubleshooting.md).
