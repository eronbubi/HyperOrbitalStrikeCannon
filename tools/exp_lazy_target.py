"""Near-diagonal long shot with the target chunk kept loaded but not ticking.

Question: when the payload was lost on the 7800 block diagonal shot, was it lost on arrival
in an unloaded chunk? Here the neighbour chunks are force-loaded, so the target chunk stays
in memory (block-ticking only) and the payload cannot be unloaded.
"""
import re
import sys
import time

import aim
from cannon import CELL, LEVER, overworld
from exp_shot import set_counter, value
from lab import Rcon, gametime, wait_ticks

n = dict(zip(("w", "nw", "sw"), map(int, sys.argv[1].split(","))))
n["timer"] = max(n.values()) + 15
with Rcon(timeout=1800) as r:
    b, info = overworld()
    r.cmd("tick rate 100")
    for name in ("w", "nw", "sw", "timer"):
        set_counter(r, info[f"counter_{name}"], n[name])
    wait_ticks(r, 40)
    r.cmd("tick rate 20")
    print("counters:", {k: value(r, info[f"counter_{k}"]) for k in n})
    dx, dz = aim.displacement(n)
    tx, tz = CELL[0] + 0.49 + dx, CELL[2] + 0.49 + dz
    cx, cz = int(tx // 16) * 16, int(tz // 16) * 16
    box = f"x={cx - 64},y=-64,z={cz - 64},dx=144,dy=400,dz=144"
    r.cmd(f"forceload add {cx - 64} {cz - 64} {cx + 79} {cz + 79}")
    wait_ticks(r, 60)
    r.cmd(f"kill @e[type=tnt,{box}]")
    wait_ticks(r, 20)
    r.cmd(f"forceload remove {cx - 64} {cz - 64} {cx + 79} {cz + 79}")
    # a ring of force-loaded chunks two chunks out: everything inside is loaded but lazy
    for ox in (-4, -2, 0, 2, 4):
        for oz in (-4, -2, 0, 2, 4):
            if max(abs(ox), abs(oz)) == 4:
                r.cmd(f"forceload add {cx + ox * 16} {cz + oz * 16}")
    wait_ticks(r, 20)
    lx, ly, lz = LEVER
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=true]")
    t0 = gametime(r)
    r.cmd("tick rate 1250")
    wait_ticks(r, 2200)
    while value(r, info["counter_timer"]) > 0:
        time.sleep(0.2)
    wait_ticks(r, 400)
    r.cmd("tick rate 20")
    reply = r.cmd(f"execute as @e[type=tnt,{box}] run data get entity @s Pos")
    pos = re.findall(r"\[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]", reply)
    print("payload found while the target was only lazily loaded:", len(pos), pos[:1])
    if pos:
        px, pz = float(pos[0][0]), float(pos[0][2])
        print(f"landing {px:.3f} {pz:.3f}; model {tx:.3f} {tz:.3f}; miss {px - tx:+.3f} {pz - tz:+.3f}")
    print("payload still in the cell:", r.cmd(f"execute if entity @e[type=tnt,x={CELL[0]},y={CELL[1] - 0.5},z={CELL[2]},dx=0,dy=1.5,dz=0]"))
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
    r.cmd(f"kill @e[type=tnt,{box}]")
    r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd("tick rate 1250"); wait_ticks(r, 2300); r.cmd("tick rate 20")
