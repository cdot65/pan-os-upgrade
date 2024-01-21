# Configuration Guide for pan-os-upgrade

Proper configuration is vital for the effective use of the `pan-os-upgrade` package. As of the latest update, configuration can be done primarily through command-line arguments.

## Executing `pan-os-upgrade`

### Option 1: Execute Without Command-Line Arguments

You can start the script by simply issuing `pan-os-upgrade` from your current working directory. The interactive shell will prompt you to input the required arguments.

```bash
$ pan-os-upgrade
IP address: 192.168.255.1
Username: admin
Password:
Target PAN-OS version: 11.1.1
...output...
```

### Option 2: Execute Using Command-Line Arguments

Alternatively, you can pass these details as command-line arguments:

```bash
$ pan-os-upgrade --ip-address 192.168.1.1 --username admin --password secret --version 10.1.0
```

For a dry run:

```bash
$ pan-os-upgrade --ip-address 192.168.1.1 --username admin --password secret --version 10.1.0 --dry-run
```

## CLI Arguments Description

When using command-line arguments, the following options are available:

| Argument       | Description                                                          | Required |
| -------------- | -------------------------------------------------------------------- | -------- |
| `--ip-address` | IP address of the target PAN-OS firewall.                            | Yes      |
| `--username`   | Username for authentication with the firewall.                       | Yes      |
| `--password`   | Password for authentication with the firewall.                       | Yes      |
| `--version`    | Target PAN-OS version to upgrade to.                                 | Yes      |
| `--dry-run`    | Perform a dry run of all tests and downloads without actual upgrade. | No       |
| `--log-level`  | Set the logging output level (e.g., debug, info, warning).           | No       |

Note: The use of an API key and `.env` file for configuration is no longer supported.

## Next Steps

After configuring `pan-os-upgrade`, you're ready to execute the upgrade process. For more details on execution steps and options, proceed to the [Execution Guide](execution.md).
