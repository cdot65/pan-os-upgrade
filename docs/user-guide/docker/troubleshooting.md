# Troubleshooting Guide for Docker Execution of pan-os-upgrade

Encountering issues during the Docker execution of `pan-os-upgrade` can happen, especially when dealing with different system environments. This guide aims to address common problems and their solutions.

## Common Issues and Solutions

### 1. Docker Image Not Found

**Problem:** Unable to find or pull the `pan-os-upgrade` Docker image.

**Solution:** Ensure you have a stable internet connection and access to GitHub Packages. Verify the image name: `ghcr.io/cdot65/pan-os-upgrade:latest`.

**Alternative:** You can build your own image by navigating to the `docker/` directory in the repository and running the standard `docker build` process.

### 2. Volume Mount Issues

**Problem:** Errors related to mounting volumes for `assurance` and `logs` directories.

**Solution:** Ensure the directories exist on your host machine. Check your Docker run command for typos. For Windows, replace `$(pwd)` with `%CD%`.

### 3. Interactive Shell Not Responding

**Problem:** The interactive shell within the Docker container does not accept input.

**Solution:** Ensure the container is running in interactive mode (`-it` flag). Try restarting the Docker service.

### 4. No Output in Mounted Directories

**Problem:** The `assurance` and `logs` directories on the host are empty after container execution.

**Solution:** Verify the Docker run command for correct volume mounting syntax. Ensure the container has the necessary permissions to write to these directories.

### 5. Docker Container Exits Unexpectedly

**Problem:** The Docker container stops running prematurely.

**Solution:** Check the Docker container logs for any error messages. Ensure the container has sufficient resources (memory, CPU).

### 6. Network Connectivity Issues

**Problem:** The script within the Docker container cannot connect to the PAN-OS device.

**Solution:** Verify network settings and ensure the Docker container has network access. Check firewall settings, Hostname, and IP address.

### 7. Docker Version Compatibility

**Problem:** Issues running `pan-os-upgrade` due to Docker version incompatibility.

**Solution:** Ensure you are using a compatible version of Docker. Update Docker to the latest version if necessary.

## General Tips

- Always verify your Docker setup and configurations before running `pan-os-upgrade`.
- For complex Docker setups, consider simplifying or breaking down the execution process to isolate issues.
- Regularly update your Docker images to get the latest version of `pan-os-upgrade`.

## Reporting Issues

If you encounter a problem not covered in this guide, please report it on the [GitHub issues page](https://github.com/cdot65/pan-os-upgrade/issues) of `pan-os-upgrade`. Include detailed information, such as the Docker version, system environment, and any relevant logs or error messages.
