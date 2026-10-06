"""Follow the loop item through both auto stations, tick window by tick window."""
import sys
from lab import Rcon, wait_ticks, gametime
import exp_trigger as e
from modules import station

N = e.NETHER
with Rcon(timeout=120) as r:
    r.cmd("tick unfreeze"); r.cmd("kill @e[type=!player]"); r.cmd("forceload remove all"); r.cmd(N + "forceload remove all")
    r.cmd("forceload add 10000 10000"); r.cmd("forceload add 16 16 47 31"); r.cmd(N + "forceload add 0 0 15 15"); wait_ticks(r, 5)
    auto, P = station()
    print(e.paste(r, "", e.O1, auto), e.paste(r, N, e.N1, auto)); wait_ticks(r, 10)
    conts = {k: v for k, v in auto.blocks.items() if v[0].split(":")[1] in ("hopper", "dropper")}
    for pre, o, name in (("", e.O1, "OW"), (N, e.N1, "NE")):
        wires = [(p, r.cmd(f"{pre}data get block {e.at(o, p)}")) for p in []]
        lz = P["lift"][2]
        states = []
        for p in ((-1, 0, lz - 1), (-2, 0, lz - 1), (-2, 0, lz), (-1, 0, lz), (0, 0, lz)):
            for lvl in range(16):
                if "passed" in r.cmd(f"{pre}execute if block {e.at(o, p)} redstone_wire[power={lvl}]"):
                    states.append(f"{p}:wire{lvl}")
            if "passed" in r.cmd(f"{pre}execute if block {e.at(o, p)} comparator[powered=true]"):
                states.append(f"{p}:cmp-on")
            if "passed" in r.cmd(f"{pre}execute if block {e.at(o, p)} comparator[powered=false]"):
                states.append(f"{p}:cmp-off")
        print(name, "clock snapshot:", states)
    r.cmd(f'data merge block {e.at(e.O1, P["send"])} {{Items:[{{Slot:0b,id:"minecraft:cobblestone",count:1}}]}}')
    for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 16):
        wait_ticks(r, 10)
        out = []
        for pre, o, name in (("", e.O1, "OW"), (N, e.N1, "NE")):
            for p in conts:
                if "id:" in r.cmd(f"{pre}data get block {e.at(o, p)} Items"):
                    out.append(f"{name}{p}:{conts[p][0].split(':')[1]}")
        ents = r.cmd('execute as @e[type=item,nbt={Item:{id:"minecraft:cobblestone"}}] run data get entity @s Pos')
        print(gametime(r), out, ents[-70:] if "entity data" in ents else "")
