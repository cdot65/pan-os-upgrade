# Execution Guide for pan-os-upgrade

The `pan-os-upgrade` tool automates the entire process of upgrading PAN-OS firewalls. This guide will walk you through the execution steps, detailing how to use the script with different configuration options, and what to expect in terms of output and logging.

## Execution Options

You can execute `pan-os-upgrade` using two primary methods: either by using a `.env` file or command-line arguments. Each method provides flexibility depending on your preference or automation setup.

### Using a `.env` File

If you have set up a `.env` file as per the configuration guide, simply execute the script without any additional arguments:

<div class="termy">

```console
pan-os-upgrade
```

</div>

This command will automatically pick up the configuration details from your `.env` file.

### Using Command-Line Arguments

Alternatively, pass the configuration details directly as command-line arguments:

<div class="termy">

```console
pan-os-upgrade --hostname 192.168.1.1 --username admin --password secret --version 10.1.0
```

</div>

Here, replace `192.168.1.1`, `admin`, `secret`, and `10.1.0` with your firewall's details and the desired PAN-OS version.

## Output

<div class="termy">

```console
pan-os-upgrade --hostname 192.168.255.211 --username admin --password secret --version 10.2.0-h2
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
INFO - Device 007054000242050 downloading version: 10.2.0-h2
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

## Assurance Functions

The script performs various assurance functions like readiness checks, snapshots, and configuration backups. These are stored in the `assurance/` directory, structured as follows:

- `snapshots/`: Contains pre and post-upgrade network state snapshots in JSON format.
- `readiness_checks/`: Holds results of readiness checks in JSON format.
- `configurations/`: Stores backups of the firewall's configuration in XML format.

## Log Files

Log entries are recorded in the `logs/` directory. The script maintains a detailed log file that includes every step of the execution process. This is particularly useful for troubleshooting and review.

### Log Levels

You can control the verbosity of logs with the `--log-level` argument. Available options are `debug`, `info`, `warning`, `error`, and `critical`. The default level is `info`.

## Next Steps

After familiarizing yourself with the execution process and output, proceed to the [Troubleshooting Guide](troubleshooting.md) of the user guide for detailed insights into troubleshooting and advanced tips.
