"""Long shot with the target area force-loaded, as if a player stood there.

Runs fast until shortly before the timer ends, then at normal speed and watches the target.
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
    box = f"x={cx - 112},y=-64,z={cz - 112},dx=240,dy=400,dz=240"
    r.cmd(f"forceload add {cx - 112} {cz - 112} {cx + 127} {cz + 127}")
    wait_ticks(r, 60)
    r.cmd(f"kill @e[type=tnt,{box}]")
    wait_ticks(r, 20)
    lx, ly, lz = LEVER
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=true]")
    t0 = gametime(r)
    r.cmd("tick rate 1250")
    wait_ticks(r, 2200)
    while value(r, info["counter_timer"]) > 60:
        time.sleep(0.1)
    r.cmd("tick rate 20")
    seen, first, last = 0, None, None
    for _ in range(1200):
        reply = r.cmd(f"execute as @e[type=tnt,{box}] run data get entity @s Pos")
        pos = re.findall(r"\[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]", reply)
        if pos:
            seen = max(seen, len(pos))
            first = first or pos[0]
            last = pos[0]
        elif first:
            break
        time.sleep(0.03)
    print("payload TNT seen at the loaded target:", seen)
    if first:
        px, pz = float(first[0]), float(first[2])
        print(f"arrived at {px:.3f} / {pz:.3f}, height {float(first[1]):.1f}; model {tx:.3f} / {tz:.3f}; miss {px - tx:+.3f} {pz - tz:+.3f}")
        print(f"last seen at height {float(last[1]):.1f} (ground is -60): it fell {float(first[1]) - float(last[1]):.1f} blocks before exploding")
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
    r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd("tick rate 1250"); wait_ticks(r, 2300); r.cmd("tick rate 20")
