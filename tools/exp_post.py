"""Nether post: panel -> nether -> cannon. Presses panel buttons and reads the counters at the cannon.

Usage: python exp_post.py [--keep] [--fire] E,NE,SE
  --fire  also send START and watch the shot
"""
import sys
import time

import post
from cannon3 import nether_turned, overworld_turned
from exp_mk2 import NETHER, lit, tnt_in
from exp_mk3 import GROUPS, build
from exp_shot import at, value
from lab import Rcon, gametime, wait_ticks
from modules import enter_presses

RATE = 200
LENGTH = 41  # nether blocks between the two nether portals of the post


def layout():
    b, info = overworld_turned(0, post=True)
    nb, ninfo = nether_turned(0, post=True)
    lb, np_origin = post.nether_link(ninfo["m"], LENGTH)
    nb.merge(lb)
    pb, pinfo = post.panel()
    origin = (np_origin[0] * 8 + 2, np_origin[1], np_origin[2] * 8 + 4)  # panel station: lands on the arrival portal
    return b, info, nb, ninfo, np_origin, pb, pinfo, origin


def prime(r, info):
    """Filters back to 18 items, release hoppers empty. Pasting block by block lets a release
    hopper take one item before its lock torch stands; a schematic paste does not."""
    from cannon3 import BITS, D, ROWS, SHIFT, XC
    cells = [(XC + 3 * k, ROWS[g], post.ITEMS[(g, k)]) for g in GROUPS for k in range(BITS[g])]
    cells.append((XC + 42, ROWS["e"], post.ITEMS[("start", 0)]))
    for x, z, item in cells:
        x, z = x + SHIFT[0], z + SHIFT[2]
        r.cmd(f"data merge block {x} {D + 4} {z - 1} {{Items:[]}}")
        r.cmd(f"data merge block {x} {D + 5} {z - 1} {{{post.filter_items(item)}}}")
        r.cmd(f"data merge block {x} {D + 4} {z - 2} {{Items:[]}}")
    r.cmd(f"data merge block {at(info['post_trash'])} {{Items:[]}}")


def press(r, pos):
    r.cmd(f"setblock {at(pos)} stone_button[face=floor,facing=north,powered=true]")
    wait_ticks(r, 6)
    r.cmd(f"setblock {at(pos)} stone_button[face=floor,facing=north,powered=false]")
    wait_ticks(r, 6)


if __name__ == "__main__":
    args = sys.argv[1:]
    want = dict(zip(GROUPS, map(int, next(a for a in args if "," in a).split(","))))
    b, info, nb, ninfo, np_origin, pb, pinfo, origin = layout()
    px, py, pz = origin
    area = f"{px - 16} {pz - 16} {px + 48} {pz + 32}"
    with Rcon(timeout=900) as r:
        if "--keep" not in args:
            r.cmd("tp @a -500 67 49")
            build(r, b, info, nb, list(ninfo.values()) + [np_origin])
            r.cmd(f"forceload add {area}")
            wait_ticks(r, 10)
            for y in range(py - 3, py + 8):
                r.cmd(f"fill {px - 8} {y} {pz - 8} {px + 40} {y} {pz + 20} air")
            bad = [c for c in pb.to_commands(px, py, pz) if "Changed" not in r.cmd(c)]
            print("panel at", origin, "blocks", len(pb.blocks), "paste errors", len(bad), bad[:2], "| nether arrival portal", np_origin)
            wait_ticks(r, 40)
        r.cmd(f"forceload add {area}")  # stands in for the player at the panel
        prime(r, info)
        wait_ticks(r, 40)
        counters = {g: info[f"counter_{g}"] for g in GROUPS}
        before = {g: value(r, counters[g]) for g in GROUPS}
        t0 = gametime(r)
        n = 0
        todo = post.order({g: enter_presses(want[g], counters[g]["bits"], before[g]) for g in GROUPS})
        for key in todo:
            bx, by, bz = pinfo["buttons"][key]
            press(r, (px + bx, py + by, pz + bz))
            n += 1
        print(f"pressed {n} panel buttons in {gametime(r) - t0} gt; counters before: {before}")
        r.cmd(f"tick rate {RATE}")
        shown = None
        for _ in range(400):
            wait_ticks(r, 200)
            shown = {g: value(r, counters[g]) for g in GROUPS}
            gate = r.cmd(f"data get block {at(info['gate_dropper'])} Items")
            if shown == want and "id:" not in gate:
                break
        r.cmd("tick rate 20")
        print(f"counters at the cannon after {gametime(r) - t0} gt: {shown}", "OK" if shown == want else f"WANTED {want}")
        print("trash barrel:", r.cmd(f"data get block {at(info['post_trash'])} Items")[-80:])
        if "--fire" in args and shown == want:
            wait_ticks(r, 100)
            bx, by, bz = pinfo["buttons"][("start", 0)]
            press(r, (px + bx, py + by, pz + bz))
            t0 = gametime(r)
            r.cmd(f"tick rate {RATE}")
            state = {}
            deadline = t0 + 2700 + 8 * max(want.values()) + 2500
            while gametime(r) < deadline:
                row = {"start bulb": "passed" in r.cmd(f"execute if block {at(info['start_bulb'])} waxed_copper_bulb[lit=true]"),
                       "release": not lit(r, info["gate"], "redstone_wire[power=0]"),
                       "payload in flight cell": len([1 for p, f in tnt_in(r, f"x={info['cell'][0] - 1},y=83.5,z={info['cell'][2] - 1},dx=2,dy=1.5,dz=2")
                                                      if p[2] >= info['cell'][2]])}
                for key, v in row.items():
                    if state.get(key) != v:
                        print(f"  t{gametime(r) - t0:6d} {key} -> {v}")
                        state[key] = v
                if state.get("release") and not row["payload in flight cell"] and gametime(r) - t0 > 2000:
                    break
                time.sleep(0.2)
            r.cmd("tick rate 20")
            print("  counters:", {g: value(r, counters[g]) for g in GROUPS}, "| chamber:", r.cmd(f"execute if block {at(info['cell'])} powder_snow"))
            press(r, (px + bx, py + by, pz + bz))  # START again = lever off
        r.cmd(f"forceload remove {area}")
