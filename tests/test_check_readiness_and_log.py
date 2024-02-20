from pan_os_upgrade.assurance import check_readiness_and_log
from pan_os_upgrade.utilities import get_emoji


def test_readiness_check_passed(mocker):
    mock_info = mocker.patch("pan_os_upgrade.main.logging.info")

    result = {"software_version_check": {"state": True}}
    test_info = {
        "description": "Software Version Check",
        "log_level": "info",
        "exit_on_failure": False,
    }

    check_readiness_and_log(
        hostname="fw01.example.com",
        result=result,
        test_info=test_info,
        test_name="software_version_check",
    )

    mock_info.assert_called_with(
        f"{get_emoji('success')} fw01.example.com: Passed Readiness Check: Software Version Check"
    )


def test_readiness_check_failed_non_critical(mocker):
    mock_error = mocker.patch("pan_os_upgrade.main.logging.error")

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
        hostname="fw01.example.com",
        result=result,
        test_info=test_info,
        test_name="software_version_check",
    )

    mock_error.assert_called_with(
        f"{get_emoji('error')} fw01.example.com: Unsupported software version: Software Version Check"
    )


def test_readiness_check_failed_critical(mocker):
    mock_error = mocker.patch("pan_os_upgrade.main.logging.error")
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
        hostname="fw01.example.com",
        result=result,
        test_info=test_info,
        test_name="software_version_check",
    )

    mock_error.assert_any_call(
        f"{get_emoji('error')} fw01.example.com: Unsupported software version: Software Version Check"
    )
    mock_error.assert_any_call(f"{get_emoji('stop')} fw01.example.com: Halting script.")
    mock_exit.assert_called_once_with(1)
