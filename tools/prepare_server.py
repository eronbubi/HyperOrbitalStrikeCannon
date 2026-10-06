"""Builds the west cannon with its portal stations on the test server, enters a target and
builds a bullseye there, so a player only has to flip the lever.

Usage: python prepare_server.py PLAYER [TARGET_X TARGET_Z]
"""
import sys

import aim
from cannon import nether_turned, overworld_turned
from exp_shot import set_counter, value
from exp_turn import build
from lab import Rcon, wait_ticks

FLOOR = 52  # top of the bullseye; the payload arrives at y 84 and falls


def bullseye(r, tx, tz):
    r.cmd(f"forceload add {tx - 24} {tz - 24} {tx + 24} {tz + 24}")
    wait_ticks(r, 60)
    r.cmd(f"kill @e[type=tnt,x={tx - 96},y=-64,z={tz - 96},dx=192,dy=400,dz=192]")  # parked by earlier tests
    for y in range(FLOOR - 2, 140):
        r.cmd(f"fill {tx - 20} {y} {tz - 20} {tx + 20} {y} {tz + 20} air")
    for half, block in ((16, "white_concrete"), (12, "red_concrete"), (8, "white_concrete"), (4, "red_concrete"), (0, "gold_block")):
        r.cmd(f"fill {tx - half} {FLOOR} {tz - half} {tx + half} {FLOOR} {tz + half} {block}")
    # a place to stand and watch, out of the blast
    r.cmd(f"fill {tx - 3} {FLOOR + 10} {tz + 34} {tx + 3} {FLOOR + 10} {tz + 40} glass")
    wait_ticks(r, 20)
    r.cmd(f"forceload remove {tx - 24} {tz - 24} {tx + 24} {tz + 24}")


if __name__ == "__main__":
    player = sys.argv[1]
    tx, tz = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (-500, 8)
    with Rcon(timeout=900) as r:
        b, info = overworld_turned(0)
        nb, ninfo = nether_turned(0)
        build(r, b, info, nb, ninfo)
        cell = info["cell"]
        counts, miss = aim.plan(cell[0], cell[2], tx, tz, "west")
        print("cell", cell, "target", (tx, tz), "counts", counts, "expected miss", miss)
        bullseye(r, tx, tz)
        r.cmd("tick rate 100")  # buttons: the script cannot time presses any faster than this
        for name in ("w", "nw", "sw", "timer"):
            set_counter(r, info[f"counter_{name}"], counts[name])
        wait_ticks(r, 40)
        r.cmd("tick rate 20")
        shown = {name: value(r, info[f"counter_{name}"]) for name in counts}
        print("counters:", shown, "ok" if shown == counts else f"WANTED {counts}")
        print("lever", info["lever"], "| watch from", (tx, FLOOR + 11, tz + 37))
        print(r.cmd(f"op {player}"))
        print(r.cmd("tick query"))
