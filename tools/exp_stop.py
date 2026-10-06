"""Experiment: payload rests inside a movement-slowing block while it is charged.

Entity.move zeroes the velocity of an entity whose movementMultiplier is set, so the
payload should cover (multiplier * velocity) in the release tick and arrive with no speed.

Usage: python exp_stop.py N medium
"""
import sys
import time

from lab import Rcon, get, wait_ticks, write_function

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
MEDIUM = sys.argv[2] if len(sys.argv) > 2 else "cobweb"
PAY = "@e[tag=pay,limit=1]"


def show(r, label):
    print(f"{label}: Pos {get(r, PAY, 'Pos')} Motion {get(r, PAY, 'Motion')} fuse {get(r, PAY, 'fuse')}")


with Rcon(timeout=600) as r:
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=tnt]")
    r.cmd("forceload remove all")
    r.cmd("forceload add -16 0 15 15")
    r.cmd("fill -4 90 4 4 110 12 air")
    r.cmd("setblock 0 99 8 obsidian")
    r.cmd("setblock -1 99 8 obsidian")
    print(r.cmd(f"setblock -1 100 8 {MEDIUM}"))
    write_function("charge", ["summon tnt 0.5 100 8.5 {fuse:1}"] * N)
    r.cmd("reload")
    r.cmd('summon tnt -0.5 100 8.5 {fuse:80,Tags:["pay"]}')
    wait_ticks(r, 5)
    show(r, "ticking in medium")
    r.cmd("forceload remove -16 0 -1 15")
    wait_ticks(r, 5)
    show(r, "lazy a")
    wait_ticks(r, 5)
    show(r, "lazy b")
    r.cmd("function lab:charge")
    wait_ticks(r, 4)
    show(r, "charged")
    r.cmd("tick freeze")
    r.cmd("forceload add -16 0 -1 15")
    for step in range(1, 5):
        r.cmd("tick step 1")
        time.sleep(0.5)
        show(r, f"step {step}")
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=tnt]")
