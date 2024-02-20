import pytest

from pan_os_upgrade.components.utilities import parse_version


# Test cases for valid version strings, including the new "-c" prefix and the blip of time when "-xfr" was used
@pytest.mark.parametrize(
    "version, expected",
    [
        ("1.0.0", (1, 0, 0, 0)),
        ("2.5.3", (2, 5, 3, 0)),
        ("4.2.0-h1", (4, 2, 0, 1)),
        ("3.10.4-h2", (3, 10, 4, 2)),
        ("0.9.0-h0", (0, 9, 0, 0)),
        ("6.3.5-c1", (6, 3, 5, 1)),
        ("5.4.2-c232", (5, 4, 2, 232)),
        ("9.0.9.xfr", (9, 0, 9, 0)),
        ("9.0.9-h1.xfr", (9, 0, 9, 1)),
    ],
)
def test_parse_version_valid(version, expected):
    assert (
        parse_version(version) == expected
    ), f"Expected {expected} for version '{version}'"


# Test cases for invalid version strings
@pytest.mark.parametrize(
    "invalid_version",
    [
        "1.0-h3",
        "a.b.c",
        "1.0.0-h",
        "1.0.-1",
        "1..0",
        "1.0.0.h1",
        "1.0.0-hx",  # Invalid hotfix format
        "1.0.0-cx",  # Invalid custom format
    ],
)
def test_parse_version_invalid(invalid_version):
    with pytest.raises(ValueError):
        parse_version(invalid_version)
