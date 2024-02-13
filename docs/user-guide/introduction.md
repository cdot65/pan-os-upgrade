# Introduction

## Purpose of the Project

The `pan-os-upgrade` CLI tool is designed to streamline and simplify the process of upgrading Palo Alto Networks firewalls. This tool offers two distinct workflows to cater to different user preferences and environments: a Python-based workflow and a Docker-based workflow.

## Problem Statement

Upgrading firewalls can be intricate and tedious, posing numerous challenges. The `pan-os-upgrade` tool addresses these by:

- Performing a series of readiness checks.
- Taking snapshots of the current network state.
- Creating backups of the configuration before initiating the upgrade process.

## Two Distinct Workflows

### Python Workflow

This workflow is ideal for those who prefer working within a Python environment. It involves setting up a Python virtual environment, installing dependencies, and executing the tool via command-line interface.

- **Advantages**: Offers more control and flexibility, especially for users familiar with Python.
- **Details**: See the [Python Workflow Getting Started Guide](python/getting-started.md) for detailed instructions on setup and usage.

### Docker Workflow

The Docker workflow simplifies the setup by encapsulating the tool and its dependencies within a Docker container. It's suitable for users seeking an easy-to-deploy solution without configuring a Python environment.

- **Advantages**: Ensures consistent runtime environment, simplifies deployment, and is ideal for users not familiar with Python.
- **Details**: Refer to the [Docker Workflow Getting Started Guide](docker/getting-started.md) for comprehensive steps on using the Docker container.

## Key Features

`pan-os-upgrade` is equipped with several features for efficient and reliable upgrades:

- **Automation of Routine Tasks**: Reduces manual errors and saves time by automating upgrades, configurations, and system checks.
- **Support for Direct and Proxy Connections**: Connect directly to firewalls or through a Panorama appliance.
- **Active/Passive High Availability (HA) Workflow**: Fully supports upgrading devices in active/passive HA configurations, ensuring both members are properly upgraded and synchronized.
- **Multi-threading for Efficiency**: Utilizes multi-threading to parallelize upgrades, especially beneficial when upgrading multiple devices through Panorama, enhancing performance and reducing overall upgrade time.
- **Customizable and Extensible**: Scripts can be tailored to fit diverse network environments and requirements, offering flexibility for various deployment scenarios.
- **Comprehensive PAN-OS Interactions**: Facilitates extensive interactions with Palo Alto Networks appliances for operations like readiness checks, state snapshots, and report generation.
- **Interactive Menu for Firewall Selection**: Introduces an interactive menu for selecting specific firewalls to target for upgrade, streamlining the process of identifying and confirming devices for upgrade within a Panorama-managed environment.

## Next Steps

With an understanding of `pan-os-upgrade` and its dual workflows, you can choose the approach that best suits your needs. Follow the respective guides to set up and start using the tool for upgrading your Palo Alto Networks firewalls.
