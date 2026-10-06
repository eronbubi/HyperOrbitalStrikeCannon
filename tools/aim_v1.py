"""Aim calculator for the cannon (one module covers a cone of +-44 degrees).

Usage: python aim.py CELL_X CELL_Z TARGET_X TARGET_Z [west|north|east|south]
  CELL_X / CELL_Z  world coordinates of the payload cell (the powder snow block)
  TARGET_X / _Z    where the payload should come down
  last argument    which way this cannon module fires (default west)

Prints the three propellant counts, the timer, and which buttons to press on each counter.
"""
import sys

from cannon import BITS
from modules import enter_presses

# Measured with real shots on the test server (300 to 6000 propellant per group):
# displacement of the payload = SLOPE * count + OFFSET for every group that is used at all.
SLOPE = {"w": (-0.674556, -0.003340), "nw": (-0.408040, -0.408681), "sw": (-0.411124, 0.407673)}
OFFSET = {"w": (0.0, -0.124), "nw": (-0.176, -0.345), "sw": (-0.302, 0.565)}
START = (0.49, 0.49)  # the payload sits in the north-west corner of its cell


def displacement(counts):
    dx = sum(SLOPE[g][0] * n + OFFSET[g][0] for g, n in counts.items() if g in SLOPE and n)
    dz = sum(SLOPE[g][1] * n + OFFSET[g][1] for g, n in counts.items() if g in SLOPE and n)
    return dx, dz


def solve(dx, dz):
    """Counts (w, nw, sw) whose pushes add up closest to the displacement (dx, dz)."""
    best = None
    for diag in ("nw", "sw"):
        (ax, az), (bx, bz) = SLOPE["w"], SLOPE[diag]
        ox, oz = OFFSET["w"][0] + OFFSET[diag][0], OFFSET["w"][1] + OFFSET[diag][1]
        det = ax * bz - az * bx
        w = ((dx - ox) * bz - (dz - oz) * bx) / det
        d = (ax * (dz - oz) - az * (dx - ox)) / det
        for nw in range(max(1, int(w) - 2), max(1, int(w)) + 4):
            for nd in range(max(0, int(d) - 2), max(0, int(d)) + 4):
                counts = {"w": nw, "nw": 0, "sw": 0}
                counts[diag] = nd
                gx, gz = displacement(counts)
                err = (gx - dx) ** 2 + (gz - dz) ** 2
                if best is None or err < best[0]:
                    best = (err, counts, (gx - dx, gz - dz))
    return best[1], best[2]


TURNS = {"west": 0, "north": 1, "east": 2, "south": 3}


def _turn(px, pz, turns):
    for _ in range(turns % 4):
        px, pz = -pz, px
    return px, pz


def plan(cell_x, cell_z, target_x, target_z, direction="west"):
    turns = TURNS[direction]
    # where the payload rests inside its cell, for a cannon turned that way
    bx, bz = _turn(15 + START[0], 8 + START[1], turns)
    cx, cz = _turn(15.5, 8.5, turns)
    sx, sz = cell_x + 0.5 + (bx - cx), cell_z + 0.5 + (bz - cz)
    wx, wz = target_x + 0.5 - sx, target_z + 0.5 - sz
    dx, dz = _turn(wx, wz, -turns % 4)  # back into the frame of the west-firing design
    # At 45 degrees the payload would try to leave sideways first and hit the wall of its cell.
    if dx >= 0 or abs(dz) > -dx * 0.97:
        raise SystemExit(f"Target is outside the cone of the {direction} module: less than about 44 degrees off its axis.")
    counts, miss = solve(dx, dz)
    for name, n in counts.items():
        if n >= 1 << BITS[name]:
            raise SystemExit(f"Too far: counter {name} would need {n}, it holds {(1 << BITS[name]) - 1}.")
    counts["timer"] = max(counts.values()) + 15
    return counts, _turn(miss[0], miss[1], turns)


if __name__ == "__main__":
    if len(sys.argv) not in (5, 6):
        raise SystemExit(__doc__)
    direction = sys.argv[5] if len(sys.argv) == 6 else "west"
    counts, miss = plan(*map(int, sys.argv[1:5]), direction)
    names = {"w": "W  (straight)", "nw": "NW (right of axis)", "sw": "SW (left of axis)", "timer": "TIMER"}
    print(f"module firing {direction}; expected miss: {miss[0]:+.2f} blocks in x, {miss[1]:+.2f} in z")
    for key in ("w", "nw", "sw", "timer"):
        n = counts[key]
        presses = enter_presses(n, BITS[key])
        lit = [k for k in range(BITS[key]) if n >> k & 1]
        print(f"{names[key]:19s} {n:6d}   press buttons {', '.join(map(str, presses)) or '-'}"
              f"   -> lit afterwards: {', '.join(map(str, lit)) or 'none'}")
    seconds = (counts["timer"] * 8 + 2020) / 20
    print(f"from lever to shot: about {seconds / 60:.1f} minutes")
