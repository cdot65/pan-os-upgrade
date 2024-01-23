# Getting Started with pan-os-upgrade

Welcome to the `pan-os-upgrade` library! This guide is designed to help you set up the library in your environment, with a special focus on users who may be new to Python, pip, and virtual environments.

## Prerequisites

Before you begin, ensure you have the following:

- Python 3.8 or newer.
- Access to a Palo Alto Networks firewall or Panorama appliance.
- An active internet connection for downloading the package from PyPI.

## Installation

`pan-os-upgrade` is available on PyPI and can be easily installed within a Python virtual environment, which is a self-contained directory containing a Python installation and additional packages.

### Setting Up a Python Virtual Environment

A Python virtual environment is recommended, especially for beginners. It helps isolate the library installation from your system-wide Python setup.

**Create a Virtual Environment:**

Run the following command to create a new virtual environment named `panos_env`:

<div class="termy">

```console
python3 -m venv panos_env
```

</div>

This creates a new directory named `panos_env` with a copy of the Python interpreter and the standard library.

**Activate the Virtual Environment:**

- On Windows:

<div class="termy">

```console
panos_env\Scripts\activate
```

</div>

- On macOS and Linux:

<div class="termy">

```console
source panos_env/bin/activate
```

</div>

After activation, your command line will indicate that you are now in the virtual environment.

**Install `pan-os-upgrade`:**

Within the activated environment, install the package using pip:

<div class="termy">

```console
$ pip install pan-os-upgrade

---> 100%
```

</div>

## Next Steps

With `pan-os-upgrade` successfully installed in your virtual environment, the next step is to configure the library for use with your firewall. Visit the [Python Execution Guide](execution.md) to learn how to set up and configure `pan-os-upgrade` for your specific needs.
