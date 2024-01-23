# Troubleshooting Guide for pan-os-upgrade

Encountering issues while using the `pan-os-upgrade` tool is not uncommon, especially in complex network environments. This guide provides troubleshooting steps for common problems you might face during the upgrade process, including connections through Panorama.

## Common Issues and Solutions

### 1. Connection Issues

**Problem:** The script fails to connect to the PAN-OS device.

**Solution:** Ensure that the firewall's or Panorama's hostname/IP and credentials are correct. Verify network connectivity and accessibility. If connecting through Panorama, ensure Panorama is reachable.

### 2. Filter Option Issues

**Problem:** Incorrect or no devices selected when using `--filter` with Panorama.

**Solution:** Verify the filter string used in the `--filter` option. Ensure it accurately matches the criteria of the devices managed by Panorama. Check for correct syntax and valid values.

### 3. Upgrade Failures

**Problem:** The script stops during the upgrade process.

**Solution:** Check the firewall and network settings. Make sure the PAN-OS device is responding correctly. Review the logs in the `logs/` directory for specific error messages.

### 4. Script Hangs

**Problem:** The script hangs or does not progress.

**Solution:** Interrupt the script (Ctrl+C) and check the log files for any clues. Common issues might be network latency or firewall response delays.

### 5. Incorrect PAN-OS Version

**Problem:** The wrong PAN-OS version is downloaded or installed.

**Solution:** Verify the target PAN-OS version specified in the command-line arguments. Ensure compatibility with your firewall model.

### 6. Readiness Check Failures

**Problem:** The script fails during readiness checks.

**Solution:** Investigate individual readiness check failures. Common issues include unsynchronized system clocks, pending configuration changes, or insufficient disk space.

### 7. HA Synchronization Issues

**Problem:** The script reports High Availability (HA) synchronization issues.

**Solution:** Check the HA status of the firewall. Ensure both HA members are in a stable and synchronized state before proceeding with the upgrade.

### 8. Configuration Backup Errors

**Problem:** The script fails to back up the firewall's configuration.

**Solution:** Verify that there is enough disk space for the backup. Check permissions and paths specified for saving the backup files.

## General Tips

- Always perform a dry run (`--dry-run`) before executing the actual upgrade.
- Keep the firewall's firmware and `pan-os-upgrade` tool updated to the latest versions.
- Review the `logs/` directory for detailed logs if any issues arise.
- For complex environments, consider running the script in stages to isolate issues.

## Reporting Issues

If you encounter an issue not covered in this guide, please report it on the [issues page](https://github.com/cdot65/pan-os-upgrade/issues) of our GitHub repository. Provide detailed information including log excerpts, firewall models, PAN-OS versions, and Panorama configurations to help diagnose the problem.
