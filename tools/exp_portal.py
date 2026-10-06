"""Portal chunk-loading test: which chunks tick entities after an item arrives through a nether portal."""
import time

from lab import Rcon, get, wait_ticks, gametime

N = "execute in minecraft:the_nether run "
Y = 100


def frame(r, prefix, x0, z, y=Y):
    """Portal in the x/y plane: interior x0..x0+1, y+1..y+3."""
    r.cmd(f"{prefix}fill {x0 - 3} {y - 1} {z - 3} {x0 + 4} {y + 6} {z + 3} air")
    r.cmd(f"{prefix}fill {x0 - 3} {y - 1} {z - 3} {x0 + 4} {y - 1} {z + 3} obsidian")
    r.cmd(f"{prefix}fill {x0 - 1} {y} {z} {x0 + 2} {y + 4} {z} obsidian")
    return r.cmd(f"{prefix}fill {x0} {y + 1} {z} {x0 + 1} {y + 3} {z} nether_portal[axis=x]")


def probes(r, label):
    out = {}
    for cx in range(-2, 7):
        tag = f"p{cx + 2}"
        out[cx] = r.cmd(f'summon tnt {cx * 16 + 8} 120 8 {{fuse:30000,NoGravity:1b,Tags:["probe","{tag}"]}}')
    wait_ticks(r, 3)
    a = {cx: get(r, f"@e[tag=p{cx + 2},limit=1]", "fuse") for cx in range(-2, 7)}
    wait_ticks(r, 10)
    b = {cx: get(r, f"@e[tag=p{cx + 2},limit=1]", "fuse") for cx in range(-2, 7)}
    line = []
    for cx in range(-2, 7):
        if a[cx] is None:
            state = "unloaded"
        else:
            state = "TICK" if b[cx] and b[cx][0] < a[cx][0] else "lazy"
        line.append(f"{cx}:{state}")
    print(label, " ".join(line))
    r.cmd("kill @e[tag=probe]")


with Rcon(timeout=120) as r:
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all")
    r.cmd("forceload add 10000 10000")  # stands in for a player being online somewhere else
    # build both portals while the areas are force-loaded, then drop the force-loads
    r.cmd("forceload add 32 0 47 15")
    r.cmd(N + "forceload add 0 0 15 15")
    wait_ticks(r, 5)
    print("overworld portal:", frame(r, "", 38, 8))
    print("nether portal:   ", frame(r, N, 4, 1))
    wait_ticks(r, 5)
    print("portal blocks stay:", r.cmd("execute if block 38 101 8 nether_portal"), "|", r.cmd(N + "execute if block 4 101 1 nether_portal"))
    r.cmd("forceload remove 32 0 47 15")
    wait_ticks(r, 40)
    probes(r, "before (portal chunk is 2):")
    # item enters the nether portal and comes out in the overworld
    r.cmd(N + 'summon item 5.0 101.5 1.5 {Item:{id:"minecraft:cobblestone",count:1},Tags:["loader"]}')
    t0 = gametime(r)
    wait_ticks(r, 6)
    print("item now:", r.cmd("data get entity @e[tag=loader,limit=1] Pos"), "|", r.cmd(N + "execute if entity @e[tag=loader]"))
    r.cmd(N + "forceload remove all")
    for wait in (10, 150, 280, 300, 320):
        while gametime(r) - t0 < wait:
            time.sleep(0.05)
        probes(r, f"t+{gametime(r) - t0:4d}:")
