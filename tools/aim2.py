"""Aim calculator for the OSC MK.2 (one module covers a cone of +-44 degrees).

Usage: python aim2.py CELL_X CELL_Z TARGET_X TARGET_Z [west|north|east|south] [--ring R] [--noring]
  CELL_X / CELL_Z  world coordinates of the payload cell (the powder snow block)
  TARGET_X / _Z    centre of the ring of TNT
  direction        which way this cannon module fires (default west)
  --ring R         wanted ring radius in blocks (default: whatever the fastest shot gives)
  --noring         the "no ring charge" lever is on: the ring comes out about 2.5 times smaller

Prints the three counts, the buttons to press, the expected ring and the time to the shot.

How the ring comes about: the 16 payload TNT sit on a small circle in the cell. Every blast
of the middle cell (STRAIGHT) pushes them apart a little more, the two side cells together
almost not at all. So the middle count sets the ring size and the side counts do the rest
of the distance. A target off the axis needs one side count more than the other, and that
stretches the ring into an ellipse.
"""
import math
import sys

from modules import enter_presses

BITS = {"e": 14, "ne": 15, "se": 15}
NAMES = {"e": "STRAIGHT", "ne": "LEFT", "se": "RIGHT"}  # where the count moves the impact, seen along the shot
CELL = (15.5, 8.5)  # payload cell centre in the frame of the west-firing design
# feet of the propellant TNT when it explodes, same frame
SOURCE = {"e": (19.49, 8.5), "ne": (18.49, 5.5), "se": (18.49, 11.5)}
BLAST_UP = 0.98 * 0.0625  # the blast centre lies this far above the feet
SNOW = 0.9  # powder snow: the payload moves 0.9 x its speed in the release tick, then stops
# Push compared with the game's explosion formula. Thirteen real shots (real dupers and
# loaders, up to 6700 blocks) landed within 0.25 blocks of the formula, so nothing is scaled.
SCALE = {"e": 1.0, "ne": 1.0, "se": 1.0}
RADIUS = {True: 0.096, False: 0.0376}  # circle the payload sits on, with / without ring charge
PAYLOAD = 16
SCAN_LIMIT = 2.0e9  # blocks; the game's collision scan overflows at 2^31


def push(px, pz, group):
    """Blocks one count of `group` moves a payload TNT that sits at (px, pz); also its drop speed."""
    sx, sz = SOURCE[group]
    dx, dy, dz = px - sx, -BLAST_UP, pz - sz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    k = (1 - dist / 8) / dist * SCALE[group]
    return SNOW * dx * k, SNOW * dz * k, -dy * k


def landing(counts, px=CELL[0], pz=CELL[1]):
    x, z = px, pz
    for g, n in counts.items():
        if g in SOURCE:
            dx, dz, _ = push(px, pz, g)
            x, z = x + n * dx, z + n * dz
    return x, z


def ring(counts, charge=True):
    """(smallest, largest) distance of the payload TNT from the centre of their landing."""
    cx, cz = landing(counts)
    r = RADIUS[charge]
    dist = []
    for i in range(72):
        a = math.radians(5 * i)
        x, z = landing(counts, CELL[0] + r * math.cos(a), CELL[1] + r * math.sin(a))
        dist.append(math.hypot(x - cx, z - cz))
    return min(dist), max(dist)


def sides(dx, dz, n_e):
    """Side counts that bring the centre to (dx, dz) from the cell when the middle count is n_e."""
    ex, ez, _ = push(*CELL, "e")
    ax, az, _ = push(*CELL, "ne")
    bx, bz, _ = push(*CELL, "se")
    rx, rz = dx - n_e * ex, dz - n_e * ez
    det = ax * bz - az * bx
    return (rx * bz - rz * bx) / det, (ax * rz - az * rx) / det


def solve(dx, dz, want=None, charge=True):
    """Counts for a displacement (dx, dz). want = ring radius, or None for the fastest shot."""
    best = None
    top = min((1 << BITS["e"]) - 1, int(-dx / 0.4) + 3)
    step = max(1, top // 4000)
    for n_e in list(range(0, top + 1, step)):
        a, b = sides(dx, dz, n_e)
        if a < -0.5 or b < -0.5:
            continue
        for na in (math.floor(a), math.ceil(a)):
            for nb in (math.floor(b), math.ceil(b)):
                if na < 0 or nb < 0:
                    continue
                counts = {"e": n_e, "ne": na, "se": nb}
                x, z = landing(counts)
                miss = math.hypot(x - CELL[0] - dx, z - CELL[1] - dz)
                if want is None:
                    score = (round(miss), max(counts.values()), miss)
                else:
                    lo, hi = ring(counts, charge)
                    score = (round(miss), abs((lo + hi) / 2 - want), miss)
                if best is None or score < best[0]:
                    best = (score, counts, (x - CELL[0] - dx, z - CELL[1] - dz))
    if best is None:
        raise SystemExit("No combination of counts reaches that target.")
    return best[1], best[2]


def scan_volume(counts, wx, wz):
    """Blocks the game scans for collisions in the release tick."""
    drop = 1.5 * sum(push(*CELL, g)[2] * counts[g] for g in SOURCE) + 4
    return abs(wx) * abs(wz) * drop


TURNS = {"west": 0, "north": 1, "east": 2, "south": 3}


def _turn(px, pz, turns):
    for _ in range(turns % 4):
        px, pz = -pz, px
    return px, pz


def plan(cell_x, cell_z, target_x, target_z, direction="west", want=None, charge=True):
    turns = TURNS[direction]
    wx, wz = target_x - cell_x, target_z - cell_z  # block centre to block centre
    dx, dz = _turn(wx, wz, -turns % 4)  # back into the frame of the west-firing design
    # At 45 degrees the payload would try to leave sideways first and hit something beside its cell.
    if dx >= 0 or abs(dz) > -dx * 0.97:
        raise SystemExit(f"Target is outside the cone of the {direction} module: less than about 44 degrees off its axis.")
    counts, miss = solve(dx, dz, want, charge)
    if wz < 0 and scan_volume(counts, wx, wz) > SCAN_LIMIT:
        raise SystemExit("Not reachable from here: a long shot with a northward part this far off the axis makes the "
                         "game lose the payload. Shots to the south, straight shots and shorter or flatter northward "
                         "shots are fine.")
    for name, n in counts.items():
        if n >= 1 << BITS[name]:
            raise SystemExit(f"Too far: counter {NAMES[name]} would need {n}, it holds {(1 << BITS[name]) - 1}.")
    return counts, _turn(miss[0], miss[1], turns)


if __name__ == "__main__":
    raw, args, want = sys.argv[1:], [], None
    while raw:
        a = raw.pop(0)
        if a == "--ring":
            want = float(raw.pop(0))
        elif not a.startswith("--") or a.lstrip("-").isdigit():
            args.append(a)
    if len(args) not in (4, 5):
        raise SystemExit(__doc__)
    charge = "--noring" not in sys.argv
    direction = args[4] if len(args) == 5 else "west"
    counts, miss = plan(*map(int, args[:4]), direction, want, charge)
    lo, hi = ring(counts, charge)
    print(f"module firing {direction}; ring charge {'on' if charge else 'OFF (lever on)'}; "
          f"expected miss: {miss[0]:+.2f} blocks in x, {miss[1]:+.2f} in z")
    for key in ("e", "ne", "se"):
        n = counts[key]
        presses = enter_presses(n, BITS[key])
        lit = [k for k in range(BITS[key]) if n >> k & 1]
        print(f"{NAMES[key]:9s} {n:6d}   press buttons {', '.join(map(str, presses)) or '-'}"
              f"   -> lit afterwards: {', '.join(map(str, lit)) or 'none'}")
    print(f"ring of {PAYLOAD} TNT: {lo:.1f} to {hi:.1f} blocks from its centre")
    seconds = (max(counts.values()) * 8 + 2200) / 20
    print(f"from lever to shot: about {seconds / 60:.1f} minutes")
