"""Counter + driver alone: enter pattern, arm, count the pulses that come out."""
import re
import sys
import time

from build import Build
from lab import Rcon, wait_ticks, step
from modules import PITCH, counter, driver, enter_presses

CO = (30, 112, 8)
BITS = 8


def at(p):
    return f"{CO[0] + p[0]} {CO[1] + p[1]} {CO[2] + p[2]}"


def lit(r):
    return sum(1 << k for k in range(BITS) if "passed" in r.cmd(f"execute if block {at((PITCH * k, 0, 0))} waxed_copper_bulb[lit=true]"))


def press(r, k):
    r.cmd(f"setblock {at((PITCH * k, 1, 0))} stone_button[face=floor,facing=north,powered=true]")
    wait_ticks(r, 3)
    r.cmd(f"setblock {at((PITCH * k, 1, 0))} stone_button[face=floor,facing=north,powered=false]")
    wait_ticks(r, 3)


with Rcon(timeout=600) as r:
    r.cmd("tick unfreeze"); r.cmd("tick rate 20"); r.cmd("kill @e[type=!player]")
    r.cmd("forceload add 0 0 63 15"); r.cmd("fill 8 96 0 62 120 15 air")
    b = Build(); kb, kp = counter(BITS); vb, vp = driver(); b.merge(kb); b.merge(vb)
    dis = at((-4, 0, 5))
    r.cmd(f"setblock {dis} redstone_block")
    print("errors", [c for c in b.to_commands(*CO) if "Changed" not in r.cmd(c)]); wait_ticks(r, 6)
    r.cmd(f"setblock {dis} redstone_block"); wait_ticks(r, 6)
    current = 0
    for n in [int(a) for a in sys.argv[1:]] or [37, 1, 6, 200]:
        r.cmd(f"setblock {dis} redstone_block"); wait_ticks(r, 6)
        presses = enter_presses(n, BITS, current)
        for k in presses:
            press(r, k)
            wait_ticks(r, 60)
        entered = lit(r)
        r.cmd("tick freeze"); time.sleep(0.2)
        r.cmd(f"setblock {dis} air")
        seq, t = "", 0
        while t < n * 8 + 60:
            step(r, 1); t += 1
            seq += "." if "passed" in r.cmd(f"execute if block {at(vp['out'])} redstone_wire[power=0]") else "#"
        r.cmd("tick unfreeze")
        pulses = re.findall(r"#+", seq)
        current = lit(r)
        print(f"N={n}: pressed bits {presses}, bulbs then show {entered}, pulses out {len(pulses)}, "
              f"lengths {sorted(set(map(len, pulses)))}, final value {current}")
