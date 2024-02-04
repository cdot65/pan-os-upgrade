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

**Solution:** Investigate individual readiness check failures. Common issues include unsynchronized system clocks, pending configuration changes, or insufficient disk space. Also consider using `pan-os-upgrade settings` to create a custom `settings.yaml` file that will allow you to bypass the readiness checks that you're comfortable with skipping.

### 7. HA Synchronization Issues

**Problem:** The script reports High Availability (HA) synchronization issues.

**Solution:** Check the HA status of the firewall. Ensure both HA members are in a stable and synchronized state before proceeding with the upgrade.

### 8. Configuration Backup Errors

**Problem:** The script fails to back up the firewall's configuration.

**Solution:** Verify that there is enough disk space for the backup. Check permissions and paths specified for saving the backup files.

### 9. WSL2 Locale Errors

**Problem:** The script fails performing snapshots with the error of: `Error: unsupported locale setting`.

**Solution:**

1: Open your WSL2 terminal.
2: Run the command `sudo dpkg-reconfigure locales`.
3: In the configuration menu, scroll through the list of locales until you find `en_US.UTF-8`.
4: Use the space bar to select `en_US.UTF-8`.
5: Press Tab to select "Ok" and press Enter.
6: When prompted to choose the default locale, select `en_US.UTF-8` again and confirm.

After generating the locale, you can verify it's available by running `locale -a` in the terminal. You should see `en_US.UTF-8` in the list.

If you cannot request `sudo` permissions within WSL2, either use the `pan-os-upgrade` script from the Windows CMD terminal, or use the Docker container.

### 10. ARP Table Comparison Failures

**Problem:** When capturing ARP tables for comparison, the script fails with `WrongDataTypeException: Unknown value format for key ttl`.

**Solution:** This issue can arise when ARP table entries contain integer values for `ttl`, which the current implementation may not handle properly. To address this, consider installing a custom fork of `panos-upgrade-assurance` that includes a fix for this issue, available at [https://github.com/cdot65/pan-os-upgrade-assurance/tree/main](https://github.com/cdot65/pan-os-upgrade-assurance/tree/main). Alternatively, you can configure the script to omit ARP snapshots from the tests if modifying the script is not feasible.

**Steps to Install Custom Fork:**

1. Run this command: `pip install git+https://github.com/cdot65/pan-os-upgrade-assurance.git@main`

**Steps to Omit ARP Snapshots:**

1. If using a `settings.yaml` file, ensure ARP snapshots are disabled.
2. If running the script interactively, choose not to capture ARP snapshots when prompted.

## General Tips

- Always perform a dry run (`--dry-run`) before executing the actual upgrade.
- Keep the firewall's firmware and `pan-os-upgrade` tool updated to the latest versions.
- Review the `logs/` directory for detailed logs if any issues arise.
- For complex environments, consider running the script in stages to isolate issues.

## Reporting Issues

If you encounter an issue not covered in this guide, please report it on the [issues page](https://github.com/cdot65/pan-os-upgrade/issues) of our GitHub repository. Provide detailed information including log excerpts, firewall models, PAN-OS versions, and Panorama configurations to help diagnose the problem.
