"""MK.3 with nether post on the test server: cannon, nether link, control panel, bullseye.

Usage: python prepare_server_post.py [TARGET_X TARGET_Z]
Nothing is entered: the player presses the panel buttons the calculator app shows.
"""
import sys

from exp_mk3 import build
from exp_post import layout, prime
from lab import Rcon, wait_ticks
from prepare_server3 import FLOOR, PLAYER, bullseye

if __name__ == "__main__":
    tx, tz = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (-1500, 0)
    b, info, nb, ninfo, np_origin, pb, pinfo, origin = layout()
    px, py, pz = origin
    with Rcon(timeout=900) as r:
        r.cmd(f"tp {PLAYER} {tx} {FLOOR + 15} {tz + 49}")  # a player near the cannon would keep its chunks awake
        build(r, b, info, nb, list(ninfo.values()) + [np_origin])
        area = f"{px - 16} {pz - 16} {px + 48} {pz + 32}"
        r.cmd(f"forceload add {area}")
        wait_ticks(r, 10)
        for y in range(py - 3, py + 8):
            r.cmd(f"fill {px - 8} {y} {pz - 8} {px + 40} {y} {pz + 20} air")
        bad = [c for c in pb.to_commands(px, py, pz) if "Changed" not in r.cmd(c)]
        print("panel at", origin, "paste errors", len(bad))
        prime(r, info)
        wait_ticks(r, 40)
        r.cmd(f"forceload remove {area}")
        bullseye(r, tx, tz)
        print("flight cell", info["cell"], "| target", (tx, tz), "| panel: stand at", (px + 3, py + 1, pz + 4),
              "| watch from", (tx, FLOOR + 15, tz + 49))
        print(r.cmd("tick query")[:60])
