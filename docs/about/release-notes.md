# Release Notes

Welcome to the release notes for the `pan-os-upgrade` tool. This document provides a detailed record of changes, enhancements, and fixes in each version of the tool.

## Version 0.2.4

**Release Date:** *<20240122>*

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
