# Configuration Guide for pan-os-upgrade

Proper configuration is crucial for the effective use of the `pan-os-upgrade` package. There are two main methods to configure the tool: using a `.env` file or passing command-line arguments. Each method has its strengths and weaknesses, which we'll explore below.

## Option 1: Using a `.env` File

A `.env` file is a simple way to store configuration settings in key-value pairs. This method is advantageous for keeping your configuration organized and easily editable in one place.

**Creating a `.env` File:**

1. Create a `.env` file in your project's root directory.
2. Add your firewall's details to the file, as shown below:

```env
# PAN-OS credentials - use either API key or username/password combination
PAN_USERNAME=admin
PAN_PASSWORD=paloalto123
API_KEY=

# Hostname or IP address of the firewall
HOSTNAME=firewall1.example.com

# Target PAN-OS version for the upgrade
TARGET_VERSION=11.0.2-h3

# Logging level (e.g., debug, info, warning, error, critical)
LOG_LEVEL=debug

# Set to true for a dry run
DRY_RUN=false
```

**Pros:**

- Centralized configuration management.
- Easy to update or modify settings.

**Cons:**

- Risk of committing sensitive information to a version control system if not properly ignored.
- Less flexibility for dynamic or per-run configurations.

## Option 2: Using Command-Line Arguments

Command-line arguments offer a direct way to pass configuration settings each time you run the script.

**Passing Details via Command-Line:**

- Standard Usage:

```bash
pan-os-upgrade --hostname 192.168.1.1 --username admin --password secret --version 10.1.0
```

- For a Dry Run:

```bash
pan-os-upgrade --hostname 192.168.1.1 --username admin --password secret --version 10.1.0 --dry-run
```

**Pros:**

- Greater control and flexibility for each run.
- Avoids storing sensitive details in a file.

**Cons:**

- Risk of exposing sensitive information in console history.
- Less convenient for repeated use with the same settings.

## CLI Arguments Description

When using command-line arguments, the following options are available:

| argument      | description                                                               | required  |
| ------------- | ------------------------------------------------------------------------- | --------- |
| `--api-key`   | API Key for authentication                                                | required* |
| `--dry-run`   | Dry run of all tests and downloads without performing the actual upgrade. | optional  |
| `--hostname`  | Hostname or IP address of the PAN-OS firewall.                            | optional  |
| `--log-level` | Set the logging output level (e.g., debug, info, warning).                | optional  |
| `--password`  | Password for authentication.                                              | required* |
| `--username`  | Username for authentication.                                              | required* |
| `--version`   | Target PAN-OS version to upgrade to.                                      | required  |

<small>* if using a <code>--api-key</code> for authentication, omit the <code>--username</code> and <code>--password</code> arguments; opposite is also true.</small>

## Next Steps

After configuring `pan-os-upgrade`, you're ready to execute the upgrade process. To learn more about the execution steps and options, proceed to the [Execution Guide](execution.md).
