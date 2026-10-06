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

# Measured with real shots on the test server (60 to 7200 counts per group, up to 8500 blocks).
# The W counter drives three dupers at once: one W count moves the payload about 1.03 blocks.
# A diagonal count moves it by ALONE; while the W group fires at the same time each diagonal
# count is a little weaker (TOGETHER is what goes missing per count fired in parallel).
W = (-1.027865, -0.0019086)
W_OFFSET = (0.0, -0.023)
ALONE = {"nw": (-0.409662, -0.411699), "sw": (-0.412806, 0.410785)}
TOGETHER = {"nw": (-0.001587, -0.002910), "sw": (-0.001004, 0.003087)}
START = (0.49, 0.49)  # the payload sits in the north-west corner of its cell
DROP_PER_COUNT = {"w": 0.0354, "nw": 0.0139, "sw": 0.0139}  # downward speed the payload collects
SCAN_LIMIT = 2.0e9  # blocks; the game's collision scan overflows at 2^31


def displacement(counts):
    nw = counts.get("w", 0)
    dx, dz = W[0] * nw, W[1] * nw
    if nw:
        dx, dz = dx + W_OFFSET[0], dz + W_OFFSET[1]
    for g in ("nw", "sw"):
        n = counts.get(g, 0)
        both = min(n, nw)
        dx += ALONE[g][0] * n - TOGETHER[g][0] * both
        dz += ALONE[g][1] * n - TOGETHER[g][1] * both
    return dx, dz


def solve(dx, dz):
    """Counts (w, nw, sw) whose pushes add up closest to the displacement (dx, dz)."""
    best = None
    for diag in ("nw", "sw"):
        for case in ("diag_longer", "w_longer"):
            (ax, az), (bx, bz) = W, ALONE[diag]
            if case == "diag_longer":  # the W group runs the whole time next to part of the diagonal
                ax, az = ax - TOGETHER[diag][0], az - TOGETHER[diag][1]
            else:
                bx, bz = bx - TOGETHER[diag][0], bz - TOGETHER[diag][1]
            det = ax * bz - az * bx
            w = ((dx - W_OFFSET[0]) * bz - (dz - W_OFFSET[1]) * bx) / det
            d = (ax * (dz - W_OFFSET[1]) - az * (dx - W_OFFSET[0])) / det
            for nw in range(max(1, int(w) - 2), max(1, int(w)) + 4):
                for nd in range(max(0, int(d) - 2), max(0, int(d)) + 4):
                    counts = {"w": nw, "nw": 0, "sw": 0}
                    counts[diag] = nd
                    gx, gz = displacement(counts)
                    err = (gx - dx) ** 2 + (gz - dz) ** 2
                    if best is None or err < best[0]:
                        best = (err, counts, (gx - dx, gz - dz))
    return best[1], best[2]


def scan_volume(counts, wx, wz):
    """Blocks the game scans for collisions in the release tick (see modules.chamber)."""
    drop = 1.5 * sum(DROP_PER_COUNT[g] * counts.get(g, 0) for g in DROP_PER_COUNT) + 4
    return abs(wx) * abs(wz) * drop


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
    if wz < 0 and scan_volume(counts, wx, wz) > SCAN_LIMIT:
        raise SystemExit("Not reachable from here: a long shot with a northward part this far off the axis makes the "
                         "game lose the payload (it drops through the chamber floor). Shots to the south, straight "
                         "shots and shorter or flatter northward shots are fine.")
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
