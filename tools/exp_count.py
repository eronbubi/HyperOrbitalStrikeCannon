"""Counter + clock + duper + drop shaft + chamber: does a set number N arrive as N pushes?"""
import sys

from build import Build
from lab import Rcon, get, wait_ticks, gametime
from modules import PITCH, chamber, counter, driver, duper_side, shaft

N = int(sys.argv[1]) if len(sys.argv) > 1 else 37
BITS = 8
CH = (15, 100, 8)
DU = (17, 130, 8)
CO = (30, 130, 8)
PAY = "@e[tag=pay,limit=1]"


def at(o, p):
    return f"{o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]}"


def assemble():
    b = Build()
    cb, cp = chamber()
    b.merge(cb, *CH)
    sb, sp = shaft(28)
    b.merge(sb, *DU)
    db, dp = duper_side(1)
    b.merge(db, *DU)
    kb, kp = counter(BITS)
    b.merge(kb, *CO)
    vb, vp = driver()
    b.merge(vb, *CO)
    # driver output -> piston
    ox, oy, oz = CO[0] + vp["out"][0], CO[1], CO[2]
    b.set(ox - 1, oy - 1, oz, "smooth_stone")
    b.set(ox - 1, oy, oz, "redstone_wire")
    b.set(ox - 2, oy, oz, "smooth_stone")
    b.set(ox - 2, oy + 1, oz, "redstone_wire")
    return b, cp, dp, kp, vp


if __name__ == "__main__":
    with Rcon(timeout=600) as r:
        r.cmd("tick unfreeze")
        r.cmd("tick rate 20")
        r.cmd("kill @e[type=!player]")
        r.cmd("forceload remove all")
        r.cmd("forceload add 0 0 63 15")
        r.cmd("fill 8 96 0 62 114 15 air")
        r.cmd("fill 8 115 0 62 136 15 air")
        b, cp, dp, kp, vp = assemble()
        inhibit, disable = at(CO, kp["inhibit"]), at(CO, (vp["disable"][0], 0, vp["disable"][2] + 1))
        r.cmd(f"setblock {disable} redstone_block")
        r.cmd(f"setblock {inhibit} redstone_block")
        bad = [c for c in b.to_commands() if "Changed" not in r.cmd(c)]
        print("paste errors:", bad[:5], len(bad))
        rail = dp["rail"]
        r.cmd(f"summon minecart {DU[0] + rail[0] + 0.5} {DU[1] + rail[1] + 0.1} {DU[2] + rail[2] + 0.5}")
        wait_ticks(r, 10)
        r.cmd(f"setblock {at(DU, dp['prime'])} tnt")
        for k in range(BITS):
            if N >> k & 1:
                r.cmd(f"setblock {at(CO, (PITCH * k, 0, 0))} waxed_copper_bulb[lit=true]")
        wait_ticks(r, 10)
        r.cmd(f"setblock {inhibit} air")
        wait_ticks(r, 10)
        lit = [k for k in range(BITS) if "passed" in r.cmd(f"execute if block {at(CO, (PITCH * k, 0, 0))} waxed_copper_bulb[lit=true]")]
        print("bulbs lit before start:", lit, "= value", sum(1 << k for k in lit))
        r.cmd("forceload remove 0 0 15 15")  # payload chunk goes lazy
        wait_ticks(r, 5)
        r.cmd(f'summon tnt {CH[0] + 0.49} {CH[1]} {CH[2] + 0.49} {{fuse:2000,Tags:["pay"]}}')
        t0 = gametime(r)
        r.cmd(f"setblock {disable} air")
        while True:
            wait_ticks(r, 20)
            lit = [k for k in range(BITS) if "passed" in r.cmd(f"execute if block {at(CO, (PITCH * k, 0, 0))} waxed_copper_bulb[lit=true]")]
            if not lit or gametime(r) - t0 > N * 8 + 400:
                break
        print(f"counter reached zero after {gametime(r) - t0} gt (bulbs lit: {lit})")
        wait_ticks(r, 160)
        mot = get(r, PAY, "Motion")
        print("payload Motion:", mot)
        if mot:
            print(f"pushes that arrived: {mot[0] / -0.748274:.2f} of {N}; z drift {mot[2]:+.4f}")
        print("TNT block still in duper:", "passed" in r.cmd(f"execute if block {at(DU, dp['slot'])} tnt"),
              "| tnt entities left:", r.cmd("execute if entity @e[type=tnt,tag=!pay]"))
        r.cmd("kill @e[type=tnt]")
