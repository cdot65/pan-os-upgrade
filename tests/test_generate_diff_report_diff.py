from pan_os_upgrade.assurance import generate_diff_report_pdf


def test_generate_diff_report_pdf(tmp_path):
    pre_post_diff = {
        "interfaces": {
            "Ethernet1/1": {
                "status": "Changed",
                "details": "IP address changed from 192.168.1.1 to 192.168.1.2",
                "passed": True,
            },
            "Ethernet1/2": {
                "status": "Added",
                "details": "New interface configured with IP 192.168.2.1",
                "passed": True,
            },
        },
        "policies": {
            "SecurityPolicy1": {
                "status": "Removed",
                "details": "Policy removed during upgrade",
                "passed": True,
            },
        },
    }
    file_path = tmp_path / "upgrade_diff_report.pdf"
    hostname = "fw-hostname"
    target_version = "9.1.3"

    generate_diff_report_pdf(pre_post_diff, str(file_path), hostname, target_version)

    # Check if the file was created
    assert file_path.is_file()

    # Check the file size to ensure it's not empty
    assert file_path.stat().st_size > 0
