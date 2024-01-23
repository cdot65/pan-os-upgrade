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

- **Leveraging `panos-upgrade-assurance`**: It utilizes the `panos-upgrade-assurance` library to manage complex aspects of the upgrade process.
- **Data Validation with Pydantic**: Ensures robust data structure validation, minimizing bugs and streamlining workflow execution.
- **Flexible Connection Methods**: Connect to firewalls directly or by targeting a Panorama appliance with a `--filter` CLI option.

## Next Steps

With an understanding of `pan-os-upgrade` and its dual workflows, you can choose the approach that best suits your needs. Follow the respective guides to set up and start using the tool for upgrading your Palo Alto Networks firewalls.
