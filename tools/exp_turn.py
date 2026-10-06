"""Complete cannon, turned by 90 degree steps, with real portal stations: one shot per direction.

Usage: python exp_turn.py TURNS [W,NW,SW]     TURNS 0 = west, 1 = north, 2 = east, 3 = south
"""
import re
import time
import sys

from cannon import DIRECTION, Y0, nether_turned, overworld_turned
from exp_shot import PUSH, at, set_counter, value
from lab import Rcon, gametime, get, wait_ticks

NETHER = "execute in minecraft:the_nether run "


def turn_xy(px, pz, turns):
    for _ in range(turns % 4):
        px, pz = -pz, px
    return px, pz


def cell_tnt(r, cell):
    reply = r.cmd(f"execute as @e[type=tnt,x={cell[0]},y={Y0 - 0.5},z={cell[2]},dx=0,dy=1.5,dz=0] run data get entity @s fuse")
    return [int(v) for v in re.findall(r"data: (\d+)s", reply)]


def chunk_state(r, cx, cz):
    tag = f"probe{cx}_{cz}".replace("-", "m")
    if "Summoned" not in r.cmd(f'summon tnt {cx * 16 + 2} 150 {cz * 16 + 2} {{fuse:30000,NoGravity:1b,Tags:["probe","{tag}"]}}'):
        return "unloaded"
    wait_ticks(r, 2)
    a = get(r, f"@e[tag={tag},limit=1]", "fuse")
    wait_ticks(r, 6)
    b = get(r, f"@e[tag={tag},limit=1]", "fuse")
    r.cmd(f"kill @e[tag={tag}]")
    return "TICK" if a and b and b[0] < a[0] else "lazy"


def build(r, b, info, nb, ninfo):
    (x0, y0, z0), (x1, y1, z1) = b.bounds()
    cx0, cz0, cx1, cz1 = (x0 - 8) // 16 * 16, (z0 - 8) // 16 * 16, (x1 + 8) // 16 * 16 + 15, (z1 + 8) // 16 * 16 + 15
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all"); r.cmd(NETHER + "forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd(f"forceload add {cx0} {cz0} {cx1} {cz1}")
    r.cmd(NETHER + "forceload add -32 -32 31 31")
    wait_ticks(r, 5)
    for y in range(52, 142):
        r.cmd(f"fill {x0 - 8} {y} {z0 - 8} {x1 + 8} {y} {z1 + 8} air")
    r.cmd("kill @e[type=!player]")
    for y in (56, 64, 72, 96, 104, 112):  # stations of earlier experiments
        r.cmd(NETHER + f"fill -20 {y} -20 20 {y + 8} 20 netherrack")
    for n in ninfo.values():
        r.cmd(NETHER + f"fill {n[0] - 9} {n[1] - 6} {n[2] - 9} {n[0] + 9} {n[1] + 9} {n[2] + 9} obsidian hollow")
    for n in ninfo.values():
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
    wait_ticks(r, 10)
    print("TNT lit by placing it:", r.cmd("execute if entity @e[type=tnt]"))
    r.cmd(f'data merge block {at(info["o1_send"])} {{Items:[{{Slot:0b,id:"minecraft:cobblestone",count:2}}]}}')
    r.cmd(f'data merge block {at(info["o3_send"])} {{Items:[{{Slot:0b,id:"minecraft:redstone",count:4}}]}}')
    wait_ticks(r, 80)
    r.cmd(f"forceload remove {cx0} {cz0} {cx1} {cz1}")
    r.cmd(NETHER + "forceload remove all")
    r.cmd("tick rate 1250")
    wait_ticks(r, 400)
    r.cmd("tick rate 20")


def shot(r, info, n, turns):
    n = dict(n)
    n["timer"] = max(n.values()) + 15
    cell = info["cell"]
    r.cmd("tick rate 100")  # buttons: the script cannot time presses any faster than this
    for name in ("w", "nw", "sw", "timer"):
        set_counter(r, info[f"counter_{name}"], n[name])
    wait_ticks(r, 40)
    r.cmd("tick rate 20")
    shown = {name: value(r, info[f"counter_{name}"]) for name in n}
    print("  counters:", shown, "ok" if shown == n else f"WANTED {n}")
    bx = 15.49 + 0.9 * sum(n[k] * PUSH[k][0] for k in PUSH)
    bz = 8.49 + 0.9 * sum(n[k] * PUSH[k][1] for k in PUSH)
    tx, tz = turn_xy(bx, bz, turns)
    cx, cz = int(tx // 16) * 16, int(tz // 16) * 16
    box = f"x={cx - 32},y=-64,z={cz - 32},dx=80,dy=400,dz=80"
    r.cmd(f"forceload add {cx - 32} {cz - 32} {cx + 47} {cz + 47}")
    wait_ticks(r, 60)  # the chunks need a moment before parked entities show up
    r.cmd(f"kill @e[type=tnt,{box}]")  # payloads parked there by earlier tests
    wait_ticks(r, 20)
    r.cmd(f"kill @e[type=tnt,{box}]")
    # the target stays unloaded during the shot: the payload then waits in the air where it
    # arrived, so the game can run far faster than this script could watch it
    r.cmd(f"forceload remove {cx - 32} {cz - 32} {cx + 47} {cz + 47}")
    wait_ticks(r, 20)
    lx, ly, lz = info["lever"]
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing={['north', 'east', 'south', 'west'][turns % 4]},powered=true]")
    t0 = gametime(r)
    r.cmd("tick rate 1250")
    deadline = t0 + 2600 + n["timer"] * 8 + 2000
    wait_ticks(r, 2200)
    while gametime(r) < deadline and value(r, info["counter_timer"]) > 0:
        time.sleep(0.2)
    done = gametime(r)
    wait_ticks(r, 400)
    r.cmd("tick rate 20")
    r.cmd(f"forceload add {cx - 32} {cz - 32} {cx + 47} {cz + 47}")
    result = None
    for _ in range(60):
        reply = r.cmd(f"execute as @e[type=tnt,{box}] run data get entity @s Pos")
        pos = [tuple(float(v) for v in q) for q in re.findall(r"\[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]", reply)]
        if pos:
            result = pos
            break
        wait_ticks(r, 1)
    print(f"  timer reached zero {done - t0} gt after the lever")
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing={['north', 'east', 'south', 'west'][turns % 4]},powered=false]")
    if result is None:
        print("  no payload seen at the target")
        return None
    px = sum(p[0] for p in result) / len(result)
    pz = sum(p[2] for p in result) / len(result)
    print(f"  arrived: {len(result)} TNT at x {px:.3f} z {pz:.3f}; predicted {tx:.3f} {tz:.3f}; miss {px - tx:+.3f} {pz - tz:+.3f}; "
          f"read {gametime(r) - t0} gt after the lever")
    wait_ticks(r, 120)
    r.cmd("kill @e[type=tnt]")
    r.cmd(f"forceload remove {cx - 32} {cz - 32} {cx + 47} {cz + 47}")
    return (px, pz)


if __name__ == "__main__":
    turns = int(sys.argv[1])
    n = dict(zip(("w", "nw", "sw"), map(int, sys.argv[2].split(",")))) if len(sys.argv) > 2 else {"w": 100, "nw": 60, "sw": 0}
    with Rcon(timeout=900) as r:
        b, info = overworld_turned(turns)
        nb, ninfo = nether_turned(turns)
        print("direction:", DIRECTION[turns])
        build(r, b, info, nb, ninfo)
        cc = (info["cell"][0] // 16, info["cell"][2] // 16)
        pc = (info["duper_w"]["rail"][0] // 16, info["duper_w"]["rail"][2] // 16)
        print("chunks before the shot: payload", cc, chunk_state(r, *cc), "| propellant", pc, chunk_state(r, *pc))
        shot(r, info, n, turns)
        print("dupers hold TNT:", {k: "passed" in r.cmd(f"execute if block {at(info[f'duper_{k}']['slot'])} tnt") or
                                   "passed" in r.cmd(f"execute if block {at(info[f'duper_{k}']['prime'])} tnt") for k in info["dupers"]})
