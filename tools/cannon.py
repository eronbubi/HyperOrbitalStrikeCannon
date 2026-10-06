"""Whole overworld cannon (one module, firing cone = west +-45 degrees), in design coordinates.

Chunk grid of the design: payload chunk (0,0) = x 0..15, z 0..15. The always-on loader in
chunk (2,1) makes chunks 1..3 / 0..2 tick entities and leaves the payload chunk block-ticking.
Place the build so that these coordinates keep their position inside the chunks (shift by
multiples of 16 only).

Floor plan of the control deck (y = D), x east, z south:
  z -2..2   counter SW      z 4..8  counter W      z 10..14  counter NW   (x 26..78)
  z 17..19  aligner pulse former and its wire
  z 20      lever at x=22 and the main delay line eastwards
  z 21..25  loader station (x 17..21) / fire pulse former (x 23..25) / payload former
  z 27      payload wire -> stairs down      z 31  enable wire -> stairs down
  z 36..40  timer counter (mirrored, its clock sits at the east end)
  z 42      release line back west
"""
from build import Build, items
from modules import PITCH, chamber, counter, driver, duper_side, shaft, station

Y0 = 84  # payload cell
D = Y0 + 30  # control deck and the two diagonal dupers
CELL = (15, Y0, 8)
BITS = {"w": 14, "nw": 15, "sw": 15, "timer": 15}
# dupers: name -> (counter group, x, y, z, side row). Each sits on top of its own drop shaft.
# The W group has three: straight west, and a pair four blocks to either side whose sideways
# pushes cancel. Heights fall off outwards so that no shaft has to pass through a duper.
UNITS = {
    "w": ("w", 17, D + 8, 8, 1),
    "w_n": ("w", 17, D, 12, 1),
    "w_s": ("w", 17, D, 4, -1),
    "nw": ("nw", 17, D + 4, 10, 1),
    "sw": ("sw", 17, D + 4, 6, -1),
}
CELLS = (-4, -2, 0, 2, 4)
XC = 33
COUNTER = {"sw": (XC, D, -2), "w": (XC, D, 8), "nw": (XC, D, 14)}
LINE = (22, D, 24)  # where the main delay line starts
LEVER = (25, D - 5, 12)  # on the lower platform, at the start of the departure delay
O3 = (19, D - 1, 28)  # on-demand station, turned 180 degrees, chunk (1,1)
O1 = (40, D - 41, 24)  # always-on station, chunk (2,1); 40 lower so the nether tells the two apart
FLOOR = "smooth_stone"

# game ticks after the lever at which the main line is tapped (multiples of 8)
T_ALIGN = 240
T_PAYLOAD = (280, 304)
T_ENABLE = 368


class Wiring:
    def __init__(self, build):
        self.b = build

    def dust(self, x, y, z):
        self.b.set(x, y - 1, z, FLOOR)
        self.b.set(x, y, z, "redstone_wire")

    def repeater(self, x, y, z, facing, delay=1):
        self.b.set(x, y - 1, z, FLOOR)
        self.b.set(x, y, z, "repeater", facing=facing, delay=delay)

    def comparator(self, x, y, z, facing, mode="subtract"):
        self.b.set(x, y - 1, z, FLOOR)
        self.b.set(x, y, z, "comparator", facing=facing, mode=mode)

    def block(self, x, y, z):
        self.b.set(x, y, z, FLOOR)

    @staticmethod
    def facing(dx, dz):
        """Repeater facing for a signal travelling in direction (dx, dz): it faces its input."""
        return {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}[(dx, dz)]

    def run(self, points, boost=13, since=0):
        """Dust along axis-parallel legs through `points` (one level).

        `since` = dust cells the signal has already crossed since its last repeater; a new
        repeater goes in before it would fade (every `boost` cells). Returns the new `since`.
        """
        cells = []
        for (x0, y0, z0), (x1, y1, z1) in zip(points, points[1:]):
            assert y0 == y1 and (x0 == x1 or z0 == z1), points
            dx, dz = (x1 > x0) - (x1 < x0), (z1 > z0) - (z1 < z0)
            for i in range(abs(x1 - x0) + abs(z1 - z0)):
                cells.append(((x0 + dx * i, y0, z0 + dz * i), (dx, dz)))
        cells.append((points[-1], cells[-1][1]))
        for i, (pos, d) in enumerate(cells):
            since += 1
            straight = 0 < i < len(cells) - 1 and cells[i - 1][1] == d and cells[i + 1][1] == d
            if since >= boost and straight:
                self.repeater(*pos, self.facing(*d))
                since = 0
            else:
                self.dust(*pos)
        return since

    def stairs(self, start, dx, dz, steps, dy=-1, boost=11, since=0):
        """Dust staircase, one block down (or up) per step in direction (dx, dz).

        Returns (last cell, since). Landings with a repeater are added where the signal needs one.
        """
        x, y, z = start
        self.dust(x, y, z)
        since += 1
        for _ in range(steps):
            if since >= boost:  # landing: repeater plus one more dust on this level
                self.repeater(x + dx, y, z + dz, self.facing(dx, dz))
                self.dust(x + 2 * dx, y, z + 2 * dz)
                x, z = x + 2 * dx, z + 2 * dz
                since = 1
            x, y, z = x + dx, y + dy, z + dz
            self.dust(x, y, z)
            since += 1
        return (x, y, z), since


def stairs_start(end_x, steps, from_x, z, since=0):
    """x where a west-going staircase must start so that it ends at end_x, fed from from_x along z."""
    for sx in range(end_x + steps, from_x - 1):
        w = Wiring(Build())
        n = w.run([(from_x, 0, z), (sx + 1, 0, z)], since=since)
        end, _ = w.stairs((sx, 0, z), -1, 0, steps, since=n)
        if end[0] == end_x:
            return sx
    raise ValueError("no room for the staircase")


def mirror_z(build):
    m = Build()
    for (x, y, z), state in build.blocks.items():
        m.blocks[(x, y, -z)] = state
    return m


def overworld(stations=True):
    b = Build()
    w = Wiring(b)
    info = {}

    cb, cp = chamber(CELLS)
    b.merge(cb, *CELL)
    b.set(CELL[0], Y0 + 1, CELL[2], "dispenser", facing="down", nbt=items("tnt"))  # the payload
    b.set(14, Y0 - 2, 8, "sticky_piston", facing="up")  # temporary west wall, up while idle
    b.set(14, Y0 - 1, 8, FLOOR)

    info["dupers"] = list(UNITS)
    for name, (group, x, y, z, side) in UNITS.items():
        db, dp = duper_side(side)
        b.merge(db, x, y, z)
        sb, sp = shaft(y - (Y0 + 2))
        b.merge(sb if side == 1 else mirror_z(sb), x, y, z)
        info[f"duper_{name}"] = {k: (x + v[0], y + v[1], z + side * v[2]) for k, v in dp.items()}

    outs = {}
    for name, (x, y, z) in COUNTER.items():
        kb, kp = counter(BITS[name])
        vb, vp = driver()
        b.merge(kb, x, y, z)
        b.merge(vb, x, y, z)
        outs[name] = (x + vp["out"][0], y, z)
        info[f"counter_{name}"] = {"bit0": (x, y, z), "step": (PITCH, 0, 0), "bits": BITS[name]}
        info[f"disable_{name}"] = (x + vp["disable"][0], y, z + vp["disable"][2])

    # counter pulses -> duper pistons. Every line ends in a dust beside the piston that is
    # reached from the east, so that it points at the piston.
    ox, oy, oz = outs["sw"]  # up a staircase to the SW duper
    w.run([(ox, oy, oz), (ox, oy, 4)])
    w.repeater(ox, oy, 5, "north")  # fresh signal, so the staircase needs no landing
    end, _ = w.stairs((ox, oy, 6), -1, 0, 5, dy=1)
    assert end == info["duper_sw"]["power"], end
    ox, oy, oz = outs["nw"]
    n = w.run([(ox, oy, oz), (ox, oy, 11)])
    end, _ = w.stairs((ox, oy, 10), -1, 0, 5, dy=1, since=n)
    assert end == info["duper_nw"]["power"], end
    ox, oy, oz = outs["w"]  # (26, D, 8)
    w.repeater(ox - 1, oy, oz, "east")
    w.run([(24, oy, 8), (24, oy, 9), (22, oy, 9)])
    w.run([(22, oy, 8), (22, oy, 4)], since=5)  # trunk in front of the tower
    w.run([(22, oy, 10), (22, oy, 12)], since=5)
    for z in (4, 12):  # the two outer W dupers stand on deck level
        b.set(21, oy, z, FLOOR)
        b.set(21, oy + 1, z, "redstone_wire")
    for i in range(1, 9):  # ladder of top slabs up to the middle W duper
        x = 23 if i % 2 else 22
        b.set(x, oy + i - 1, 8, "smooth_stone_slab", type="top")
        b.set(x, oy + i, 8, "redstone_wire")
    b.set(21, oy + 8, 8, FLOOR)
    b.set(21, oy + 9, 8, "redstone_wire")

    sequencer(b, w, info)

    if stations:
        tb, tp = station(auto_send=False)
        b.merge(tb.rotated(2), *O3)
        ab, ap = station()
        b.merge(ab, *O1)
        info["o3_send"] = (O3[0] - tp["send"][0], O3[1] + tp["send"][1], O3[2] - tp["send"][2])
        info["o1_send"] = tuple(O1[i] + ap["send"][i] for i in range(3))
    info["fire_point"] = (O3[0], D, O3[2] + 1)
    return b, info


DELAY_ROWS = 8  # x 25 repeaters x 8 gt = 80 s between the lever and the start of the sequence


def departure_delay(b, w):
    """Lever and a snake of 4-tick repeaters under the counters.

    A player anywhere near keeps every chunk ticking, and then the payload would simply
    blow up in its cell. The snake gives time to get away before anything happens.
    """
    lx, y, lz = LEVER
    b.set(lx, y - 1, lz, FLOOR)
    b.set(lx, y, lz, "lever", face="floor", facing="north", powered=False)
    z = lz
    for row in range(DELAY_ROWS):
        east = row % 2 == 0
        xs = range(26, 51) if east else range(50, 25, -1)
        for x in xs:
            w.repeater(x, y, z, "west" if east else "east", delay=4)
        if row < DELAY_ROWS - 1:
            tx = 51 if east else 25
            for dz in (0, -1, -2):
                w.dust(tx, y, z + dz)
            z -= 2
    # out at the west end of the last row, round to x=23 and up to the main line
    w.run([(25, y, z), (22, y, z), (22, y, lz), (23, y, lz), (23, y, lz + 4)])
    w.repeater(23, y, lz + 5, "north")
    end, _ = w.stairs((23, y, lz + 6), 0, 1, 5, dy=1)
    assert end == (LINE[0] + 1, LINE[1], LINE[2] - 1), end


def sequencer(b, w, info):
    """One lever, one line of repeaters, taps at fixed times.

    lever on -> short pulse to the on-demand loader: the payload chunk ticks for 300 gt
             -> T_ALIGN: one cycle of the NW duper; its TNT explodes last and pushes the
                payload into the north-west corner of its cell
             -> T_PAYLOAD: dispenser pulses, the payload
             -> T_ENABLE (payload chunk asleep again): wall down, counters and timer run
             -> timer at zero: second pulse to the loader. That is the shot.
    """
    lx, y, lz = LINE
    departure_delay(b, w)
    w.dust(lx + 1, y, lz)

    # main delay line eastwards: 4-tick repeaters, plain dust where a tap leaves
    taps = sorted({T_ALIGN, T_PAYLOAD[0], T_PAYLOAD[1], T_ENABLE})
    x, t, tap_x = lx + 2, 0, {}
    while taps:
        if t >= taps[0]:
            w.dust(x, y, lz)
            tap_x[taps.pop(0)] = x
        else:
            w.repeater(x, y, lz, "west", delay=4)
            t += 8
        x += 1
    xa, xp, xq, xe = tap_x[T_ALIGN], tap_x[T_PAYLOAD[0]], tap_x[T_PAYLOAD[1]], tap_x[T_ENABLE]
    info["taps"] = tap_x

    # fire pulse: lever minus the same signal 6 gt later
    w.dust(lx + 1, y, lz + 1)
    w.comparator(lx + 1, y, lz + 2, "north")
    w.dust(lx + 2, y, lz + 1)
    w.dust(lx + 3, y, lz + 1)
    w.dust(lx + 3, y, lz + 2)
    w.repeater(lx + 2, y, lz + 2, "east", delay=3)
    for z in (lz + 3, lz + 4, lz + 5):  # fire net, down to the station's row
        w.dust(lx + 1, y, z)
    w.dust(lx, y, lz + 5)
    for x in (lx - 1, lx - 2, lx - 3):  # repeaters, because the station's clock dust lies diagonally below
        w.repeater(x, y, lz + 5, "east")

    # aligner: 6 gt pulse into the NW piston line
    w.dust(xa, y, lz - 1)
    w.comparator(xa, y, lz - 2, "south")
    w.dust(xa + 1, y, lz - 1)
    w.dust(xa + 2, y, lz - 1)
    w.dust(xa + 2, y, lz - 2)
    w.repeater(xa + 1, y, lz - 2, "east", delay=3)
    w.run([(xa, y, lz - 3), (24, y, lz - 3), (24, y, 12)], since=2)
    w.repeater(25, y, 12, "west")  # diode into the NW piston line at (26, y, 12)

    # payload: the window between two taps powers a 4 gt oscillator
    w.dust(xp, y, lz + 1)
    w.comparator(xp, y, lz + 2, "north")
    w.dust(xq, y, lz + 1)
    w.run([(xq, y, lz + 2), (xp + 2, y, lz + 2)])
    w.repeater(xp + 1, y, lz + 2, "east")
    w.dust(xp, y, lz + 3)
    w.comparator(xp, y, lz + 4, "north")
    w.dust(xp, y, lz + 5)
    w.dust(xp + 1, y, lz + 5)
    w.dust(xp + 1, y, lz + 4)
    w.repeater(xp + 2, y, lz + 4, "west")
    drop = y - (Y0 + 2)
    sx = stairs_start(15, drop, xp + 3, lz + 7, since=3)
    n = w.run([(xp + 3, y, lz + 4), (xp + 3, y, lz + 7), (sx + 1, y, lz + 7)])
    end, n = w.stairs((sx, y, lz + 7), -1, 0, drop, since=n)
    assert end == (15, Y0 + 2, lz + 7), end
    w.run([(14, Y0 + 2, lz + 7), (13, Y0 + 2, lz + 7), (13, Y0 + 2, 8), (14, Y0 + 2, 8)], since=n)
    b.set(CELL[0], Y0 + 2, CELL[2], "redstone_wire")  # on top of the dispenser
    info["payload_wire_end"] = end

    # enable E = end of the line. North: torch = D, held up to the three counter clocks.
    w.repeater(xe + 1, y, lz, "west")  # the tap dust is a junction and would not point at the block
    w.block(xe + 2, y, lz)
    b.set(xe + 2, y - 1, lz, FLOOR)
    b.set(xe + 2, y, lz - 1, "redstone_wall_torch", facing="north", lit=True)
    top, n = w.stairs((xe + 2, y, lz - 2), 0, -1, 2, dy=1)
    bus_x = XC - 2
    w.run([(top[0] - 1, top[1], top[2]), (bus_x, y + 2, top[2]), (bus_x, y + 2, 2)], since=n)
    for name, (cx, cy, cz) in COUNTER.items():
        dz = cz + 4
        w.dust(bus_x, y + 2, dz)
        b.set(bus_x - 1, y, dz, FLOOR)
        b.set(bus_x - 1, y + 1, dz, "redstone_wire")  # steps down onto the driver's disable dust

    # E south: down to the wall piston, and a second torch for the timer
    w.run([(xe, y, lz + 1), (xe, y, lz + 14)])
    w.block(xe, y, lz + 15)
    b.set(xe, y - 1, lz + 15, FLOOR)
    b.set(xe, y, lz + 16, "redstone_wall_torch", facing="south", lit=True)
    b.set(xe, y - 1, lz + 16, FLOOR)
    sx = stairs_start(11, y - (Y0 - 3), xe - 1, lz + 11, since=11)
    n = w.run([(xe - 1, y, lz + 11), (sx + 1, y, lz + 11)], since=11)
    foot, n = w.stairs((sx, y, lz + 11), -1, 0, y - (Y0 - 3), since=n)
    assert foot == (11, Y0 - 3, lz + 11), foot
    w.run([(11, Y0 - 3, lz + 10), (11, Y0 - 3, 8)], since=n)
    w.repeater(12, Y0 - 3, 8, "west")
    w.block(13, Y0 - 3, 8)
    b.set(13, Y0 - 2, 8, "redstone_torch", lit=True)  # beside the wall piston: on = wall up
    info["wall_torch"] = (13, Y0 - 2, 8)

    # timer: mirrored counter, bit 0 at its east end, clock further east
    to = (xe - 5, y, lz + 20)
    tb = Build()
    kb, kp = counter(BITS["timer"])
    vb, vp = driver()
    tb.merge(kb)
    tb.merge(vb)
    b.merge(tb.rotated(2), *to)
    info["counter_timer"] = {"bit0": to, "step": (-PITCH, 0, 0), "bits": BITS["timer"]}
    # release = E (24 gt late) minus "timer clock still pulsing"
    for i in (1, 2, 3):
        w.repeater(xe + i, y, lz + 10, "west", delay=4)
    w.run([(xe + 4, y, lz + 10), (xe + 6, y, lz + 10), (xe + 6, y, lz + 17)])
    w.comparator(xe + 6, y, lz + 18, "north")
    # 4 gt on / 4 gt off -> steady level: the pulses plus the same pulses 4 gt later.
    # (One slow repeater does not do it: its turn-off lands exactly in the gaps.)
    w.dust(xe + 2, y, lz + 19)
    w.repeater(xe + 3, y, lz + 20, "west", delay=1)
    w.repeater(xe + 3, y, lz + 19, "west", delay=3)
    for z in (lz + 20, lz + 19, lz + 18):
        w.dust(xe + 4, y, z)
    w.repeater(xe + 5, y, lz + 18, "west")
    w.repeater(xe + 6, y, lz + 19, "north")  # the comparator only passes on what is left of E
    w.run([(xe + 6, y, lz + 20), (xe + 6, y, lz + 22), (lx, y, lz + 22), (lx, y, lz + 8)])
    for z in (lz + 7, lz + 6):  # repeaters: the station's clock dust lies diagonally below here
        w.repeater(lx, y, z, "south")
    info["E"] = (xe, y, lz)


N3 = (O3[0] // 8, O3[1], O3[2] // 8)  # nether partner of the on-demand station, turned the same way
N1 = (O1[0] // 8, O1[1], O1[2] // 8)


def nether():
    """The two nether stations, in nether coordinates = design coordinates / 8, same height.

    The game links a portal to the nearest one on the other side, so each station must
    stand at one eighth of its overworld partner's x/z. The 40 blocks of height between the
    two pairs are what keeps them from being confused.
    """
    b = Build()
    sb, sp = station()
    b.merge(sb.rotated(2), *N3)
    b.merge(sb, *N1)
    return b, {"n3_send": (N3[0] - sp["send"][0], N3[1] + sp["send"][1], N3[2] - sp["send"][2]),
               "n1_send": tuple(N1[i] + sp["send"][i] for i in range(3))}


# --- the same cannon turned in 90 degree steps ------------------------------------------
# turns = 0 fires west, 1 north, 2 east, 3 south (clockwise seen from above).

_SHIFT = {0: (0, 0), 1: (-1, 0), 2: (-1, -1), 3: (0, -1)}
DIRECTION = {0: "west", 1: "north", 2: "east", 3: "south"}


def turn_point(p, turns):
    """Block position after turning the design about the chunk corner at x=0, z=0.

    Build.rotated turns about the centre of block (0,0); the extra shift moves that to the
    block corner, so chunk borders land on chunk borders again.
    """
    x, y, z = p
    for _ in range(turns % 4):
        x, z = -z, x
    sx, sz = _SHIFT[turns % 4]
    return (x + sx, y, z + sz)


def turn_vector(v, turns):
    x, y, z = v
    for _ in range(turns % 4):
        x, z = -z, x
    return (x, y, z)


def turn_build(build, turns):
    out = Build()
    sx, sz = _SHIFT[turns % 4]
    out.merge(build.rotated(turns), sx, 0, sz)
    return out


def _turn_info(value, turns):
    if isinstance(value, dict):
        return {k: (turn_vector(v, turns) if k == "step" else _turn_info(v, turns)) for k, v in value.items()}
    if isinstance(value, tuple) and len(value) == 3 and all(isinstance(c, int) for c in value):
        return turn_point(value, turns)
    return value


def overworld_turned(turns, stations=True):
    b, info = overworld(stations)
    info = _turn_info(info, turns)
    info["cell"] = turn_point(CELL, turns)
    info["lever"] = turn_point(LEVER, turns)
    info["wall"] = turn_point((14, Y0, 8), turns)
    info["o3"] = turn_point(O3, turns)
    info["o1"] = turn_point(O1, turns)
    return turn_build(b, turns), info


def nether_turned(turns):
    """Nether stations for a turned cannon: each at one eighth of its overworld partner."""
    b = Build()
    sb, sp = station()
    info = {}
    for name, origin, extra in (("n3", O3, 2), ("n1", O1, 0)):
        ox, oy, oz = turn_point(origin, turns)
        pos = (ox // 8, oy, oz // 8)
        b.merge(sb.rotated(turns + extra), *pos)
        info[name] = pos
    return b, info
