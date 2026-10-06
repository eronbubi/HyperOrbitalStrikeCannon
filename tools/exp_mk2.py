"""MK.2: the complete cannon with its real portal stations, nothing force-loaded near it.

Usage: python exp_mk2.py [--keep] trace [E,NE,SE]      tick-by-tick log of one sequence, departure delay skipped
       python exp_mk2.py [--keep] [--noring] E,NE,SE [E,NE,SE ...]   full shots from the lever
"""
import math

import aim2
import re
import sys
import time

from cannon2 import CELL, D, LINE, N1, N3, Y0, nether, nether_turned, overworld, overworld_turned, turn_point
from exp_shot import at, set_counter, value
from lab import Rcon, gametime, step, wait_ticks

NETHER = "execute in minecraft:the_nether run "
POS = re.compile(r"Pos: \[(-?[\d.eE-]+)d, (-?[\d.eE-]+)d, (-?[\d.eE-]+)d\]")
FUSE = re.compile(r"fuse: (\d+)s")
GROUPS = ("e", "ne", "se")
RATE = 1250  # tick rate while a shot charges
# blocks per propellant TNT (x, z), first estimate from the summoned-propellant shots
PUSH = {"e": (-0.45, 0.0), "ne": (-0.30, 0.30), "se": (-0.30, -0.30)}


def build(r, b, info, nb, rooms=(N1, N3)):
    x0, z0, x1, z1 = -100, -100, 100, 100  # 13 x 13 chunks: everything a cannon of any orientation touches
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all"); r.cmd(NETHER + "forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd(f"forceload add {x0} {z0} {x1} {z1}")
    r.cmd(NETHER + "forceload add -32 -32 47 47")
    wait_ticks(r, 5)
    for y in range(52, 142):  # also wipes stations and portals of earlier experiments
        r.cmd(f"fill -100 {y} -100 0 {y} 0 air"); r.cmd(f"fill 1 {y} -100 100 {y} 0 air")
        r.cmd(f"fill -100 {y} 1 0 {y} 100 air"); r.cmd(f"fill 1 {y} 1 100 {y} 100 air")
    r.cmd("kill @e[type=!player]")
    for y in range(56, 112, 8):  # old test stations in the nether
        r.cmd(NETHER + f"fill -20 {y} -20 20 {y + 7} 20 netherrack")
    for n in rooms:  # sealed rooms: nether lava or gravel would break the redstone
        r.cmd(NETHER + f"fill {n[0] - 7} {n[1] - 4} {n[2] - 7} {n[0] + 7} {n[1] + 7} {n[2] + 7} obsidian hollow")
    for n in rooms:
        r.cmd(NETHER + f"fill {n[0] - 6} {n[1] - 3} {n[2] - 6} {n[0] + 6} {n[1] + 6} {n[2] + 6} air")
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
    r.cmd(f'data merge block {at(info["o3_send"])} {{Items:[{{Slot:0b,id:"minecraft:redstone",count:4}}]}}')
    wait_ticks(r, 80)
    print("TNT lit by placing it:", r.cmd("execute if entity @e[type=tnt]"))
    r.cmd(f"forceload remove {x0} {z0} {x1} {z1}")
    r.cmd(NETHER + "forceload remove all")
    r.cmd("tick rate 1250")
    wait_ticks(r, 400)  # all temporary tickets gone: from here on only the portal loop holds the chunks
    r.cmd("tick rate 20")


def tnt_in(r, box):
    reply = r.cmd(f"execute as @e[type=tnt,{box}] run data get entity @s")
    out = []
    for chunk in reply.split("has the following entity data: ")[1:]:
        p, f = POS.search(chunk), FUSE.search(chunk)
        if p and f:
            out.append((tuple(map(float, p.groups())), int(f.group(1))))
    return out


def lit(r, pos, state):
    return "passed" in r.cmd(f"execute if block {at(pos)} {state}")


def enter(r, info, n):
    r.cmd("tick rate 100")  # buttons: the script cannot time presses any faster than this
    for g in GROUPS:
        set_counter(r, info[f"counter_{g}"], n[g])
    wait_ticks(r, 40)
    r.cmd("tick rate 20")
    shown = {g: value(r, info[f"counter_{g}"]) for g in GROUPS}
    print("  counters:", shown, "ok" if shown == n else f"WANTED {n}")


def trace(r, info, n, b):
    """Starts the main line directly and logs every tick until the shot."""
    enter(r, info, n)
    cx, cy, cz = CELL
    cell = f"x={cx - 1},y={cy - 0.5},z={cz - 1},dx=2,dy=1.5,dz=2"
    charge = f"x={cx - 1},y={cy - 3},z={cz - 1},dx=2,dy=1.4,dz=2"
    r.cmd("tick freeze"); time.sleep(0.3)
    r.cmd('summon tnt 2 150 2 {fuse:30000,NoGravity:1b,Tags:["probe"]}')
    step(r, 2)
    start = (LINE[0] + 1, D, LINE[2] - 1)
    r.cmd(f"setblock {at(start)} redstone_block")
    probe_last, events, state = None, [], {}
    pistons = {f"duper_{g}": (info[f"duper_{g}"]["power"][0] - 1,) + info[f"duper_{g}"]["power"][1:] for g in GROUPS}
    pistons.update({f"pusher_{g}": info[f"duper_{g}"]["pusher"] for g in GROUPS})
    watch = {"dropper": info["o3_send"], "torch": (28, D, -8)}
    edges = {k: [] for k in pistons}
    released = 0
    cells = {info[f"prop_{g}"] for g in GROUPS}
    ledges = {info[f"duper_{g}"]["ledge"] for g in GROUPS}
    columns = {(p[0], p[2]) for p in ledges}
    for t in range(1, 2600):
        step(r, 1)
        probe = re.search(r"data: (\d+)s", r.cmd("data get entity @e[tag=probe,limit=1] fuse"))
        probe = int(probe.group(1)) if probe else None
        ticking = probe_last is not None and probe is not None and probe < probe_last
        probe_last = probe
        row = {"tick": ticking, "cell": len(tnt_in(r, cell)) if t < 520 or t % 8 == 0 else state.get("cell"),
               "charge": len(tnt_in(r, charge)) if t < 520 else 0,
               "enable": lit(r, (28, D, -2), "redstone_wire[power=0]") is False,
               "late": lit(r, (20, D, 18), "redstone_wire[power=0]") is False,
               "heard": lit(r, (21, D, 14), "redstone_wire[power=0]") is False,
               "boom": len(tnt_in(r, "x=16,y=83,z=3,dx=5,dy=2,dz=10")) if t > 380 else 0,
               "busy": lit(r, (19, D, 16), "redstone_wire[power=0]") is False,
               "release": lit(r, (18, D, 18), "redstone_wire[power=0]") is False,
               "sent": "redstone" not in r.cmd(f"data get block {at(watch['dropper'])} Items")}
        if row["enable"] and len(edges["duper_e"]) < 6:
            for k, p in pistons.items():
                ext = lit(r, p, "sticky_piston[extended=true]")
                if ext and not state.get(k):
                    edges[k].append(t)
                state[k] = ext
        for k, v in row.items():
            if state.get(k) != v:
                events.append((t, k, v))
                print(f"  t{t:5d} {k} -> {v}")
                state[k] = v
        if t > 400 and (t % 40 == 0 or released and t < released + 80):  # where is the propellant?
            zones = {}
            for p, f in tnt_in(r, "x=-80,y=-60,z=-40,dx=120,dy=200,dz=100"):
                bx, by, bz = int(p[0] // 1), int(p[1] // 1), int(p[2] // 1)
                if (bx, by, bz) == CELL or (bx, bz) == (CELL[0] + 1, CELL[2]) and by == Y0:
                    key = "payload"
                elif (bx, by, bz) in cells:
                    key = "cell"
                elif (bx, by, bz) in ledges:
                    key = "ledge"
                elif (bx, bz) in columns and Y0 < by < Y0 + 8 or by in (Y0 + 5, Y0 + 6) and (bx - 1, bz) in columns:
                    key = "column"
                else:
                    key = f"{bx},{by},{bz}"
                zones[key] = zones.get(key, 0) + 1
            print(f"  t{t:5d} tnt {zones}")
        if row["release"] and t > 400:
            released = released or t
            if t > released + 380:
                break
    print("  piston strokes (first ticks seen extended):", {k: v[:4] for k, v in edges.items()})
    fuses = sorted(f for _, f in tnt_in(r, cell))
    print("  payload left in the cell after the release:", len(fuses), fuses)
    print("  counters:", {g: value(r, info[f"counter_{g}"]) for g in GROUPS})
    gone = [(p, n) for p, (n, _) in b.blocks.items() if "passed" not in r.cmd(f"execute if block {at(p)} {n}")]
    print("  blocks missing:", len(gone), gone[:12])
    r.cmd(f"setblock {at(start)} air")
    r.cmd("kill @e[tag=probe]")
    r.cmd("tick unfreeze")


def ring_centre(points):
    """Centre of the ellipse through the landing points (the payload starts on a circle, and
    the shot maps it linearly). The plain mean is off by up to a fifth of the ring radius."""
    import numpy as np
    p = np.array(points)
    m = p.mean(axis=0)
    q = (p - m) / max(1e-9, np.abs(p - m).max())
    x, z = q[:, 0], q[:, 1]
    _, sv, vt = np.linalg.svd(np.column_stack([x * x, x * z, z * z, x, z, np.ones(len(x))]))
    a, b, c, d, e, _ = vt[-1]
    det = 4 * a * c - b * b
    if abs(det) < 1e-9 or sv[-2] < 1e-6:
        return tuple(m), None
    cx, cz = (b * e - 2 * c * d) / det, (b * d - 2 * a * e) / det
    scale = np.abs(p - m).max()
    return (m[0] + cx * scale, m[1] + cz * scale), float(sv[-1])


def predicted(n, cell=CELL, turns=0):
    lx, lz = aim2.landing(n)  # the calculator's own model, so the prediction is the calculator's
    dx, dz = lx - aim2.CELL[0], lz - aim2.CELL[1]
    for _ in range(turns % 4):
        dx, dz = -dz, dx
    return cell[0] + 0.5 + dx, cell[2] + 0.5 + dz


def shot(r, info, n, ring=True, turns=0):
    enter(r, info, n)
    cell = info["cell"]
    gate = turn_point((18, D, 18), turns)  # the release wire
    tx, tz = predicted(n, cell, turns)
    cx, cz = int(tx // 16) * 16, int(tz // 16) * 16
    half = 112  # 15 x 15 chunks: forceload takes at most 256 at a time
    box = f"x={cx - half},y=-400,z={cz - half},dx={2 * half},dy=900,dz={2 * half}"
    area = f"{cx - half} {cz - half} {cx + half} {cz + half}"
    r.cmd(f"forceload add {area}")
    wait_ticks(r, 60)
    r.cmd(f"kill @e[type=tnt,{box}]")  # payloads parked there by earlier tests
    wait_ticks(r, 20)
    r.cmd(f"forceload remove {area}")
    wait_ticks(r, 20)
    nx, ny, nz = info["no_ring_lever"]
    r.cmd(f"setblock {nx} {ny} {nz} lever[face=floor,facing=north,powered={'false' if ring else 'true'}]")
    lx, ly, lz = info["lever"]
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=true]")
    t0 = gametime(r)
    r.cmd(f"tick rate {RATE}")
    deadline = t0 + 2600 + max(n.values()) * 8 + 3000
    wait_ticks(r, 2300)
    print("  loaded during the shot:", r.cmd(f"execute if block {at(cell)} powder_snow"))
    while gametime(r) < deadline and not lit(r, gate, "redstone_wire[power=0]") is False:
        time.sleep(0.2)
    done = gametime(r)
    wait_ticks(r, 400)
    r.cmd("tick rate 20")
    print(f"  release {done - t0} gt after the lever; counters now", {g: value(r, info[f"counter_{g}"]) for g in GROUPS})
    print("  ", r.cmd(f"forceload add {area}")[:60])
    got = []
    for _ in range(60):
        got = tnt_in(r, box)
        if got:
            break
        wait_ticks(r, 1)
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
    if not got:
        print("  no payload seen at the target; predicted", round(tx, 1), round(tz, 1))
        print("  all TNT:", [tuple(round(c, 1) for c in p) + (f,) for p, f in tnt_in(r, "x=-30000,y=-500,z=-30000,dx=60000,dy=1000,dz=60000")][:20])
        cx0, cy0, cz0 = cell
        print("  cell:", r.cmd(f"execute if block {cx0} {cy0} {cz0} powder_snow"), "| dispenser:", r.cmd(f"data get block {cx0} {cy0 + 1} {cz0} Items")[-60:])
    else:
        px = sum(p[0] for p, _ in got) / len(got)
        pz = sum(p[2] for p, _ in got) / len(got)
        rr = sorted(math.hypot(p[0] - px, p[2] - pz) for p, _ in got)
        print(f"  arrived: {len(got)} TNT, centre x {px:.3f} z {pz:.3f} y {got[0][0][1]:.1f}; predicted {tx:.3f} {tz:.3f}; "
              f"moved {px - cell[0] - 0.5:+.3f} {pz - cell[2] - 0.5:+.3f}")
        (ex, ez), res = ring_centre([(p[0], p[2]) for p, _ in got])
        print(f"  ellipse centre: {ex:.3f} {ez:.3f}; miss {ex - tx:+.3f} {ez - tz:+.3f}; moved {ex - cell[0] - 0.5:+.3f} {ez - cell[2] - 0.5:+.3f}")
        print(f"  ring radius min/mean/max {rr[0]:.2f} / {sum(rr) / len(rr):.2f} / {rr[-1]:.2f}; fuses {sorted(f for _, f in got)}")
    wait_ticks(r, 120)
    r.cmd(f"kill @e[type=tnt,{box}]")
    r.cmd(f"forceload remove {area}")
    r.cmd("tick rate 1250")  # the lever-off has to run through the delay snake and the main line
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
            build(r, b, info, nb, (ninfo["n1"], ninfo["n3"]))
        if "trace" in args:
            trace(r, info, shots[0], b)
        else:
            for n in shots:
                print("shot", n)
                shot(r, info, n, ring="--noring" not in args, turns=turns)
        print("trigger dropper:", r.cmd(f"data get block {at(info['o3_send'])} Items")[-70:])
