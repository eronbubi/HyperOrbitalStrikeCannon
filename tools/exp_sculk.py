"""MK.2: does a calibrated sculk sensor (explosions only) follow the propellant?

Usage: python exp_sculk.py CYCLES X Y Z
"""
import re
import sys
import time

from cannon2 import core
from exp_feed import at, build
from lab import Rcon, step

if __name__ == "__main__":
    cycles = int(sys.argv[1])
    sx, sy, sz = map(int, sys.argv[2:5])
    b, info = core()
    with Rcon(timeout=600) as r:
        build(r, b, info)
        print(r.cmd(f"setblock {sx - 1} {sy} {sz} redstone_block"))
        print(r.cmd(f"setblock {sx} {sy} {sz} calibrated_sculk_sensor[facing=east]"))
        print(r.cmd(f"setblock {sx} {sy - 1} {sz + 1} obsidian"), r.cmd(f"setblock {sx} {sy} {sz + 1} redstone_wire"))
        power = [info[f"duper_{k}"]["power"] for k in info["dupers"]]
        pushers = [info[f"duper_{k}"]["pusher_power"] for k in info["dupers"]]
        r.cmd("tick freeze"); time.sleep(0.3)
        line = ""
        for t in range(cycles * 8 + 200):
            if t % 8 == 0:
                for p in pushers + (power if t < cycles * 8 else []):
                    r.cmd(f"setblock {at(p)} redstone_block")
            elif t % 8 == 4:
                for p in pushers + (power if t < cycles * 8 else []):
                    r.cmd(f"setblock {at(p)} air")
            step(r, 1)
            reply = r.cmd(f"execute if block {sx} {sy} {sz + 1} redstone_wire[power=0]")
            n = len(re.findall("tnt", r.cmd("execute if entity @e[type=tnt]"))) and 1
            line += "." if "passed" in reply else "#"
            if t % 80 == 79:
                print(f"t{t - 79:4d} {line}  tnt:{r.cmd('execute if entity @e[type=tnt]')[-12:]}")
                line = ""
        r.cmd("tick unfreeze")
        r.cmd("kill @e[type=tnt]")
