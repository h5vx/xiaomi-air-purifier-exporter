"""Prometheus collector that polls the purifier on every scrape."""
import logging
import threading

from prometheus_client.core import GaugeMetricFamily

from .miio import MiIO
from .network import find_ip

log = logging.getLogger(__name__)

# (metric name, siid, piid, help) — from MIoT spec of zhimi.airp.meb1
PROPS = [
    ("air_purifier_on", 2, 1, "Power state (1 = on)"),
    ("air_purifier_fault", 2, 2, "Fault code (0 = no faults)"),
    ("air_purifier_mode", 2, 4, "Mode enum (MIoT spec)"),
    ("air_purifier_fan_level", 2, 5, "Fan level"),
    ("air_purifier_plasma", 2, 6, "Plasma ionizer state (1 = on)"),
    ("air_purifier_uv", 2, 7, "UV lamp state (1 = on)"),
    ("environment_relative_humidity_percent", 3, 1, "Relative humidity, %"),
    ("environment_pm25_density_ugm3", 3, 4, "PM2.5 density, ug/m3"),
    ("environment_temperature_celsius", 3, 7, "Temperature, C"),
    ("environment_pm10_density_ugm3", 3, 8, "PM10 density, ug/m3"),
    ("environment_air_quality", 3, 9, "Air quality enum (0 = excellent)"),
    ("filter_life_level_percent", 4, 1, "Filter life remaining, %"),
    ("filter_used_time_hours", 4, 3, "Filter used time, hours"),
]


class PurifierCollector:
    def __init__(self, mac, token):
        self.mac, self.token = mac, token
        self.dev = None
        self.lock = threading.Lock()

    def collect(self):
        with self.lock:
            return self.poll()

    def poll(self):
        up = GaugeMetricFamily("xiaomi_purifier_up", "1 if the last poll of the device succeeded")
        try:
            if self.dev is None:
                self.dev = MiIO(find_ip(self.mac), self.token)
                log.info("device %s at %s", self.mac, self.dev.ip)
            results = []
            for i in range(0, len(PROPS), 10):  # device rejects big batches
                chunk = PROPS[i:i + 10]
                results += self.dev.call("get_properties",
                                         [{"did": n, "siid": s, "piid": p} for n, s, p, _ in chunk])
        except Exception:
            log.exception("poll failed")
            if self.dev:
                self.dev.close()
            self.dev = None  # re-resolve IP next scrape (DHCP may have moved it)
            up.add_metric([], 0)
            return [up]

        up.add_metric([], 1)
        metrics = [up]
        for (name, _, _, help_), r in zip(PROPS, results):
            if r.get("code") == 0:
                metrics.append(GaugeMetricFamily(f"xiaomi_purifier_{name}", help_, value=float(r["value"])))
        return metrics
