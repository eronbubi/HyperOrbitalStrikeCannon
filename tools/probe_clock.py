"""MK.2: which signal stops when the dupers pause? Starts the main line directly."""
import time

from cannon2 import D, LINE, nether, overworld
from exp_mk2 import build, enter, lit
from exp_shot import at
from lab import Rcon, step

POINTS = {"E": (28, D, -2), "C": (28, D, -5), "bus": (31, D + 2, 12), "dis": (29, D, 12), "nz": (30, D, 10),
          "out": (26, D, 8), "trunk": (24, D - 8, 8)}

if __name__ == "__main__":
    b, info = overworld()
    nb, _ = nether()
    with Rcon(timeout=900) as r:
        build(r, b, info, nb)
        enter(r, info, {"e": 30, "ne": 30, "se": 30})
        r.cmd("tick freeze"); time.sleep(0.3)
        r.cmd(f"setblock {LINE[0] + 1} {D} {LINE[2] - 1} redstone_block")
        step(r, 380)
        rows = {k: "" for k in POINTS}
        rows["piston"] = ""
        for t in range(380, 700):
            step(r, 1)
            for k, p in POINTS.items():
                rows[k] += "." if lit(r, p, "redstone_wire[power=0]") else "#"
            rows["piston"] += "#" if lit(r, (23, D, 8), "sticky_piston[extended=true]") else "."
        for a in range(0, 320, 160):
            print(f"t{380 + a}")
            for k, v in rows.items():
                print(f"  {k:7s}{v[a:a + 160]}")
        r.cmd(f"setblock {LINE[0] + 1} {D} {LINE[2] - 1} air")
        r.cmd("tick unfreeze")
