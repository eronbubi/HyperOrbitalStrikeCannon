"""Flip the lever and log when chosen redstone points change (for tuning the sequencer)."""
import sys
from cannon import CELL, D, LEVER, Y0, overworld
from lab import Rcon, gametime, wait_ticks

b, info = overworld(stations=False)
T = info["taps"]
xa, xp, xq, xe = T[240], T[280], T[304], T[368]
LZ = LEVER[2]
POINTS = {
    "tapA": (xa, D, LZ), "alignOut": (xa, D, LZ - 3), "alignJoin": (24, D, 11), "nwPistonDust": (21, D + 1, 10),
    "tapP1": (xp, D, LZ), "tapP2": (xq, D, LZ), "window": (xp, D, LZ + 3), "oscRep": (xp + 2, D, LZ + 4),
    "payWireDeck": (48, D, LZ + 7), "payWireLow": (13, Y0 + 2, 20), "dispDust": (CELL[0], Y0 + 2, CELL[2]),
    "E": (xe, D, LZ), "torchD": (xe + 1, D, LZ - 1), "busD": (31, D + 2, 8), "disableW": (29, D, 8),
    "E_south": (xe, D, LZ + 14), "torchTimer": (xe, D, LZ + 16), "E_deck31": (51, D, LZ + 11),
    "E_low": (11, Y0 - 3, 20), "wallRep": (12, Y0 - 3, 8), "wallTorch": (13, Y0 - 2, 8),
    "timerOut": (xe + 2, D, LZ + 20), "running": (xe + 4, D, LZ + 18), "E_late": (xe + 6, D, LZ + 17),
    "release": (xe + 6, D, LZ + 19), "relWire": (LEVER[0], D, LZ + 8), "fire": info["fire_point"],
}


def on(r, p):
    q = f"{p[0]} {p[1]} {p[2]}"
    for test, val in (("redstone_wire[power=0]", 0), ("repeater[powered=false]", 0), ("comparator[powered=false]", 0),
                      ("redstone_torch[lit=false]", 0), ("redstone_wall_torch[lit=false]", 0)):
        if "passed" in r.cmd(f"execute if block {q} {test}"):
            return 0
    for test in ("redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch"):
        if "passed" in r.cmd(f"execute if block {q} {test}"):
            return 1
    return "?"


if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 460
    with Rcon(timeout=900) as r:
        lx, ly, lz = LEVER
        r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
        wait_ticks(r, 40)
        state = {k: on(r, p) for k, p in POINTS.items()}
        print("idle:", {k: v for k, v in state.items() if v})
        print("missing blocks:", [k for k, v in state.items() if v == "?"])
        r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=true]")
        t0 = gametime(r)
        while gametime(r) - t0 < dur:
            for k, p in POINTS.items():
                v = on(r, p)
                if v != state[k]:
                    print(f"t+{gametime(r) - t0:4d} {k} -> {v}")
                    state[k] = v
        r.cmd(f"setblock {lx} {ly} {lz} lever[face=floor,facing=north,powered=false]")
