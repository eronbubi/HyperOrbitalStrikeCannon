"""Steady-state view of a wire: block and power level at every cell of a path."""
from lab import Rcon

KINDS = ["redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch", "smooth_stone", "air",
         "dispenser", "obsidian", "sticky_piston", "piston_head", "lever"]


def cell(r, p):
    q = f"{p[0]} {p[1]} {p[2]}"
    for k in KINDS:
        if "passed" in r.cmd(f"execute if block {q} {k}"):
            if k == "redstone_wire":
                for lvl in range(16):
                    if "passed" in r.cmd(f"execute if block {q} redstone_wire[power={lvl}]"):
                        return f"w{lvl}"
            if k in ("repeater", "comparator"):
                return ("R" if k == "repeater" else "C") + ("1" if "passed" in r.cmd(f"execute if block {q} {k}[powered=true]") else "0")
            if "torch" in k:
                return "T" + ("1" if "passed" in r.cmd(f"execute if block {q} {k}[lit=true]") else "0")
            return k[:4]
    return "?"


def path(points):
    out = []
    for (x0, y0, z0), (x1, y1, z1) in zip(points, points[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
        for i in range(n):
            out.append((x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n, z0 + (z1 - z0) * i // n))
    out.append(points[-1])
    return out


def show(r, label, points):
    cells = path(points)
    print(label, " ".join(cell(r, p) for p in cells))
