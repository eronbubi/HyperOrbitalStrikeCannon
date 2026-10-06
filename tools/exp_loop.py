"""Portal loop test: two bounce stations keep each other loaded without any force-load."""
import sys
import time

from lab import Rcon, get, wait_ticks, gametime
from modules import station

NETHER = "execute in minecraft:the_nether run "
OW = (40, 100, 24)  # chunk (2,1)
NE = (5, 100, 3)
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 1500


def paste(r, prefix, origin, build):
    x, y, z = origin
    r.cmd(f"{prefix}fill {x - 4} {y - 2} {z - 5} {x + 5} {y + 6} {z + 5} air")
    return [c for c in build.to_commands(*origin) if "Changed" not in r.cmd(prefix + c)]


def probe(r, chunks):
    out = []
    for cx, cz in chunks:
        r.cmd(f'summon tnt {cx * 16 + 8} 130 {cz * 16 + 8} {{fuse:30000,NoGravity:1b,Tags:["probe","c{cx}_{cz}"]}}')
    wait_ticks(r, 2)
    a = {c: get(r, f"@e[tag=c{c[0]}_{c[1]},limit=1]", "fuse") for c in chunks}
    wait_ticks(r, 6)
    for c in chunks:
        b = get(r, f"@e[tag=c{c[0]}_{c[1]},limit=1]", "fuse")
        state = "unloaded" if a[c] is None else ("TICK" if b and b[0] < a[c][0] else "lazy")
        out.append(f"{c}:{state}")
    r.cmd("kill @e[tag=probe]")
    return " ".join(out)


with Rcon(timeout=120) as r:
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all")
    r.cmd(NETHER + "forceload remove all")
    r.cmd("forceload add 10000 10000")
    r.cmd("forceload add 32 16 47 31")
    r.cmd(NETHER + "forceload add 0 0 15 15")
    wait_ticks(r, 5)
    b, P = station()
    print("paste errors overworld:", paste(r, "", OW, b))
    print("paste errors nether:   ", paste(r, NETHER, NE, b))
    wait_ticks(r, 10)
    print("portals alive:", r.cmd(f"execute if block {OW[0]} {OW[1] + 1} {OW[2]} nether_portal"), "|",
          r.cmd(NETHER + f"execute if block {NE[0]} {NE[1] + 1} {NE[2]} nether_portal"))
    s = P["send"]
    r.cmd(f'data merge block {OW[0] + s[0]} {OW[1] + s[1]} {OW[2] + s[2]} {{Items:[{{Slot:0b,id:"minecraft:cobblestone",count:2}}]}}')
    wait_ticks(r, 40)
    r.cmd("forceload remove 32 16 47 31")
    r.cmd(NETHER + "forceload remove all")
    t0 = gametime(r)
    chunks = [(0, 0), (1, 0), (1, 1), (2, 1), (3, 2), (4, 1)]
    while gametime(r) - t0 < DURATION:
        wait_ticks(r, 250)
        items = r.cmd("execute if entity @e[type=item]")
        print(f"t+{gametime(r) - t0:5d} {probe(r, chunks)} | item entities: {items.replace('Test ', '')}")
    def inv(prefix, origin, key):
        p = P[key]
        return r.cmd(f"{prefix}data get block {origin[0] + p[0]} {origin[1] + p[1]} {origin[2] + p[2]} Items")
    print("overworld send:", inv("", OW, "send")[-70:])
