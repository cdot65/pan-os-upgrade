# models/session_stats.py

from pydantic import BaseModel, Field
from typing import Optional


class SessionStats(BaseModel):
    age_accel_thresh: Optional[str] = Field(..., alias="age-accel-thresh")
    age_accel_tsf: Optional[str] = Field(..., alias="age-accel-tsf")
    age_scan_ssf: Optional[str] = Field(..., alias="age-scan-ssf")
    age_scan_thresh: Optional[str] = Field(..., alias="age-scan-thresh")
    age_scan_tmo: Optional[str] = Field(..., alias="age-scan-tmo")
    cps: Optional[str]
    dis_def: Optional[str] = Field(..., alias="dis-def")
    dis_sctp: Optional[str] = Field(..., alias="dis-sctp")
    dis_tcp: Optional[str] = Field(..., alias="dis-tcp")
    dis_udp: Optional[str] = Field(..., alias="dis-udp")
    icmp_unreachable_rate: Optional[str] = Field(..., alias="icmp-unreachable-rate")
    kbps: Optional[str]
    max_pending_mcast: Optional[str] = Field(..., alias="max-pending-mcast")
    num_active: Optional[str] = Field(..., alias="num-active")
    num_bcast: Optional[str] = Field(..., alias="num-bcast")
    num_gtpc: Optional[str] = Field(..., alias="num-gtpc")
    num_gtpu_active: Optional[str] = Field(..., alias="num-gtpu-active")
    num_gtpu_pending: Optional[str] = Field(..., alias="num-gtpu-pending")
    num_http2_5gc: Optional[str] = Field(..., alias="num-http2-5gc")
    num_icmp: Optional[str] = Field(..., alias="num-icmp")
    num_imsi: Optional[str] = Field(None, alias="num-imsi")
    num_installed: Optional[str] = Field(..., alias="num-installed")
    num_max: Optional[str] = Field(..., alias="num-max")
    num_mcast: Optional[str] = Field(..., alias="num-mcast")
    num_pfcpc: Optional[str] = Field(..., alias="num-pfcpc")
    num_predict: Optional[str] = Field(..., alias="num-predict")
    num_sctp_assoc: Optional[str] = Field(..., alias="num-sctp-assoc")
    num_sctp_sess: Optional[str] = Field(..., alias="num-sctp-sess")
    num_tcp: Optional[str] = Field(..., alias="num-tcp")
    num_udp: Optional[str] = Field(..., alias="num-udp")
    pps: Optional[str]
    tcp_cong_ctrl: Optional[str] = Field(None, alias="tcp-cong-ctrl")
    tcp_reject_siw_thresh: Optional[str] = Field(..., alias="tcp-reject-siw-thresh")
    tmo_cp: Optional[str] = Field(..., alias="tmo-cp")
    tmo_def: Optional[str] = Field(..., alias="tmo-def")
    tmo_icmp: Optional[str] = Field(..., alias="tmo-icmp")
    tmo_sctp: Optional[str] = Field(..., alias="tmo-sctp")
    tmo_sctpcookie: Optional[str] = Field(..., alias="tmo-sctpcookie")
    tmo_sctpinit: Optional[str] = Field(..., alias="tmo-sctpinit")
    tmo_sctpshutdown: Optional[str] = Field(..., alias="tmo-sctpshutdown")
    tmo_tcp: Optional[str] = Field(..., alias="tmo-tcp")
    tmo_tcp_delayed_ack: Optional[str] = Field(..., alias="tmo-tcp-delayed-ack")
    tmo_tcp_unverif_rst: Optional[str] = Field(..., alias="tmo-tcp-unverif-rst")
    tmo_tcphalfclosed: Optional[str] = Field(..., alias="tmo-tcphalfclosed")
    tmo_tcphandshake: Optional[str] = Field(..., alias="tmo-tcphandshake")
    tmo_tcpinit: Optional[str] = Field(..., alias="tmo-tcpinit")
    tmo_tcptimewait: Optional[str] = Field(..., alias="tmo-tcptimewait")
    tmo_udp: Optional[str] = Field(..., alias="tmo-udp")
    vardata_rate: Optional[str] = Field(..., alias="vardata-rate")
    # below are only found on later releases of PAN-OS and will be ignored for now
    # tmo_5gcdelete: Optional[str] = Field(..., alias="tmo-5gcdelete")
