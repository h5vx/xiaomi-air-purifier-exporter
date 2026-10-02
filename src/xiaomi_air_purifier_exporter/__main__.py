"""Entry point. env: XIAOMI_TOKEN (32 hex), XIAOMI_MAC, LISTEN_PORT (default 9811)"""
import logging
import os
import threading

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY

from .collector import PurifierCollector

log = logging.getLogger("xiaomi_air_purifier_exporter")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = bytes.fromhex(os.environ["XIAOMI_TOKEN"])
    if len(token) != 16:
        raise SystemExit("XIAOMI_TOKEN must be 32 hex chars")
    mac = os.environ["XIAOMI_MAC"].strip().lower()
    port = int(os.environ.get("LISTEN_PORT", "9811"))

    REGISTRY.register(PurifierCollector(mac, token))
    start_http_server(port)
    log.info("listening on :%d", port)
    threading.Event().wait()


if __name__ == "__main__":
    main()
