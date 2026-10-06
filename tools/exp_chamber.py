"""Chamber test with summoned propellant: alignment, per-TNT push vectors, release distance."""
import sys
import time

from build import Build
from lab import Rcon, get, wait_ticks, write_function
from modules import chamber

OX, OY, OZ = 15, 100, 8  # payload cell: last column of chunk (0,0)
PAY = "@e[tag=pay,limit=1]"


def A(p):
    return f"{OX + p[0]} {OY + p[1]} {OZ + p[2]}"


def centre(p):
    return f"{OX + p[0] + 0.5} {OY + p[1]} {OZ + p[2] + 0.5}"


def show(r, label):
    pos, mot, fuse = get(r, PAY, "Pos"), get(r, PAY, "Motion"), get(r, PAY, "fuse")
    print(f"{label}: Pos {pos} Motion {mot} fuse {fuse}")
    return pos, mot


n_w = int(sys.argv[1]) if len(sys.argv) > 1 else 300
n_nw = int(sys.argv[2]) if len(sys.argv) > 2 else 100
n_sw = int(sys.argv[3]) if len(sys.argv) > 3 else 0

with Rcon(timeout=600) as r:
    b, P = chamber()
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all")
    r.cmd("forceload add 0 0 31 15")  # chunks (0,0) and (1,0) both entity-ticking for the set-up
    r.cmd(f"fill {OX - 6} {OY - 3} {OZ - 6} {OX + 8} {OY + 6} {OZ + 6} air")
    bad = [c for c in b.to_commands(OX, OY, OZ) if "Changed" not in r.cmd(c)]
    print("paste errors:", bad)
    r.cmd(f"setblock {A(P['wall'])} obsidian")
    wait_ticks(r, 10)
    water = [k for k in ("prop_w", "prop_nw", "prop_sw") if "passed" in r.cmd(f"execute if block {A(P[k])} water[level=0]")]
    leaked = r.cmd(f"execute if block {A((1, 1, 0))} water")
    print("water cells intact:", water, "| snow:", "passed" in r.cmd(f"execute if block {A(P['payload'])} powder_snow"))
    for name in ("w", "nw", "sw"):
        write_function(f"prop_{name}", [f"summon tnt {centre(P['prop_' + name])} {{fuse:1}}"])
    write_function("many_w", ["function lab:prop_w"] * n_w)
    write_function("many_nw", ["function lab:prop_nw"] * n_nw)
    write_function("many_sw", ["function lab:prop_sw"] * max(n_sw, 1))
    r.cmd("reload")
    # payload slightly off-centre, as a dropped TNT would be
    x, y, z = OX + 0.5 + 0.007, OY, OZ + 0.5 - 0.004
    r.cmd(f'summon tnt {x} {y} {z} {{fuse:2000,Tags:["pay"]}}')
    wait_ticks(r, 4)
    show(r, "dropped      ")
    r.cmd("function lab:prop_nw")  # aligner: one north-west push while the chunk still ticks
    wait_ticks(r, 5)
    show(r, "aligned      ")
    r.cmd("forceload remove 0 0 15 15")
    wait_ticks(r, 6)
    f0 = get(r, PAY, "fuse")
    wait_ticks(r, 6)
    print("lazy (fuse frozen):", f0 == get(r, PAY, "fuse"))
    r.cmd(f"setblock {A(P['wall'])} air")
    wait_ticks(r, 2)
    total = [0.0, 0.0, 0.0]
    for name, n in (("w", n_w), ("nw", n_nw), ("sw", n_sw)):
        if not n:
            continue
        r.cmd(f"function lab:many_{name}")
        wait_ticks(r, 5)
        pos, mot = show(r, f"after {n:5d} {name:2s}")
        d = [mot[i] - total[i] for i in range(3)]
        print(f"   per TNT: x {d[0] / n:+.6f}  y {d[1] / n:+.6f}  z {d[2] / n:+.6f}")
        total = mot
    intact = "passed" in r.cmd(f"execute if block {A(P['payload'])} powder_snow")
    traps = sum("passed" in r.cmd(f"execute if block {A(p)} iron_trapdoor") for p, s in b.blocks.items() if "trapdoor" in s[0])
    print("snow intact:", intact, "| trapdoors left:", traps, "of", sum("trapdoor" in s[0] for s in b.blocks.values()))
    start, mot = show(r, "before release")
    r.cmd("tick freeze")
    tx, tz = start[0] + 0.9 * mot[0], start[2] + 0.9 * mot[2]
    cx, cz = int(tx // 16) * 16, int(tz // 16) * 16
    r.cmd(f"forceload add {cx - 16} {cz - 16} {cx + 31} {cz + 31}")
    r.cmd("forceload add 0 0 15 15")
    for i in range(3):
        r.cmd("tick step 1")
        time.sleep(0.4)
    end, _ = show(r, "after release ")
    if end:
        print(f"moved: dx {end[0] - start[0]:+.3f} dz {end[2] - start[2]:+.3f}  expected dx {0.9 * mot[0]:+.3f} dz {0.9 * mot[2]:+.3f}")
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=tnt]")
