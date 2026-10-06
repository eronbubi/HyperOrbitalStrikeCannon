"""Friend's cannon (ItokuMC "MOSC"): paste it on the test server exactly as saved.

Schematic coordinates + O = world coordinates. The red glass in the floor marks the chunk of the
payload cell (27, *, 24): that block is the south-west corner block of its chunk.
"""
import time

from litemapy import Schematic

from lab import Rcon, write_function, wait_ticks

O = (1973, 150, 1991)          # payload cell lands on x = 2000 (mod 16 = 0), z = 2015 (mod 16 = 15)
CELL = (27, 24)
SRC = "../extern/MOSC.litematic"
# chunks the four stasis pearls of the owner keep entity-ticking (relative to the payload chunk)
PEARL_CHUNKS = [(-1, 0), (-1, 1), (0, 1), (-1, 2)]


def w(x, y, z):
    return O[0] + x, O[1] + y, O[2] + z


def region(src=SRC):
    return list(Schematic.load(src).regions.values())[0]


def paste_lines(reg, pearls=False):
    lines, late = [], []
    for y in reg.yrange():
        for x in reg.xrange():
            for z in reg.zrange():
                b = reg[x, y, z]
                if b.id == "minecraft:air":
                    continue
                wx, wy, wz = w(x, y, z)
                lines.append(f"setblock {wx} {wy} {wz} {b.to_block_state_identifier()} strict")
    for t in reg.tile_entities:
        d = t.data
        keep = {k: v for k, v in d.items() if k in ("Items", "OutputSignal", "front_text", "back_text")}
        if not keep:
            continue
        x, y, z = t.position
        wx, wy, wz = w(x, y + min(reg.yrange()), z)
        body = ",".join(f"{k}:{v.snbt()}" for k, v in keep.items())
        late.append(f"data merge block {wx} {wy} {wz} {{{body}}}")
    for e in reg.entities:
        if e.id == "minecraft:minecart":
            px, py, pz = e.position
            late.append(f"summon minecart {O[0] + px} {O[1] + py} {O[2] + pz}")
    return lines + late


def clear_lines(reg):
    x0, y0, z0 = w(min(reg.xrange()) - 4, min(reg.yrange()) - 2, min(reg.zrange()) - 4)
    x1, y1, z1 = w(max(reg.xrange()) + 4, max(reg.yrange()) + 6, max(reg.zrange()) + 4)
    return [f"fill {x0} {y} {z0} {x1} {y} {z1} air strict" for y in range(y0, y1 + 1)]


def chunk_of_cell():
    return (O[0] + CELL[0]) >> 4, (O[2] + CELL[1]) >> 4


def load_like_pearls(r):
    cx, cz = chunk_of_cell()
    r.cmd("forceload remove all")
    for dx, dz in PEARL_CHUNKS:
        r.cmd(f"forceload add {(cx + dx) * 16} {(cz + dz) * 16}")


def paste(r, src=SRC):
    reg = region(src)
    write_function("mosc_clear", clear_lines(reg))
    write_function("mosc_paste", paste_lines(reg))
    r.cmd("reload"); time.sleep(2)
    r.cmd("tick unfreeze"); r.cmd("tick rate 20")
    cx, cz = chunk_of_cell()
    r.cmd("forceload remove all")
    r.cmd(f"forceload add {(cx - 3) * 16} {(cz - 2) * 16} {(cx + 2) * 16} {(cz + 4) * 16}")
    wait_ticks(r, 20)
    r.cmd("tick freeze"); time.sleep(0.3)
    r.cmd(f"kill @e[type=!player,x={O[0]},y={O[1] - 60},z={O[2]},dx=50,dy=70,dz=50]")
    print(r.cmd("function lab:mosc_clear"))
    r.cmd(f"kill @e[type=item,x={O[0]},y={O[1] - 60},z={O[2]},dx=50,dy=70,dz=50]")
    print(r.cmd("function lab:mosc_paste"))
    load_like_pearls(r)
    r.cmd("tick unfreeze")


if __name__ == "__main__":
    with Rcon(timeout=600) as r:
        paste(r)
        wait_ticks(r, 100)
        print("TNT:", r.cmd("execute if entity @e[type=tnt]"), "| items:", r.cmd("execute if entity @e[type=item]"))


def verify(r, reg=None):
    """Count blocks that differ from the schematic (ignores states that change by running)."""
    reg = reg or region()
    lines = ["scoreboard objectives add mosc dummy", "scoreboard players set bad mosc 0"]
    for y in reg.yrange():
        for x in reg.xrange():
            for z in reg.zrange():
                b = reg[x, y, z]
                if b.id == "minecraft:air":
                    continue
                wx, wy, wz = w(x, y, z)
                lines.append(f"execute unless block {wx} {wy} {wz} {b.id} run scoreboard players add bad mosc 1")
    write_function("mosc_verify", lines)
    r.cmd("reload"); time.sleep(2)
    r.cmd("function lab:mosc_verify")
    return r.cmd("scoreboard players get bad mosc")


import re
import collections


BOX = f"x={O[0] - 40},y={O[1] - 70},z={O[2] - 40},dx=130,dy=120,dz=130"


def tnt(r, sel=None):
    """[(x, y, z, fuse, mx, my, mz)] in schematic coordinates."""
    sel = sel or f"@e[type=tnt,{BOX}]"
    reply = r.cmd(f"execute as {sel} run data get entity @s")
    out = []
    for chunk in reply.split("has the following entity data: ")[1:]:
        p = re.search(r"Pos: \[([^\]]+)\]", chunk)
        m = re.search(r"Motion: \[([^\]]+)\]", chunk)
        f = re.search(r"fuse: (-?\d+)s", chunk)
        if p and f:
            pos = [float(v.rstrip("d")) - O[i] for i, v in enumerate(p.group(1).split(", "))]
            mot = [float(v.rstrip("d")) for v in m.group(1).split(", ")] if m else [0, 0, 0]
            out.append((*pos, int(f.group(1)), *mot))
    return out


def watch(r, ticks, every=4, quiet=False):
    """Poll primed TNT while the game runs; print a line whenever the picture changes."""
    from lab import gametime
    t0 = gametime(r)
    last = None
    seen = collections.Counter()
    while True:
        t = gametime(r) - t0
        if t > ticks:
            break
        cur = tnt(r)
        groups = collections.Counter((round(x), round(y), round(z)) for x, y, z, *_ in cur)
        key = tuple(sorted(groups.items()))
        if key != last and not quiet:
            fuses = [c[3] for c in cur]
            print(f"t={t:5d} n={len(cur):3d} fuse {min(fuses, default=0)}..{max(fuses, default=0)} "
                  + " ".join(f"{k}x{v}" for k, v in sorted(groups.items())[:8]))
            last = key
        for k in groups:
            seen[k] = max(seen[k], groups[k])
        time.sleep(every / 20)
    return seen


def put(r, pos, n, item="wooden_sword"):
    """Put n unstackable items into the container at schematic position pos."""
    x, y, z = w(*pos)
    for i in range(n):
        r.cmd(f"item replace block {x} {y} {z} container.{i} with {item}")


def lever(r, pos, on):
    x, y, z = w(*pos)
    state = r.cmd(f"data get block {x} {y} {z}")
    reg = region()
    b = reg[pos[0], pos[1], pos[2]].to_block_state_identifier()
    b = re.sub(r"powered=\w+", f"powered={'true' if on else 'false'}", b)
    return r.cmd(f"setblock {x} {y} {z} {b}")


def inventory(r, reg=None):
    """Item count of every container (schematic position -> count), read from the server."""
    reg = reg or region()
    out = {}
    lo = min(reg.yrange())
    for t in reg.tile_entities:
        if str(t.data.get("id", "")).split(":")[-1] in ("hopper", "barrel", "chest", "dropper"):
            x, y, z = t.position
            wx, wy, wz = w(x, y + lo, z)
            reply = r.cmd(f"data get block {wx} {wy} {wz} Items")
            out[(x, y + lo, z)] = reply.count("Slot:")
    return out


def diff(a, b):
    return {k: (a.get(k, 0), b.get(k, 0)) for k in sorted(set(a) | set(b)) if a.get(k, 0) != b.get(k, 0)}


ACTIVE = ("redstone_wire", "repeater", "comparator", "observer", "piston", "sticky_piston", "redstone_torch",
          "redstone_wall_torch", "waxed_copper_bulb", "redstone_lamp", "dropper", "hopper", "note_block",
          "activator_rail", "lever", "oak_pressure_plate", "tnt", "piston_head", "slime_block", "honey_block",
          "iron_trapdoor", "dead_tube_coral_wall_fan", "powder_snow")


def components(reg=None):
    reg = reg or region()
    out = {}
    for y in reg.yrange():
        for x in reg.xrange():
            for z in reg.zrange():
                b = reg[x, y, z]
                if b.id.split(":")[1] in ACTIVE:
                    out[(x, y, z)] = b.to_block_state_identifier()
    return out


def snapshot(r, comps):
    """Set of component positions whose block state differs from the saved schematic."""
    off = set()
    for (x, y, z), state in comps.items():
        wx, wy, wz = w(x, y, z)
        if "passed" not in r.cmd(f"execute if block {wx} {wy} {wz} {state}"):
            off.add((x, y, z))
    return off


def trace(r, steps, stride=2, comps=None):
    """Frozen game: step and list which components changed state in each step."""
    from lab import step
    comps = comps or components()
    prev = snapshot(r, comps)
    for i in range(steps):
        step(r, stride)
        cur = snapshot(r, comps)
        ch = sorted(cur ^ prev)
        if ch:
            names = collections.Counter(comps[p].split("[")[0].split(":")[1] for p in ch)
            xs, ys, zs = zip(*ch)
            print(f"+{(i + 1) * stride:4d}: {len(ch):3d} changed x{min(xs)}..{max(xs)} y{min(ys)}..{max(ys)} "
                  f"z{min(zs)}..{max(zs)} {dict(names)}", flush=True)
        n = tnt(r)
        if n:
            print(f"      TNT {len(n)}: " + " ".join(f"({a:.1f},{b:.1f},{c:.1f})f{f}" for a, b, c, f, *_ in n[:6]))
        prev = cur
    return prev
