"""Tick-by-tick trace of a duper layout: python-importable helper."""
import time
from lab import wait_ticks
import exp_duper2 as e

NAMES = ("tnt", "moving_piston", "detector_rail[powered=true]", "detector_rail[powered=false]", "slime_block", "air",
         "dead_tube_coral_wall_fan", "smooth_stone")


def blk(r, p):
    for name in NAMES:
        if "passed" in r.cmd(f"execute if block {e.at(p)} {name}"):
            return name.replace("detector_rail", "rail").replace("dead_tube_coral_wall_fan", "fan").replace("moving_piston", "moving")
    return "?"


def trace(r, lay, watch, strokes=2, ticks=5):
    """watch: {label: pos}. Prints one line per tick for `strokes` extend/retract pairs."""
    O = e.O
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=!player]")
    r.cmd(f"fill {O[0] - 8} {O[1] - 6} {O[2] - 6} {O[0] + 10} {O[1] + 8} {O[2] + 6} air")
    r.cmd(f"setblock {e.at(lay['piston'][0])} {lay['piston'][1]}")
    for pos, state in lay["blocks"]:
        r.cmd(f"setblock {e.at(pos)} {state}")
    rail = lay["rail"]
    r.cmd(f"setblock {e.at(rail)} detector_rail[shape=east_west]")
    r.cmd(f"summon minecart {O[0] + rail[0] + 0.5} {O[1] + rail[1] + 0.1} {O[2] + rail[2] + 0.5}")
    wait_ticks(r, 6)
    r.cmd(f"setblock {e.at(lay['tnt'])} stone")
    r.cmd(f"setblock {e.at(lay['fan'][0])} {lay['fan'][1]} strict")
    r.cmd(f"setblock {e.at(lay['tnt'])} tnt strict")
    wait_ticks(r, 3)
    r.cmd("tick freeze")
    time.sleep(0.2)

    def snap(label):
        ent = r.cmd("execute if entity @e[type=tnt]").replace("Test ", "").replace("passed. Count: ", "n=").replace("failed", "n=0")
        cart = r.cmd("data get entity @e[type=minecart,limit=1] Pos").split(": ")[-1]
        cx = cart.strip("[]").split(",")[0][:8] if "[" in cart else "none"
        print(label, ent, "cart.x", cx, " ".join(f"{k}={blk(r, p)}" for k, p in watch.items()))

    snap("rest ")
    for s in range(strokes):
        r.cmd(f"setblock {e.at(lay['power'])} redstone_block")
        for i in range(1, ticks + 1):
            r.cmd("tick step 1")
            time.sleep(0.25)
            snap(f"ext{s} t{i}")
        r.cmd(f"setblock {e.at(lay['power'])} air")
        for i in range(1, ticks + 1):
            r.cmd("tick step 1")
            time.sleep(0.25)
            snap(f"ret{s} t{i}")
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=!player]")
