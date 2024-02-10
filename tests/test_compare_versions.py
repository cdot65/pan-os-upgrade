import pytest
from pan_os_upgrade.upgrade import (
    compare_versions,
)


# Test cases for versions where the first is older than the second
@pytest.mark.parametrize(
    "version1, version2, expected",
    [
        ("8.1.0", "8.2.0", "older"),
        ("8.0.0", "8.0.1", "older"),
        ("9.1.0", "9.1.1-h1", "older"),
        ("10.0.0", "10.0.0-h1", "older"),
    ],
)
def test_compare_versions_older(version1, version2, expected):
    # trunk-ignore(bandit/B101)
    assert compare_versions(version1, version2) == expected


# Test cases for versions where the first is newer than the second
@pytest.mark.parametrize(
    "version1, version2, expected",
    [
        ("8.2.0", "8.1.0", "newer"),
        ("8.0.1", "8.0.0", "newer"),
        ("9.1.1-h1", "9.1.0", "newer"),
        ("10.0.0-h1", "10.0.0", "newer"),
    ],
)
def test_compare_versions_newer(version1, version2, expected):
    # trunk-ignore(bandit/B101)
    assert compare_versions(version1, version2) == expected


# Test cases for versions that are equal
@pytest.mark.parametrize(
    "version1, version2",
    [
        ("8.1.0", "8.1.0"),
        ("9.0.1-h1", "9.0.1-h1"),
        ("10.0.0-h1", "10.0.0-h1"),
    ],
)
def test_compare_versions_equal(version1, version2):
    # trunk-ignore(bandit/B101)
    assert compare_versions(version1, version2) == "equal"
