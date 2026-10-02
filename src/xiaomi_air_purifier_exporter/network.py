"""Resolve the device IP from its MAC address via the kernel ARP table."""
import ipaddress
import logging
import socket
import time

from .miio import HELLO, MIIO_PORT

log = logging.getLogger(__name__)


def arp_lookup(mac, arp_text):
    for line in arp_text.splitlines()[1:]:
        f = line.split()
        # IP, HW type, Flags, HW address, ... ; flag 0x2 = complete entry
        if len(f) >= 4 and f[3].lower() == mac and int(f[2], 16) & 0x2:
            return f[0]
    return None


def local_networks(route_text):
    def le_ip(h):
        return str(ipaddress.IPv4Address(int.from_bytes(bytes.fromhex(h), "little")))

    for line in route_text.splitlines()[1:]:
        f = line.split()
        iface, dest, gw, flags, mask = f[0], f[1], f[2], int(f[3], 16), f[7]
        if (gw != "00000000" or mask == "00000000" or not flags & 0x1
                or iface.startswith(("lo", "docker", "br-", "veth"))):
            continue
        net = ipaddress.IPv4Network((le_ip(dest), le_ip(mask)))
        # ponytail: sweep only /22 and smaller, set a static ARP entry / reserve DHCP if LAN is bigger
        if net.prefixlen >= 22:
            yield net


def read(path):
    with open(path) as fh:
        return fh.read()


def find_ip(mac):
    ip = arp_lookup(mac, read("/proc/net/arp"))
    if ip:
        return ip
    # Not in ARP cache: poke every host on local subnets so the kernel resolves them.
    log.info("%s not in ARP table, sweeping local subnets", mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for net in local_networks(read("/proc/net/route")):
            for host in net.hosts():
                try:
                    s.sendto(HELLO, (str(host), MIIO_PORT))
                except OSError:
                    pass
    time.sleep(3)
    ip = arp_lookup(mac, read("/proc/net/arp"))
    if not ip:
        raise RuntimeError(f"{mac} not found in ARP table")
    return ip
