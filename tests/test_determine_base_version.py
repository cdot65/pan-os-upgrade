import pytest

from pan_os_upgrade.components.utilities import determine_base_version


@pytest.mark.parametrize(
    "available_versions, target_major, target_minor, expected",
    [
        # Legacy releases whose base image is x.y.0
        (["10.1.0", "10.1.1", "10.1.11-h4", "10.2.0"], 10, 1, "10.1.0"),
        (["11.1.4", "11.1.0", "11.1.2-h3"], 11, 1, "11.1.0"),
        # Releases whose base image is not x.y.0
        (["12.1.2", "12.1.3-h1", "12.1.4", "11.2.0"], 12, 1, "12.1.2"),
        (["12.2.10", "12.2.3", "12.2.2", "12.1.2"], 12, 2, "12.2.2"),
        # Hotfixes are never treated as the base image
        (["12.1.1-h1", "12.1.2", "12.1.2-h2"], 12, 1, "12.1.2"),
        # Other feature releases must not be matched (e.g. 2.1 vs 12.1 / 12.10)
        (["12.10.1", "2.1.1", "12.1.2"], 12, 1, "12.1.2"),
        # Falls back to x.y.0 when nothing is known about the feature release
        (["11.2.0", "11.2.1"], 12, 1, "12.1.0"),
        ([], 12, 1, "12.1.0"),
    ],
)
def test_determine_base_version(
    available_versions, target_major, target_minor, expected
):
    assert (
        determine_base_version(
            available_versions=available_versions,
            target_major=target_major,
            target_minor=target_minor,
        )
        == expected
    )


def test_determine_base_version_accepts_software_versions_dict():
    available_versions = {
        "12.1.2": {"downloaded": False},
        "12.1.4": {"downloaded": False},
    }
    assert determine_base_version(available_versions, 12, 1) == "12.1.2"
