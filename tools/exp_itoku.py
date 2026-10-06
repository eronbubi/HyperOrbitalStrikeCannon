"""Paste ItokuMC's accelerator on the test server and measure what it does.

Counts new primed TNT per tick, shows where it comes to rest and where it explodes.
"""
import collections
import re
import sys
import time

from litemapy import Schematic

from lab import Rcon, gametime, step, wait_ticks

O = (900, 150, 900)  # schematic coordinates are added to this
FRAGILE = ("redstone_wire", "repeater", "torch", "lever", "rail", "fan", "water")


def load():
    reg = list(Schematic.load("../extern/itoku_accelerator.litematic").regions.values())[0]
    blocks = {}
    for x in reg.xrange():
        for y in reg.yrange():
            for z in reg.zrange():
                b = reg[x, y, z]
                if b.id != "minecraft:air":
                    blocks[(x, y, z)] = b.to_block_state_identifier()
    return blocks


def paste(r, blocks, lever_on):
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd(f"forceload add {O[0] - 32} {O[2] - 16} {O[0] + 31} {O[2] + 47}")
    for y in range(O[1] - 20, O[1] + 20):
        r.cmd(f"fill {O[0] - 20} {y} {O[2] - 8} {O[0] + 8} {y} {O[2] + 30} air")
    order = sorted(blocks.items(), key=lambda kv: (any(f in kv[1] for f in FRAGILE), kv[0][1]))
    bad = []
    for (x, y, z), state in order:
        if "lever" in state:
            state = state.replace("powered=true", "powered=false") if not lever_on else state
        # pasted in its resting state: nothing powered yet
        state = re.sub(r"power=\d+", "power=0", state)
        if "repeater" in state or "note_block" in state or "activator_rail" in state:
            state = state.replace("powered=true", "powered=false")
        reply = r.cmd(f"setblock {O[0] + x} {O[1] + y} {O[2] + z} {state}")
        if "Changed" not in reply:
            bad.append((state, reply))
    return bad


if __name__ == "__main__":
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    blocks = load()
    lever = next(p for p, s in blocks.items() if "lever" in s)
    with Rcon(timeout=600) as r:
        bad = paste(r, blocks, lever_on=False)
        print("pasted", len(blocks), "blocks; errors:", bad[:3])
        wait_ticks(r, 40)
        print("TNT before the lever:", r.cmd("execute if entity @e[type=tnt]"))
        lx, ly, lz = (O[i] + lever[i] for i in range(3))
        # the schematic was saved with the lever ON and nothing moving: ON = stop, OFF = run
        r.cmd(f"setblock {lx} {ly} {lz} minecraft:lever[face=floor,facing=west,powered=true]")
        wait_ticks(r, 120)
        r.cmd("kill @e[type=tnt]")
        print("TNT with the lever on (stopped):", r.cmd("execute if entity @e[type=tnt]"))
        r.cmd("tick freeze"); time.sleep(0.2)
        r.cmd(f"setblock {lx} {ly} {lz} minecraft:lever[face=floor,facing=west,powered=false]")
        births, rest, booms = [], collections.Counter(), collections.Counter()
        prev = {}
        for t in range(ticks):
            step(r, 1)
            reply = r.cmd("execute as @e[type=tnt] run data get entity @s")
            cur = {}
            for uuid, pos, fuse in re.findall(r"UUID: \[I; ([^\]]+)\].*?Pos: \[([^\]]+)\].*?fuse: (\d+)s", reply):
                cur[uuid] = (tuple(round(float(v[:-1]) - O[i], 2) for i, v in enumerate(pos.split(", "))), int(fuse))
            if not cur and "fuse" in reply:  # field order differs: parse separately
                for chunk in reply.split("Primed TNT has the following entity data: ")[1:]:
                    u = re.search(r"UUID: \[I; ([^\]]+)\]", chunk)
                    p = re.search(r"Pos: \[([^\]]+)\]", chunk)
                    f = re.search(r"fuse: (\d+)s", chunk)
                    if u and p and f:
                        cur[u.group(1)] = (tuple(round(float(v[:-1]) - O[i], 2) for i, v in enumerate(p.group(1).split(", "))), int(f.group(1)))
            births.append(sum(1 for u in cur if u not in prev))
            for u, (pos, fuse) in prev.items():
                if u not in cur:
                    booms[pos] += 1
            for pos, fuse in cur.values():
                if fuse == 20:
                    rest[pos] += 1
            prev = cur
        r.cmd("tick unfreeze")
        r.cmd(f"setblock {lx} {ly} {lz} minecraft:lever[face=floor,facing=west,powered=true]")
        line = "".join(str(min(b, 9)) if b else "." for b in births)
        print("new TNT per tick:", line)
        total = sum(births)
        print(f"total {total} TNT in {ticks} ticks = one per {ticks / max(total, 1):.2f} gt")
        print("position 20 ticks before exploding (schematic coordinates):", rest.most_common(6))
        print("explosion positions:", booms.most_common(6))
        print("TNT block still there:", r.cmd(f"execute if block {O[0] - 3} {O[1] + 11} {O[2] + 8} tnt"),
              "| water cell:", r.cmd(f"execute if block {O[0] - 3} {O[1] + 6} {O[2] + 4} water"))
        wait_ticks(r, 100)
        r.cmd("kill @e[type=tnt]")
