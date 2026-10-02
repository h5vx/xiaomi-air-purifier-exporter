from xiaomi_air_purifier_exporter.miio import MiIO
from xiaomi_air_purifier_exporter.network import arp_lookup, local_networks

ARP = """IP address       HW type     Flags       HW address            Mask     Device
192.168.31.80    0x1         0x2         aa:bb:cc:dd:ee:ff     *        wlan0
192.168.31.99    0x1         0x0         00:00:00:00:00:00     *        wlan0
"""
ROUTE = """Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT
wlan0\t00000000\t011FA8C0\t0003\t0\t0\t600\t00000000\t0\t0\t0
wlan0\t001FA8C0\t00000000\t0001\t0\t0\t600\t00FFFFFF\t0\t0\t0
docker0\t000011AC\t00000000\t0001\t0\t0\t0\t0000FFFF\t0\t0\t0
"""


def test_arp_lookup():
    assert arp_lookup("aa:bb:cc:dd:ee:ff", ARP) == "192.168.31.80"
    assert arp_lookup("00:00:00:00:00:00", ARP) is None  # incomplete entry


def test_local_networks():
    assert [str(n) for n in local_networks(ROUTE)] == ["192.168.31.0/24"]


def test_encrypt_roundtrip():
    dev = MiIO("127.0.0.1", bytes(range(16)))
    try:
        assert dev.decrypt(dev.encrypt(b'{"id": 1}')) == b'{"id": 1}'
    finally:
        dev.close()
