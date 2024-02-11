import pytest
from pan_os_upgrade.upgrade import filter_string_to_dict


def test_filter_string_to_dict_with_valid_input():
    filter_string = "status=active,region=eu,env=production"
    expected_dict = {"status": "active", "region": "eu", "env": "production"}
    assert filter_string_to_dict(filter_string) == expected_dict


def test_filter_string_to_dict_with_empty_string():
    filter_string = ""
    expected_dict = {}
    assert filter_string_to_dict(filter_string) == expected_dict


def test_filter_string_to_dict_with_malformed_input():
    filter_string = "status-active,region=eu"
    with pytest.raises(ValueError) as exc_info:
        filter_string_to_dict(filter_string)
    assert "malformed" in str(exc_info.value)


def test_filter_string_to_dict_with_duplicate_keys():
    filter_string = "status=active,status=pending"
    expected_dict = {"status": "pending"}  # Last one wins
    assert filter_string_to_dict(filter_string) == expected_dict
