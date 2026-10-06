"""Test explicit TNT duper layouts stroke by stroke on the real server.

Layout from the Minecraft Wiki schematic (Tutorial:Block and item duplication), in its
primed state, pushed west by a sticky piston. Reports primed TNT per extend / retract
stroke and whether TNT block, fan and minecart are still where they belong.
"""
import re
import sys

from lab import Rcon, wait_ticks

O = (600, 150, 600)


def at(p):
    return f"{O[0] + p[0]} {O[1] + p[1]} {O[2] + p[2]}"


def count(r):
    m = re.search(r"Count: (\d+)", r.cmd("execute if entity @e[type=tnt]"))
    return int(m.group(1)) if m else 0


def layout(wall="cobblestone_wall", fan="dead_tube_coral_wall_fan[facing=north,waterlogged=false]", side=1):
    z = side
    return {
        "piston": ((4, 1, 0), "sticky_piston[facing=west]"),
        "power": (5, 1, 0),
        "blocks": [
            ((3, 1, 0), "slime_block"), ((2, 1, 0), "slime_block"), ((3, 2, 0), "slime_block"),
            ((2, 1, z), "slime_block"), ((2, 0, z), "slime_block"), ((1, 0, z), "slime_block"),
            ((1, 1, 0), wall),
        ],
        "rail": (2, 2, 0),
        "tnt": (2, 0, 0),
        "fan": ((1, 0, 0), fan),
    }


def run(r, lay, cycles=4, verbose=True):
    r.cmd("kill @e[type=!player]")
    r.cmd(f"fill {O[0] - 8} {O[1] - 6} {O[2] - 6} {O[0] + 10} {O[1] + 8} {O[2] + 6} air")
    r.cmd(f"setblock {at(lay['piston'][0])} {lay['piston'][1]}")
    for pos, state in lay["blocks"]:
        r.cmd(f"setblock {at(pos)} {state}")
    rail = lay["rail"]
    r.cmd(f"setblock {at(rail)} detector_rail[shape=east_west]")
    r.cmd(f"summon minecart {O[0] + rail[0] + 0.5} {O[1] + rail[1] + 0.1} {O[2] + rail[2] + 0.5}")
    wait_ticks(r, 6)
    powered = "passed" in r.cmd(f"execute if block {at(rail)} detector_rail[powered=true]")
    r.cmd(f"setblock {at(lay['tnt'])} stone")
    reply = r.cmd(f"setblock {at(lay['fan'][0])} {lay['fan'][1]} strict")
    r.cmd(f"setblock {at(lay['tnt'])} tnt strict")
    wait_ticks(r, 4)
    start = count(r)
    r.cmd("kill @e[type=tnt]")
    if verbose:
        print(f"  rail powered {powered}; fan placed: {reply}; TNT primed during setup: {start}")
    strokes = []
    for _ in range(cycles):
        r.cmd(f"setblock {at(lay['power'])} redstone_block")
        wait_ticks(r, 8)
        ext = count(r)
        r.cmd("kill @e[type=tnt]")
        r.cmd(f"setblock {at(lay['power'])} air")
        wait_ticks(r, 8)
        ret = count(r)
        r.cmd("kill @e[type=tnt]")
        strokes.append((ext, ret))
    tnt_home = "passed" in r.cmd(f"execute if block {at(lay['tnt'])} tnt")
    fan_home = "passed" in r.cmd(f"execute if block {at(lay['fan'][0])} {lay['fan'][1].split('[')[0]}")
    rail_home = "passed" in r.cmd(f"execute if block {at(rail)} detector_rail")
    cart = r.cmd("data get entity @e[type=minecart,limit=1] Pos")
    return strokes, tnt_home, fan_home, rail_home, cart


if __name__ == "__main__":
    with Rcon(timeout=120) as r:
        r.cmd("tick unfreeze")
        r.cmd(f"forceload add {O[0] - 16} {O[2] - 16} {O[0] + 31} {O[2] + 31}")
        # is a slime block a redstone conductor? lamp below, rail with cart above, then update the lamp
        r.cmd("kill @e[type=!player]")
        r.cmd(f"fill {O[0] - 8} {O[1] - 6} {O[2] - 6} {O[0] + 10} {O[1] + 8} {O[2] + 6} air")
        r.cmd(f"setblock {at((0, 1, 0))} slime_block")
        r.cmd(f"setblock {at((0, 2, 0))} detector_rail")
        r.cmd(f"summon minecart {O[0] + 0.5} {O[1] + 2.1} {O[2] + 0.5}")
        wait_ticks(r, 5)
        r.cmd(f"setblock {at((0, 0, 0))} redstone_lamp")
        r.cmd(f"setblock {at((1, 0, 0))} stone")
        wait_ticks(r, 4)
        print("slime conducts rail power:", "passed" in r.cmd(f"execute if block {at((0, 0, 0))} redstone_lamp[lit=true]"))

        variants = []
        for wall in ("cobblestone_wall", "stone", "air"):
            for fan in ("dead_tube_coral_wall_fan[facing=north,waterlogged=false]",
                        "dead_tube_coral_wall_fan[facing=west,waterlogged=false]",
                        "dead_tube_coral_fan[waterlogged=false]"):
                variants.append((wall, fan))
        for wall, fan in variants:
            print(f"wall={wall} fan={fan}")
            lay = layout(wall, fan)
            if wall == "air":
                lay["blocks"] = [b for b in lay["blocks"] if b[1] != "air"]
            print("  ", run(r, lay))
        r.cmd("kill @e[type=!player]")
