# Docker Execution for pan-os-upgrade

The `pan-os-upgrade` tool can be conveniently run using Docker, offering a consistent and streamlined setup process across different systems. This guide will walk you through configuring and executing the tool within a Docker container, including steps for connecting to firewalls through Panorama as a proxy.

## Pulling the Docker Image

If you haven't already done so, start off by pulling the `pan-os-upgrade` Docker image from GitHub Packages:

```bash
docker pull ghcr.io/cdot65/pan-os-upgrade:latest
```

## Setting Up the Docker Environment

Before executing the tool, ensure your Docker environment is correctly set up.

### Directory Setup

Create `assurance` and `logs` directories in your working directory to store outputs and logs:

```bash
mkdir assurance logs
```

### Running the Docker Container

Run `pan-os-upgrade` in Docker using the following commands:

#### On macOS and Linux

```bash
docker run -v $(pwd)/assurance:/app/assurance -v $(pwd)/logs:/app/logs -it ghcr.io/cdot65/pan-os-upgrade:latest
```

This mounts your host's `assurance` and `logs` directories to the container.

#### On Windows

```bash
docker run -v %CD%/assurance:/app/assurance -v %CD%/logs:/app/logs -it ghcr.io/cdot65/pan-os-upgrade:latest
```

## Interacting with the Docker Container

The container runs interactively, prompting you for details like IP address, username, password, and target PAN-OS version. If connecting to firewalls through Panorama as a proxy, you will also be prompted to provide a `--filter` option to specify the criteria for selecting the managed firewalls to upgrade.

<div class="termy">

```console
$ docker run -v $(pwd)/assurance:/app/assurance -v $(pwd)/logs:/app/logs -it ghcr.io/cdot65/pan-os-upgrade:latest
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

## Troubleshooting Panorama Proxy Connections

When using Panorama as a connection proxy:

- Ensure the `--filter` option is correctly formatted and corresponds to the criteria for selecting firewalls.
- Verify network connectivity between the Docker container and the Panorama appliance.
- Check the Panorama and firewall configurations to ensure proper communication and permissions.

## Output and Logs

After running the container, you'll find all necessary outputs and logs in the `assurance` and `logs` directories on your host machine.

## Next Steps

With `pan-os-upgrade` successfully executed using Docker, check the outputs and logs for insights into the upgrade process. For detailed troubleshooting steps or further assistance, refer to the [Troubleshooting Guide](troubleshooting.md).
