import pytest
from pan_os_upgrade.components.utilities import console_welcome_banner
from pathlib import Path


@pytest.mark.parametrize(
    "mode, key_phrases",
    [
        (
            "inventory",
            [
                "Welcome to the PAN-OS upgrade inventory menu",
                "The selected 'inventory' subcommand will create `inventory.yaml` in your current directory.\nThis `inventory.yaml` file will contain firewalls to upgrade and will be loaded at runtime.",
            ],
        ),
        (
            "settings",
            [
                "Welcome to the PAN-OS upgrade settings menu",
                "The selected 'settings' subcommand will create `settings.yaml` in your current directory.\nThis `settings.yaml` file will contain your custom settings and will be loaded at runtime.",
            ],
        ),
        (
            "firewall",
            [
                "Welcome to the PAN-OS upgrade tool",
                "The selected `firewall` subcommand will upgrade a single Firewall appliance.",
            ],
        ),
        (
            "panorama",
            [
                "Welcome to the PAN-OS upgrade tool",
                "The selected `panorama` subcommand will upgrade a single Panorama appliance.",
            ],
        ),
        (
            "batch",
            [
                "Welcome to the PAN-OS upgrade tool",
                "The selected `batch` subcommand will upgrade one or more firewalls.",
            ],
        ),
    ],
)
def test_console_welcome_banner_modes(mode, key_phrases):
    banner = console_welcome_banner(mode)
    for phrase in key_phrases:
        assert phrase in banner


def test_console_welcome_banner_with_config_path(mocker):
    config_path = Path("/path/to/config.yaml")
    mocker.patch.object(Path, "exists", return_value=True)
    banner = console_welcome_banner("firewall", config_path=config_path)
    assert (
        f"Settings: Custom configuration loaded file detected and loaded at:\n{config_path}"
        in banner
    )


def test_console_welcome_banner_without_config_path():
    banner = console_welcome_banner("firewall")
    expected_message = (
        "Settings: No settings.yaml file was found, default values will be used.\n"
        "You can create a settings.yaml file with 'pan-os-upgrade settings' command."
    )
    assert expected_message in banner


def test_console_welcome_banner_with_inventory_path(mocker):
    inventory_path = Path("/path/to/inventory.yaml")
    mocker.patch.object(Path, "exists", return_value=True)
    banner = console_welcome_banner("batch", inventory_path=inventory_path)
    assert (
        f"Inventory: Custom inventory loaded file detected and loaded at:\n{inventory_path}"
        in banner
    )


def test_console_welcome_banner_without_inventory_path():
    banner = console_welcome_banner("batch")
    expected_message = "Inventory: No inventory.yaml file was found, firewalls will need be selected through the menu.\nYou can create an inventory.yaml file with 'pan-os-upgrade inventory' command."
    assert expected_message in banner
