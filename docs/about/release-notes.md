# Release Notes

Welcome to the release notes for the `pan-os-upgrade` tool. This document provides a detailed record of changes, enhancements, and fixes in each version of the tool.

## Version 0.2.0

**Release Date:** *<20240121>*

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

### Highlights

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
