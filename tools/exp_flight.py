"""Experiment: charge a lazy TNT with N propellant explosions, release it, track the flight.

Usage: python exp_flight.py N [dy]
  N   number of propellant explosions
  dy  vertical offset of the propellant relative to the payload (aims the shot up or down)
"""
import sys
import time

from lab import Rcon, get, wait_ticks, write_function

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
DY = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

PAY = "@e[tag=pay,limit=1]"

with Rcon(timeout=600) as r:
    r.cmd("tick unfreeze")
    r.cmd("kill @e[type=tnt]")
    r.cmd("forceload remove all")
    r.cmd("forceload add 0 0 15 15")
    # propellant cell floor, so the downward self-push of stacked propellant is absorbed
    r.cmd("fill -4 90 4 4 110 12 air")
    floor_y = 99 + int(DY // 1)
    r.cmd(f"setblock 0 {floor_y} 8 obsidian")
    prop_y = floor_y + 1
    pay_y = prop_y - DY
    write_function("charge", [f"summon tnt 0.5 {prop_y} 8.5 {{fuse:1}}"] * N)
    print(r.cmd("reload"))
    r.cmd(f"summon tnt -0.5 {pay_y} 8.5 {{fuse:80,NoGravity:1b,Tags:[\"pay\"]}}")
    wait_ticks(r, 3)
    t0 = time.time()
    print(r.cmd("function lab:charge"))
    wait_ticks(r, 4)
    print(f"charge wall time {time.time() - t0:.2f}s")
    motion = get(r, PAY, "Motion")
    print("after charge  Motion", motion, "Pos", get(r, PAY, "Pos"), "fuse", get(r, PAY, "fuse"))
    if not motion:
        sys.exit("payload lost")

    r.cmd("tick freeze")
    wait_ticks_done = r.cmd("tick query")
    vx = motion[0]
    # load a corridor where the payload should be over the next ticks
    x = -0.5
    v = vx
    spots = []
    for _ in range(4):
        x += v
        v *= 0.98
        spots.append(x)
    for sx in spots:
        cx = int(sx // 16) * 16
        print(r.cmd(f"forceload add {cx - 32} 0 {cx + 47} 15"))
    r.cmd("forceload add -16 0 -1 15")
    for step in range(1, 5):
        t0 = time.time()
        r.cmd("tick step 1")
        time.sleep(0.4)
        while "sprint" in r.cmd("tick query").lower():
            time.sleep(0.1)
        pos = get(r, PAY, "Pos")
        print(f"step {step}: Pos {pos} Motion {get(r, PAY, 'Motion')} fuse {get(r, PAY, 'fuse')} ({time.time() - t0:.2f}s)")
        if not pos:
            break
    r.cmd("tick unfreeze")
