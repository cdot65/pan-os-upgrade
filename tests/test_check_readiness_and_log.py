from pan_os_upgrade.upgrade import check_readiness_and_log


def mock_get_emoji(emoji_name):
    return f":{emoji_name}:"


def test_readiness_check_passed(mocker):
    mock_info = mocker.patch("pan_os_upgrade.upgrade.logging.info")
    mocker.patch("pan_os_upgrade.upgrade.get_emoji", side_effect=mock_get_emoji)

    result = {"software_version_check": {"state": True}}
    test_info = {
        "description": "Software Version Check",
        "log_level": "info",
        "exit_on_failure": False,
    }

    check_readiness_and_log(
        result, "fw01.example.com", "software_version_check", test_info
    )

    mock_info.assert_called_with(
        ":success: fw01.example.com: Passed Readiness Check: Software Version Check"
    )


def test_readiness_check_failed_non_critical(mocker):
    mock_error = mocker.patch("pan_os_upgrade.upgrade.logging.error")
    mocker.patch("pan_os_upgrade.upgrade.get_emoji", side_effect=mock_get_emoji)

    result = {
        "software_version_check": {
            "state": False,
            "reason": "Unsupported software version",
        }
    }
    test_info = {
        "description": "Software Version Check",
        "log_level": "error",
        "exit_on_failure": False,
    }

    check_readiness_and_log(
        result, "fw01.example.com", "software_version_check", test_info
    )

    mock_error.assert_called_with(
        ":error: fw01.example.com: Unsupported software version: Software Version Check"
    )


def test_readiness_check_failed_critical(mocker):
    mock_error = mocker.patch("pan_os_upgrade.upgrade.logging.error")
    mocker.patch("pan_os_upgrade.upgrade.get_emoji", side_effect=mock_get_emoji)
    mock_exit = mocker.patch("sys.exit")

    result = {
        "software_version_check": {
            "state": False,
            "reason": "Unsupported software version",
        }
    }
    test_info = {
        "description": "Software Version Check",
        "log_level": "error",
        "exit_on_failure": True,
    }

    check_readiness_and_log(
        result, "fw01.example.com", "software_version_check", test_info
    )

    mock_error.assert_any_call(
        ":error: fw01.example.com: Unsupported software version: Software Version Check"
    )
    mock_error.assert_any_call(":stop: fw01.example.com: Halting script.")
    mock_exit.assert_called_once_with(1)
