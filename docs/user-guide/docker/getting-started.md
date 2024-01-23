# Getting Started with pan-os-upgrade using Docker

Welcome to the Docker-based workflow of the `pan-os-upgrade` library! This guide will help you set up and use the `pan-os-upgrade` tool within a Docker container. This approach is ideal for users who prefer a containerized environment or who are not as familiar with Python environments.

## Prerequisites

Before starting, make sure you have:

- Docker installed on your system. Visit the [Docker installation guide](https://docs.docker.com/get-docker/) for instructions.
- Access to a Palo Alto Networks firewall or Panorama appliance.
- An active internet connection for pulling the Docker image.

## Pulling the Docker Image

The `pan-os-upgrade` Docker image is hosted on GitHub Packages. Pull the image using the following command:

```bash
docker pull ghcr.io/cdot65/pan-os-upgrade:latest
```

## Building the Docker Image

As an alternative, if you would like to build the container yourself then simply navigate to the `docker` directory in the root of the repository. From there you can modify the Dockerfile to your liking and build your own custom image.

## Next Steps

With the Docker container set up and ready, you can begin using the `pan-os-upgrade` tool to automate PAN-OS upgrades. For detailed configuration instructions, proceed to the [Docker Execution Guide](execution.md).
