from pan_os_upgrade.utilities import resolve_hostname


def test_resolve_hostname_success():
    # Test with a well-known domain expected to resolve successfully
    hostname = "google.com"
    assert resolve_hostname(
        hostname
    ), f"Expected True for resolving '{hostname}', but it failed."


def test_resolve_hostname_failure():
    # Test with a made-up domain that is unlikely to exist
    # Note: There's a small chance this test could fail if the domain gets registered
    hostname = "nonexistent-domain-1234567890.com"
    assert not resolve_hostname(
        hostname
    ), f"Expected False for resolving '{hostname}', but it succeeded."
