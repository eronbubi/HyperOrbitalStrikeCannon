"""MK.2: builds the west cannon with its portal stations on the test server, enters a target
and builds a bullseye there, so a player only has to flip the lever.

Usage: python prepare_server2.py [TARGET_X TARGET_Z] [--ring R] [--noring]
"""
import sys

import aim2
from cannon2 import nether_turned, overworld_turned
from exp_mk2 import GROUPS, build, enter
from lab import Rcon, wait_ticks

PLAYER = "ZalzQ"
FLOOR = 52  # top of the bullseye; the payload arrives at y 84 and falls


def bullseye(r, tx, tz):
    r.cmd(f"forceload add {tx - 40} {tz - 40} {tx + 40} {tz + 56}")
    wait_ticks(r, 60)
    r.cmd(f"kill @e[type=tnt,x={tx - 96},y=-64,z={tz - 96},dx=192,dy=400,dz=192]")  # parked by earlier tests
    for y in range(FLOOR - 2, 140):
        r.cmd(f"fill {tx - 36} {y} {tz - 36} {tx + 36} {y} {tz + 36} air")
    r.cmd(f"fill {tx - 36} {FLOOR} {tz - 36} {tx + 36} {FLOOR} {tz + 36} smooth_stone")
    for half, block in ((24, "white_concrete"), (18, "red_concrete"), (12, "white_concrete"), (6, "red_concrete"), (0, "gold_block")):
        r.cmd(f"fill {tx - half} {FLOOR} {tz - half} {tx + half} {FLOOR} {tz + half} {block}")
    # a place to stand and watch, out of the blast
    r.cmd(f"fill {tx - 3} {FLOOR + 14} {tz + 46} {tx + 3} {FLOOR + 14} {tz + 52} glass")
    wait_ticks(r, 20)
    r.cmd(f"forceload remove {tx - 40} {tz - 40} {tx + 40} {tz + 56}")


if __name__ == "__main__":
    raw, pos, want = sys.argv[1:], [], None
    while raw:
        a = raw.pop(0)
        if a == "--ring":
            want = float(raw.pop(0))
        elif a != "--noring":
            pos.append(int(a))
    tx, tz = pos if len(pos) == 2 else (-500, 8)
    charge = "--noring" not in sys.argv
    with Rcon(timeout=900) as r:
        b, info = overworld_turned(0)
        nb, ninfo = nether_turned(0)
        build(r, b, info, nb, (ninfo["n1"], ninfo["n3"]))
        cell = info["cell"]
        counts, miss = aim2.plan(cell[0], cell[2], tx, tz, "west", want, charge)
        lo, hi = aim2.ring(counts, charge)
        print("cell", cell, "target", (tx, tz), "counts", counts, "expected miss", miss, f"ring {lo:.1f}..{hi:.1f}")
        bullseye(r, tx, tz)
        enter(r, info, counts)
        nx, ny, nz = info["no_ring_lever"]
        r.cmd(f"setblock {nx} {ny} {nz} lever[face=floor,facing=north,powered={'false' if charge else 'true'}]")
        print("lever", info["lever"], "| watch from", (tx, FLOOR + 15, tz + 49),
              f"| shot about {(max(counts.values()) * 8 + 2200) / 20:.0f} s after the lever")
        print(r.cmd(f"op {PLAYER}"))
        print(r.cmd("tick query")[:80])
