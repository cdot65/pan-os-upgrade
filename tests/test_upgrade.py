# Test Functions for `upgrade.py`
import os

import pytest
from unittest.mock import MagicMock
from dotenv import load_dotenv


@pytest.fixture
def show_devices_all_fixture():
    from xml.etree.ElementTree import fromstring

    return fromstring(
        """
        <response status="success">
<result>
    <devices>
        <entry name="111111111111111">
            <serial>111111111111111</serial>
            <connected>yes</connected>
            <unsupported-version>no</unsupported-version>
            <deactivated>no</deactivated>
            <hostname>pantf-outbound-fw000000</hostname>
            <ip-address>1.1.1.1</ip-address>
            <ipv6-address>unknown</ipv6-address>
            <mac-addr></mac-addr>
            <uptime>0 days, 0:07:11</uptime>
            <family>vm</family>
            <model>PA-VM</model>
            <sw-version>9.1.13</sw-version>
            <app-version>8742-8215</app-version>
            <av-version>0</av-version>
            <wildfire-version>0</wildfire-version>
            <threat-version>8742-8215</threat-version>
            <url-db>paloaltonetworks</url-db>
            <url-filtering-version>0000.00.00.000</url-filtering-version>
            <logdb-version>9.1.22</logdb-version>
            <vpnclient-package-version></vpnclient-package-version>
            <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
            <prev-app-version>8103-5197</prev-app-version>
            <prev-av-version>0</prev-av-version>
            <prev-threat-version>0</prev-threat-version>
            <prev-wildfire-version>0</prev-wildfire-version>
            <domain></domain>
            <plugin_versions>
                <entry name="vm_series" version="2.0.7">
                    <pkginfo>vm_series-2.0.7</pkginfo>
                </entry>
            </plugin_versions>
            <vm-mode-type>yes</vm-mode-type>
            <is-dhcp>yes</is-dhcp>
            <vpn-disable-mode>no</vpn-disable-mode>
            <operational-mode>normal</operational-mode>
            <certificate-status></certificate-status>
            <certificate-subject-name> </certificate-subject-name>
            <certificate-expiry> </certificate-expiry>
            <connected-at> </connected-at>
            <custom-certificate-usage> </custom-certificate-usage>
            <multi-vsys>no</multi-vsys>
            <vsys>
                <entry name="vsys1">
                    <display-name>vsys1</display-name>
                    <shared-policy-status></shared-policy-status>
                    <shared-policy-md5sum>c985ab2fce1b080f0ae985caa4bf4f69</shared-policy-md5sum>
                    <shared-policy-version></shared-policy-version>
                </entry>
            </vsys>
            <last-masterkey-push-status>Unknown</last-masterkey-push-status>
            <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
            <express-mode>no</express-mode>
            <device-cert-present>None</device-cert-present>
            <device-cert-expiry-date>N/A</device-cert-expiry-date>
        </entry>
    </devices>
</result>
</response>
        """
    )


@pytest.fixture
def panorama():
    """A real Panorama host for use in integration testing. If not available, this fixture will skip dependent
    integration tests."""

    try:
        load_dotenv(".dev.env")
    except FileNotFoundError:
        pass

    username = os.getenv("PAN_USERNAME")
    password = os.getenv("PAN_PASSWORD")
    panorama = os.getenv("PANORAMA")

    from panos.panorama import Panorama

    if not all([username, password, panorama]):
        pytest.skip("Integration test skipped - no Panorama available")

    return Panorama(api_username=username, api_password=password, hostname=panorama)


class TestModelCreation:
    def test_model_from_api_response_managed_devices(self, show_devices_all_fixture):
        from pan_os_upgrade.upgrade import model_from_api_response
        from pan_os_upgrade.models.devices import ManagedDevices

        test_xml = show_devices_all_fixture

        assert model_from_api_response(test_xml, ManagedDevices) == ManagedDevices(
            **{
                "devices": [
                    {
                        "hostname": "pantf-outbound-fw000000",
                        "serial": "111111111111111",
                        "connected": True,
                    }
                ]
            }
        )


class TestPanoramaMethods:
    def test_get_managed_devices_integration(self, panorama):
        """Validate it works with actual data as well."""
        from pan_os_upgrade.upgrade import get_managed_devices

        unfiltered = get_managed_devices(panorama)
        assert unfiltered

    def test_get_managed_devices(self, show_devices_all_fixture):
        from pan_os_upgrade.upgrade import get_managed_devices
        from pan_os_upgrade.models.devices import ManagedDevice

        mock_panorama = MagicMock()
        mock_panorama.op = MagicMock(return_value=show_devices_all_fixture)

        devices = get_managed_devices(mock_panorama)
        assert devices == [
            ManagedDevice(
                hostname="pantf-outbound-fw000000",
                serial="111111111111111",
                connected=True,
            )
        ]

        assert not get_managed_devices(mock_panorama, hostname="badhostname")
        assert get_managed_devices(mock_panorama, serial="111111111111111")
