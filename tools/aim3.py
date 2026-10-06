"""Aim calculator for the OSC MK.3 (one module covers a cone of +-44 degrees).

Usage: python aim3.py CELL_X CELL_Z TARGET_X TARGET_Z [west|north|east|south] [--ring R]
  CELL_X / CELL_Z  world coordinates of the flight cell (the powder snow block with nothing above it)
  TARGET_X / _Z    centre of the ring of TNT
  direction        which way this cannon module fires (default west)
  --ring R         wanted ring radius in blocks (default: whatever the fastest shot gives)

Prints the three counts, the buttons to press, the expected ring and the time to the shot.

How the ring comes about: the 65 payload TNT sit on a small circle in the cell, all with one fuse. Every blast
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
CELL = (0.0, 0.0)  # flight cell centre; everything below is measured from it, in the west-firing frame
# feet of the propellant TNT when it explodes
SOURCE = {"e": (3.99, 0.0), "ne": (2.99, -3.0), "se": (2.99, 3.0)}
BLAST_UP = 0.98 * 0.0625  # the blast centre lies this far above the feet
SNOW = 0.9  # powder snow: a TNT moves 0.9 x its speed in one tick, then stops
STACK = (1.0, -1.0)  # where the payload is piled up before the transfer charge throws it over
TRANSFER = 3  # TNT of the transfer charge; they go off in the NE cell
RADIUS = 0.0376  # circle the pile opens into when its chunk wakes up
PAYLOAD = 65
SCAN_LIMIT = 2.0e9  # blocks; the game's collision scan overflows at 2^31
# Nothing here is fitted: eleven real shots (real dupers and loaders) landed within 0.3 blocks.


def push(px, pz, group):
    """Blocks one blast of `group` moves a TNT that sits at (px, pz); also its drop speed."""
    sx, sz = SOURCE[group]
    dx, dy, dz = px - sx, -BLAST_UP, pz - sz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    k = (1 - dist / 8) / dist
    return SNOW * dx * k, SNOW * dz * k, -dy * k


def transfer(px, pz):
    """Where a TNT of the pile ends up in the flight cell."""
    dx, dz, _ = push(px, pz, "ne")
    return px + TRANSFER * dx, pz + TRANSFER * dz


START = transfer(*STACK)  # centre of the payload in the flight cell: (-0.233, +0.239)


def landing(counts, px=None, pz=None):
    if px is None:
        px, pz = START
    x, z = px, pz
    for g, n in counts.items():
        if g in SOURCE:
            dx, dz, _ = push(px, pz, g)
            x, z = x + n * dx, z + n * dz
    return x, z


def displacement(counts):
    """Ring centre measured from the centre of the flight cell."""
    return landing(counts)


def ring(counts, charge=True):
    """(smallest, largest) distance of the payload TNT from the centre of their landing."""
    cx, cz = landing(counts)
    dist = []
    for i in range(72):
        a = math.radians(5 * i)
        x, z = landing(counts, *transfer(STACK[0] + RADIUS * math.cos(a), STACK[1] + RADIUS * math.sin(a)))
        dist.append(math.hypot(x - cx, z - cz))
    return min(dist), max(dist)


def sides(dx, dz, n_e):
    """Side counts that bring the centre to (dx, dz) from the cell when the middle count is n_e."""
    ex, ez, _ = push(*START, "e")
    ax, az, _ = push(*START, "ne")
    bx, bz, _ = push(*START, "se")
    rx, rz = dx - START[0] - n_e * ex, dz - START[1] - n_e * ez
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
                miss = math.hypot(x - dx, z - dz)
                if want is None:
                    score = (round(miss), max(counts.values()), miss)
                else:
                    lo, hi = ring(counts, charge)
                    score = (round(miss), abs((lo + hi) / 2 - want), miss)
                if best is None or score < best[0]:
                    best = (score, counts, (x - dx, z - dz))
    if best is None:
        raise SystemExit("No combination of counts reaches that target.")
    return best[1], best[2]


def scan_volume(counts, wx, wz):
    """Blocks the game scans for collisions in the release tick."""
    drop = 1.5 * sum(push(*START, g)[2] * counts[g] for g in SOURCE) + 4
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
    charge = True
    direction = args[4] if len(args) == 5 else "west"
    counts, miss = plan(*map(int, args[:4]), direction, want, charge)
    lo, hi = ring(counts, charge)
    print(f"module firing {direction}; expected miss: {miss[0]:+.2f} blocks in x, {miss[1]:+.2f} in z")
    for key in ("e", "ne", "se"):
        n = counts[key]
        presses = enter_presses(n, BITS[key])
        lit = [k for k in range(BITS[key]) if n >> k & 1]
        print(f"{NAMES[key]:9s} {n:6d}   press buttons {', '.join(map(str, presses)) or '-'}"
              f"   -> lit afterwards: {', '.join(map(str, lit)) or 'none'}")
    print(f"ring of {PAYLOAD} TNT: {lo:.1f} to {hi:.1f} blocks from its centre")
    seconds = (max(counts.values()) * 8 + 2260) / 20
    print(f"from lever to shot: about {seconds / 60:.1f} minutes")
