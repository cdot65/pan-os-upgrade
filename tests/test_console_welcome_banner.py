import pytest
from pan_os_upgrade.upgrade import console_welcome_banner
from pathlib import Path


@pytest.mark.parametrize(
    "mode, key_phrases",
    [
        ("inventory", ["Welcome to the PAN-OS upgrade inventory menu"]),
        ("settings", ["Welcome to the PAN-OS upgrade settings menu"]),
        (
            "firewall",
            [
                "Welcome to the PAN-OS upgrade tool",
                "You have selected to upgrade a single Firewall appliance.",
            ],
        ),
        (
            "panorama",
            [
                "Welcome to the PAN-OS upgrade tool",
                "You have selected to upgrade a single Panorama appliance.",
            ],
        ),
        (
            "batch",
            [
                "Welcome to the PAN-OS upgrade tool",
                "You have selected to perform a batch upgrade of firewalls through Panorama.",
            ],
        ),
    ],
)
def test_console_welcome_banner_modes(capsys, mode, key_phrases):
    console_welcome_banner(mode)
    captured = capsys.readouterr().out
    for phrase in key_phrases:
        assert phrase in captured


def test_console_welcome_banner_with_config_path(capsys):
    config_path = Path("/path/to/config.yaml")
    console_welcome_banner("firewall", config_path=config_path)
    captured = capsys.readouterr().out
    assert f"Custom configuration loaded from:\n{config_path}" in captured


def test_console_welcome_banner_without_config_path(capsys):
    console_welcome_banner("firewall")
    captured = capsys.readouterr().out
    expected_message = (
        "No settings.yaml file was found, the script's default values will be used.\n"
        "Create a settings.yaml file with 'pan-os-upgrade settings' command."
    )
    assert expected_message in captured


def test_console_welcome_banner_inventory_mode(capsys):
    console_welcome_banner("inventory")
    captured = capsys.readouterr().out
    expected_phrases = [
        "Welcome to the PAN-OS upgrade inventory menu",
        "Select which firewalls to upgrade based on a list of those connected to Panorama.",
        "This will create an `inventory.yaml` file in your current working directory.",
    ]

    for phrase in expected_phrases:
        assert phrase in captured, f"Phrase '{phrase}' not found in banner output"
