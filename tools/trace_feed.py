"""Follows every TNT of one feed unit tick by tick (MK.2).

Usage: python trace_feed.py GROUP CYCLES [TICKS]
"""
import sys
import time

from cannon2 import core
from exp_feed import at, build, tnt
from lab import Rcon, step

if __name__ == "__main__":
    group = sys.argv[1]
    cycles = int(sys.argv[2])
    ticks = int(sys.argv[3]) if len(sys.argv) > 3 else cycles * 8 + 100
    b, info = core()
    with Rcon(timeout=600) as r:
        build(r, b, info)
        keys = info["groups"][group]
        power = [info[f"duper_{k}"]["power"] for k in keys]
        power += [info[f"duper_{k}"]["pusher_power"] for k in keys]
        for k in keys:
            print(k, {n: p for n, p in info[f"duper_{k}"].items()})
        print("cell", info[f"prop_{group}"])
        r.cmd("tick freeze"); time.sleep(0.3)
        names, prev = {}, {}
        for t in range(ticks):
            if t < cycles * 8:
                if t % 8 == 0:
                    for p in power:
                        r.cmd(f"setblock {at(p)} redstone_block")
                elif t % 8 == 4:
                    for p in power:
                        r.cmd(f"setblock {at(p)} air")
            step(r, 1)
            cur = tnt(r)
            row = []
            for u, (pos, fuse) in cur.items():
                n = names.setdefault(u, chr(65 + len(names) % 26))
                row.append(f"{n}({pos[0]:.2f},{pos[1]:.2f},{pos[2]:.2f} f{fuse})")
            for u in prev:
                if u not in cur:
                    p = prev[u][0]
                    row.append(f"BOOM {names[u]} at {p[0]:.2f},{p[1]:.2f},{p[2]:.2f}")
            if row:
                print(f"t{t:3d} " + " ".join(row))
            prev = cur
        r.cmd("tick unfreeze")
        r.cmd("kill @e[type=tnt]")
