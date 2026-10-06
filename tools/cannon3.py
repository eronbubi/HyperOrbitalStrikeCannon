"""MK.3: whole overworld cannon (one module, firing cone = west +-45 degrees), design coordinates.

Chunk grid of the design: payload chunk (0,0) = x 0..15, z 0..15, block-ticking only. Chunk
(1,0) holds everything that needs ticking entities (propellant cells, feeds, dupers).
"""
from build import Build, items
from modules import duper_side, rot_point
from modules2 import SOURCES, TRAP

Y0 = 84  # payload cell
CELL = (15, Y0, 8)
WALL = "obsidian"  # everything near slime or water: immovable and blast-proof

# Feed unit of each propellant cell: (ledge side of the cell as dx, dz; quarter turns of the
# duper, 0 = body to the east; side of its slime row; extra height of the duper).
# One duper per cell, and the ledge on the far side from the payload. Tried and dropped:
# - two ledges on opposite sides: a thrown TNT slides 3 blocks and shoots through the cell;
# - two ledges on neighbouring sides: both dupers push their top block into the same place,
#   and TNT lying in the cell is kicked out through the second opening by its neighbours.
FEEDS = {
    "e": [((1, 0), 0, 1, 3)],
    "ne": [((1, 0), 0, -1, 3)],
    "se": [((1, 0), 0, 1, 3)],
}
SIGNS = set()
# Walls between the propellant cells, off every line of sight to the payload: without them
# the blasts of one cell throw the TNT waiting in the next one about.
SHIELDS = [(3, -1), (4, -1), (3, 1), (4, 1)]
_FACING = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}


def funnel(side=1):
    """Trough under a duper (duper frame): duped TNT appears in x 0..2 one level below the
    slot, water carries strays west, and everything leaves through the hole at (0, -3, 0)."""
    b = Build()
    for x in range(0, 3):
        for y in (-1, -2):
            b.set(x, y, -side, WALL)
        b.set(x, -2, side, WALL)
    for y in (-1, -2, -3):
        b.set(-1, y, 0, WALL)
    for y in (-1, -2):
        b.set(3, y, 0, WALL)
    for x in (1, 2):
        b.set(x, -3, 0, WALL)
    for z in (-1, 1):
        b.set(0, -3, z, WALL)
    b.set(2, -2, 0, "water", level=0)
    return b


def place(b, x, y, z, name, clashes, **props):
    """Set a block; note it when something that is not a wall or a trapdoor was there."""
    old = b.get(x, y, z)
    if old and old[0] not in ("minecraft:obsidian", "minecraft:iron_trapdoor") and old[0] != f"minecraft:{name}":
        clashes.append(((x, y, z), old[0], name))
    b.set(x, y, z, name, **props)


def merge(b, other, dx, dy, dz, clashes):
    for (x, y, z), (name, props) in other.blocks.items():
        pos = (x + dx, y + dy, z + dz)
        old = b.get(*pos)
        if old and old[0] != name and not (old[0] in ("minecraft:obsidian", "minecraft:iron_trapdoor") and name == "minecraft:obsidian"):
            clashes.append((pos, old[0], name))
    b.merge(other, dx, dy, dz)


STACK = (1, 0, -1)  # stack cell, seen from the flight cell
TRANSFER = 3  # TNT that throw the stack over into the flight cell


def chamber3():
    """Firing chamber of MK.3. Local origin = flight cell.

    Stack cell (diagonal neighbour, in the next chunk to the north): powder snow under the
    payload dispenser. Its chunk sleeps while the payload is dispensed, so every TNT stays
    on the dispenser's point with its fuse at 80 and its own random push. When the chunk
    wakes they all take their first step together: a circle of radius 0.0376, one fuse.
    Flight cell: powder snow, nothing beside it, in a chunk that still sleeps. The transfer
    charge in the NE propellant cell throws the whole circle over into it.
    Both cells stand on a single iron bar post.
    """
    b = Build()
    sx, sy, sz = STACK
    b.set(0, 0, 0, "powder_snow")
    b.set(0, -1, 0, "iron_bars", north=False, east=False, south=False, west=False, waterlogged=False)
    b.set(sx, 0, sz, "powder_snow")
    b.set(sx, -1, sz, "iron_bars", north=False, east=False, south=False, west=False, waterlogged=False)
    b.set(sx, 1, sz, "dispenser", facing="down", nbt=items("tnt"))
    for dx, dz in SOURCES.values():
        b.set(dx, -1, dz, "obsidian")
        for ox, oz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            b.set(dx + ox, 0, dz + oz, "iron_trapdoor", **TRAP)
            b.set(dx + ox, -1, dz + oz, "obsidian")
        b.set(dx, 0, dz, "water", level=0)
    points = {"payload": (0, 0, 0), "stack": STACK, "payload_dispenser": (sx, 1, sz)}
    points.update({f"prop_{k}": (dx, 0, dz) for k, (dx, dz) in SOURCES.items()})
    return b, points


def core():
    """Chamber, feeds and dupers. Returns (build, info).

    Feed of one duper: the duped TNT falls straight down a column and lands on a ledge beside
    the propellant cell, on the cell's own level. A blast in the cell can only shove it
    against the wall there. A slime block on a sticky piston, on the same pulse line as the
    duper, then throws it sideways into the cell.
    Measured on the way to this: a TNT that falls in full view of the blasts is juggled until
    it goes off in mid-air; a TNT lying in a water current creeps one block in 30 ticks; a
    plain piston moves a TNT half a block and takes it back when it retracts.
    """
    b = Build()
    cb, cp = chamber3()
    b.merge(cb, *CELL)
    cx, cy, cz = CELL
    clashes = []
    for dx, dz in SHIELDS:
        b.set(cx + dx, cy, cz + dz, WALL)
        b.set(cx + dx, cy - 1, cz + dz, WALL)
    info = {"cell": CELL, "dupers": [], "groups": {}}
    for name, units in FEEDS.items():
        sx, sz = cx + SOURCES[name][0], cz + SOURCES[name][1]
        b.set(sx, cy + 1, sz, WALL)  # lid of the cell: nothing above it sees a blast
        info["groups"][name] = []
        info[f"prop_{name}"] = (sx, cy, sz)
        for i, ((dx, dz), turns, side, rise) in enumerate(units):
            key = name if len(units) == 1 else f"{name}{i + 1}"
            lx, lz = sx + dx, sz + dz
            b.blocks.pop((lx, cy, lz), None)  # the ledge itself: open towards the cell
            px, pz = -dz, dx  # across the feed line
            for k in (1, -1):
                wx, wz = lx + k * px, lz + k * pz
                if (wx - cx, wz - cz) in SIGNS:
                    place(b, wx, cy - 1, wz, WALL, clashes)
                    place(b, wx, cy, wz, "oak_sign", clashes, rotation=0, waterlogged=False)
                else:
                    place(b, wx, cy, wz, WALL, clashes)
            for step in (0, 1, 2):
                place(b, lx + step * dx, cy - 1, lz + step * dz, WALL, clashes)
            place(b, lx + dx, cy, lz + dz, "slime_block", clashes)
            place(b, lx + 2 * dx, cy, lz + 2 * dz, "sticky_piston", clashes, facing=_FACING[(-dx, -dz)], extended=False)
            ox, oy, oz = lx, cy + 4 + rise, lz
            for y in range(cy + 1, oy - 3):  # column between the hole and the ledge
                for wx, wz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    place(b, lx + wx, y, lz + wz, WALL, clashes)
            merge(b, funnel(side).rotated(turns), ox, oy, oz, clashes)
            db, dp = duper_side(side)
            merge(b, db.rotated(turns), ox, oy, oz, clashes)
            points = {}
            for k, v in dp.items():
                qx, qy, qz = rot_point((v[0], v[1], v[2] * side), turns)
                points[k] = (ox + qx, oy + qy, oz + qz)
            points["pusher"] = (lx + 2 * dx, cy, lz + 2 * dz)
            points["pusher_power"] = (lx + 3 * dx, cy, lz + 3 * dz)
            points["ledge"] = (lx, cy, lz)
            info[f"duper_{key}"] = points
            info["dupers"].append(key)
            info["groups"][name].append(key)
    info.update({k: (cx + v[0], cy + v[1], cz + v[2]) for k, v in cp.items()})
    lx, ly, lz = info["duper_ne"]["ledge"]
    b.set(lx + 1, ly + 2, lz, "dispenser", facing="west", nbt=items("tnt"))
    b.set(lx, ly + 2, lz - 1, "dispenser", facing="south", nbt=items("tnt"))
    b.set(lx, ly + 2, lz + 1, "dispenser", facing="north", nbt=items("tnt"))
    info["transfer"] = [(lx + 1, ly + 2, lz), (lx, ly + 2, lz - 1), (lx, ly + 2, lz + 1)]
    info["clashes"] = clashes
    return b, info


# --- the complete cannon -------------------------------------------------------------------
#
# Floor plan (x east, z south), control deck on y = D:
#   z -8..-2  master clock, its inverter, start of the pusher line          (x 24..31)
#   z 2..18   counters NE-cell / E-cell / SE-cell rows                      (x 26..77)
#   z 14..20  explosion listener, pulse stretcher, release gate             (x 13..24)
#   z 20      "enable, late" back west (deck) and "enable" west (two levels up)
#   z 24      main delay line eastwards; fire, ring charge, payload, enable taps
#   z 25..29  pulse formers; z 33 transfer wire, z 35 payload wire, both back west
# Under the counters (y = D-3): the departure delay.

from cannon import DIRECTION, FLOOR, Wiring, _turn_info, turn_build, turn_point
from modules import PITCH, counter, station

D = Y0 + 8  # control deck = level of the duper pistons
XC = 33  # x of bit 0 of every counter
ROWS = {"ne": 2, "e": 8, "se": 14}  # z of the bulb row
BITS = {"e": 14, "ne": 15, "se": 15}
LINE = (22, D, 24)
LEVER = (21, D, 2)
# Chunk grid of the design: the flight cell (15, 8) is the north-east corner block of its
# chunk, so chunk borders lie at x = 2 + 16k and z = 8 + 16k. SHIFT moves the finished build
# so that they land on multiples of 16.
SHIFT = (-2, 0, -8)
OA = (26, D - 1, -15)  # wakes the stack cell's chunk; chunk (1,-2)
OB = (30, D - 9, 19)  # release station; chunk (1,0)
O1 = (42, D - 17, 0)  # always-on station; chunk (2,-1)
PAYLOAD = 64  # TNT per shot; the dispenser gives one every 4 gt

# game ticks after the start of the main line at which it is tapped (multiples of 8)
T_PAYLOAD = 8
T_TRANSFER = T_PAYLOAD + 4 * PAYLOAD + 16  # after the last payload TNT is out
T_ENABLE = T_TRANSFER + 40  # propellant needs 100 gt more before it goes off: the stack has jumped by then
LATE = 24  # four-tick repeaters between "enable" and the release gate

SOLID = {"minecraft:smooth_stone", "minecraft:obsidian", "minecraft:dispenser", "minecraft:dropper",
         "minecraft:hopper", "minecraft:smooth_stone_slab"}


class Safe(Wiring):
    """Wiring that refuses to overwrite anything and keeps what is already a floor."""

    def __init__(self, build):
        super().__init__(build)
        self.net = "?"
        self.nets = {}  # dust position -> name of its signal, for check()

    def put(self, x, y, z, name, **props):
        old = self.b.get(x, y, z)
        assert old is None, f"{name} at {(x, y, z)} would replace {old[0]} (net {self.net})"
        self.b.set(x, y, z, name, **props)

    def floor(self, x, y, z):
        old = self.b.get(x, y, z)
        if old is None:
            self.b.set(x, y, z, WALL if x < 26 and z < 14 else FLOOR)
        else:
            assert old[0] in SOLID, f"no floor at {(x, y, z)}: {old[0]} (net {self.net})"

    def dust(self, x, y, z):
        self.floor(x, y - 1, z)
        self.put(x, y, z, "redstone_wire")
        self.nets[(x, y, z)] = self.net

    def repeater(self, x, y, z, facing, delay=1):
        self.floor(x, y - 1, z)
        self.put(x, y, z, "repeater", facing=facing, delay=delay)

    def comparator(self, x, y, z, facing, mode="subtract"):
        self.floor(x, y - 1, z)
        self.put(x, y, z, "comparator", facing=facing, mode=mode)

    def block(self, x, y, z):
        self.put(x, y, z, FLOOR)

    def add(self, other, dx, dy, dz, net=None):
        """Merge a module; nothing may be replaced. Its dust gets the net name `net`."""
        for (x, y, z), (name, props) in other.blocks.items():
            pos = (x + dx, y + dy, z + dz)
            old = self.b.get(*pos)
            assert old is None or (old[0] == name and name in SOLID), f"{name} at {pos} would replace {old[0]}"
            if name == "minecraft:redstone_wire":
                self.nets[pos] = net or f"module{dx},{dz}"
        self.b.merge(other, dx, dy, dz)


def driver2():
    """Low end of a counter (same frame as modules.driver, x < 0), clocked from outside.

    The comparator passes the counter's 'nonzero' signal whenever its side input is off. The
    side input is the inverted master clock, so every counter that is not at zero gives one
    pulse per clock cycle, all of them in step. That step is what the slime pushers of the
    feeds need (see overworld()).
    points['disable']: inverted clock in. points['out']: pulses for the duper piston.
    """
    b = Build()
    for x, z in [(-1, 2), (-2, 2), (-3, 2), (-4, 2), (-5, 2), (-5, 1), (-5, 0), (-4, 0), (-3, 0),
                 (-2, 0), (-1, 0), (-6, 0), (-7, 0), (-2, 3), (-4, 3), (-4, 4)]:
        b.set(x, -1, z, FLOOR)
    b.set(-1, 0, 2, "repeater", facing="east", delay=1)  # bit 0, fast path
    b.set(-2, 0, 3, "repeater", facing="south", delay=1)  # bits 1.. from the nonzero line
    b.set(-2, 0, 2, "redstone_wire")
    b.set(-3, 0, 2, "redstone_wire")
    b.set(-4, 0, 2, "comparator", facing="east", mode="subtract")
    b.set(-4, 0, 3, "repeater", facing="south", delay=1)  # inverted clock
    b.set(-4, 0, 4, "redstone_wire")
    for pos in ((-5, 0, 2), (-5, 0, 1), (-5, 0, 0), (-4, 0, 0), (-3, 0, 0), (-2, 0, 0), (-1, 0, 0)):
        b.set(*pos, "redstone_wire")
    b.set(-6, 0, 0, "repeater", facing="east", delay=1)  # diode towards the duper
    b.set(-7, 0, 0, "redstone_wire")
    return b, {"out": (-7, 0, 0), "disable": (-4, 0, 4)}


def descend(w, points, end_x, steps):
    """Run through `points`, on westwards, then a staircase down that ends at x = end_x.

    A repeater right before the first step gives the staircase a fresh signal, so it needs
    no landing and its length is known. Returns (since, last cell).
    """
    px, py, pz = points[-1]
    sx = end_x + steps
    w.run(points + [(sx + 2, py, pz)])
    w.repeater(sx + 1, py, pz, "east")
    end, n = w.stairs((sx, py, pz), -1, 0, steps)
    return n, end


def overworld(stations=True, post=False):
    b, info = core()
    w = Safe(b)
    y = D
    for key, origin, auto in (("oa", OA, False), ("ob", OB, False), ("o1", O1, True)):
        sb, sp = station(auto_send=auto)
        if stations:
            w.add(sb, *origin)
        info[f"{key}_send"] = tuple(origin[i] + sp["send"][i] for i in range(3))

    # --- counters, and their pulses to the duper pistons (dust only: no delay on the way)
    for name, z0 in ROWS.items():
        w.add(counter(BITS[name])[0], XC, y, z0, net=f"counter_{name}")
        w.add(driver2()[0], XC, y, z0, net=f"counter_{name}")
        info[f"counter_{name}"] = {"bit0": (XC, y, z0), "step": (PITCH, 0, 0), "bits": BITS[name]}
        w.nets[(XC - 7, y, z0)] = f"duper_{name}"
        w.nets[(XC - 4, y, z0 + 4)] = "bus"
    w.net = "duper_e"
    w.run([(25, y, 8), (24, y, 8)])
    w.net = "duper_ne"
    w.run([(25, y, 2), (25, y, 5), (23, y, 5)])
    w.net = "duper_se"
    w.run([(25, y, 14), (25, y, 11), (23, y, 11)])
    for name in ROWS:
        assert w.nets.get(info[f"duper_{name}"]["power"]) == f"duper_{name}", name

    # --- slime pushers of the three feeds: one trunk on the level of the cells
    w.net = "pusher"
    w.repeater(25, y, -5, "east")  # from the clock dust at (26, y, -5)
    end, _ = w.stairs((24, y, -5), 0, 1, 8)
    assert end == (24, Y0, 3), end
    w.repeater(24, Y0, 4, "north")
    w.run([(24, Y0, 5), (24, Y0, 11)], boost=99)
    for pos in ((23, Y0, 5), (22, Y0, 5), (23, Y0, 8), (23, Y0, 11), (22, Y0, 11)):
        w.dust(*pos)
    for name in ROWS:
        assert w.nets.get(info[f"duper_{name}"]["pusher_power"]) == "pusher", name

    # --- master clock (north-west corner of the deck)
    # E arrives at (28, y, -2). Comparator oscillator: 4 gt on, 4 gt off while E is on.
    w.net = "clock"
    w.repeater(28, y, -3, "south")
    w.comparator(28, y, -4, "south")
    for pos in ((28, y, -5), (27, y, -5), (26, y, -5), (26, y, -4)):
        w.dust(*pos)
    w.repeater(27, y, -4, "west")  # feedback into the comparator's side
    # Inverter: a comparator that subtracts the clock from a redstone block. (A torch burns
    # out here: it would have to switch 15 times in 60 gt, and the dupers then ran in bursts.)
    w.repeater(28, y, -6, "south")
    w.comparator(28, y, -7, "west")
    w.floor(27, y - 1, -7)
    w.put(27, y, -7, "redstone_block")
    w.net = "bus"
    for x in (29, 30, 31):
        w.dust(x, y, -7)
    top, _ = w.stairs((31, y + 1, -6), 0, 1, 1, dy=1)
    assert top == (31, y + 2, -5), top
    w.run([(31, y + 2, -4), (31, y + 2, 4)], boost=99)
    w.repeater(31, y + 2, 5, "north")  # the last repeater: from here on dust only, so that
    w.run([(31, y + 2, 6), (31, y + 2, 18)], boost=99)  # all three counters switch in the same tick
    for z0 in ROWS.values():
        w.dust(30, y + 1, z0 + 4)  # one step down onto the counter's 'disable' dust

    # --- departure delay under the counters: lever, 200 four-tick repeaters = 80 s
    w.net = "lever"
    lx, ly, lz = LEVER
    w.floor(lx, ly - 1, lz)
    w.put(lx, ly, lz, "lever", face="floor", facing="north", powered=False)
    end, _ = w.stairs((lx + 1, ly, lz), 1, 0, 3)
    sy = y - 3
    assert end == (25, sy, 2), end
    w.net = "snake"
    for k in range(8):
        z, east = 2 + 2 * k, k % 2 == 0
        for x in (range(26, 51) if east else range(50, 25, -1)):
            w.repeater(x, sy, z, "west" if east else "east", delay=4)
        if k < 7:
            for dz in (0, 1, 2):
                w.dust(51 if east else 25, sy, z + dz)
    w.run([(25, sy, 16), (23, sy, 16)])
    w.repeater(23, sy, 17, "north")
    w.dust(23, sy, 18)
    w.dust(23, sy, 19)
    end, _ = w.stairs((23, sy, 20), 0, 1, 3, dy=1)
    assert end == (LINE[0] + 1, y, LINE[2] - 1), end

    # --- main delay line eastwards: four-tick repeaters, plain dust where a tap leaves
    w.net = "line"
    mx, _, mz = LINE
    w.dust(mx + 1, y, mz)
    taps = {"p0": T_PAYLOAD, "p1": T_PAYLOAD + 4 * PAYLOAD, "transfer": T_TRANSFER, "enable": T_ENABLE}
    todo = sorted(taps.items(), key=lambda kv: kv[1])
    x, t, tap = mx + 2, 0, {}
    while todo:
        if t >= todo[0][1]:
            w.net = f"tap_{todo[0][0]}"
            w.dust(x, y, mz)
            tap[todo.pop(0)[0]] = x
        else:
            w.repeater(x, y, mz, "west", delay=4)
            t += 8
        x += 1
    info["taps"] = tap
    xp, xq, xt, xe = tap["p0"], tap["p1"], tap["transfer"], tap["enable"]
    cx, _, cz = CELL

    # payload: the window between two taps powers a 4 gt oscillator, one TNT per pulse.
    # The stack cell's chunk sleeps meanwhile: the TNT pile up, fuses untouched.
    w.net = "tap_p0"
    w.dust(xp, y, mz + 1)
    w.comparator(xp, y, mz + 2, "north")
    w.net = "tap_p1"
    w.dust(xq, y, mz + 1)
    w.run([(xq, y, mz + 2), (xp + 2, y, mz + 2)])
    w.repeater(xp + 1, y, mz + 2, "east")
    w.net = "window"
    w.dust(xp, y, mz + 3)
    w.comparator(xp, y, mz + 4, "north")
    w.net = "payload_osc"
    w.dust(xp, y, mz + 5)
    w.dust(xp + 1, y, mz + 5)
    w.dust(xp + 1, y, mz + 4)
    w.repeater(xp + 2, y, mz + 4, "west")
    w.net = "payload"
    py = Y0 + 2  # dust on top of the payload dispenser
    n, end = descend(w, [(xp + 3, y, mz + 4), (xp + 3, y, mz + 9)], 16, y - py)
    assert end == (16, py, mz + 9), end
    w.run([(15, py, mz + 9), (15, py, cz), (cx + STACK[0], py, cz), (cx + STACK[0], py, cz + STACK[2])], since=n)
    assert w.nets.get((info["payload_dispenser"][0], py, info["payload_dispenser"][2])) == "payload"

    # transfer: one 6 gt pulse, carried round the west side to the north-west corner. There it
    # fires the three transfer dispensers, 16 gt later the station that wakes the stack cell's
    # chunk, and 24 gt later one stroke of the slime pushers (the transfer TNT lie on a ledge).
    w.net = "tap_transfer"
    w.dust(xt, y, mz + 1)
    w.comparator(xt, y, mz + 2, "north")
    w.net = "transfer_late"
    w.dust(xt + 1, y, mz + 1)
    w.dust(xt + 2, y, mz + 1)
    w.dust(xt + 2, y, mz + 2)
    w.repeater(xt + 1, y, mz + 2, "east", delay=3)
    w.net = "transfer"
    w.run([(xt, y, mz + 3), (xt, y, mz + 11), (11, y, mz + 11), (11, y, -3), (20, y, -3)])
    w.repeater(21, y, -3, "west")
    w.dust(22, y, -3)
    end, _ = w.stairs((22, y, -2), 0, 1, 6)
    assert end == (22, Y0 + 2, 4), end
    w.dust(22, Y0 + 2, 5)
    w.dust(22, Y0 + 2, 6)
    for z in (4, 6):  # a powered block between two dispensers fires both
        w.repeater(21, Y0 + 2, z, "east")
        w.put(20, Y0 + 2, z, WALL)
    w.repeater(22, y, -4, "south", delay=4)
    w.repeater(22, y, -5, "south", delay=4)
    w.net = "wake"
    w.dust(22, y, -6)
    w.run([(21, y, -6), (20, y, -6), (20, y, OA[2] - 1), (23, y, OA[2] - 1)])
    for x in (24, 25, 26):  # repeaters: the station's clock dust lies diagonally below
        w.repeater(x, y, OA[2] - 1, "west")
    w.repeater(22, y, -7, "south", delay=3)
    w.net = "transfer_push"
    w.run([(22, y, -8), (24, y, -8), (24, y, -7)], boost=99)
    w.repeater(24, y, -6, "north")

    # --- E = end of the line. Along z = 20 it runs west twice: on the deck through LATE slow
    # repeaters to the release gate, and two levels up to the master clock.
    w.net = "enable"
    w.dust(xe, y, mz - 1)
    w.dust(xe, y, mz - 2)
    w.repeater(xe, y, mz - 3, "south")
    w.net = "late"
    w.dust(xe, y, 20)
    for i in range(1, LATE + 1):
        w.repeater(xe - i, y, 20, "east", delay=4)
    w.run([(xe - LATE - 1, y, 20), (26, y, 20)])
    w.repeater(25, y, 20, "east")
    w.run([(24, y, 20), (24, y, 18), (20, y, 18)], boost=99)
    w.net = "enable"
    w.dust(xe + 1, y, mz)
    top, n = w.stairs((xe + 2, y + 1, mz), 1, 0, 1, dy=1)
    w.run([(top[0], y + 2, mz - 1), (top[0], y + 2, 20), (28, y + 2, 20), (28, y + 2, 2)], since=n + 1)
    w.repeater(28, y + 2, 1, "south")
    end, _ = w.stairs((28, y + 2, 0), 0, -1, 2)
    assert end == (28, y, -2), end

    # --- release: a calibrated sculk sensor that hears explosions only. It answers every
    # 32 gt with a 10 gt pulse while propellant goes off; four delayed copies fill the gaps.
    # "Enable, late" minus that signal = everything has gone off -> the release station fires.
    w.net = "heard"
    w.put(22, y, 14, "calibrated_sculk_sensor", facing="west", power=0, sculk_sensor_phase="inactive", waterlogged=False)
    w.put(23, y, 14, "redstone_block")  # input 15 = frequency of an explosion
    for x in (21, 19, 17, 15, 13):
        w.net = f"heard{x}"
        w.dust(x, y, 14)
        if x > 13:
            w.repeater(x - 1, y, 14, "east", delay=4)
        w.repeater(x, y, 15, "north")
    w.net = "busy"
    w.run([(13, y, 16), (21, y, 16)], boost=99)
    w.repeater(19, y, 17, "north")
    w.comparator(19, y, 18, "east")
    w.net = "release"
    w.dust(18, y, 18)
    w.repeater(17, y, 18, "east")
    w.dust(16, y, 18)
    end, n = w.stairs((16, y, 19), 1, 0, 7, since=1)
    assert end == (23, OB[1] + 2, 19), end
    send = info["ob_send"]
    w.run([(24, send[1] + 1, 19), (24, send[1] + 1, send[2]), (send[0], send[1] + 1, send[2])], since=n)

    if post:
        import post as mail
        mail.receiver(w, info, XC, ROWS, BITS, D)
    info["lever"] = LEVER
    info["sensor"] = (22, y, 14)
    info["gate"] = (18, y, 18)
    info["line"] = (LINE[0] + 1, y, LINE[2] - 1)
    info["probe"] = {"enable": (28, y, -2), "late": (20, y, 18), "busy": (19, y, 16), "wake": (22, y, -6)}
    info["nets"] = w.nets
    return shifted(b, info)


def shifted(b, info):
    """Move the build so that the chunk borders of the design lie on multiples of 16."""
    def move(v):
        if isinstance(v, dict):
            return {key: (val if key == "step" else move(val)) for key, val in v.items()}
        if isinstance(v, list):
            return [move(e) for e in v]
        if isinstance(v, tuple) and len(v) == 3 and all(isinstance(c, int) for c in v):
            return (v[0] + SHIFT[0], v[1] + SHIFT[1], v[2] + SHIFT[2])
        return v

    out = Build()
    out.merge(b, *SHIFT)
    nets = {move(p): n for p, n in info.pop("nets").items()}
    info = move(info)
    info["nets"] = nets
    return out, info


def _at(p):
    return (p[0] + SHIFT[0], p[1], p[2] + SHIFT[2])


STATIONS = {"a": (_at(OA), 0), "b": (_at(OB), 0), "1": (_at(O1), 0)}  # placed origin, extra quarter turns


def nether():
    return nether_turned(0)


# --- the same cannon turned in 90 degree steps: 0 fires west, 1 north, 2 east, 3 south ---

def overworld_turned(turns, stations=True, post=False):
    b, info = overworld(stations, post)
    info.pop("nets")
    info = _turn_info(info, turns)
    return turn_build(b, turns), info


OM = (28, D + 7, -3)  # receiving portal of the nether post (post.receiver)


def nether_turned(turns, post=False):
    """Nether stations for a turned cannon: each at one eighth of its overworld partner, same height."""
    b = Build()
    sb, _ = station()
    info = {}
    todo = dict(STATIONS)
    if post:
        todo["m"] = (_at(OM), 0)
    for name, (origin, extra) in todo.items():
        ox, oy, oz = turn_point(origin, turns)
        pos = (ox // 8, oy, oz // 8)
        b.merge(sb.rotated(turns + extra), *pos)
        info[name] = pos
    return b, info


_STEP = ((1, 0), (-1, 0), (0, 1), (0, -1))
_CONDUCTOR = SOLID - {"minecraft:hopper", "minecraft:smooth_stone_slab"} | {"minecraft:waxed_copper_bulb", "minecraft:redstone_block"}
_SOURCES = ("minecraft:redstone_block", "minecraft:lever", "minecraft:redstone_wall_torch", "minecraft:redstone_torch",
            "minecraft:calibrated_sculk_sensor")


def check(b, nets):
    """Wires that touch although they carry different signals. Returns a list of findings."""
    def solid(p):
        s = b.get(*p)
        return bool(s) and s[0] in _CONDUCTOR

    found = []
    for (x, y, z), net in nets.items():
        for dx, dz in _STEP:
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy, z + dz)
                if q not in nets or nets[q] == net or q < (x, y, z):
                    continue
                if dy == 1 and solid((x, y + 1, z)) or dy == -1 and solid((x + dx, y, z + dz)):
                    continue
                found.append(f"dust {net} {(x, y, z)} touches dust {nets[q]} {q}")
        for q in ((x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1), (x, y + 1, z), (x, y - 1, z)):
            s = b.get(*q)
            if s and s[0] in _SOURCES:
                found.append(f"dust {net} {(x, y, z)} beside {s[0].split(':')[1]} {q}")
    return found


if __name__ == "__main__":
    import sys
    build, facts = overworld(post="post" in sys.argv)
    (x0, y0, z0), (x1, y1, z1) = build.bounds()
    print(len(build.blocks), "blocks,", (x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1), "from", (x0, y0, z0), "taps", facts["taps"])
    for key in ("cell", "stack", "prop_e", "prop_ne", "prop_se", "oa_send", "ob_send", "o1_send"):
        px, _, pz = facts[key]
        print(f"  {key:8s} {facts[key]} chunk ({px // 16}, {pz // 16})")
    print("clashes:", facts["clashes"])
    for line in check(build, facts["nets"]):
        print(" ", line)
