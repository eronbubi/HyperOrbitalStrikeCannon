"""Stage 2: the complete cannon with its real portal stations in both dimensions.

Nothing is force-loaded near the cannon while it runs; the script only flips the lever
and watches. One far chunk stays force-loaded to stand in for a player being online.

Usage: python exp_shot2.py [--keep] W,NW,SW [W,NW,SW ...]
"""
import re

import aim
import time
import sys

from cannon import CELL, D, LEVER, N1, N3, Y0, nether, overworld
from exp_shot import PUSH, at, cell_tnt, set_counter, value
from lab import Rcon, gametime, get, wait_ticks

NETHER = "execute in minecraft:the_nether run "


def build(r, b, info, nb, ninfo):
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all"); r.cmd(NETHER + "forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd("forceload add 0 -16 79 47")
    r.cmd(NETHER + "forceload add -16 -16 31 31")
    wait_ticks(r, 5)
    for y in range(52, 142):  # also wipes stations and portals of earlier experiments
        r.cmd(f"fill 4 {y} -8 79 {y} 50 air")
    r.cmd("kill @e[type=!player]")
    for n in (N1, N3):  # sealed rooms: nether lava or gravel would break the redstone
        r.cmd(NETHER + f"fill {n[0] - 9} {n[1] - 6} {n[2] - 9} {n[0] + 9} {n[1] + 9} {n[2] + 9} obsidian hollow")
        r.cmd(NETHER + f"fill {n[0] - 8} {n[1] - 5} {n[2] - 8} {n[0] + 8} {n[1] + 8} {n[2] + 8} air")
    for y in (56, 64, 96, 104):  # old test stations in the nether
        r.cmd(NETHER + f"fill -6 {y} -6 14 {y + 8} 12 netherrack")
    for n in (N1, N3):
        r.cmd(NETHER + f"fill {n[0] - 8} {n[1] - 5} {n[2] - 8} {n[0] + 8} {n[1] + 8} {n[2] + 8} air")
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
    r.cmd("forceload remove 0 -16 79 47")
    r.cmd(NETHER + "forceload remove all")
    r.cmd("tick rate 1250")
    wait_ticks(r, 400)  # all temporary tickets gone: from here on only the portal loop holds the chunks
    r.cmd("tick rate 20")


def chunk_state(r, cx, cz):
    tag = f"probe{cx}_{cz}".replace("-", "m")
    reply = r.cmd(f'summon tnt {cx * 16 + 2} 150 {cz * 16 + 2} {{fuse:30000,NoGravity:1b,Tags:["probe","{tag}"]}}')
    if "Summoned" not in reply:
        return "unloaded"
    wait_ticks(r, 2)
    a = get(r, f"@e[tag={tag},limit=1]", "fuse")
    wait_ticks(r, 6)
    b = get(r, f"@e[tag={tag},limit=1]", "fuse")
    r.cmd(f"kill @e[tag={tag}]")
    return "TICK" if a and b and b[0] < a[0] else "lazy"


def shot(r, info, n):
    n = dict(n)
    n["timer"] = max(n.values()) + 15
    r.cmd("tick rate 100")  # buttons: the script cannot time presses any faster than this
    for name in ("w", "nw", "sw", "timer"):
        set_counter(r, info[f"counter_{name}"], n[name])
    wait_ticks(r, 40)
    r.cmd("tick rate 20")
    shown = {name: value(r, info[f"counter_{name}"]) for name in n}
    print("  counters:", shown, "ok" if shown == n else f"WANTED {n}")
    dx, dz = aim.displacement(n)  # the calibrated model, so the prediction is the calculator's
    tx, tz = CELL[0] + 0.49 + dx, CELL[2] + 0.49 + dz
    cx, cz = int(tx // 16) * 16, int(tz // 16) * 16
    box = f"x={cx - 96},y=-400,z={cz - 96},dx=208,dy=800,dz=208"
    r.cmd(f"forceload add {cx - 96} {cz - 96} {cx + 111} {cz + 111}")
    wait_ticks(r, 60)  # the chunks need a moment before parked entities show up
    r.cmd(f"kill @e[type=tnt,{box}]")  # payloads parked there by earlier tests
    wait_ticks(r, 20)
    r.cmd(f"kill @e[type=tnt,{box}]")
    # the target stays unloaded during the shot: the payload then waits in the air where it
    # arrived, so the game can run far faster than this script could watch it
    r.cmd(f"forceload remove {cx - 96} {cz - 96} {cx + 111} {cz + 111}")
    wait_ticks(r, 20)
    lx, ly, lz = LEVER
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=true]")
    t0 = gametime(r)
    r.cmd("tick rate 1250")
    deadline = t0 + 2600 + n["timer"] * 8 + 2000
    wait_ticks(r, 2200)
    while gametime(r) < deadline and value(r, info["counter_timer"]) > 0:
        time.sleep(0.2)
    done = gametime(r)
    wait_ticks(r, 400)
    r.cmd("tick rate 20")
    r.cmd(f"forceload add {cx - 96} {cz - 96} {cx + 111} {cz + 111}")
    result = None
    for _ in range(60):
        reply = r.cmd(f"execute as @e[type=tnt,{box}] run data get entity @s Pos")
        pos = [tuple(float(v) for v in q) for q in re.findall(r"\[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]", reply)]
        if pos:
            result = pos
            break
        wait_ticks(r, 1)
    print(f"  timer reached zero {done - t0} gt after the lever")
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
    if result is None:
        print("  no payload seen at the target")
        r.cmd("tick rate 1250")
        wait_ticks(r, 2300)
        r.cmd("tick rate 20")
        return None
    px = sum(p[0] for p in result) / len(result)
    pz = sum(p[2] for p in result) / len(result)
    print(f"  arrived: {len(result)} TNT at x {px:.3f} z {pz:.3f}; predicted {tx:.3f} {tz:.3f}; miss {px - tx:+.3f} {pz - tz:+.3f}; "
          f"read {gametime(r) - t0} gt after the lever")
    wait_ticks(r, 120)
    r.cmd("kill @e[type=tnt]")
    r.cmd(f"forceload remove {cx - 96} {cz - 96} {cx + 111} {cz + 111}")
    # the lever-off has to run through the delay snake and the main line (about 2000 gt)
    # before the counter clocks are held again; buttons pressed earlier are counted away at once
    r.cmd("tick rate 1250")
    wait_ticks(r, 2300)
    r.cmd("tick rate 20")
    return (px, pz)


if __name__ == "__main__":
    args = sys.argv[1:]
    shots = [dict(zip(("w", "nw", "sw"), map(int, a.split(",")))) for a in args if "," in a] or [{"w": 100, "nw": 60, "sw": 0}]
    with Rcon(timeout=900) as r:
        b, info = overworld()
        nb, ninfo = nether()
        if "--keep" not in args:
            build(r, b, info, nb, ninfo)
        print("chunks before the shot: payload (0,0)", chunk_state(r, 0, 0), "| propellant (1,0)", chunk_state(r, 1, 0),
              "| deck east (4,0)", chunk_state(r, 4, 0), "| loader (2,1)", chunk_state(r, 2, 1))
        for n in shots:
            print("shot", n)
            shot(r, info, n)
        print("chunks after: payload (0,0)", chunk_state(r, 0, 0), "| propellant (1,0)", chunk_state(r, 1, 0))
        print("trigger dropper:", r.cmd(f"data get block {at(info['o3_send'])} Items")[-70:])
