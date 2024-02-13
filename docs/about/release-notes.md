# Release Notes

Welcome to the release notes for the `pan-os-upgrade` tool. This document provides a detailed record of changes, enhancements, and fixes in each version of the tool.

## Version 1.2.0

**Release Date:** *<20240213>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Revamped ability to select multiple firewalls when using Panorama as a communication proxy
- Removed support for `-f` and `--filter` flags, instead relying on interactive selection menu
- Added new subcommand `inventory`, which will create an `inventory.yaml` file based on selected firewalls

## Version 1.1.6

**Release Date:** *<20240211>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Added over 100 tests
- Changed default behavior of ARP snapshots to False

## Version 1.1.5

**Release Date:** *<20240209>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Support for skipping all readiness checks and snapshots with `settings` subcommand

## Version 1.1.4

**Release Date:** *<20240209>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Documentation bug fixes
- Support for `-c` in hotfix name

## Version 1.1.3

**Release Date:** *<20240208>*

### What's New

- Documentation bug fixes

## Version 1.1.2

**Release Date:** *<20240208>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Fixed a bug that prevented HA Panorama appliances from being targeted for upgrades

## Version 1.1.1

**Release Date:** *<20240204>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Fixed a bug that prevented access to the `logo.png` file used by the PDF generation process

## Version 1.1.0

**Release Date:** *<20240204>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Pre/Post upgrade diff report created in PDF format
- Changed structure of AssuranceOptions
- `enabled_by_default` key added to allow for declaring which tests will execute by default
- Introduced "skipped" emoji to bring awareness to which tests and checks are skipped
- Using custom fork for `panos-upgrade-assurance` to account for integer values for `ttl` in ARP snapshots
- Added a new troubleshooting item to address how to handle when ARP snapshots fail due to a bug in the dependency
- Formatting and docstrings revisited

## Version 1.0.0

**Release Date:** *<20240131>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Shipping first release! 🚀

## Version 0.4.3

**Release Date:** *<20240129>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Created workflow that will download the base image if making a major/minor upgrade
- Included new download settings to be overridden with `pan-os-upgrade` settings
- Provide helpful message when a target version is not selected, providing suggestions of similar versions that are available.

## Version 0.4.2

**Release Date:** *<20240127>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Created mechanism to override the default settings of `pan-os-upgrade`
- Added support for new CLI argument, `pan-os-upgrade settings`
- Created a banner message to help with usability

## Version 0.4.1

**Release Date:** *<20240127>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Resolved an issue where missing fields in session snapshots for older PAN-OS versions caused errors in Pydantic models
- Updated the requirements.txt file to reflect the latest compatible versions of dependencies
- Refined the reboot logic to make it more straightforward, improving code readability and maintainability

## Version 0.4.0

**Release Date:** *<20240126>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Support for three unique workflows:
  - `firewall`: targets and upgrades an individual firewall
  - `panorama`: targets and upgrades an individual Panorama appliance
  - `batch`: targets a Panorama appliance and upgrades firewalls in batch
    - The script will support up to ten simultaneous upgrades
    - Requires a filter string to be passed to identify target firewalls

## Version 0.3.0

**Release Date:** *<20240125>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Multi-threading added for concurrent upgrades (max limit of threads is 10).
- Gracefully handle HA upgrades for HA active/passive peers.
- Added hostname to log entries to differentiate threaded upgrades.

## Version 0.2.5

**Release Date:** *<20240123>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Supports the ability to connect to Panorama as a proxy for firewall connections
- Added new `--filter` CLI option for Panorama connections
- Resolved issue where standalone firewalls were not properly signaling their completion
- Added additional validation step to ensure the upgraded firewall matches the target version after reboot

## Version 0.2.4

**Release Date:** *<20240122>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Resolved a bug where console logging was duplicated
- Simplified the non-debug console log output
- Removed `requirements.txt` from Docker container image

## Version 0.2.4

**Release Date:** *<20240121>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Improved error handling for network layer transport.
- Included new dependency [DNS Python](https://www.dnspython.org/) for hostname lookup

## Version 0.2.2

**Release Date:** *<20240121>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Optimized for Docker execution.
- Refreshed documentation to showcase both paths of execution (Python virtual environments and Docker)

## Version 0.2.1

**Release Date:** *<20240121>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Adjusting the execution of our script to instead reference the Typer app `app()` instead of `main()`.
- Updated the `pan-os-upgrade` alias within the pyproject.toml file to directly call `app()` instead of `main()`

## Version 0.2.0

**Release Date:** *<20240121>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- Allow for simply running `pan-os-upgrade` without arguments, providing an interactive prompt for missing variables
- Replaced `argparse` with `typer` for command-line argument parsing, offering a more intuitive and user-friendly CLI experience.
- Removed the option for API key authentication to streamline the authentication process.
- Removed the `.env` file lookup feature. Configuration is now exclusively handled through command-line arguments.
- Updated the `hostname` variable to `ip_address` for clarity and consistency.
- Changed `target_version` parameter name to simply `version` to make it more concise.

### Breaking Changes

- Scripts and automation tools using the previous `argparse` syntax or `.env` file for configuration will need to be updated to use the new `typer` CLI arguments.

## Version 0.1.1

**Release Date:** *<20240119>*

<!-- trunk-ignore(markdownlint/MD024) -->
### What's New

- First official release of the `pan-os-upgrade` tool on PyPi.
- Made available for wide usage and distribution.

### Notes

- Includes all the features and functionalities as they were in the initial development build.

## Version 0.1.0

**Release Date:** *<20240118>*

### Introduction

- Initial development build of the `pan-os-upgrade` tool.
- Laid down the foundation for the tool's functionalities and features.

---

For more detailed information on each release, visit the [GitHub repository](https://github.com/cdot65/pan-os-upgrade/releases) or check the [commit history](https://github.com/cdot65/pan-os-upgrade/commits/main).