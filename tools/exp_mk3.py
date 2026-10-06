"""MK.3: the complete cannon with its three real portal stations, nothing force-loaded near it.

Usage: python exp_mk3.py [--keep] [--turn=N] trace [E,NE,SE]      tick-by-tick log, departure delay skipped
       python exp_mk3.py [--keep] [--turn=N] [--rate=R] E,NE,SE [E,NE,SE ...]   full shots from the lever
"""
import math
import re
import sys
import time

import aim3
from cannon3 import nether_turned, overworld_turned
from exp_mk2 import NETHER, lit, ring_centre, tnt_in
from exp_shot import at, set_counter, value
from lab import Rcon, gametime, step, wait_ticks

GROUPS = ("e", "ne", "se")
RATE = 300  # tick rate while a shot charges; unthrottled 1250 wrecked MK.2 shots now and then


def build(r, b, info, nb, rooms):
    x0, z0, x1, z1 = -100, -100, 100, 100
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all"); r.cmd(NETHER + "forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd(f"forceload add {x0} {z0} {x1} {z1}")
    r.cmd(NETHER + "forceload add -32 -32 47 47")
    wait_ticks(r, 5)
    for y in range(52, 142):  # also wipes stations and portals of earlier experiments
        r.cmd(f"fill -100 {y} -100 0 {y} 0 air"); r.cmd(f"fill 1 {y} -100 100 {y} 0 air")
        r.cmd(f"fill -100 {y} 1 0 {y} 100 air"); r.cmd(f"fill 1 {y} 1 100 {y} 100 air")
    r.cmd("kill @e[type=!player]")
    for y in range(56, 120, 8):  # old test stations in the nether
        r.cmd(NETHER + f"fill -24 {y} -24 24 {y + 7} 24 netherrack")
    for n in rooms:  # sealed rooms: nether lava or gravel would break the redstone
        r.cmd(NETHER + f"fill {n[0] - 7} {n[1] - 3} {n[2] - 7} {n[0] + 7} {n[1] + 6} {n[2] + 7} obsidian hollow")
    bad = [c for c in b.to_commands() if "Changed" not in r.cmd(c)]
    bad += [c for c in nb.to_commands() if "Changed" not in r.cmd(NETHER + c)]
    print("blocks:", len(b.blocks), "+", len(nb.blocks), "paste errors:", len(bad), bad[:3])
    for name in info["dupers"]:
        rail = info[f"duper_{name}"]["rail"]
        r.cmd(f"summon minecart {rail[0] + 0.5} {rail[1] + 0.1} {rail[2] + 0.5}")
    wait_ticks(r, 20)
    for name in info["dupers"]:
        r.cmd(f"setblock {at(info[f'duper_{name}']['prime'])} tnt")
    r.cmd(f'data merge block {at(info["o1_send"])} {{Items:[{{Slot:0b,id:"minecraft:cobblestone",count:2}}]}}')
    for key in ("oa_send", "ob_send"):
        r.cmd(f'data merge block {at(info[key])} {{Items:[{{Slot:0b,id:"minecraft:redstone",count:4}}]}}')
    wait_ticks(r, 80)
    print("TNT lit by placing it:", r.cmd("execute if entity @e[type=tnt]"))
    r.cmd(f"forceload remove {x0} {z0} {x1} {z1}")
    r.cmd(NETHER + "forceload remove all")
    r.cmd("tick rate 1250")
    wait_ticks(r, 400)  # all temporary tickets gone: from here on only the portal loop holds the chunks
    r.cmd("tick rate 20")


def enter(r, info, n):
    r.cmd("tick rate 100")  # buttons: the script cannot time presses any faster than this
    for g in GROUPS:
        set_counter(r, info[f"counter_{g}"], n[g])
    wait_ticks(r, 40)
    r.cmd("tick rate 20")
    shown = {g: value(r, info[f"counter_{g}"]) for g in GROUPS}
    print("  counters:", shown, "ok" if shown == n else f"WANTED {n}")


def box(p, r=1):
    return f"x={p[0] - r},y={p[1] - 0.5},z={p[2] - r},dx={2 * r},dy=1.5,dz={2 * r}"


def summary(tnt, ref):
    if not tnt:
        return "0"
    pts = [(p[0], p[2]) for p, _ in tnt]
    mx, mz = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    rr = [math.hypot(p[0] - mx, p[1] - mz) for p in pts]
    return (f"{len(tnt)} at {mx - ref[0] - 0.5:+.3f} {mz - ref[2] - 0.5:+.3f} y {tnt[0][0][1]:.2f} "
            f"radius {min(rr):.4f}..{max(rr):.4f} fuses {sorted({f for _, f in tnt})}")


def trace(r, info, n):
    """Starts the main line directly and logs every tick until the shot."""
    enter(r, info, n)
    cell, stack = info["cell"], info["stack"]
    r.cmd("tick freeze"); time.sleep(0.3)
    probes = {"stack_chunk": (stack[0] // 16 * 16 + 2, 150, stack[2] // 16 * 16 + 2),
              "flight_chunk": (cell[0] // 16 * 16 + 2, 150, cell[2] // 16 * 16 + 2)}
    for name, p in probes.items():
        r.cmd(f'summon tnt {p[0]} {p[1]} {p[2]} {{fuse:30000,NoGravity:1b,Tags:["probe","{name}"]}}')
    step(r, 2)
    r.cmd(f"setblock {at(info['line'])} redstone_block")
    last, state, released = {}, {}, 0
    for t in range(1, 3000):
        step(r, 1)
        row = {}
        for name in probes:
            f = re.search(r"data: (\d+)s", r.cmd(f"data get entity @e[tag={name},limit=1] fuse"))
            f = int(f.group(1)) if f else None
            row[name] = last.get(name) is not None and f is not None and f < last[name]
            last[name] = f
        for name, p in info["probe"].items():
            row[name] = not lit(r, p, "redstone_wire[power=0]")
        row["release"] = not lit(r, info["gate"], "redstone_wire[power=0]")
        if t < 700 or t % 20 == 0 or released:
            a = [e for e in tnt_in(r, box(stack)) if int(e[0][0] // 1) == stack[0] and int(e[0][2] // 1) == stack[2]]
            c = [e for e in tnt_in(r, box(cell)) if not (int(e[0][0] // 1) == stack[0] and int(e[0][2] // 1) == stack[2])]
            row["stack"] = len(a) if len(a) != state.get("stack") and len(a) % 16 and 0 < len(a) < 64 else summary(a, stack)
            if isinstance(row["stack"], int):
                row["stack"] = state.get("stack")
            row["flight"] = summary(c, cell)
        for k, v in row.items():
            if state.get(k) != v:
                print(f"  t{t:5d} {k} -> {v}")
                state[k] = v
        if row["release"] and t > 500:
            released = released or t
            if t > released + 60:
                break
    far = tnt_in(r, "x=-400,y=-100,z=-200,dx=440,dy=400,dz=400")
    print("  TNT west of the cannon after the release:", summary([e for e in far if e[0][0] < cell[0] - 3], cell))
    print("  counters:", {g: value(r, info[f"counter_{g}"]) for g in GROUPS})
    r.cmd(f"setblock {at(info['line'])} air")
    r.cmd("kill @e[tag=probe]")
    r.cmd("tick unfreeze")


def shot(r, info, n, turns=0):
    enter(r, info, n)
    cell = info["cell"]
    dx, dz = aim3.displacement(n)
    for _ in range(turns % 4):
        dx, dz = -dz, dx
    tx, tz = cell[0] + 0.5 + dx, cell[2] + 0.5 + dz
    cx, cz = int(tx // 16) * 16, int(tz // 16) * 16
    half = 112  # 15 x 15 chunks: forceload takes at most 256 at a time
    area = f"{cx - half} {cz - half} {cx + half} {cz + half}"
    sel = f"x={cx - half},y=-400,z={cz - half},dx={2 * half},dy=900,dz={2 * half}"
    r.cmd(f"forceload add {area}")
    wait_ticks(r, 60)
    r.cmd(f"kill @e[type=tnt,{sel}]")  # payloads parked there by earlier tests
    wait_ticks(r, 20)
    r.cmd(f"forceload remove {area}")
    wait_ticks(r, 20)
    r.cmd(f"setblock {at(info['lever'])} lever[face=floor,facing=north,powered=true]")
    t0 = gametime(r)
    r.cmd(f"tick rate {RATE}")
    deadline = t0 + 2600 + max(n.values()) * 8 + 3000
    wait_ticks(r, 2300)
    print("  loaded during the shot:", r.cmd(f"execute if block {at(cell)} powder_snow"))
    while gametime(r) < deadline and lit(r, info["gate"], "redstone_wire[power=0]"):
        time.sleep(0.2)
    done = gametime(r)
    wait_ticks(r, 400)
    r.cmd("tick rate 20")
    print(f"  release {done - t0} gt after the lever; counters now", {g: value(r, info[f"counter_{g}"]) for g in GROUPS})
    print("  ", r.cmd(f"forceload add {area}")[:60])
    got = []
    for _ in range(60):
        got = tnt_in(r, sel)
        if got:
            wait_ticks(r, 3)  # a ring across a chunk border loads in two parts
            got = tnt_in(r, sel)
            break
        wait_ticks(r, 1)
    r.cmd(f"setblock {at(info['lever'])} lever[face=floor,facing=north,powered=false]")
    if not got:
        print("  no payload seen at the target; predicted", round(tx, 1), round(tz, 1))
        print("  all TNT:", [tuple(round(c, 1) for c in p) + (f,) for p, f in tnt_in(r, "x=-30000,y=-500,z=-30000,dx=60000,dy=1000,dz=60000")][:12])
        print("  cell:", r.cmd(f"execute if block {at(cell)} powder_snow"))
    else:
        (ex, ez), _ = ring_centre([(p[0], p[2]) for p, _ in got])
        rr = sorted(math.hypot(p[0] - ex, p[2] - ez) for p, _ in got)
        print(f"  arrived: {len(got)} TNT, fuses {sorted({f for _, f in got})}, y {got[0][0][1]:.1f}")
        print(f"  ring centre {ex:.3f} {ez:.3f}; predicted {tx:.3f} {tz:.3f}; miss {ex - tx:+.3f} {ez - tz:+.3f}; "
              f"radius {rr[0]:.2f}..{rr[-1]:.2f}")
    wait_ticks(r, 120)
    r.cmd(f"kill @e[type=tnt,{sel}]")
    r.cmd(f"forceload remove {area}")
    r.cmd(f"tick rate {RATE}")  # the lever-off has to run through the delay snake and the main line
    wait_ticks(r, 2600)
    r.cmd("tick rate 20")
    return got


if __name__ == "__main__":
    args = sys.argv[1:]
    shots = [dict(zip(GROUPS, map(int, a.split(",")))) for a in args if "," in a] or [{"e": 20, "ne": 20, "se": 20}]
    for a in args:
        if a.startswith("--rate="):
            RATE = int(a[7:])
    turns = next((int(a[7:]) for a in args if a.startswith("--turn=")), 0)
    with Rcon(timeout=900) as r:
        b, info = overworld_turned(turns)
        nb, ninfo = nether_turned(turns)
        if "--keep" not in args:
            build(r, b, info, nb, list(ninfo.values()))
        if "trace" in args:
            trace(r, info, shots[0])
        else:
            for n in shots:
                print("shot", n)
                shot(r, info, n, turns=turns)
        for key in ("oa_send", "ob_send"):
            print(key, r.cmd(f"data get block {at(info[key])} Items")[-60:])
