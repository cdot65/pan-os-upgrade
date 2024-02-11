import pytest
from unittest.mock import patch
from pan_os_upgrade.upgrade import ha_sync_check_panorama

# Define test cases for different HA synchronization states for Panorama
# 'expected_result' is True if HA sync check should pass, and False if it should fail or the device is not in HA
test_cases = [
    ("panorama.cdot.io", None, True, False),  # Not in HA, should not pass
    (
        "panorama1.cdot.io",
        {"result": {"running-sync": "synchronized"}},
        True,
        True,
    ),  # In HA and synchronized
    (
        "panorama2.cdot.io",
        {"result": {"running-sync": "unsynchronized"}},
        True,
        False,
    ),  # In HA but unsynchronized
]


@pytest.mark.integration
@pytest.mark.parametrize(
    "hostname, ha_details, strict_sync_check, expected_result", test_cases
)
def test_ha_sync_check_panorama(
    hostname, ha_details, strict_sync_check, expected_result
):
    # Patch the logging within ha_sync_check_panorama to prevent actual logging during the test
    with patch("pan_os_upgrade.upgrade.logging"):
        if strict_sync_check and not expected_result:
            # Expect SystemExit due to strict sync check failure
            with pytest.raises(SystemExit):
                ha_sync_check_panorama(hostname, ha_details, strict_sync_check)
        else:
            result = ha_sync_check_panorama(hostname, ha_details, strict_sync_check)

            # Assert the function's behavior matches the expected outcome
            assert (
                result == expected_result
            ), f"HA sync check for {hostname} returned {result}, expected {expected_result}."
