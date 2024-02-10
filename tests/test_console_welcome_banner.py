import pytest
from pan_os_upgrade.upgrade import console_welcome_banner
from pathlib import Path


@pytest.mark.parametrize(
    "mode, key_phrases",
    [
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
    assert "No settings.yaml file was found. Default values will be used." in captured
