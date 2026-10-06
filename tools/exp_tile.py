"""Nether post: one filter tile on its own. Items go into the input hopper; does the bulb toggle once each?"""
import time

from build import Build
from lab import Rcon, step, wait_ticks
from post import tile

X, Y, Z = 3000, 100, 3000

if __name__ == "__main__":
    b = Build()
    b.set(0, 0, 0, "waxed_copper_bulb", lit=False, powered=False)
    b.set(0, -1, 0, "smooth_stone")
    b.merge(tile("white_wool"))
    b.set(0, 6, -1, "hopper", facing="east")
    b.set(1, 6, -1, "barrel", facing="up", open=False)
    with Rcon(timeout=300) as r:
        r.cmd("tick unfreeze"); r.cmd(f"forceload add {X - 16} {Z - 16} {X + 16} {Z + 16}")
        wait_ticks(r, 10)
        for y in range(Y - 3, Y + 10):
            r.cmd(f"fill {X - 6} {y} {Z - 6} {X + 6} {y} {Z + 6} air")
        bad = [c for c in b.to_commands(X, Y, Z) if "Changed" not in r.cmd(c)]
        print("paste errors:", bad[:3])
        wait_ticks(r, 20)
        print("idle: bulb lit", "passed" in r.cmd(f"execute if block {X} {Y} {Z} waxed_copper_bulb[lit=true]"),
              "| torch lit", "passed" in r.cmd(f"execute if block {X} {Y + 3} {Z - 1} redstone_wall_torch[lit=true]"))
        r.cmd("tick freeze"); time.sleep(0.3)
        for name, items in (("3 wool", 'Items:[{Slot:0b,id:"minecraft:white_wool",count:3}]'),
                            ("2 other", 'Items:[{Slot:0b,id:"minecraft:red_wool",count:2}]'),
                            ("1 wool", 'Items:[{Slot:0b,id:"minecraft:white_wool",count:1}]')):
            r.cmd(f"data merge block {X} {Y + 6} {Z - 1} {{{items}}}")
            line, toggles, last = "", 0, None
            for t in range(90):
                step(r, 1)
                lit = "passed" in r.cmd(f"execute if block {X} {Y} {Z} waxed_copper_bulb[lit=true]")
                toggles += last is not None and lit != last
                last = lit
                line += "#" if "passed" not in r.cmd(f"execute if block {X} {Y + 2} {Z} redstone_wire[power=0]") else "."
            f = r.cmd(f"data get block {X} {Y + 5} {Z - 1} Items[0].count")[-6:]
            print(f"{name}: bulb toggled {toggles} times; pulse {line}")
            print("   filter slot 0:", f, "| taken out:", r.cmd(f"data get block {X} {Y + 4} {Z - 2} Items")[-70:],
                  "| passed on:", r.cmd(f"data get block {X + 1} {Y + 6} {Z - 1} Items")[-60:])
        r.cmd("tick unfreeze")
        r.cmd(f"forceload remove {X - 16} {Z - 16} {X + 16} {Z + 16}")
