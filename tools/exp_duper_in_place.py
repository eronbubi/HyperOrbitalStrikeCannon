"""One duper of the assembled cannon, driven by its counter, watched closely."""
import re
import sys
from lab import Rcon, wait_ticks, gametime
from cannon import overworld, D, Y0, CELL, LEVER
from modules import enter_presses

NAME = sys.argv[1] if len(sys.argv) > 1 else "w"
COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 30


def at(p):
    return f"{p[0]} {p[1]} {p[2]}"


with Rcon(timeout=900) as r:
    b, info = overworld(stations=False)
    d = info[f"duper_{NAME}"]
    c = info[f"counter_{NAME}"]
    xe = info["taps"][368]
    r.cmd("tick rate 20"); r.cmd("kill @e[type=tnt]")
    r.cmd(f"setblock {at(d['prime'])} tnt"); wait_ticks(r, 5)
    print("primed at placement:", r.cmd("execute if entity @e[type=tnt]"))
    r.cmd("tick rate 100")
    for k in enter_presses(COUNT, c["bits"]):
        x, y, z = c["bit0"][0] + c["step"][0] * k, c["bit0"][1], c["bit0"][2]
        r.cmd(f"setblock {x} {y + 1} {z} stone_button[face=floor,facing=north,powered=true]"); wait_ticks(r, 3)
        r.cmd(f"setblock {x} {y + 1} {z} stone_button[face=floor,facing=north,powered=false]"); wait_ticks(r, 70)
    r.cmd("tick rate 20")
    torch = f"{xe + 2} {D} {LEVER[2] - 1}"
    r.cmd(f"setblock {torch} air")  # lets the counter clocks run without the rest of the sequence
    t0 = gametime(r)
    seen = set()
    for i in range(COUNT + 16):
        wait_ticks(r, 8)
        ents = r.cmd("execute as @e[type=tnt] run data get entity @s Pos")
        pos = [tuple(round(float(v), 2) for v in p) for p in re.findall(r"\[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]", ents)]
        where = {"slot": "passed" in r.cmd(f"execute if block {at(d['slot'])} tnt"), "prime": "passed" in r.cmd(f"execute if block {at(d['prime'])} tnt")}
        odd = [p for p in pos if not (abs(p[0] - (d['prime'][0] + 0.5)) < 0.03 and abs(p[2] - (d['prime'][2] + 0.5)) < 0.03)]
        if i < 6 or odd or not (where["slot"] or where["prime"]):
            print(f"t+{gametime(r) - t0}: tnt block {where}, {len(pos)} entities, off-column: {odd[:4]}")
    r.cmd(f"setblock {torch} redstone_wall_torch[facing=north]")
