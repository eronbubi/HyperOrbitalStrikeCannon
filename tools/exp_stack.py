"""MK.3 physics: a payload stacked in a sleeping chunk, all with the same fuse.

1. Dispense N TNT into a powder snow cell whose chunk does not tick entities: they pile up
   on one point, fuse frozen at 80, each with its own random prime momentum.
2. Let that chunk tick, and a moment later set off a transfer charge in a chunk that always
   ticks: the pile jumps into a second cell in a chunk that still sleeps.
3. Propellant, release, look at the landing.

Usage: python exp_stack.py N [TRANSFER] [E NE SE] [--wait W]
"""
import math
import sys
import time

from exp_ring2 import entities, opt, shape
from lab import Rcon, step, wait_ticks, write_function

Y = 100
C1 = (2014, Y, 1999)  # stack cell, chunk (125,124), diagonal neighbour of C2
C2 = (2013, Y, 2000)  # flight cell, chunk (125,125)
CHARGE = (2016, Y, 1997)  # = the NE propellant cell, chunk (126,124): always ticking
SOURCES = {"e": (4, 0), "ne": (3, -3), "se": (3, 3)}  # from C2


def cell(r, pos):
    x, y, z = pos
    r.cmd(f"setblock {x} {y} {z} powder_snow")
    r.cmd(f"setblock {x} {y - 1} {z} iron_bars")


def water_cell(r, x, y, z):
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r.cmd(f"setblock {x + dx} {y} {z + dz} iron_trapdoor[half=top]")
        r.cmd(f"setblock {x + dx} {y - 1} {z + dz} obsidian")
    r.cmd(f"setblock {x} {y - 1} {z} obsidian")
    r.cmd(f"setblock {x} {y} {z} water")
    r.cmd(f"setblock {x} {y + 1} {z} obsidian")


if __name__ == "__main__":
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    n, transfer = nums[0], (nums[1] if len(nums) > 1 else 5)
    counts = dict(zip(("e", "ne", "se"), nums[2:5] + [0] * 3))
    wait = opt("--wait", 30)
    with Rcon(timeout=600) as r:
        r.cmd("tick unfreeze"); r.cmd("tick rate 20")
        r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
        r.cmd("forceload add 1990 1970 2040 2030")
        wait_ticks(r, 10)
        r.cmd("kill @e[type=tnt]")
        for y in range(Y - 6, Y + 6):
            r.cmd(f"fill 1996 {y} 1984 2032 {y} 2016 air")
        for dx, dz in SOURCES.values():
            water_cell(r, C2[0] + dx, Y, C2[2] + dz)
        cell(r, C1); cell(r, C2)
        r.cmd(f"setblock {C1[0]} {Y + 1} {C1[2]} dispenser[facing=down]")
        r.cmd(f'data merge block {C1[0]} {Y + 1} {C1[2]} {{Items:[{{Slot:0b,id:"minecraft:tnt",count:64}},{{Slot:1b,id:"minecraft:tnt",count:64}},{{Slot:2b,id:"minecraft:tnt",count:64}}]}}')
        wait_ticks(r, 10)
        # only the east column of chunks ticks entities from here on
        r.cmd("forceload remove 1990 1970 2040 2030")
        r.cmd("forceload add 2016 1984 2031 2015")
        wait_ticks(r, 20)
        r.cmd("tick freeze"); time.sleep(0.3)
        for i in range(n):
            r.cmd(f"setblock {C1[0]} {Y + 2} {C1[2]} redstone_block"); step(r, 2)
            r.cmd(f"setblock {C1[0]} {Y + 2} {C1[2]} air"); step(r, 2)
        step(r, 8)
        box1 = f"x={C1[0] - 1},y={Y - 1},z={C1[2] - 1},dx=2,dy=3,dz=2"
        box2 = f"x={C2[0] - 1},y={Y - 1},z={C2[2] - 1},dx=2,dy=3,dz=2"
        got = entities(r, box1)
        print(f"stacked: {len(got)} TNT, fuses {sorted({f for _, _, f in got})}, positions {sorted({tuple(round(c, 3) for c in p) for p, _, _ in got})[:3]}")
        # the transfer charge starts counting now; the stack's chunk wakes up `wait` ticks before it goes off
        fuse = 60
        r.cmd("kill @e[tag=x]")
        for _ in range(transfer):
            r.cmd(f"summon tnt {CHARGE[0] + 0.49} {Y} {CHARGE[2] + 0.5} {{fuse:{fuse}}}")
        step(r, fuse - wait)
        r.cmd("forceload add 2000 1984 2015 1999")  # chunk (125,124) ticks
        for t in range(wait + 6):
            step(r, 1)
            a, b = entities(r, box1), entities(r, box2)
            if t in (0, 1, 2, wait - 2) or t >= wait - 1:
                pts = [(p[0], p[2]) for p, _, _ in a]
                print(f"  wake+{t + 1}: cell1 {len(a)} cell2 {len(b)}"
                      + (f" radius {shape(pts, C1[0] + 0.5, C1[2] + 0.5)} y {a[0][0][1]:.3f} fuse {sorted({f for _, _, f in a})}" if a else "")
                      + (f" | cell2 at {b[0][0][0]:.3f} {b[0][0][1]:.3f} {b[0][0][2]:.3f} fuses {sorted({f for _, _, f in b})} speed {max(max(abs(v) for v in m) for _, m, _ in b):.3f}" if b else ""))
        r.cmd("forceload remove 2000 1984 2015 1999")
        b = entities(r, box2)
        other = entities(r, "x=1990,y=60,z=1970,dx=60,dy=80,dz=70")
        print(f"after the transfer: cell2 {len(b)} of {len(other)} TNT alive")
        if b and sum(counts.values()):
            pts = [(p[0], p[2]) for p, _, _ in b]
            mx, mz = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
            print(f"  cell2 centre {mx:.4f} {mz:.4f}, radius {shape(pts, mx, mz)}")
            r.cmd("tick unfreeze")
            lines = []
            for name, k in counts.items():
                dx, dz = SOURCES[name]
                lines += [f"summon tnt {C2[0] + dx + 0.5} {Y} {C2[2] + dz + 0.5} {{fuse:1}}"] * k
            for i in range(0, len(lines), 2000):
                write_function(f"charge{i // 2000}", lines[i:i + 2000])
            r.cmd("reload")
            for i in range(0, len(lines), 2000):
                r.cmd(f"function lab:charge{i // 2000}")
                wait_ticks(r, 3)
            wait_ticks(r, 5)
            import aim2
            aim2.CELL = (mx, mz)
            aim2.SOURCE = {g: (C2[0] + d[0] + 0.5, C2[2] + d[1] + 0.5) for g, d in SOURCES.items()}
            tx, tz = aim2.landing(counts, mx, mz)
            r.cmd("tick freeze"); time.sleep(0.2)
            r.cmd("forceload add 2000 2000 2015 2015")
            step(r, 2)
            r.cmd(f"forceload add {int(tx) - 100} {int(tz) - 100} {int(tx) + 100} {int(tz) + 100}")
            time.sleep(1.0)
            after = entities(r, f"x={int(tx) - 100},y=-400,z={int(tz) - 100},dx=200,dy=900,dz=200")
            r.cmd("tick unfreeze")
            if after:
                g = [(p[0], p[2]) for p, _, _ in after]
                gx, gz = sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)
                print(f"  arrived: {len(after)} TNT, mean {gx:.2f} {gz:.2f} (model {tx:.2f} {tz:.2f}), radius {shape(g, gx, gz)}, "
                      f"fuses {sorted({f for _, _, f in after})}, y {after[0][0][1]:.2f}")
            else:
                print("  nothing at the target", round(tx, 1), round(tz, 1))
            wait_ticks(r, 100)
        r.cmd("tick unfreeze")
        r.cmd("kill @e[type=tnt]")
        r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
