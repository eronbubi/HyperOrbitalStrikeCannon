"""MK.2: when does the payload chunk tick after the fire pulse, at different tick rates?

Usage: python exp_window.py RATE [RATE ...]
"""
import re
import sys

from cannon2 import CELL, D, LINE, nether, overworld
from exp_mk2 import build, tnt_in
from lab import Rcon, gametime, wait_ticks

if __name__ == "__main__":
    b, info = overworld()
    nb, _ = nether()
    cx, cy, cz = CELL
    cell = f"x={cx - 1},y={cy - 0.5},z={cz - 1},dx=2,dy=1.5,dz=2"
    with Rcon(timeout=900) as r:
        for rate in map(int, sys.argv[1:]):
            build(r, b, info, nb)
            r.cmd('summon tnt 2 150 2 {fuse:30000,NoGravity:1b,Tags:["probe"]}')
            wait_ticks(r, 5)
            r.cmd(f"tick rate {rate}")
            r.cmd(f"setblock {LINE[0] + 1} {D} {LINE[2] - 1} redstone_block")
            t0 = gametime(r)
            samples = []
            while gametime(r) - t0 < 420:
                reply = r.cmd("execute store result score #t lab run time query gametime") if False else None
                f = re.search(r"data: (\d+)s", r.cmd("data get entity @e[tag=probe,limit=1] fuse"))
                samples.append((gametime(r) - t0, int(f.group(1)) if f else None))
            r.cmd("tick rate 20")
            first = next((t for (t, f), (_, g) in zip(samples[1:], samples) if f is not None and g is not None and f < g), None)
            last = max((t for (t, f), (_, g) in zip(samples[1:], samples) if f is not None and g is not None and f < g), default=None)
            ticked = samples[0][1] - samples[-1][1] if samples[0][1] and samples[-1][1] else None
            fuses = sorted(f for _, f in tnt_in(r, cell))
            print(f"rate {rate}: {len(samples)} samples; probe ticked {ticked} times, first seen moving at t<={first}, last at t<={last}; "
                  f"payload in the cell: {len(fuses)} {fuses}")
            r.cmd(f"setblock {LINE[0] + 1} {D} {LINE[2] - 1} air")
            r.cmd("kill @e[type=tnt]")
