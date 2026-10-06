"""Minimal RCON client for the local test server (stdlib only).

Usage:  python rcon.py "command one" "command two" ...
Reads port and password from ../server/server.properties.
"""
import socket
import struct
import sys
from pathlib import Path

PROPS = Path(__file__).resolve().parent.parent / "server" / "server.properties"


def _props():
    out = {}
    for line in PROPS.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


class Rcon:
    def __init__(self, host="127.0.0.1", port=None, password=None, timeout=30):
        props = _props()
        self.sock = socket.create_connection((host, int(port or props["rcon.port"])), timeout=timeout)
        self._id = 0
        self._send(3, password or props["rcon.password"])
        rid, _, _ = self._recv()
        if rid == -1:
            raise RuntimeError("rcon auth failed")

    def _send(self, kind, body):
        self._id += 1
        payload = struct.pack("<ii", self._id, kind) + body.encode("utf-8") + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(payload)) + payload)
        return self._id

    def _read(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("rcon closed")
            buf += chunk
        return buf

    def _recv(self):
        (length,) = struct.unpack("<i", self._read(4))
        data = self._read(length)
        rid, kind = struct.unpack("<ii", data[:8])
        return rid, kind, data[8:-2].decode("utf-8", "replace")

    def cmd(self, command):
        """Run one command. Long replies are fragmented, so a sentinel packet marks the end.

        The server drops the connection if two packets arrive in one read, so the
        sentinel is only sent once the first reply fragment is in.
        """
        self._send(2, command)
        parts = [self._recv()[2]]
        sentinel = self._send(2, "")
        while True:
            rid, _, body = self._recv()
            if rid == sentinel:
                break
            parts.append(body)
        return "".join(parts)

    def close(self):
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


if __name__ == "__main__":
    with Rcon() as r:
        for c in sys.argv[1:]:
            print(f"> {c}\n{r.cmd(c)}")
