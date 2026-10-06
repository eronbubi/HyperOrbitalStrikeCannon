"""MK.2 feed test: real dupers, short feeds. Where does every duped TNT explode?

The piston lines are pulsed by the script (4 gt on, 4 gt off) while the game is stepped
tick by tick, and every TNT is followed until it disappears.

Usage: python exp_feed.py CYCLES [groups, e.g. e,ne,se]
"""
import collections
import re
import sys
import time

from cannon2 import core
from lab import Rcon, step, wait_ticks

ENT = re.compile(r"UUID: \[I; ([^\]]+)\]")
POS = re.compile(r"Pos: \[(-?[\d.eE-]+)d, (-?[\d.eE-]+)d, (-?[\d.eE-]+)d\]")
FUSE = re.compile(r"fuse: (\d+)s")


def at(p):
    return f"{p[0]} {p[1]} {p[2]}"


def tnt(r):
    reply = r.cmd("execute as @e[type=tnt] run data get entity @s")
    out = {}
    for chunk in reply.split("has the following entity data: ")[1:]:
        u, p, f = ENT.search(chunk), POS.search(chunk), FUSE.search(chunk)
        if u and p and f:
            out[u.group(1)] = (tuple(map(float, p.groups())), int(f.group(1)))
    return out


def build(r, b, info):
    (x0, y0, z0), (x1, y1, z1) = b.bounds()
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd("forceload add -16 -32 95 63")
    wait_ticks(r, 20)
    failed = [y for y in range(52, 142) if "illed" not in r.cmd(f"fill -12 {y} -24 90 {y} 60 air") + "illed"[:0]
              and "No blocks" not in r.cmd(f"fill -12 {y} -24 90 {y} 60 air")]
    if failed:
        print("clearing failed on levels", failed[:5])
    r.cmd("forceload remove -16 -32 95 63")
    r.cmd("forceload add -16 -16 47 47")
    wait_ticks(r, 5)
    r.cmd("kill @e[type=!player]")
    bad = [c for c in b.to_commands() if "Changed" not in r.cmd(c)]
    print("blocks:", len(b.blocks), "size", (x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1), "paste errors:", len(bad), bad[:3])
    for key in info["dupers"]:
        rail = info[f"duper_{key}"]["rail"]
        r.cmd(f"summon minecart {rail[0] + 0.5} {rail[1] + 0.1} {rail[2] + 0.5}")
    wait_ticks(r, 20)
    for key in info["dupers"]:
        r.cmd(f"setblock {at(info[f'duper_{key}']['prime'])} tnt")
    wait_ticks(r, 10)
    print("TNT lit by placing it:", r.cmd("execute if entity @e[type=tnt]"))


if __name__ == "__main__":
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    period = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    on = int(sys.argv[4]) if len(sys.argv) > 4 else period // 2
    groups = sys.argv[2].split(",") if len(sys.argv) > 2 else ["e", "ne", "se"]
    phase = int(sys.argv[5]) if len(sys.argv) > 5 else 0  # pusher clock runs this many gt behind the dupers
    b, info = core()
    with Rcon(timeout=600) as r:
        build(r, b, info)
        power = [info[f"duper_{key}"]["power"] for g in groups for key in info["groups"][g]]
        # feed pistons: a redstone block underneath, same rhythm
        pushers = [info[f"duper_{key}"]["pusher_power"] for key in info["dupers"]]
        r.cmd("tick freeze"); time.sleep(0.3)
        cells = {info[f"prop_{g}"]: g for g in ("e", "ne", "se")}
        booms, rest, age = collections.Counter(), collections.defaultdict(collections.Counter), []
        prev = {}
        for t in range(cycles * period + 140):
            if t < cycles * period:
                if t % period == 0:
                    for p in power:
                        r.cmd(f"setblock {at(p)} redstone_block")
                elif t % period == on:
                    for p in power:
                        r.cmd(f"setblock {at(p)} air")
            if (t - phase) % period == 0:  # the slime pushers run all the time
                for p in pushers:
                    r.cmd(f"setblock {at(p)} redstone_block")
            elif (t - phase) % period == on:
                for p in pushers:
                    r.cmd(f"setblock {at(p)} air")
            step(r, 1)
            cur = tnt(r)
            for u, (pos, fuse) in prev.items():
                if u not in cur:
                    block = (int(pos[0] // 1), int(pos[1] // 1), int(pos[2] // 1))
                    where = cells.get(block, f"ELSEWHERE {block}")
                    booms[where] += 1
                    if block in cells:
                        rest[cells[block]][(round(pos[0] - block[0], 4), round(pos[1] - block[1], 4), round(pos[2] - block[2], 4))] += 1
            for u, (pos, fuse) in cur.items():
                block = (int(pos[0] // 1), int(pos[1] // 1), int(pos[2] // 1))
                if u in prev and block in cells and (int(prev[u][0][0] // 1), int(prev[u][0][1] // 1), int(prev[u][0][2] // 1)) not in cells:
                    age.append(80 - fuse)
            prev = cur
        r.cmd("tick unfreeze")
        made = sum(booms.values())
        print(f"{cycles} cycles of {period} gt ({on} on) on {len(power)} dupers: {made} TNT exploded:", dict(booms))
        for g, c in rest.items():
            print(f"  position inside cell {g} at the explosion: {c.most_common(4)}")
        if age:
            print(f"  ticks from priming to arrival in the cell: {min(age)}..{max(age)}")
        gone = [pos for pos, (name, _) in b.blocks.items()
                if name in ("minecraft:obsidian", "minecraft:iron_trapdoor", "minecraft:dispenser", "minecraft:powder_snow", "minecraft:iron_bars")
                and "passed" not in r.cmd(f"execute if block {at(pos)} {name}")]
        print("blocks missing afterwards:", gone[:8], len(gone))
        print("dupers still hold TNT:", {k: "passed" in r.cmd(f"execute if block {at(info[f'duper_{k}']['slot'])} tnt") for k in info["dupers"]})
        r.cmd("kill @e[type=tnt]")
