"""Print layers of the friend's MOSC schematic as text maps (x to the right, z down)."""
import sys
from litemapy import Schematic

SYM = {"white_concrete": "#", "light_gray_concrete": "#", "gray_concrete": "#", "glass": "g", "obsidian": "O",
       "redstone_wire": "+", "repeater": "r", "comparator": "c", "observer": "o", "hopper": "h", "piston": "P",
       "sticky_piston": "S", "piston_head": "p", "slime_block": "s", "honey_block": "y", "tnt": "T", "water": "W",
       "bubble_column": "W", "iron_trapdoor": "t", "note_block": "n", "activator_rail": "a", "rail": "a",
       "redstone_torch": "i", "redstone_wall_torch": "i", "barrel": "B", "chest": "C", "dropper": "D",
       "lever": "L", "powder_snow": "*", "nether_portal": "N", "dead_tube_coral_wall_fan": "f", "anvil": "A",
       "soul_sand": "u", "waxed_copper_bulb": "b", "redstone_block": "R", "redstone_lamp": "l", "oak_slab": "_",
       "cobblestone_slab": "_", "oak_fence": "|", "composter": "m", "oak_pressure_plate": "-",
       "oxidized_copper_chest": "C", "pale_oak_wall_sign": "$"}


def region():
    return list(Schematic.load("../extern/MOSC.litematic").regions.values())[0]


if __name__ == "__main__":
    y0, y1, x0, x1, z0, z1 = (int(v) for v in sys.argv[1:7])
    reg = region()
    for y in range(y0, y1 + 1):
        print(f"y={y}   x {x0}..{x1}")
        for z in range(z0, z1 + 1):
            row = ""
            for x in range(x0, x1 + 1):
                b = reg[x, y, z]
                n = b.id.split(":")[1]
                row += "." if n == "air" else SYM.get(n, "?")
            print(f"{z:3d} {row}")
    if len(sys.argv) > 7:
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    b = reg[x, y, z]
                    if b.id.split(":")[1] in sys.argv[7].split(","):
                        print((x, y, z), b.to_block_state_identifier())
