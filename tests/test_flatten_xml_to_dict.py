import xml.etree.ElementTree as ET
from pan_os_upgrade.upgrade import flatten_xml_to_dict


def test_flatten_show_highavailability_state():
    xml_string = """
    <response status="success">
        <result>
            <devices>
                <entry name="007054000543213">
                    <serial>007054000543213</serial>
                    <connected>yes</connected>
                    <unsupported-version>no</unsupported-version>
                    <wildfire-rt>no</wildfire-rt>
                    <deactivated>no</deactivated>
                    <hostname>lab-fw3</hostname>
                    <ip-address>192.168.255.13</ip-address>
                    <ipv6-address>unknown</ipv6-address>
                    <mac-addr></mac-addr>
                    <uptime>0 days, 0:12:01</uptime>
                    <family>vm</family>
                    <model>PA-VM</model>
                    <sw-version>10.1.4</sw-version>
                    <app-version>8729-8157</app-version>
                    <av-version>0</av-version>
                    <device-dictionary-version>114-473</device-dictionary-version>
                    <wildfire-version>0</wildfire-version>
                    <threat-version>8729-8157</threat-version>
                    <url-db>paloaltonetworks</url-db>
                    <url-filtering-version>20240210.20316</url-filtering-version>
                    <logdb-version>10.1.2</logdb-version>
                    <vpnclient-package-version></vpnclient-package-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <prev-app-version>0</prev-app-version>
                    <prev-av-version>0</prev-av-version>
                    <prev-threat-version>0</prev-threat-version>
                    <prev-wildfire-version>0</prev-wildfire-version>
                    <prev-device-dictionary-version>113-471</prev-device-dictionary-version>
                    <domain></domain>
                    <slot-count>1</slot-count>
                    <type></type>
                    <tag></tag>
                    <plugin_versions>
                        <entry name="dlp" version="1.0.4">
                            <pkginfo>dlp-1.0.4</pkginfo>
                        </entry>
                        <entry name="vm_series" version="2.1.9">
                            <pkginfo>vm_series-2.1.9</pkginfo>
                        </entry>
                    </plugin_versions>
                    <ha-cluster>
                        <state>cluster-unknown</state>
                    </ha-cluster>
                    <vpn-disable-mode>no</vpn-disable-mode>
                    <operational-mode>normal</operational-mode>
                    <certificate-status></certificate-status>
                    <certificate-subject-name>183e29c3-5669-4c28-bf96-2994d8dc19fd</certificate-subject-name>
                    <certificate-expiry>2024/05/05 19:48:38</certificate-expiry>
                    <connected-at>2024/02/10 15:03:31</connected-at>
                    <custom-certificate-usage>no</custom-certificate-usage>
                    <multi-vsys>no</multi-vsys>
                    <vsys>
                        <entry name="vsys1">
                            <display-name>vsys1</display-name>
                            <shared-policy-status></shared-policy-status>
                            <shared-policy-md5sum>659e7d433a40772daec9f750125391bf</shared-policy-md5sum>
                            <shared-policy-version>35</shared-policy-version>
                        </entry>
                    </vsys>
                    <last-masterkey-push-status>Unknown</last-masterkey-push-status>
                    <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
                    <express-mode>no</express-mode>
                    <device-cert-present>Valid</device-cert-present>
                    <device-cert-expiry-date>2024/05/05 10:44:29 CDT</device-cert-expiry-date>
                </entry>
                <entry name="007054000543211">
                    <serial>007054000543211</serial>
                    <connected>yes</connected>
                    <unsupported-version>no</unsupported-version>
                    <wildfire-rt>no</wildfire-rt>
                    <deactivated>no</deactivated>
                    <hostname>lab-fw1</hostname>
                    <ip-address>192.168.255.11</ip-address>
                    <ipv6-address>unknown</ipv6-address>
                    <mac-addr></mac-addr>
                    <uptime>0 days, 0:09:50</uptime>
                    <family>vm</family>
                    <model>PA-VM</model>
                    <sw-version>10.1.4</sw-version>
                    <app-version>8729-8157</app-version>
                    <av-version>0</av-version>
                    <device-dictionary-version>114-473</device-dictionary-version>
                    <wildfire-version>0</wildfire-version>
                    <threat-version>8729-8157</threat-version>
                    <url-db>paloaltonetworks</url-db>
                    <url-filtering-version>20240210.20316</url-filtering-version>
                    <logdb-version>10.1.2</logdb-version>
                    <vpnclient-package-version></vpnclient-package-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <prev-app-version>0</prev-app-version>
                    <prev-av-version>0</prev-av-version>
                    <prev-threat-version>0</prev-threat-version>
                    <prev-wildfire-version>0</prev-wildfire-version>
                    <prev-device-dictionary-version>113-471</prev-device-dictionary-version>
                    <domain></domain>
                    <slot-count>1</slot-count>
                    <type></type>
                    <tag></tag>
                    <plugin_versions>
                        <entry name="dlp" version="1.0.4">
                            <pkginfo>dlp-1.0.4</pkginfo>
                        </entry>
                        <entry name="vm_series" version="2.1.9">
                            <pkginfo>vm_series-2.1.9</pkginfo>
                        </entry>
                    </plugin_versions>
                    <ha-cluster>
                        <state>cluster-unknown</state>
                    </ha-cluster>
                    <vpn-disable-mode>no</vpn-disable-mode>
                    <operational-mode>normal</operational-mode>
                    <certificate-status></certificate-status>
                    <certificate-subject-name>c4ac27e2-da10-40de-836e-445a99356648</certificate-subject-name>
                    <certificate-expiry>2024/05/05 19:47:44</certificate-expiry>
                    <connected-at>2024/02/10 15:01:00</connected-at>
                    <custom-certificate-usage>no</custom-certificate-usage>
                    <multi-vsys>no</multi-vsys>
                    <vsys>
                        <entry name="vsys1">
                            <display-name>vsys1</display-name>
                            <shared-policy-status></shared-policy-status>
                            <shared-policy-md5sum>659e7d433a40772daec9f750125391bf</shared-policy-md5sum>
                            <shared-policy-version>35</shared-policy-version>
                        </entry>
                    </vsys>
                    <last-masterkey-push-status>Unknown</last-masterkey-push-status>
                    <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
                    <express-mode>no</express-mode>
                    <device-cert-present>Valid</device-cert-present>
                    <device-cert-expiry-date>2024/05/05 10:34:43 CDT</device-cert-expiry-date>
                </entry>
                <entry name="007054000543212">
                    <serial>007054000543212</serial>
                    <connected>yes</connected>
                    <unsupported-version>no</unsupported-version>
                    <wildfire-rt>no</wildfire-rt>
                    <deactivated>no</deactivated>
                    <hostname>katy-fw1</hostname>
                    <ip-address>192.168.255.41</ip-address>
                    <ipv6-address>unknown</ipv6-address>
                    <mac-addr></mac-addr>
                    <uptime>2 days, 22:15:28</uptime>
                    <family>vm</family>
                    <model>PA-VM</model>
                    <sw-version>10.1.4</sw-version>
                    <app-version>8799-8509</app-version>
                    <av-version>0</av-version>
                    <device-dictionary-version>114-473</device-dictionary-version>
                    <wildfire-version>0</wildfire-version>
                    <threat-version>8799-8509</threat-version>
                    <url-db>paloaltonetworks</url-db>
                    <url-filtering-version>20240209.20242</url-filtering-version>
                    <logdb-version>10.1.2</logdb-version>
                    <vpnclient-package-version></vpnclient-package-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <prev-app-version>8635-7675</prev-app-version>
                    <prev-av-version>0</prev-av-version>
                    <prev-threat-version>0</prev-threat-version>
                    <prev-wildfire-version>0</prev-wildfire-version>
                    <prev-device-dictionary-version>113-471</prev-device-dictionary-version>
                    <domain></domain>
                    <slot-count>1</slot-count>
                    <type></type>
                    <tag></tag>
                    <plugin_versions>
                        <entry name="vm_series" version="2.1.5">
                            <pkginfo>vm_series-2.1.5</pkginfo>
                        </entry>
                        <entry name="dlp" version="1.0.4">
                            <pkginfo>dlp-1.0.4</pkginfo>
                        </entry>
                    </plugin_versions>
                    <ha>
                        <state>active</state>
                        <peer>
                            <serial>007054000543217</serial>
                        </peer>
                    </ha>
                    <ha-cluster>
                        <state>cluster-unknown</state>
                    </ha-cluster>
                    <vpn-disable-mode>no</vpn-disable-mode>
                    <operational-mode>normal</operational-mode>
                    <certificate-status></certificate-status>
                    <certificate-subject-name>3b5592c5-ec7c-4a7d-a9c5-514e66a6d6cf</certificate-subject-name>
                    <certificate-expiry>2024/05/06 15:06:50</certificate-expiry>
                    <connected-at>2024/02/08 03:08:53</connected-at>
                    <custom-certificate-usage>no</custom-certificate-usage>
                    <multi-vsys>no</multi-vsys>
                    <vsys>
                        <entry name="vsys1">
                            <display-name>vsys1</display-name>
                            <shared-policy-status></shared-policy-status>
                            <shared-policy-md5sum>f82283898afbf91e11d6f3071db0b241</shared-policy-md5sum>
                            <shared-policy-version>35</shared-policy-version>
                        </entry>
                    </vsys>
                    <last-masterkey-push-status>Unknown</last-masterkey-push-status>
                    <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
                    <express-mode>no</express-mode>
                    <device-cert-present>Valid</device-cert-present>
                    <device-cert-expiry-date>2024/04/12 12:39:54 CDT</device-cert-expiry-date>
                </entry>
                <entry name="007054000543215">
                    <serial>007054000543215</serial>
                    <connected>yes</connected>
                    <unsupported-version>no</unsupported-version>
                    <wildfire-rt>no</wildfire-rt>
                    <deactivated>no</deactivated>
                    <hostname>lab-fw4</hostname>
                    <ip-address>192.168.255.14</ip-address>
                    <ipv6-address>unknown</ipv6-address>
                    <mac-addr></mac-addr>
                    <uptime>3 days, 10:39:45</uptime>
                    <family>vm</family>
                    <model>PA-VM</model>
                    <sw-version>10.1.3-h3</sw-version>
                    <app-version>8729-8157</app-version>
                    <av-version>0</av-version>
                    <device-dictionary-version>114-473</device-dictionary-version>
                    <wildfire-version>0</wildfire-version>
                    <threat-version>8729-8157</threat-version>
                    <url-db>paloaltonetworks</url-db>
                    <url-filtering-version>20240209.20242</url-filtering-version>
                    <logdb-version>10.1.2</logdb-version>
                    <vpnclient-package-version></vpnclient-package-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <prev-app-version>0</prev-app-version>
                    <prev-av-version>0</prev-av-version>
                    <prev-threat-version>0</prev-threat-version>
                    <prev-wildfire-version>0</prev-wildfire-version>
                    <prev-device-dictionary-version>113-471</prev-device-dictionary-version>
                    <domain></domain>
                    <slot-count>1</slot-count>
                    <type></type>
                    <tag></tag>
                    <plugin_versions>
                        <entry name="vm_series" version="2.1.9">
                            <pkginfo>vm_series-2.1.9</pkginfo>
                        </entry>
                    </plugin_versions>
                    <ha-cluster>
                        <state>cluster-unknown</state>
                    </ha-cluster>
                    <vpn-disable-mode>no</vpn-disable-mode>
                    <operational-mode>normal</operational-mode>
                    <certificate-status></certificate-status>
                    <certificate-subject-name>fa4c2efe-8546-4725-96fc-e14dcb57d0be</certificate-subject-name>
                    <certificate-expiry>2024/05/05 19:47:53</certificate-expiry>
                    <connected-at>2024/02/08 03:09:00</connected-at>
                    <custom-certificate-usage>no</custom-certificate-usage>
                    <multi-vsys>no</multi-vsys>
                    <vsys>
                        <entry name="vsys1">
                            <display-name>vsys1</display-name>
                            <shared-policy-status></shared-policy-status>
                            <shared-policy-md5sum>659e7d433a40772daec9f750125391bf</shared-policy-md5sum>
                            <shared-policy-version>35</shared-policy-version>
                        </entry>
                    </vsys>
                    <last-masterkey-push-status>Unknown</last-masterkey-push-status>
                    <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
                    <express-mode>no</express-mode>
                    <device-cert-present>Valid</device-cert-present>
                    <device-cert-expiry-date>2024/05/05 10:45:55 CDT</device-cert-expiry-date>
                </entry>
                <entry name="007054000543216">
                    <serial>007054000543216</serial>
                    <connected>yes</connected>
                    <unsupported-version>no</unsupported-version>
                    <wildfire-rt>no</wildfire-rt>
                    <deactivated>no</deactivated>
                    <hostname>lab-fw2</hostname>
                    <ip-address>192.168.255.12</ip-address>
                    <ipv6-address>unknown</ipv6-address>
                    <mac-addr></mac-addr>
                    <uptime>4 days, 15:28:18</uptime>
                    <family>vm</family>
                    <model>PA-VM</model>
                    <sw-version>10.1.3-h3</sw-version>
                    <app-version>8729-8157</app-version>
                    <av-version>0</av-version>
                    <device-dictionary-version>114-473</device-dictionary-version>
                    <wildfire-version>0</wildfire-version>
                    <threat-version>8729-8157</threat-version>
                    <url-db>paloaltonetworks</url-db>
                    <url-filtering-version>20240210.20313</url-filtering-version>
                    <logdb-version>10.1.2</logdb-version>
                    <vpnclient-package-version></vpnclient-package-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <prev-app-version>0</prev-app-version>
                    <prev-av-version>0</prev-av-version>
                    <prev-threat-version>0</prev-threat-version>
                    <prev-wildfire-version>0</prev-wildfire-version>
                    <prev-device-dictionary-version>113-471</prev-device-dictionary-version>
                    <domain></domain>
                    <slot-count>1</slot-count>
                    <type></type>
                    <tag></tag>
                    <plugin_versions>
                        <entry name="vm_series" version="2.1.9">
                            <pkginfo>vm_series-2.1.9</pkginfo>
                        </entry>
                    </plugin_versions>
                    <ha-cluster>
                        <state>cluster-unknown</state>
                    </ha-cluster>
                    <vpn-disable-mode>no</vpn-disable-mode>
                    <operational-mode>normal</operational-mode>
                    <certificate-status></certificate-status>
                    <certificate-subject-name>65e8ca7c-684f-4004-88a8-9b22137f10ec</certificate-subject-name>
                    <certificate-expiry>2024/05/05 19:49:29</certificate-expiry>
                    <connected-at>2024/02/08 03:08:49</connected-at>
                    <custom-certificate-usage>no</custom-certificate-usage>
                    <multi-vsys>no</multi-vsys>
                    <vsys>
                        <entry name="vsys1">
                            <display-name>vsys1</display-name>
                            <shared-policy-status></shared-policy-status>
                            <shared-policy-md5sum>659e7d433a40772daec9f750125391bf</shared-policy-md5sum>
                            <shared-policy-version>35</shared-policy-version>
                        </entry>
                    </vsys>
                    <last-masterkey-push-status>Unknown</last-masterkey-push-status>
                    <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
                    <express-mode>no</express-mode>
                    <device-cert-present>Valid</device-cert-present>
                    <device-cert-expiry-date>2024/05/05 10:36:42 CDT</device-cert-expiry-date>
                </entry>
                <entry name="007054000543217">
                    <serial>007054000543217</serial>
                    <connected>yes</connected>
                    <unsupported-version>no</unsupported-version>
                    <wildfire-rt>no</wildfire-rt>
                    <deactivated>no</deactivated>
                    <hostname>katy-fw2</hostname>
                    <ip-address>192.168.255.42</ip-address>
                    <ipv6-address>unknown</ipv6-address>
                    <mac-addr></mac-addr>
                    <uptime>2 days, 22:15:26</uptime>
                    <family>vm</family>
                    <model>PA-VM</model>
                    <sw-version>10.1.4</sw-version>
                    <app-version>8799-8509</app-version>
                    <av-version>0</av-version>
                    <device-dictionary-version>114-473</device-dictionary-version>
                    <wildfire-version>0</wildfire-version>
                    <threat-version>8799-8509</threat-version>
                    <url-db>paloaltonetworks</url-db>
                    <url-filtering-version>20240206.20317</url-filtering-version>
                    <logdb-version>10.1.2</logdb-version>
                    <vpnclient-package-version></vpnclient-package-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <prev-app-version>8635-7675</prev-app-version>
                    <prev-av-version>0</prev-av-version>
                    <prev-threat-version>0</prev-threat-version>
                    <prev-wildfire-version>0</prev-wildfire-version>
                    <prev-device-dictionary-version>113-471</prev-device-dictionary-version>
                    <domain></domain>
                    <slot-count>1</slot-count>
                    <type></type>
                    <tag></tag>
                    <plugin_versions>
                        <entry name="vm_series" version="2.1.5">
                            <pkginfo>vm_series-2.1.5</pkginfo>
                        </entry>
                        <entry name="dlp" version="1.0.4">
                            <pkginfo>dlp-1.0.4</pkginfo>
                        </entry>
                    </plugin_versions>
                    <ha>
                        <state>passive</state>
                        <peer>
                            <serial>007054000543212</serial>
                        </peer>
                    </ha>
                    <ha-cluster>
                        <state>cluster-unknown</state>
                    </ha-cluster>
                    <vpn-disable-mode>no</vpn-disable-mode>
                    <operational-mode>normal</operational-mode>
                    <certificate-status></certificate-status>
                    <certificate-subject-name>2468241f-c476-4523-a3aa-2df04398dabb</certificate-subject-name>
                    <certificate-expiry>2024/05/06 16:07:52</certificate-expiry>
                    <connected-at>2024/02/08 03:08:57</connected-at>
                    <custom-certificate-usage>no</custom-certificate-usage>
                    <multi-vsys>no</multi-vsys>
                    <vsys>
                        <entry name="vsys1">
                            <display-name>vsys1</display-name>
                            <shared-policy-status></shared-policy-status>
                            <shared-policy-md5sum>f82283898afbf91e11d6f3071db0b241</shared-policy-md5sum>
                            <shared-policy-version>35</shared-policy-version>
                        </entry>
                    </vsys>
                    <last-masterkey-push-status>Unknown</last-masterkey-push-status>
                    <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
                    <express-mode>no</express-mode>
                    <device-cert-present>Valid</device-cert-present>
                    <device-cert-expiry-date>2024/04/12 12:38:35 CDT</device-cert-expiry-date>
                </entry>
                <entry name="007054000543218">
                    <serial>007054000543218</serial>
                    <connected>yes</connected>
                    <unsupported-version>no</unsupported-version>
                    <wildfire-rt>no</wildfire-rt>
                    <deactivated>no</deactivated>
                    <hostname>lab-fw5</hostname>
                    <ip-address>192.168.255.15</ip-address>
                    <ipv6-address>unknown</ipv6-address>
                    <mac-addr></mac-addr>
                    <uptime>0 days, 0:09:35</uptime>
                    <family>vm</family>
                    <model>PA-VM</model>
                    <sw-version>10.1.4</sw-version>
                    <app-version>8729-8157</app-version>
                    <av-version>0</av-version>
                    <device-dictionary-version>114-473</device-dictionary-version>
                    <wildfire-version>0</wildfire-version>
                    <threat-version>8729-8157</threat-version>
                    <url-db>paloaltonetworks</url-db>
                    <url-filtering-version>20240210.20316</url-filtering-version>
                    <logdb-version>10.1.2</logdb-version>
                    <vpnclient-package-version></vpnclient-package-version>
                    <global-protect-client-package-version>0.0.0</global-protect-client-package-version>
                    <prev-app-version>0</prev-app-version>
                    <prev-av-version>0</prev-av-version>
                    <prev-threat-version>0</prev-threat-version>
                    <prev-wildfire-version>0</prev-wildfire-version>
                    <prev-device-dictionary-version>113-471</prev-device-dictionary-version>
                    <domain></domain>
                    <slot-count>1</slot-count>
                    <type></type>
                    <tag></tag>
                    <plugin_versions>
                        <entry name="vm_series" version="2.1.9">
                            <pkginfo>vm_series-2.1.9</pkginfo>
                        </entry>
                        <entry name="dlp" version="1.0.4">
                            <pkginfo>dlp-1.0.4</pkginfo>
                        </entry>
                    </plugin_versions>
                    <ha-cluster>
                        <state>cluster-unknown</state>
                    </ha-cluster>
                    <vpn-disable-mode>no</vpn-disable-mode>
                    <operational-mode>normal</operational-mode>
                    <certificate-status></certificate-status>
                    <certificate-subject-name>c9d5e709-dfb2-4a0a-825e-252a6fa66140</certificate-subject-name>
                    <certificate-expiry>2024/05/05 19:48:55</certificate-expiry>
                    <connected-at>2024/02/10 15:01:42</connected-at>
                    <custom-certificate-usage>no</custom-certificate-usage>
                    <multi-vsys>no</multi-vsys>
                    <vsys>
                        <entry name="vsys1">
                            <display-name>vsys1</display-name>
                            <shared-policy-status></shared-policy-status>
                            <shared-policy-md5sum>659e7d433a40772daec9f750125391bf</shared-policy-md5sum>
                            <shared-policy-version>35</shared-policy-version>
                        </entry>
                    </vsys>
                    <last-masterkey-push-status>Unknown</last-masterkey-push-status>
                    <last-masterkey-push-timestamp></last-masterkey-push-timestamp>
                    <express-mode>no</express-mode>
                    <device-cert-present>Valid</device-cert-present>
                    <device-cert-expiry-date>2024/05/05 10:47:19 CDT</device-cert-expiry-date>
                </entry>Total Connected Devices: 0
            </devices>
        </result>
    </response>
    """
    element = ET.fromstring(xml_string)
    expected_dict = {
        "result": {
            "devices": {
                "entry": [
                    {
                        "serial": "007054000543213",
                        "connected": "yes",
                        "unsupported-version": "no",
                        "wildfire-rt": "no",
                        "deactivated": "no",
                        "hostname": "lab-fw3",
                        "ip-address": "192.168.255.13",
                        "ipv6-address": "unknown",
                        "mac-addr": {},
                        "uptime": "0 days, 0:12:01",
                        "family": "vm",
                        "model": "PA-VM",
                        "sw-version": "10.1.4",
                        "app-version": "8729-8157",
                        "av-version": "0",
                        "device-dictionary-version": "114-473",
                        "wildfire-version": "0",
                        "threat-version": "8729-8157",
                        "url-db": "paloaltonetworks",
                        "url-filtering-version": "20240210.20316",
                        "logdb-version": "10.1.2",
                        "vpnclient-package-version": {},
                        "global-protect-client-package-version": "0.0.0",
                        "prev-app-version": "0",
                        "prev-av-version": "0",
                        "prev-threat-version": "0",
                        "prev-wildfire-version": "0",
                        "prev-device-dictionary-version": "113-471",
                        "domain": {},
                        "slot-count": "1",
                        "type": {},
                        "tag": {},
                        "plugin_versions": {
                            "entry": [
                                {"pkginfo": "dlp-1.0.4"},
                                {"pkginfo": "vm_series-2.1.9"},
                            ]
                        },
                        "ha-cluster": {"state": "cluster-unknown"},
                        "vpn-disable-mode": "no",
                        "operational-mode": "normal",
                        "certificate-status": {},
                        "certificate-subject-name": "183e29c3-5669-4c28-bf96-2994d8dc19fd",
                        "certificate-expiry": "2024/05/05 19:48:38",
                        "connected-at": "2024/02/10 15:03:31",
                        "custom-certificate-usage": "no",
                        "multi-vsys": "no",
                        "vsys": {
                            "entry": [
                                {
                                    "display-name": "vsys1",
                                    "shared-policy-status": {},
                                    "shared-policy-md5sum": "659e7d433a40772daec9f750125391bf",
                                    "shared-policy-version": "35",
                                }
                            ]
                        },
                        "last-masterkey-push-status": "Unknown",
                        "last-masterkey-push-timestamp": {},
                        "express-mode": "no",
                        "device-cert-present": "Valid",
                        "device-cert-expiry-date": "2024/05/05 10:44:29 CDT",
                    },
                    {
                        "serial": "007054000543211",
                        "connected": "yes",
                        "unsupported-version": "no",
                        "wildfire-rt": "no",
                        "deactivated": "no",
                        "hostname": "lab-fw1",
                        "ip-address": "192.168.255.11",
                        "ipv6-address": "unknown",
                        "mac-addr": {},
                        "uptime": "0 days, 0:09:50",
                        "family": "vm",
                        "model": "PA-VM",
                        "sw-version": "10.1.4",
                        "app-version": "8729-8157",
                        "av-version": "0",
                        "device-dictionary-version": "114-473",
                        "wildfire-version": "0",
                        "threat-version": "8729-8157",
                        "url-db": "paloaltonetworks",
                        "url-filtering-version": "20240210.20316",
                        "logdb-version": "10.1.2",
                        "vpnclient-package-version": {},
                        "global-protect-client-package-version": "0.0.0",
                        "prev-app-version": "0",
                        "prev-av-version": "0",
                        "prev-threat-version": "0",
                        "prev-wildfire-version": "0",
                        "prev-device-dictionary-version": "113-471",
                        "domain": {},
                        "slot-count": "1",
                        "type": {},
                        "tag": {},
                        "plugin_versions": {
                            "entry": [
                                {"pkginfo": "dlp-1.0.4"},
                                {"pkginfo": "vm_series-2.1.9"},
                            ]
                        },
                        "ha-cluster": {"state": "cluster-unknown"},
                        "vpn-disable-mode": "no",
                        "operational-mode": "normal",
                        "certificate-status": {},
                        "certificate-subject-name": "c4ac27e2-da10-40de-836e-445a99356648",
                        "certificate-expiry": "2024/05/05 19:47:44",
                        "connected-at": "2024/02/10 15:01:00",
                        "custom-certificate-usage": "no",
                        "multi-vsys": "no",
                        "vsys": {
                            "entry": [
                                {
                                    "display-name": "vsys1",
                                    "shared-policy-status": {},
                                    "shared-policy-md5sum": "659e7d433a40772daec9f750125391bf",
                                    "shared-policy-version": "35",
                                }
                            ]
                        },
                        "last-masterkey-push-status": "Unknown",
                        "last-masterkey-push-timestamp": {},
                        "express-mode": "no",
                        "device-cert-present": "Valid",
                        "device-cert-expiry-date": "2024/05/05 10:34:43 CDT",
                    },
                    {
                        "serial": "007054000543212",
                        "connected": "yes",
                        "unsupported-version": "no",
                        "wildfire-rt": "no",
                        "deactivated": "no",
                        "hostname": "katy-fw1",
                        "ip-address": "192.168.255.41",
                        "ipv6-address": "unknown",
                        "mac-addr": {},
                        "uptime": "2 days, 22:15:28",
                        "family": "vm",
                        "model": "PA-VM",
                        "sw-version": "10.1.4",
                        "app-version": "8799-8509",
                        "av-version": "0",
                        "device-dictionary-version": "114-473",
                        "wildfire-version": "0",
                        "threat-version": "8799-8509",
                        "url-db": "paloaltonetworks",
                        "url-filtering-version": "20240209.20242",
                        "logdb-version": "10.1.2",
                        "vpnclient-package-version": {},
                        "global-protect-client-package-version": "0.0.0",
                        "prev-app-version": "8635-7675",
                        "prev-av-version": "0",
                        "prev-threat-version": "0",
                        "prev-wildfire-version": "0",
                        "prev-device-dictionary-version": "113-471",
                        "domain": {},
                        "slot-count": "1",
                        "type": {},
                        "tag": {},
                        "plugin_versions": {
                            "entry": [
                                {"pkginfo": "vm_series-2.1.5"},
                                {"pkginfo": "dlp-1.0.4"},
                            ]
                        },
                        "ha": {
                            "state": "active",
                            "peer": {"serial": "007054000543217"},
                        },
                        "ha-cluster": {"state": "cluster-unknown"},
                        "vpn-disable-mode": "no",
                        "operational-mode": "normal",
                        "certificate-status": {},
                        "certificate-subject-name": "3b5592c5-ec7c-4a7d-a9c5-514e66a6d6cf",
                        "certificate-expiry": "2024/05/06 15:06:50",
                        "connected-at": "2024/02/08 03:08:53",
                        "custom-certificate-usage": "no",
                        "multi-vsys": "no",
                        "vsys": {
                            "entry": [
                                {
                                    "display-name": "vsys1",
                                    "shared-policy-status": {},
                                    "shared-policy-md5sum": "f82283898afbf91e11d6f3071db0b241",
                                    "shared-policy-version": "35",
                                }
                            ]
                        },
                        "last-masterkey-push-status": "Unknown",
                        "last-masterkey-push-timestamp": {},
                        "express-mode": "no",
                        "device-cert-present": "Valid",
                        "device-cert-expiry-date": "2024/04/12 12:39:54 CDT",
                    },
                    {
                        "serial": "007054000543215",
                        "connected": "yes",
                        "unsupported-version": "no",
                        "wildfire-rt": "no",
                        "deactivated": "no",
                        "hostname": "lab-fw4",
                        "ip-address": "192.168.255.14",
                        "ipv6-address": "unknown",
                        "mac-addr": {},
                        "uptime": "3 days, 10:39:45",
                        "family": "vm",
                        "model": "PA-VM",
                        "sw-version": "10.1.3-h3",
                        "app-version": "8729-8157",
                        "av-version": "0",
                        "device-dictionary-version": "114-473",
                        "wildfire-version": "0",
                        "threat-version": "8729-8157",
                        "url-db": "paloaltonetworks",
                        "url-filtering-version": "20240209.20242",
                        "logdb-version": "10.1.2",
                        "vpnclient-package-version": {},
                        "global-protect-client-package-version": "0.0.0",
                        "prev-app-version": "0",
                        "prev-av-version": "0",
                        "prev-threat-version": "0",
                        "prev-wildfire-version": "0",
                        "prev-device-dictionary-version": "113-471",
                        "domain": {},
                        "slot-count": "1",
                        "type": {},
                        "tag": {},
                        "plugin_versions": {"entry": [{"pkginfo": "vm_series-2.1.9"}]},
                        "ha-cluster": {"state": "cluster-unknown"},
                        "vpn-disable-mode": "no",
                        "operational-mode": "normal",
                        "certificate-status": {},
                        "certificate-subject-name": "fa4c2efe-8546-4725-96fc-e14dcb57d0be",
                        "certificate-expiry": "2024/05/05 19:47:53",
                        "connected-at": "2024/02/08 03:09:00",
                        "custom-certificate-usage": "no",
                        "multi-vsys": "no",
                        "vsys": {
                            "entry": [
                                {
                                    "display-name": "vsys1",
                                    "shared-policy-status": {},
                                    "shared-policy-md5sum": "659e7d433a40772daec9f750125391bf",
                                    "shared-policy-version": "35",
                                }
                            ]
                        },
                        "last-masterkey-push-status": "Unknown",
                        "last-masterkey-push-timestamp": {},
                        "express-mode": "no",
                        "device-cert-present": "Valid",
                        "device-cert-expiry-date": "2024/05/05 10:45:55 CDT",
                    },
                    {
                        "serial": "007054000543216",
                        "connected": "yes",
                        "unsupported-version": "no",
                        "wildfire-rt": "no",
                        "deactivated": "no",
                        "hostname": "lab-fw2",
                        "ip-address": "192.168.255.12",
                        "ipv6-address": "unknown",
                        "mac-addr": {},
                        "uptime": "4 days, 15:28:18",
                        "family": "vm",
                        "model": "PA-VM",
                        "sw-version": "10.1.3-h3",
                        "app-version": "8729-8157",
                        "av-version": "0",
                        "device-dictionary-version": "114-473",
                        "wildfire-version": "0",
                        "threat-version": "8729-8157",
                        "url-db": "paloaltonetworks",
                        "url-filtering-version": "20240210.20313",
                        "logdb-version": "10.1.2",
                        "vpnclient-package-version": {},
                        "global-protect-client-package-version": "0.0.0",
                        "prev-app-version": "0",
                        "prev-av-version": "0",
                        "prev-threat-version": "0",
                        "prev-wildfire-version": "0",
                        "prev-device-dictionary-version": "113-471",
                        "domain": {},
                        "slot-count": "1",
                        "type": {},
                        "tag": {},
                        "plugin_versions": {"entry": [{"pkginfo": "vm_series-2.1.9"}]},
                        "ha-cluster": {"state": "cluster-unknown"},
                        "vpn-disable-mode": "no",
                        "operational-mode": "normal",
                        "certificate-status": {},
                        "certificate-subject-name": "65e8ca7c-684f-4004-88a8-9b22137f10ec",
                        "certificate-expiry": "2024/05/05 19:49:29",
                        "connected-at": "2024/02/08 03:08:49",
                        "custom-certificate-usage": "no",
                        "multi-vsys": "no",
                        "vsys": {
                            "entry": [
                                {
                                    "display-name": "vsys1",
                                    "shared-policy-status": {},
                                    "shared-policy-md5sum": "659e7d433a40772daec9f750125391bf",
                                    "shared-policy-version": "35",
                                }
                            ]
                        },
                        "last-masterkey-push-status": "Unknown",
                        "last-masterkey-push-timestamp": {},
                        "express-mode": "no",
                        "device-cert-present": "Valid",
                        "device-cert-expiry-date": "2024/05/05 10:36:42 CDT",
                    },
                    {
                        "serial": "007054000543217",
                        "connected": "yes",
                        "unsupported-version": "no",
                        "wildfire-rt": "no",
                        "deactivated": "no",
                        "hostname": "katy-fw2",
                        "ip-address": "192.168.255.42",
                        "ipv6-address": "unknown",
                        "mac-addr": {},
                        "uptime": "2 days, 22:15:26",
                        "family": "vm",
                        "model": "PA-VM",
                        "sw-version": "10.1.4",
                        "app-version": "8799-8509",
                        "av-version": "0",
                        "device-dictionary-version": "114-473",
                        "wildfire-version": "0",
                        "threat-version": "8799-8509",
                        "url-db": "paloaltonetworks",
                        "url-filtering-version": "20240206.20317",
                        "logdb-version": "10.1.2",
                        "vpnclient-package-version": {},
                        "global-protect-client-package-version": "0.0.0",
                        "prev-app-version": "8635-7675",
                        "prev-av-version": "0",
                        "prev-threat-version": "0",
                        "prev-wildfire-version": "0",
                        "prev-device-dictionary-version": "113-471",
                        "domain": {},
                        "slot-count": "1",
                        "type": {},
                        "tag": {},
                        "plugin_versions": {
                            "entry": [
                                {"pkginfo": "vm_series-2.1.5"},
                                {"pkginfo": "dlp-1.0.4"},
                            ]
                        },
                        "ha": {
                            "state": "passive",
                            "peer": {"serial": "007054000543212"},
                        },
                        "ha-cluster": {"state": "cluster-unknown"},
                        "vpn-disable-mode": "no",
                        "operational-mode": "normal",
                        "certificate-status": {},
                        "certificate-subject-name": "2468241f-c476-4523-a3aa-2df04398dabb",
                        "certificate-expiry": "2024/05/06 16:07:52",
                        "connected-at": "2024/02/08 03:08:57",
                        "custom-certificate-usage": "no",
                        "multi-vsys": "no",
                        "vsys": {
                            "entry": [
                                {
                                    "display-name": "vsys1",
                                    "shared-policy-status": {},
                                    "shared-policy-md5sum": "f82283898afbf91e11d6f3071db0b241",
                                    "shared-policy-version": "35",
                                }
                            ]
                        },
                        "last-masterkey-push-status": "Unknown",
                        "last-masterkey-push-timestamp": {},
                        "express-mode": "no",
                        "device-cert-present": "Valid",
                        "device-cert-expiry-date": "2024/04/12 12:38:35 CDT",
                    },
                    {
                        "serial": "007054000543218",
                        "connected": "yes",
                        "unsupported-version": "no",
                        "wildfire-rt": "no",
                        "deactivated": "no",
                        "hostname": "lab-fw5",
                        "ip-address": "192.168.255.15",
                        "ipv6-address": "unknown",
                        "mac-addr": {},
                        "uptime": "0 days, 0:09:35",
                        "family": "vm",
                        "model": "PA-VM",
                        "sw-version": "10.1.4",
                        "app-version": "8729-8157",
                        "av-version": "0",
                        "device-dictionary-version": "114-473",
                        "wildfire-version": "0",
                        "threat-version": "8729-8157",
                        "url-db": "paloaltonetworks",
                        "url-filtering-version": "20240210.20316",
                        "logdb-version": "10.1.2",
                        "vpnclient-package-version": {},
                        "global-protect-client-package-version": "0.0.0",
                        "prev-app-version": "0",
                        "prev-av-version": "0",
                        "prev-threat-version": "0",
                        "prev-wildfire-version": "0",
                        "prev-device-dictionary-version": "113-471",
                        "domain": {},
                        "slot-count": "1",
                        "type": {},
                        "tag": {},
                        "plugin_versions": {
                            "entry": [
                                {"pkginfo": "vm_series-2.1.9"},
                                {"pkginfo": "dlp-1.0.4"},
                            ]
                        },
                        "ha-cluster": {"state": "cluster-unknown"},
                        "vpn-disable-mode": "no",
                        "operational-mode": "normal",
                        "certificate-status": {},
                        "certificate-subject-name": "c9d5e709-dfb2-4a0a-825e-252a6fa66140",
                        "certificate-expiry": "2024/05/05 19:48:55",
                        "connected-at": "2024/02/10 15:01:42",
                        "custom-certificate-usage": "no",
                        "multi-vsys": "no",
                        "vsys": {
                            "entry": [
                                {
                                    "display-name": "vsys1",
                                    "shared-policy-status": {},
                                    "shared-policy-md5sum": "659e7d433a40772daec9f750125391bf",
                                    "shared-policy-version": "35",
                                }
                            ]
                        },
                        "last-masterkey-push-status": "Unknown",
                        "last-masterkey-push-timestamp": {},
                        "express-mode": "no",
                        "device-cert-present": "Valid",
                        "device-cert-expiry-date": "2024/05/05 10:47:19 CDT",
                    },
                ]
            }
        }
    }
    assert flatten_xml_to_dict(element) == expected_dict


def test_flatten_reboot_job():
    xml_string = """
    <response status="success">
        <result>
            <enabled>yes</enabled>
            <local-info>
                <version>1</version>
                <state>primary-active</state>
                <state-duration>218028</state-duration>
                <mgmt-ip>192.168.255.191/24</mgmt-ip>
                <mgmt-ipv6></mgmt-ipv6>
                <preemptive>yes</preemptive>
                <promotion-hold>2000</promotion-hold>
                <hello-interval>8000</hello-interval>
                <heartbeat-interval>2000</heartbeat-interval>
                <preempt-hold>1</preempt-hold>
                <monitor-fail-holdup>0</monitor-fail-holdup>
                <addon-master-holdup>7000</addon-master-holdup>
                <encrypt-imported>no</encrypt-imported>
                <mgmt-macaddr>82:2c:5b:03:6b:c1</mgmt-macaddr>
                <encrypt-enable>no</encrypt-enable>
                <link-mon-intv>3000</link-mon-intv>
                <priority>primary</priority>
                <build-rel>11.0.1</build-rel>
                <url-version>Not Installed</url-version>
                <app-version>8804-8537</app-version>
                <iot-version>114-473</iot-version>
                <av-version>4719-5237</av-version>
                <cloudconnector>Match</cloudconnector>
                <VMS>Match</VMS>
                <build-compat>Match</build-compat>
                <url-compat>Match</url-compat>
                <app-compat>Match</app-compat>
                <iot-compat>Match</iot-compat>
                <av-compat>Match</av-compat>
            </local-info>
            <peer-info>
                <conn-ha1>
                    <conn-status>up</conn-status>
                    <conn-primary>yes</conn-primary>
                    <conn-desc>heartbeat status</conn-desc>
                </conn-ha1>
                <conn-status>up</conn-status>
                <version>1</version>
                <state>secondary-passive</state>
                <state-duration>132146</state-duration>
                <last-error-reason>User requested</last-error-reason>
                <last-error-state>secondary-suspended</last-error-state>
                <preemptive>yes</preemptive>
                <mgmt-ip>192.168.255.192</mgmt-ip>
                <mgmt-macaddr>82:2c:5b:03:6b:c2</mgmt-macaddr>
                <priority>secondary</priority>
                <build-rel>11.0.1</build-rel>
                <url-version>Not Installed</url-version>
                <app-version>8804-8537</app-version>
                <iot-version>114-473</iot-version>
                <av-version>4719-5237</av-version>
                <cloudconnector>2.0.0</cloudconnector>
                <VMS>4.0.1</VMS>
            </peer-info>
            <path-monitoring>
                <enabled>yes</enabled>
                <failure-condition>any</failure-condition>
                <groups>
                    <entry>
                        <name>panorama2</name>
                        <failure-condition>any</failure-condition>
                        <enabled>yes</enabled>
                        <ping-interval>5000</ping-interval>
                        <ping-count>3</ping-count>
                        <destination-groups>
                            <entry>
                                <name>panorama2</name>
                                <enabled>yes</enabled>
                                <failure-condition>any</failure-condition>
                                <dest-ip>
                                    <entry>
                                        <addr>192.168.255.192</addr>
                                        <status>up</status>
                                    </entry>
                                </dest-ip>
                            </entry>
                        </destination-groups>
                    </entry>
                </groups>
            </path-monitoring>
            <running-sync>synchronized</running-sync>
            <running-sync-enabled>yes</running-sync-enabled>
        </result>
    </response>
    """
    element = ET.fromstring(xml_string)
    expected_dict = {
        "result": {
            "enabled": "yes",
            "local-info": {
                "version": "1",
                "state": "primary-active",
                "state-duration": "218028",
                "mgmt-ip": "192.168.255.191/24",
                "mgmt-ipv6": {},
                "preemptive": "yes",
                "promotion-hold": "2000",
                "hello-interval": "8000",
                "heartbeat-interval": "2000",
                "preempt-hold": "1",
                "monitor-fail-holdup": "0",
                "addon-master-holdup": "7000",
                "encrypt-imported": "no",
                "mgmt-macaddr": "82:2c:5b:03:6b:c1",
                "encrypt-enable": "no",
                "link-mon-intv": "3000",
                "priority": "primary",
                "build-rel": "11.0.1",
                "url-version": "Not Installed",
                "app-version": "8804-8537",
                "iot-version": "114-473",
                "av-version": "4719-5237",
                "cloudconnector": "Match",
                "VMS": "Match",
                "build-compat": "Match",
                "url-compat": "Match",
                "app-compat": "Match",
                "iot-compat": "Match",
                "av-compat": "Match",
            },
            "peer-info": {
                "conn-ha1": {
                    "conn-status": "up",
                    "conn-primary": "yes",
                    "conn-desc": "heartbeat status",
                },
                "conn-status": "up",
                "version": "1",
                "state": "secondary-passive",
                "state-duration": "132146",
                "last-error-reason": "User requested",
                "last-error-state": "secondary-suspended",
                "preemptive": "yes",
                "mgmt-ip": "192.168.255.192",
                "mgmt-macaddr": "82:2c:5b:03:6b:c2",
                "priority": "secondary",
                "build-rel": "11.0.1",
                "url-version": "Not Installed",
                "app-version": "8804-8537",
                "iot-version": "114-473",
                "av-version": "4719-5237",
                "cloudconnector": "2.0.0",
                "VMS": "4.0.1",
            },
            "path-monitoring": {
                "enabled": "yes",
                "failure-condition": "any",
                "groups": {
                    "entry": [
                        {
                            "name": "panorama2",
                            "failure-condition": "any",
                            "enabled": "yes",
                            "ping-interval": "5000",
                            "ping-count": "3",
                            "destination-groups": {
                                "entry": [
                                    {
                                        "name": "panorama2",
                                        "enabled": "yes",
                                        "failure-condition": "any",
                                        "dest-ip": {
                                            "entry": [
                                                {
                                                    "addr": "192.168.255.192",
                                                    "status": "up",
                                                }
                                            ]
                                        },
                                    }
                                ]
                            },
                        }
                    ]
                },
            },
            "running-sync": "synchronized",
            "running-sync-enabled": "yes",
        }
    }

    assert flatten_xml_to_dict(element) == expected_dict
