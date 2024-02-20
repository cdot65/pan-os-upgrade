from pan_os_upgrade.utilities import find_close_matches


def test_find_close_matches_exact_match():
    available_versions = ["9.1.0", "10.0.0", "10.1.0", "10.1.1"]
    target_version = "10.1.0"
    expected_matches = ["10.1.0", "10.1.1", "10.0.0", "9.1.0"]
    assert find_close_matches(available_versions, target_version) == expected_matches


def test_find_close_matches_minor_differences():
    available_versions = ["9.1.0", "10.0.1", "10.1.0", "10.1.2"]
    target_version = "10.1.1"
    expected_matches = {"10.1.2", "10.1.0", "10.0.1", "9.1.0"}
    results = set(find_close_matches(available_versions, target_version))
    assert results.issubset(expected_matches)


def test_find_close_matches_with_hotfixes():
    available_versions = ["10.1.0", "10.1.1-h1", "10.1.1-h2", "10.1.2"]
    target_version = "10.1.1"
    expected_matches = {"10.1.1-h1", "10.1.1-h2", "10.1.2", "10.1.0"}
    results = set(find_close_matches(available_versions, target_version))
    assert results.issubset(expected_matches)


def test_find_close_matches_limited_results():
    available_versions = ["9.0.0", "9.1.0", "10.0.0", "10.1.0", "10.1.1", "10.1.2"]
    target_version = "10.1.1"
    max_results = 3
    expected_matches = {"10.1.1", "10.1.2", "10.1.0"}
    results = set(find_close_matches(available_versions, target_version, max_results))
    assert len(results) <= max_results and results.issubset(expected_matches)
