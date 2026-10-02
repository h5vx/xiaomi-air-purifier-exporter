#!/usr/bin/env python3
"""Find Xiaomi miIO devices on the LAN via the miIO "hello" broadcast (UDP 54321)."""
import socket
import sys
import time

HELLO = bytes.fromhex("21310020" + "ff" * 28)
TARGET = sys.argv[1] if len(sys.argv) > 1 else "255.255.255.255"  # or pass device IP / subnet broadcast
TIMEOUT = 5

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.settimeout(1)

for _ in range(3):
    s.sendto(HELLO, (TARGET, 54321))

seen = set()
end = time.time() + TIMEOUT
while time.time() < end:
    try:
        data, (ip, _) = s.recvfrom(1024)
    except socket.timeout:
        continue
    if len(data) < 32 or data[:2] != b"\x21\x31" or ip in seen:
        continue
    seen.add(ip)
    did = int.from_bytes(data[8:12], "big")
    stamp = int.from_bytes(data[12:16], "big")
    token = data[16:32].hex()
    print(f"{ip}\tdid={did}\tstamp={stamp}\ttoken={token}")

if not seen:
    print("no devices answered")
