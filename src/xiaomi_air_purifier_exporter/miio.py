"""Minimal miIO protocol client (UDP 54321, AES-128-CBC keyed by the device token)."""
import hashlib
import json
import socket
import struct

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MIIO_PORT = 54321
HELLO = bytes.fromhex("21310020" + "ff" * 28)


class MiIO:
    """Minimal miIO client: AES-128-CBC with key/iv derived from the device token."""

    def __init__(self, ip, token):
        self.ip, self.token = ip, token
        self.key = hashlib.md5(token).digest()
        self.iv = hashlib.md5(self.key + token).digest()
        self.id = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.sock.connect((ip, MIIO_PORT))

    def encrypt(self, data):
        padder = padding.PKCS7(128).padder()
        enc = Cipher(algorithms.AES(self.key), modes.CBC(self.iv)).encryptor()
        return enc.update(padder.update(data) + padder.finalize()) + enc.finalize()

    def decrypt(self, data):
        dec = Cipher(algorithms.AES(self.key), modes.CBC(self.iv)).decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(dec.update(data) + dec.finalize()) + unpadder.finalize()

    def pack(self, did, stamp, payload):
        header = struct.pack(">HHI4sI", 0x2131, 32 + len(payload), 0, did, stamp)
        return header + hashlib.md5(header + self.token + payload).digest() + payload

    def call(self, method, params):
        # Handshake before every call: gets device id + current stamp, survives device reboots.
        self.sock.send(HELLO)
        hello = self.sock.recv(1024)
        did, stamp = hello[8:12], int.from_bytes(hello[12:16], "big")

        self.id += 1
        body = json.dumps({"id": self.id, "method": method, "params": params}).encode()
        self.sock.send(self.pack(did, stamp + 1, self.encrypt(body)))
        while True:  # skip late replies to earlier timed-out requests
            data = self.sock.recv(4096)
            if len(data) <= 32:
                continue
            resp = json.loads(self.decrypt(data[32:]).rstrip(b"\x00"))
            if resp.get("id") == self.id:
                break
        if "error" in resp:
            raise RuntimeError(f"{method}: {resp['error']}")
        return resp["result"]

    def close(self):
        self.sock.close()
