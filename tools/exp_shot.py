"""Full shots from the lever on the real server, one after another.

Stage 1: the build without portal stations; this script plays the on-demand loader
(payload chunk ticks from 40 gt after each fire pulse, for 300 gt), using the timing
measured with the real stations in exp_trigger.py.

Usage: python exp_shot.py [--keep] W,NW,SW [W,NW,SW ...]
  --keep  reuse the cannon that is already standing instead of pasting it again
"""
import re
import sys
import time

from cannon import CELL, LEVER, Y0, overworld
from lab import Rcon, gametime, wait_ticks
from modules import enter_presses

# velocity per propellant TNT in blocks/tick (x, z), from the calibration shots with real dupers
PUSH = {"w": (-1.1430, -0.0040), "nw": (-0.454367, -0.455930), "sw": (-0.457922, 0.455248)}


def at(p):
    return f"{p[0]} {p[1]} {p[2]}"


def value(r, c):
    x, y, z = c["bit0"]
    sx, _, sz = c["step"]
    return sum(1 << k for k in range(c["bits"])
               if "passed" in r.cmd(f"execute if block {x + sx * k} {y} {z + sz * k} waxed_copper_bulb[lit=true]"))


def set_counter(r, c, n):
    """Enters n with the buttons. Run at 20 tps: the script cannot time presses at high speed."""
    for k in enter_presses(n, c["bits"], value(r, c)):
        x, y, z = c["bit0"][0] + c["step"][0] * k, c["bit0"][1], c["bit0"][2] + c["step"][2] * k
        r.cmd(f"setblock {x} {y + 1} {z} stone_button[face=floor,facing=north,powered=true]")
        wait_ticks(r, 12)
        r.cmd(f"setblock {x} {y + 1} {z} stone_button[face=floor,facing=north,powered=false]")
        wait_ticks(r, 160)  # a borrow ripples through all bits; the next press has to wait for it


def cell_tnt(r):
    reply = r.cmd(f"execute as @e[type=tnt,x={CELL[0]},y={Y0 - 0.5},z={CELL[2]},dx=0,dy=1.5,dz=0] run data get entity @s fuse")
    return [int(v) for v in re.findall(r"data: (\d+)s", reply)]


def build(r, b, info):
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all"); r.cmd("forceload add 10000 10000")
    r.cmd("forceload add 0 -16 79 47")
    for y in range(78, 142):
        r.cmd(f"fill 4 {y} -8 79 {y} 50 air")
    r.cmd("kill @e[type=!player]")
    bad = [c for c in b.to_commands() if "Changed" not in r.cmd(c)]
    print("blocks:", len(b.blocks), "paste errors:", len(bad), bad[:3])
    for name in info["dupers"]:
        rail = info[f"duper_{name}"]["rail"]
        r.cmd(f"summon minecart {rail[0] + 0.5} {rail[1] + 0.1} {rail[2] + 0.5}")
    wait_ticks(r, 20)
    for name in info["dupers"]:
        r.cmd(f"setblock {at(info[f'duper_{name}']['prime'])} tnt")
    wait_ticks(r, 10)
    print("TNT lit by placing it:", r.cmd("execute if entity @e[type=tnt]"))


def shot(r, info, n, verbose=True):
    """Arms the counters, flips the lever, plays the loader, returns where the payload arrived."""
    n = dict(n)
    n["timer"] = max(n.values()) + 15
    r.cmd("forceload add 0 -16 79 47")
    r.cmd("tick rate 100")
    for name in ("w", "nw", "sw", "timer"):
        set_counter(r, info[f"counter_{name}"], n[name])
    wait_ticks(r, 40)
    r.cmd("tick rate 20")
    shown = {name: value(r, info[f"counter_{name}"]) for name in n}
    if shown != n:
        print("counter entry failed:", shown, "wanted", n)
    r.cmd("forceload remove 0 -16 15 47")  # payload chunk column: block-ticking only from here on
    wait_ticks(r, 10)

    vx = sum(n[k] * PUSH[k][0] for k in PUSH)
    vz = sum(n[k] * PUSH[k][1] for k in PUSH)
    tx, tz = CELL[0] + 0.49 + 0.9 * vx, CELL[2] + 0.49 + 0.9 * vz
    cx, cz = int(tx // 16) * 16, int(tz // 16) * 16

    fx, fy, fz = info["fire_point"]
    lx, ly, lz = LEVER
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=true]")
    t0 = gametime(r)
    edges, last_fire, window, last, result = 0, False, None, {}, None
    deadline = t0 + 2500 + n["timer"] * 8 + 500
    r.cmd("tick rate 40")
    while gametime(r) < deadline and result is None:
        now = gametime(r)
        fire = "passed" in r.cmd(f"execute if block {fx} {fy} {fz} repeater[powered=true]")
        if fire and not last_fire:
            edges += 1
            if verbose:
                print(f"  t+{now - t0}: fire pulse #{edges}")
            window = [now + 40, now + 340, False]
            if edges == 2:
                r.cmd("tick rate 20")
                r.cmd(f"forceload add {cx - 32} {cz - 32} {cx + 47} {cz + 47}")
        last_fire = fire
        if window and not window[2] and now >= window[0]:
            r.cmd("forceload add 0 0 15 47")
            window[2] = True
        if window and window[2] and now >= window[1]:
            r.cmd("forceload remove 0 0 15 47")
            window = None
        if edges < 2:
            state = (len(cell_tnt(r)), "passed" in r.cmd(f"execute if block 14 {Y0} 8 smooth_stone"))
            if state != last and verbose:
                fuses = sorted(cell_tnt(r))
                print(f"  t+{gametime(r) - t0}: payload {state[0]} TNT, wall {'up' if state[1] else 'down'}, fuses {fuses[:1]}..{fuses[-1:]}")
            last = state
        elif window and window[2]:
            reply = r.cmd(f"execute as @e[type=tnt,x={cx - 32},y=-64,z={cz - 32},dx=80,dy=400,dz=80] run data get entity @s Pos")
            pos = [tuple(float(v) for v in p) for p in re.findall(r"\[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]", reply)]
            if pos:
                result = pos
    r.cmd("tick rate 20")
    r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
    if result is None:
        print("  no payload seen")
        return None
    px = sum(p[0] for p in result) / len(result)
    pz = sum(p[2] for p in result) / len(result)
    spread = max(max(abs(p[0] - px), abs(p[2] - pz)) for p in result)
    out = {"n": n, "count": len(result), "x": px, "z": pz, "dx": px - (CELL[0] + 0.49), "dz": pz - (CELL[2] + 0.49),
           "predicted": (tx, tz), "spread": spread, "ticks": gametime(r) - t0}
    print(f"  arrived: {len(result)} TNT at x {px:.3f} z {pz:.3f} (spread {spread:.4f}); predicted {tx:.3f} {tz:.3f}; "
          f"miss {px - tx:+.3f} {pz - tz:+.3f}; {out['ticks']} gt after the lever")
    wait_ticks(r, 120)
    r.cmd("kill @e[type=tnt]")
    r.cmd(f"forceload remove {cx - 32} {cz - 32} {cx + 47} {cz + 47}")
    r.cmd("forceload add 0 -16 79 47")
    r.cmd("tick rate 100")
    wait_ticks(r, 2300)  # until the lever-off has reached the counter clocks
    r.cmd("tick rate 20")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    keep = "--keep" in args
    shots = [dict(zip(("w", "nw", "sw"), map(int, a.split(",")))) for a in args if "," in a] or [{"w": 100, "nw": 60, "sw": 0}]
    with Rcon(timeout=900) as r:
        b, info = overworld(stations=False)
        if not keep:
            build(r, b, info)
        results = []
        for n in shots:
            print("shot", n)
            results.append(shot(r, info, n, verbose=len(shots) == 1))
        dupers = {k: "passed" in r.cmd(f"execute if block {at(info[f'duper_{k}']['slot'])} tnt") or
                  "passed" in r.cmd(f"execute if block {at(info[f'duper_{k}']['prime'])} tnt") for k in info["dupers"]}
        print("dupers still hold their TNT block:", dupers, "| snow:", r.cmd(f"execute if block {at(CELL)} powder_snow"))
        for res in results:
            if res:
                n = res["n"]
                total = n["w"] + n["nw"] + n["sw"]
                print(f"n={n['w']},{n['nw']},{n['sw']}: displacement per TNT x {res['dx'] / total:+.6f} z {res['dz'] / total:+.6f}")
