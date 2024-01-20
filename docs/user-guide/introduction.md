# Introduction

## Purpose of the Project

The `pan-os-upgrade` CLI tool is designed to streamline and simplify the process of upgrading Palo Alto Networks firewalls. Upgrading firewalls is not only challenging but also a tedious task fraught with potential complications. This tool aims to assist firewall administrators through this complex process by automating several critical steps.

## Problem Statement

Firewall upgrades can be intricate and tedious, with numerous issues that might arise from a variety of situations. The `pan-os-upgrade` tool addresses these challenges by:

- Performing a series of readiness checks.
- Taking snapshots of the current network state.
- Creating backups of the configuration before initiating the upgrade process.

These steps ensure a smoother and more reliable upgrade process, mitigating the risks associated with manual upgrades.

## Key Features

The tool is built with several key features to enhance its efficiency and reliability:

- **Leveraging `panos-upgrade-assurance`**: `pan-os-upgrade` utilizes the `panos-upgrade-assurance` library to manage the more complex aspects of the upgrade process. This includes pre and post-validation of the firewall's state, ensuring the integrity of the network environment, such as routing tables, ARP tables, and network interface statuses.

- **Data Validation with Pydantic**: To minimize bugs and ensure smooth workflow execution, `pan-os-upgrade` incorporates Pydantic for robust data structure validation. This feature plays a crucial role in handling the input and output of data within the automation scripts, reducing instances of errors and enhancing the script's reliability.

## Next Steps

Now that you have an overview of the `pan-os-upgrade` tool and its capabilities, the next step is to get started with setting up and using the tool. The following guide will walk you through the initial setup and basic usage.

Continue to the [Getting Started](getting-started.md) guide to begin using `pan-os-upgrade`.
