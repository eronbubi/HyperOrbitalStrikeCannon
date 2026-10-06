"""MK.2 physics: does a payload dispensed into an open powder snow cell land as a ring?

Dispensed TNT drifts 0.02 + 0.9 * 0.0196 blocks in a random direction before the snow stops
it. A propellant cell four blocks away pushes every payload TNT a little differently; the
difference grows with the number of explosions and should turn the tiny circle into a ring.

Propellant is summoned (fuse 1) instead of duped, so a shot takes seconds.

Usage: python exp_ring.py N_EAST [N_NE N_SE] [--payload P]
"""
import math
import re
import sys
import time

from lab import Rcon, gametime, wait_ticks, write_function

BX, BY, BZ = 2015, 100, 2008  # payload cell: last column of chunk (125,125)
SOURCES = {"e": (4, 0), "ne": (3, -3), "se": (3, 3)}
POS = re.compile(r"Pos: \[(-?[\d.eE-]+)d, (-?[\d.eE-]+)d, (-?[\d.eE-]+)d\]")
MOT = re.compile(r"Motion: \[(-?[\d.eE-]+)d, (-?[\d.eE-]+)d, (-?[\d.eE-]+)d\]")
FUSE = re.compile(r"fuse: (\d+)s")


def entities(r, box):
    reply = r.cmd(f"execute as @e[type=tnt,{box}] run data get entity @s")
    out = []
    for chunk in reply.split("has the following entity data: ")[1:]:
        p, m, f = POS.search(chunk), MOT.search(chunk), FUSE.search(chunk)
        out.append((tuple(map(float, p.groups())), tuple(map(float, m.groups())), int(f.group(1))))
    return out


def push(member, source):
    """Velocity one explosion at `source` (feet position of the propellant) gives a TNT at `member`."""
    cx, cy, cz = source[0], source[1] + 0.98 * 0.0625, source[2]
    dx, dy, dz = member[0] - cx, member[1] - cy, member[2] - cz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    k = (1 - dist / 8) / dist
    return dx * k, dy * k, dz * k


def build(r):
    r.cmd("tick unfreeze"); r.cmd("tick rate 20")
    r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd(f"forceload add {BX - 15} {BZ - 8} {BX + 16} {BZ + 7}")
    wait_ticks(r, 5)
    r.cmd("kill @e[type=tnt]")
    for y in range(BY - 2, BY + 6):
        r.cmd(f"fill {BX - 6} {y} {BZ - 8} {BX + 10} {y} {BZ + 8} air")
    r.cmd(f"fill {BX - 6} {BY - 1} {BZ - 8} {BX + 10} {BY - 1} {BZ + 8} obsidian")
    r.cmd(f"setblock {BX} {BY} {BZ} powder_snow")
    r.cmd(f"setblock {BX} {BY + 1} {BZ} dispenser[facing=down]")
    r.cmd(f'data merge block {BX} {BY + 1} {BZ} {{Items:[{{Slot:0b,id:"minecraft:tnt",count:64}}]}}')
    for dx, dz in SOURCES.values():
        x, z = BX + dx, BZ + dz
        r.cmd(f"fill {x - 1} {BY} {z - 1} {x + 1} {BY + 1} {z + 1} iron_trapdoor[half=top]")
        r.cmd(f"setblock {x} {BY + 1} {z} obsidian")
        r.cmd(f"setblock {x} {BY} {z} water")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    payload = int(sys.argv[sys.argv.index("--payload") + 1]) if "--payload" in sys.argv else 16
    if "--payload" in sys.argv:
        args = [a for a in args if a != str(payload)] if args.count(str(payload)) == 1 else args[:-1]
    counts = dict(zip(("e", "ne", "se"), map(int, args + ["0"] * (3 - len(args)))))
    cell = f"x={BX - 1},y={BY - 1},z={BZ - 1},dx=2,dy=3,dz=2"
    with Rcon(timeout=600) as r:
        build(r)
        for _ in range(payload):
            r.cmd(f"setblock {BX} {BY + 2} {BZ} redstone_block")
            wait_ticks(r, 2)
            r.cmd(f"setblock {BX} {BY + 2} {BZ} air")
            wait_ticks(r, 2)
        wait_ticks(r, 8)
        r.cmd(f"forceload remove {BX - 15} {BZ - 8} {BX} {BZ + 7}")  # payload chunk: lazy from here on
        wait_ticks(r, 3)
        before = entities(r, cell)
        cx, cz = BX + 0.5, BZ + 0.5
        radii = [math.hypot(p[0] - cx, p[2] - cz) for p, _, _ in before]
        print(f"payload: {len(before)} TNT, y {sorted({round(p[1], 4) for p, _, _ in before})}, "
              f"distance from the block centre {min(radii):.5f}..{max(radii):.5f}, "
              f"speed max {max(max(abs(v) for v in m) for _, m, _ in before):.4f}, fuses {sorted(f for _, _, f in before)}")
        lines = []
        for name, n in counts.items():
            dx, dz = SOURCES[name]
            lines += [f"summon tnt {BX + dx + 0.5} {BY} {BZ + dz + 0.5} {{fuse:1}}"] * n
        total = len(lines)
        for i in range(0, total, 2000):
            write_function(f"charge{i // 2000}", lines[i:i + 2000])
        r.cmd("reload")
        t = time.time()
        for i in range(0, total, 2000):
            r.cmd(f"function lab:charge{i // 2000}")
            wait_ticks(r, 3)
        wait_ticks(r, 5)
        charged = entities(r, cell)
        print(f"charged with {counts} in {time.time() - t:.1f} s; fuses now {sorted(f for _, _, f in charged)}")
        # prediction, member by member, from where each one sits
        want = []
        for p, _, _ in before:
            vx = vz = 0.0
            for name, n in counts.items():
                dx, dz = SOURCES[name]
                px, _, pz = push(p, (BX + dx + 0.5, BY, BZ + dz + 0.5))
                vx += n * px; vz += n * pz
            want.append((p[0] + 0.9 * vx, p[2] + 0.9 * vz))
        tx = sum(w[0] for w in want) / len(want); tz = sum(w[1] for w in want) / len(want)
        r.cmd("tick freeze"); time.sleep(0.2)
        r.cmd(f"forceload add {BX - 15} {BZ - 8} {BX} {BZ + 7}")
        target = gametime(r) + 2
        r.cmd("tick step 2")
        while gametime(r) < target:
            time.sleep(0.05)
        r.cmd(f"forceload add {int(tx) - 100} {int(tz) - 100} {int(tx) + 100} {int(tz) + 100}")
        time.sleep(1.0)
        box = f"x={int(tx) - 100},y=-400,z={int(tz) - 100},dx=200,dy=900,dz=200"
        after = entities(r, box)
        r.cmd("tick unfreeze")
        if not after:
            print("no payload at the target; predicted centre", round(tx, 2), round(tz, 2))
        else:
            ax = sum(p[0] for p, _, _ in after) / len(after); az = sum(p[2] for p, _, _ in after) / len(after)
            rr = sorted(math.hypot(p[0] - ax, p[2] - az) for p, _, _ in after)
            pr = sorted(math.hypot(w[0] - tx, w[1] - tz) for w in want)
            print(f"arrived: {len(after)} TNT, centre {ax:.2f} {az:.2f} (predicted {tx:.2f} {tz:.2f}), y {after[0][0][1]:.2f}, "
                  f"speed max {max(max(abs(v) for v in m) for _, m, _ in after):.3f}")
            print(f"ring radius measured {rr[0]:.2f}..{rr[-1]:.2f}, predicted {pr[0]:.2f}..{pr[-1]:.2f}")
            # member by member: nearest predicted point
            worst = max(min(math.hypot(p[0] - w[0], p[2] - w[1]) for w in want) for p, _, _ in after)
            print(f"largest distance between a landing and its predicted point: {worst:.3f}")
            print("fuses at the target:", sorted(f for _, _, f in after))
        wait_ticks(r, 100)
        r.cmd("kill @e[type=tnt]")
        r.cmd(f"forceload remove {int(tx) - 100} {int(tz) - 100} {int(tx) + 100} {int(tz) + 100}")
