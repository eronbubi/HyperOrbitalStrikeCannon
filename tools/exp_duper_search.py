"""Search sticky-piston layouts for a working TNT duper on the real server.

100 candidate layouts are built side by side and cycled together. A layout counts as a
duper when the piston cycles keep yielding primed TNT while the TNT block is still there
after the last cycle. Results go to ../out/duper_search.txt.
"""
import itertools
import re
import sys
import time

from lab import ROOT, Rcon, wait_ticks

BASE_X, BASE_Y, BASE_Z = 400, 150, 400
PITCH = 16
PER_ROW = 10
BATCH = 100
CYCLES = 5
SIX = [(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (1, 0, 0), (-1, 0, 0)]
FACING = {(0, 0, -1): "north", (0, 0, 1): "south", (1, 0, 0): "east", (-1, 0, 0): "west"}
PISTON = (0, 0, 0)
VARIANTS = {
    "line": [(1, 0, 0), (2, 0, 0)],
    "stack": [(1, 0, 0), (1, 1, 0)],
    "single": [(1, 0, 0)],
}


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def east(p):
    return add(p, (1, 0, 0))


def candidates():
    for vname, slimes in VARIANTS.items():
        slime_set = set(slimes)
        tnt_spots = sorted({add(s, d) for s in slimes for d in SIX} - slime_set - {PISTON, (-1, 0, 0)})
        for tnt in tnt_spots:
            moving = slime_set | {tnt}
            swept = moving | {east(p) for p in moving} | {PISTON, (-1, 0, 0)}
            near = {add(tnt, d) for d in SIX} | {add(east(tnt), d) for d in SIX}
            # rail options: (rail position, static support or None)
            rails = []
            for m in moving:
                top = add(m, (0, 1, 0))
                if top not in swept or top == east(m):
                    if top not in moving:
                        rails.append((top, None))
            for r in sorted(near - swept):
                below = add(r, (0, -1, 0))
                if below not in swept:
                    rails.append((r, below))
            fans = []
            for f in sorted(near - swept):
                for vec, name in FACING.items():
                    sup = (f[0] - vec[0], f[1], f[2] - vec[2])
                    state = f"dead_tube_coral_wall_fan[facing={name},waterlogged=false]"
                    if sup in moving:
                        fans.append((f, state, None))
                    elif sup not in swept:
                        fans.append((f, state, sup))
                below = add(f, (0, -1, 0))
                state = "dead_tube_coral_fan[waterlogged=false]"
                if below in moving:
                    fans.append((f, state, None))
                elif below not in swept:
                    fans.append((f, state, below))
            for (rail, rsup), (fan, fstate, fsup) in itertools.product(rails, fans):
                statics = {p for p in (rsup, fsup) if p}
                if rail == fan or rail in statics or fan in statics:
                    continue
                yield {"variant": vname, "slimes": slimes, "tnt": tnt, "rail": rail, "rail_support": rsup,
                       "fan": fan, "fan_state": fstate, "fan_support": fsup}


def cell_origin(i):
    return (BASE_X + (i % PER_ROW) * PITCH, BASE_Y, BASE_Z + (i // PER_ROW) * PITCH)


def at(origin, p):
    return f"{origin[0] + p[0]} {origin[1] + p[1]} {origin[2] + p[2]}"


def box(origin):
    return f"x={origin[0] - 5},y={origin[1] - 60},z={origin[2] - 5},dx=13,dy=70,dz=10"


def run_batch(r, batch):
    cells = [(cell_origin(i), c) for i, c in enumerate(batch)]
    r.cmd("kill @e[type=!player]")
    for o, c in cells:
        r.cmd(f"fill {o[0] - 5} {o[1] - 4} {o[2] - 5} {o[0] + 8} {o[1] + 5} {o[2] + 5} air")
    for o, c in cells:
        r.cmd(f"setblock {at(o, PISTON)} sticky_piston[facing=east]")
        for s in c["slimes"]:
            r.cmd(f"setblock {at(o, s)} slime_block")
        for sup in (c["rail_support"], c["fan_support"]):
            if sup:
                r.cmd(f"setblock {at(o, sup)} obsidian")
        r.cmd(f"setblock {at(o, c['tnt'])} tnt")
        r.cmd(f"setblock {at(o, c['fan'])} {c['fan_state']}")
        r.cmd(f"setblock {at(o, c['rail'])} detector_rail")
        rx, ry, rz = c["rail"]
        r.cmd(f"summon minecart {o[0] + rx + 0.5} {o[1] + ry + 0.1} {o[2] + rz + 0.5}")
    wait_ticks(r, 8)
    r.cmd("kill @e[type=tnt]")
    for o, c in cells:
        if "passed" not in r.cmd(f"execute if block {at(o, c['tnt'])} tnt"):
            r.cmd(f"setblock {at(o, c['tnt'])} tnt")
    wait_ticks(r, 4)
    r.cmd("kill @e[type=tnt]")
    yields = [[] for _ in cells]
    for _ in range(CYCLES):
        for o, c in cells:
            r.cmd(f"setblock {at(o, (-1, 0, 0))} redstone_block")
        wait_ticks(r, 7)
        for o, c in cells:
            r.cmd(f"setblock {at(o, (-1, 0, 0))} air")
        wait_ticks(r, 7)
        for k, (o, c) in enumerate(cells):
            m = re.search(r"Count: (\d+)", r.cmd(f"execute if entity @e[type=tnt,{box(o)}]"))
            yields[k].append(int(m.group(1)) if m else 0)
        r.cmd("kill @e[type=tnt]")
    out = []
    for k, (o, c) in enumerate(cells):
        tnt_ok = "passed" in r.cmd(f"execute if block {at(o, c['tnt'])} tnt")
        fan_ok = "passed" in r.cmd(f"execute if block {at(o, c['fan'])} {c['fan_state'].split('[')[0]}")
        out.append((c, yields[k], tnt_ok, fan_ok))
    return out


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    cands = list(candidates())[:limit]
    log = open(ROOT / "out" / "duper_search.txt", "w", encoding="utf-8")
    print(len(cands), "candidates", file=log, flush=True)
    with Rcon(timeout=300) as r:
        r.cmd("tick unfreeze")
        r.cmd("forceload remove all")
        r.cmd(f"forceload add {BASE_X - 16} {BASE_Z - 16} {BASE_X + PER_ROW * PITCH + 16} {BASE_Z + PER_ROW * PITCH + 16}")
        t0 = time.time()
        hits = 0
        for start in range(0, len(cands), BATCH):
            for c, ys, tnt_ok, fan_ok in run_batch(r, cands[start:start + BATCH]):
                if sum(ys) == 0:
                    continue
                grade = "DUPER" if tnt_ok and sum(1 for y in ys if y) >= CYCLES - 1 else "partial"
                hits += grade == "DUPER"
                print(grade, "fan_ok" if fan_ok else "fan_lost", ys, c, file=log, flush=True)
            print(f"# {start + BATCH}/{len(cands)} {time.time() - t0:.0f}s dupers={hits}", file=log, flush=True)
        r.cmd("kill @e[type=!player]")
    print("done", file=log, flush=True)
