"""MK.2 chamber: ring charge, payload circle, flight, landing ring. Propellant is summoned.

Usage: python exp_ring2.py E NE SE [--payload P] [--charges C] [--salvos S]
"""
import math
import re
import sys
import time

from lab import Rcon, step, wait_ticks, write_function
from modules2 import CHARGES, SOURCES, chamber2

BX, BY, BZ = 2015, 100, 2008
POS = re.compile(r"Pos: \[(-?[\d.eE-]+)d, (-?[\d.eE-]+)d, (-?[\d.eE-]+)d\]")
MOT = re.compile(r"Motion: \[(-?[\d.eE-]+)d, (-?[\d.eE-]+)d, (-?[\d.eE-]+)d\]")
FUSE = re.compile(r"fuse: (\d+)s")
OUT = {"west": (-1, 0, 0), "east": (1, 0, 0), "north": (0, 0, -1), "south": (0, 0, 1), "up": (0, -1, 0)}


def opt(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def entities(r, box):
    reply = r.cmd(f"execute as @e[type=tnt,{box}] run data get entity @s")
    out = []
    for chunk in reply.split("has the following entity data: ")[1:]:
        p, m, f = POS.search(chunk), MOT.search(chunk), FUSE.search(chunk)
        out.append((tuple(map(float, p.groups())), tuple(map(float, m.groups())), int(f.group(1))))
    return out


def push(member, source, exposure=1.0):
    """Velocity one explosion at `source` (feet of the propellant TNT) gives a TNT at `member`."""
    cx, cy, cz = source[0], source[1] + 0.98 * 0.0625, source[2]
    dx, dy, dz = member[0] - cx, member[1] - cy, member[2] - cz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    k = (1 - dist / 8) / dist * exposure
    return dx * k, dy * k, dz * k


def centre(points):
    n = len(points)
    return sum(p[0] for p in points) / n, sum(p[1] for p in points) / n


def shape(points, cx, cz):
    rr = [math.hypot(p[0] - cx, p[1] - cz) for p in points]
    return f"{min(rr):.4f} / {sum(rr) / len(rr):.4f} / {max(rr):.4f}"


def build(r):
    r.cmd("tick unfreeze"); r.cmd("tick rate 20")
    r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd(f"forceload add {BX - 15} {BZ - 8} {BX + 16} {BZ + 7}")
    wait_ticks(r, 5)
    r.cmd("kill @e[type=tnt]")
    for y in range(BY - 6, BY + 6):
        r.cmd(f"fill {BX - 6} {y} {BZ - 8} {BX + 10} {y} {BZ + 8} air")
    b, points = chamber2()
    bad = [c for c in b.to_commands(BX, BY, BZ) if "Changed" not in r.cmd(c)]
    if bad:
        print("paste errors:", bad[:3])
    return points


if __name__ == "__main__":
    args = [a for a in sys.argv[1:4] if not a.startswith("--")]
    counts = dict(zip(("e", "ne", "se"), map(int, args + ["0"] * (3 - len(args)))))
    payload, charges, salvos = opt("--payload", 12), opt("--charges", 0), opt("--salvos", 1)
    cell = f"x={BX - 2},y={BY - 1},z={BZ - 2},dx=4,dy=3,dz=4"
    with Rcon(timeout=600) as r:
        build(r)
        on, off = [], []
        for name in list(CHARGES)[:charges]:
            x, y, z = (BX + CHARGES[name][0] + OUT[name][0], BY + CHARGES[name][1] + OUT[name][1],
                       BZ + CHARGES[name][2] + OUT[name][2])
            on.append(f"setblock {x} {y} {z} redstone_block")
            off.append(f"setblock {x} {y} {z} air")
        write_function("salvo_on", on or ["say -"])
        write_function("salvo_off", off or ["say -"])
        r.cmd("reload")
        wait_ticks(r, 10)
        r.cmd("tick freeze"); time.sleep(0.3)
        # a ring charge dispensed at t=0 spawns at t=4 and explodes at t=83
        boom = 83 + 4 * (salvos - 1)
        plan = {}
        for s in range(salvos):
            plan.setdefault(4 * s, []).append("function lab:salvo_on")
            plan.setdefault(4 * s + 2, []).append("function lab:salvo_off")
        last = 77  # payload pulse whose TNT has ticked twice when the first salvo goes off
        for i in range(payload):
            t = last - 4 * i
            plan.setdefault(t, []).append(f"setblock {BX} {BY + 2} {BZ} redstone_block")
            plan.setdefault(t + 2, []).append(f"setblock {BX} {BY + 2} {BZ} air")
        early = []
        for t in range(min(plan), boom + 3):
            for c in plan.get(t, []):
                r.cmd(c)
            if t == 83:
                early = entities(r, cell)
            step(r, 1)
        r.cmd(f"forceload remove {BX - 15} {BZ - 8} {BX} {BZ + 7}")  # payload chunk: lazy from here on
        r.cmd("tick unfreeze")
        wait_ticks(r, 4)
        before = [e for e in entities(r, cell) if abs(e[0][1] - BY) < 0.6]
        cx0, cz0 = BX + 0.5, BZ + 0.5
        b0 = [(p[0], p[2]) for p, _, _ in early if abs(p[1] - BY) < 0.6]
        if b0:
            print(f"before the ring charge: {len(b0)} TNT, radius {shape(b0, cx0, cz0)}")
        pts = [(p[0], p[2]) for p, _, _ in before]
        fx, fz = centre(pts)
        print(f"payload: {len(before)} TNT, y {sorted({round(p[1], 4) for p, _, _ in before})}, mean off by {fx - cx0:+.4f} {fz - cz0:+.4f}, "
              f"radius about the block centre {shape(pts, cx0, cz0)}")
        print(f"         speed max {max(max(abs(v) for v in m) for _, m, _ in before):.4f}, fuses {sorted(f for _, _, f in before)}")
        lines = []
        for name, n in counts.items():
            dx, dz = SOURCES[name]
            lines += [f"summon tnt {BX + dx + 0.5} {BY} {BZ + dz + 0.5} {{fuse:1}}"] * n
        total = len(lines)
        for i in range(0, total, 2000):
            write_function(f"charge{i // 2000}", lines[i:i + 2000])
        r.cmd("reload")
        for i in range(0, total, 2000):
            r.cmd(f"function lab:charge{i // 2000}")
            wait_ticks(r, 3)
        wait_ticks(r, 5)

        def land(p):
            vx = vz = 0.0
            for name, n in counts.items():
                dx, dz = SOURCES[name]
                px, _, pz = push(p, (BX + dx + 0.5, BY, BZ + dz + 0.5))
                vx += n * px; vz += n * pz
            return p[0] + 0.9 * vx, p[2] + 0.9 * vz

        want = [land(p) for p, _, _ in before]
        tx, tz = centre(want)
        r.cmd("tick freeze"); time.sleep(0.2)
        r.cmd(f"forceload add {BX - 15} {BZ - 8} {BX} {BZ + 7}")
        step(r, 2)
        r.cmd(f"forceload add {int(tx) - 120} {int(tz) - 120} {int(tx) + 120} {int(tz) + 120}")
        time.sleep(1.0)
        box = f"x={int(tx) - 120},y=-400,z={int(tz) - 120},dx=240,dy=900,dz=240"
        after = entities(r, box)
        r.cmd("tick unfreeze")
        if not after:
            print("no payload at the target; predicted centre", round(tx, 2), round(tz, 2))
        else:
            got = [(p[0], p[2]) for p, _, _ in after]
            worst = max(min(math.hypot(g[0] - w[0], g[1] - w[1]) for w in want) for g in got)
            print(f"arrived: {len(after)} TNT, y {after[0][0][1]:.2f}; largest gap between a landing and its model point {worst:.3f}")
            rx, rz = land((cx0, before[0][0][1], cz0))  # where a TNT at the block centre would land
            print(f"ring about {rx:.2f} {rz:.2f} ({math.hypot(rx - cx0, rz - cz0):.1f} blocks away): radius {shape(got, rx, rz)}")
            print("fuses at the target:", sorted(f for _, _, f in after))
        wait_ticks(r, 100)
        r.cmd("kill @e[type=tnt]")
        r.cmd(f"forceload remove {int(tx) - 120} {int(tz) - 120} {int(tx) + 120} {int(tz) + 120}")
