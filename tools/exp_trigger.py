"""Static loader (y=60, chunk (2,1)) plus on-demand loader (y=100, chunk (1,1)).

Measures how long after the fire pulse the payload chunk (0,0) starts ticking entities
and for how many ticks, using a TNT probe whose fuse only runs while its chunk ticks.
"""
import time

from lab import Rcon, get, wait_ticks, gametime
from modules import station

NETHER = "execute in minecraft:the_nether run "
O1, N1 = (40, 60, 24), (5, 60, 3)
O3, N3 = (24, 100, 24), (3, 100, 3)


def paste(r, prefix, origin, build):
    x, y, z = origin
    # sealed room, so nether lava or gravel cannot run into the redstone
    r.cmd(f"{prefix}fill {x - 6} {y - 4} {z - 8} {x + 7} {y + 8} {z + 7} obsidian hollow")
    r.cmd(f"{prefix}fill {x - 5} {y - 3} {z - 7} {x + 6} {y + 7} {z + 6} air")
    return [c for c in build.to_commands(*origin) if "Changed" not in r.cmd(prefix + c)]


def at(o, p):
    return f"{o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]}"


def setup(r):
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=!player]")
    r.cmd("forceload remove all")
    r.cmd(NETHER + "forceload remove all")
    r.cmd("forceload add 10000 10000")
    r.cmd("forceload add 16 16 47 31")
    r.cmd(NETHER + "forceload add 0 0 15 15")
    wait_ticks(r, 5)
    # portals left over from earlier experiments would catch the items: the game links to the nearest one
    r.cmd("forceload add 32 0 47 15")
    r.cmd("fill 34 96 2 45 108 14 air")
    r.cmd("fill 34 96 16 47 108 31 air")
    wait_ticks(r, 3)
    r.cmd("forceload remove 32 0 47 15")
    auto, P = station()
    trig, _ = station(auto_send=False)
    errs = paste(r, "", O1, auto) + paste(r, NETHER, N1, auto) + paste(r, "", O3, trig) + paste(r, NETHER, N3, auto)
    wait_ticks(r, 10)
    r.cmd("kill @e[type=item]")
    r.cmd(f'data merge block {at(O1, P["send"])} {{Items:[{{Slot:0b,id:"minecraft:cobblestone",count:2}}]}}')
    r.cmd(f'data merge block {at(O3, P["send"])} {{Items:[{{Slot:0b,id:"minecraft:redstone",count:4}}]}}')
    wait_ticks(r, 60)
    r.cmd("forceload remove 16 16 47 31")
    r.cmd(NETHER + "forceload remove all")
    r.cmd("tick rate 100")
    wait_ticks(r, 330)  # let every temporary ticket run out
    r.cmd("tick rate 20")
    return P, errs


def fire(r, P):
    r.cmd(f"setblock {at(O3, P['fire'])} redstone_block")
    wait_ticks(r, 3)
    r.cmd(f"setblock {at(O3, P['fire'])} air")


if __name__ == "__main__":
    with Rcon(timeout=120) as r:
        P, errs = setup(r)
        print("paste errors:", errs)
        for shot in range(3):
            r.cmd("kill @e[tag=probe]")
            r.cmd('summon tnt 8 130 8 {fuse:30000,NoGravity:1b,Tags:["probe","pb"]}')
            r.cmd('summon tnt 24 130 8 {fuse:30000,NoGravity:1b,Tags:["probe","pa"]}')
            wait_ticks(r, 10)
            fb0 = get(r, "@e[tag=pb,limit=1]", "fuse")[0]
            fa0 = get(r, "@e[tag=pa,limit=1]", "fuse")[0]
            wait_ticks(r, 10)
            fb1 = get(r, "@e[tag=pb,limit=1]", "fuse")[0]
            fa1 = get(r, "@e[tag=pa,limit=1]", "fuse")[0]
            print(f"shot {shot}: before: payload chunk ticking {fb1 < fb0}, propellant chunk ticking {fa1 < fa0}")
            t0 = gametime(r)
            fire(r, P)
            start = end = None
            last = fb1
            while gametime(r) - t0 < 420:
                t = gametime(r) - t0
                f = get(r, "@e[tag=pb,limit=1]", "fuse")[0]
                if f < last and start is None:
                    start = t
                if start is not None and f == last and end is None and t - start > 5:
                    end = t
                last = f
                time.sleep(0.02)
            print(f"   payload chunk ticked from about t+{start} to t+{end}; probe fuse ran {fb1 - last:.0f} ticks")
            print("   trigger dropper holds:", r.cmd(f"data get block {at(O3, P['send'])} Items")[-60:])
            wait_ticks(r, 60)
