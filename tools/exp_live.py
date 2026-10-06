"""MK.2: one shot from the lever at a moderate tick rate, polled as fast as RCON allows.

Usage: python exp_live.py E,NE,SE [RATE]
"""
import sys

from cannon2 import CELL, D, nether, overworld
from exp_mk2 import GROUPS, build, enter, lit, tnt_in
from exp_shot import value
from lab import Rcon, gametime

if __name__ == "__main__":
    n = dict(zip(GROUPS, map(int, sys.argv[1].split(","))))
    rate = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    b, info = overworld()
    nb, _ = nether()
    with Rcon(timeout=900) as r:
        build(r, b, info, nb)
        enter(r, info, n)
        lx, ly, lz = info["lever"]
        r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=true]")
        t0 = gametime(r)
        r.cmd(f"tick rate {rate}")
        state, released = {}, None
        while True:
            t = gametime(r) - t0
            if t < 1900:
                continue
            row = {"late": not lit(r, (20, D, 18), "redstone_wire[power=0]"),
                   "busy": not lit(r, (19, D, 16), "redstone_wire[power=0]"),
                   "release": not lit(r, (18, D, 18), "redstone_wire[power=0]")}
            zones = {}
            for p, f in tnt_in(r, "x=-400,y=-100,z=-200,dx=500,dy=400,dz=400"):
                if int(p[0] // 1) in (15, 16) and int(p[2] // 1) == CELL[2] and int(p[1]) == CELL[1]:
                    key = "payload"
                elif 16 <= p[0] < 23 and 3 <= p[2] < 14 and p[1] >= 83.9:
                    key = "feed"
                else:
                    key = f"{round(p[0] / 4) * 4},{round(p[1] / 4) * 4},{round(p[2] / 4) * 4}"
                zones[key] = zones.get(key, 0) + 1
            row["payload"] = zones.pop("payload", 0)
            row["feeding"] = bool(zones.pop("feed", 0))
            row["stray"] = str(sorted(zones.items()))
            for k, v in row.items():
                if state.get(k) != v:
                    print(f"  t{t:5d} {k} -> {v}")
                    state[k] = v
            if row["release"] and released is None:
                released = t
            if released is not None and t > released + 500 or t > 2600 + 8 * max(n.values()) + 2000:
                break
        print("counters:", {g: value(r, info[f"counter_{g}"]) for g in GROUPS})
        r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
        r.cmd("tick rate 20")
