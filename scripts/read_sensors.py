#!/usr/bin/env python3
"""Read all readable MIoT properties (temperature, humidity, PM2.5, ...) from a Xiaomi device.

usage: read_sensors.py <ip> <token>
deps:  pip install "xiaomi-air-purifier-exporter[tools]"  (or just python-miio)
"""
import json
import sys
import urllib.request

from miio import Device

ip, token = sys.argv[1], sys.argv[2]
dev = Device(ip, token)
model = dev.info().model
print("model:", model)


def get_json(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.load(r)


# Map model -> MIoT spec (list of services/properties with siid/piid).
instances = [i for i in get_json("https://miot-spec.org/miot-spec-v2/instances?status=all")["instances"]
             if i["model"] == model]
if not instances:
    sys.exit(f"no MIoT spec found for {model}")
spec_type = max(instances, key=lambda i: i["version"])["type"]
spec = get_json(f"https://miot-spec.org/miot-spec-v2/instance?type={spec_type}")

props = []
for svc in spec["services"]:
    for p in svc.get("properties", []):
        if "read" in p.get("access", []):
            name = f'{svc["type"].split(":")[3]}.{p["type"].split(":")[3]}'
            props.append((name, svc["iid"], p["iid"], p.get("unit", "")))

# ponytail: fixed chunk of 10, some devices reject large get_properties batches
for i in range(0, len(props), 10):
    chunk = props[i:i + 10]
    req = [{"did": name, "siid": s, "piid": p} for name, s, p, _ in chunk]
    for (name, s, p, unit), res in zip(chunk, dev.send("get_properties", req)):
        val = res.get("value", f'<error code={res.get("code")}>')
        unit = "" if unit in ("", "none") else unit
        print(f"{name:45} siid={s:<3} piid={p:<3} {val} {unit}")
