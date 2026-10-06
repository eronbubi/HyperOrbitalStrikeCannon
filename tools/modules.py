"""Cannon modules as Build objects, each verified on the test server.

Coordinates are module-local; +x east, +z south. Use Build.rotated / rot_point to turn them.
"""
from build import Build


def rot_point(p, quarter_turns):
    """Same clockwise rotation as Build.rotated, for a block position."""
    x, y, z = p
    for _ in range(quarter_turns % 4):
        x, z = -z, x
    return (x, y, z)


def duper():
    """Stationary TNT duper: one primed TNT per piston cycle, dropped below the TNT block.

    Own layout, derived from the 1.21.11 piston code and verified on the server:
    the detector rail with its minecart is pushed directly by the piston, so it is the
    last block to land and the TNT under the slime below it is powered without ever
    getting a block update. On the retract stroke the coral fan loses its support for a
    moment, updates the TNT, and the TNT primes while its block still travels home.

    Returns (build, points). The TNT is NOT part of the build: placing it in the slot by
    hand would ignite it. Place it in points['prime'] and run one piston cycle.
    """
    b = Build()
    b.set(3, 1, 0, "sticky_piston", facing="west")
    b.set(2, 1, 0, "slime_block")  # pushes the minecart west
    b.set(1, 1, 0, "detector_rail", shape="east_west")
    b.set(0, 1, 0, "smooth_stone")  # pushes the minecart back east
    b.set(1, 0, 0, "slime_block")  # carries the rail and passes its power down to the TNT
    b.set(2, 0, 0, "slime_block")
    for pos in ((0, 0, 1), (0, 1, 1), (1, 0, 1), (1, -1, 1), (2, -1, 1)):
        b.set(*pos, "slime_block")
    b.set(2, -1, 0, "dead_tube_coral_wall_fan", facing="north", waterlogged=False)
    points = {
        "power": (4, 1, 0),  # power this block position to extend the piston
        "rail": (1, 1, 0),  # minecart sits here
        "slot": (1, -1, 0),  # where the TNT block lives while running
        "prime": (0, -1, 0),  # where to place the TNT by hand before the first cycle
    }
    return b, points


TRAP = dict(half="top", open=False, facing="north", powered=False, waterlogged=False)


def chamber(cells=(-2, 0, 2)):
    """Firing chamber. Local origin = payload cell; the chunk border must lie between x=0 and x=1.

    x=0 (payload chunk, block-ticking only): powder snow cell, walls north/south.
    x=1: iron trapdoors in the top half. They stop TNT entities but let explosion rays through.
    x=2 (entity-ticking chunk): water cells where propellant TNT explodes without breaking
    blocks, at the z offsets in `cells`; trapdoors between them. z=0 pushes straight west, a
    cell at +z sits south-east of the payload and pushes north-west, one at -z south-west.

    Known limit, left as it is: an explosion is centred 0.061 above the feet of its TNT, so
    every propellant also pushes the payload down a little (290 blocks' worth after 12 000).
    The floor absorbs that - unless the game's collision scan (range x width x that drop)
    exceeds 2^31 blocks AND the shot goes towards -z: then the scan stops before it reaches
    the floor and the payload leaves through it (lost twice on the test server, 7800 blocks at
    40 degrees to the north-west). aim.py refuses such targets.
    Tried and dropped: propellant on dirt path, 1/16 lower, to level the blast with the payload.
    The blast centre then lies inside the path block instead of the water, the explosion breaks
    blocks, and the chamber destroyed itself on the first shot.
    """
    b = Build()
    edge = max(abs(c) for c in cells) + 1
    for x in range(0, 4):
        for z in range(-edge, edge + 1):
            b.set(x, -1, z, "obsidian")
    b.set(0, 0, 0, "powder_snow")
    b.set(0, 0, -1, "iron_trapdoor", **TRAP)
    b.set(0, 0, 1, "iron_trapdoor", **TRAP)
    for z in range(-edge + 1, edge):
        b.set(1, 0, z, "iron_trapdoor", **TRAP)
        if z in cells:
            b.set(2, 0, z, "water", level=0)
        else:
            b.set(2, 0, z, "iron_trapdoor", **TRAP)
    for z in range(-edge, edge + 1):
        b.set(3, 0, z, "obsidian")
    for x in (1, 2):
        for z in (-edge, edge):
            b.set(x, 0, z, "obsidian")
    points = {"payload": (0, 0, 0), "wall": (-1, 0, 0)}
    points.update({f"prop_{z}": (2, 0, z) for z in cells})
    points.update({"prop_w": (2, 0, 0), "prop_nw": (2, 0, 2), "prop_sw": (2, 0, -2)})
    return b, points


def station(auto_send=True):
    """Portal bounce station (same layout in both dimensions).

    Local frame: portal in the x/y plane at z=0, inside x 0..1, y 1..3. The send dropper
    stands north of the portal and shoots south; an item coming back flies out south into
    the catch box, runs through the hoppers round the frame and is lifted into the send
    dropper again. Every arrival adds a 300 tick portal ticket: 3x3 chunks tick entities,
    the ring around them only blocks.

    The droppers are clocked by a comparator in subtract mode that reads a full water
    cauldron and feeds its own side: it flips every 2 game ticks and cannot stall. (Two
    observers facing each other did stall on the test server.)

    auto_send=True: send dropper sits on the lift dropper and fires with it (endless loop).
    auto_send=False: a hopper carries the item from lift to send dropper, which only fires
    when points['fire'] is powered. A powered dropper would otherwise fire its neighbour.
    """
    b = Build()
    for y in (1, 2, 3):
        b.set(-1, y, 0, "obsidian")
        b.set(2, y, 0, "obsidian")
    for x in (0, 1):
        b.set(x, 0, 0, "obsidian")
        b.set(x, 4, 0, "obsidian")
        for y in (1, 2, 3):
            b.set(x, y, 0, "nether_portal", axis="x")
    b.set(1, 1, -1, "dropper", facing="south")  # send
    lz = -1 if auto_send else -2  # z of the lift dropper
    b.set(1, 0, lz, "dropper", facing="up")
    if not auto_send:
        b.set(1, 1, -2, "hopper", facing="south")
    # clock: cauldron -> comparator (subtract) -> three dust back to its own side. The last
    # dust flips 1/0; a repeater takes that into the lift dropper. (Dust alone will not do:
    # it also connects to the comparator and then no longer points at the dropper.)
    b.set(0, 0, lz - 1, "water_cauldron", level=3)
    b.set(-1, 0, lz - 1, "comparator", facing="east", mode="subtract")
    for pos in ((-2, 0, lz - 1), (-2, 0, lz), (-1, 0, lz)):
        b.set(*pos, "redstone_wire")
    b.set(0, 0, lz, "repeater", facing="west", delay=1)
    for pos in ((-1, -1, lz - 1), (-2, -1, lz - 1), (-2, -1, lz), (-1, -1, lz), (0, -1, lz)):
        b.set(*pos, "obsidian")
    b.set(0, 0, 1, "hopper", facing="east")
    b.set(0, 0, 2, "hopper", facing="east")
    b.set(1, 0, 2, "hopper", facing="north")
    b.set(1, 0, 1, "hopper", facing="east")
    b.set(2, 0, 1, "hopper", facing="north")
    b.set(2, 0, 0, "hopper", facing="north")
    if auto_send:
        b.set(2, 0, -1, "hopper", facing="west")
    else:
        b.set(2, 0, -1, "hopper", facing="north")
        b.set(2, 0, -2, "hopper", facing="west")
    for y in (1, 2):
        for z in (1, 2):
            b.set(-1, y, z, "obsidian")
            b.set(2, y, z, "obsidian")
        for x in (-1, 0, 1, 2):
            b.set(x, y, 3, "obsidian")
    for x in (-1, 0, 1, 2):
        b.set(x, 0, 3, "obsidian")
    b.set(-1, 0, 1, "obsidian")
    b.set(-1, 0, 2, "obsidian")
    b.set(2, 0, 2, "obsidian")
    points = {"send": (1, 1, -1), "lift": (1, 0, lz), "fire": (0, 1, -1), "portal": (1, 1, 0)}
    return b, points


PITCH = 3  # blocks per counter bit


def counter(bits):
    """Ripple down-counter from waxed copper bulbs. Local frame: bit k at x = 3k, chain along +x.

    A copper bulb toggles on a rising edge, and bulb k switching ON is exactly the borrow of
    a binary decrement. Each link turns that switching-on into one short pulse for the next
    bulb: comparator (subtract) reads the bulb, and its side gets the same signal a moment
    later through a second comparator and a repeater. Pulses, not levels, on purpose: with
    levels a lit bulb keeps its neighbour powered, the neighbour's button stops working and
    arming the counter clocks every bulb once (seen on the test server).

    Lit bulbs are the number in binary, bit 0 at x=0. A button press on bit k always
    subtracts 2^k (a dark bulb borrows from its neighbours), so a number is entered from
    zero by pressing the bits of its two's complement: enter_presses().
    z=3/4: 'nonzero' line of bits 1.. ; bit 0 has its own faster path in driver().
    """
    b = Build()
    length = PITCH * bits
    for x in range(-2, length):
        for z in range(0, 5):
            b.set(x, -1, z, "smooth_stone")
    for k in range(bits):
        x = PITCH * k
        b.set(x, 0, 0, "waxed_copper_bulb", lit=False, powered=False)
        b.set(x, 1, 0, "stone_button", face="floor", facing="north")
        b.set(x, 0, 1, "comparator", facing="north", mode="compare")
        b.set(x, 0, 2, "redstone_wire")
        if k:
            b.set(x, 0, 3, "repeater", facing="north", delay=1)  # onto the nonzero line
        if k < bits - 1:
            b.set(x + 1, 0, 0, "comparator", facing="west", mode="subtract")
            b.set(x + 2, 0, 0, "repeater", facing="west", delay=1)
            b.set(x + 1, 0, 2, "redstone_wire")
            b.set(x + 1, 0, 1, "repeater", facing="south", delay=2)  # delayed copy of the bulb
    for x in range(-2, PITCH * (bits - 1) + 1):
        if x > 0 and x % 12 == 1:  # x = 3k+1: no bit feeds this piece
            b.set(x, 0, 4, "repeater", facing="east", delay=1)
        else:
            b.set(x, 0, 4, "redstone_wire")
    return b, {"bulb0": (0, 0, 0)}


def enter_presses(value, bits, current=0):
    """Bits whose buttons to press (once each, slowly) to get from `current` to `value`."""
    diff = (current - value) % (1 << bits)
    return [k for k in range(bits) if diff >> k & 1]


def driver():
    """Clock that sits at the low end of a counter (same local frame, x < 0).

    The counter's 'nonzero' signal is the power source of a comparator oscillator (subtract
    mode, output fed back to its side through a repeater: 4 gt on, 4 gt off). It pulses
    exactly while the counter is not zero and every pulse counts down by one, so no inverter
    is needed. Bit 0 reaches the oscillator within 6 gt; that is what stops it before a
    further pulse could wrap the counter round to all ones.

    points['disable']: powered = oscillator held off (second side input of the comparator).
    points['out']: the same pulses for a duper piston.
    """
    b = Build()
    for x, z in [(-1, 2), (-2, 2), (-3, 2), (-4, 2), (-5, 2), (-5, 1), (-5, 0), (-4, 0), (-4, 1), (-3, 0),
                 (-2, 0), (-1, 0), (-6, 0), (-7, 0), (-2, 3), (-4, 3), (-4, 4)]:
        b.set(x, -1, z, "smooth_stone")
    b.set(-1, 0, 2, "repeater", facing="east", delay=1)  # bit 0, fast path
    b.set(-2, 0, 3, "repeater", facing="south", delay=1)  # bits 1.. from the nonzero line
    b.set(-2, 0, 2, "redstone_wire")
    b.set(-3, 0, 2, "redstone_wire")
    b.set(-4, 0, 2, "comparator", facing="east", mode="subtract")
    b.set(-4, 0, 1, "repeater", facing="north", delay=1)  # feedback
    b.set(-4, 0, 3, "repeater", facing="south", delay=1)  # disable
    b.set(-4, 0, 4, "redstone_wire")
    for pos in ((-5, 0, 2), (-5, 0, 1), (-5, 0, 0), (-4, 0, 0), (-3, 0, 0), (-2, 0, 0), (-1, 0, 0)):
        b.set(*pos, "redstone_wire")
    b.set(-6, 0, 0, "repeater", facing="east", delay=1)  # diode towards the duper
    b.set(-7, 0, 0, "redstone_wire")
    points = {"out": (-7, 0, 0), "disable": (-4, 0, 4)}
    return b, points


def duper_side(side=1):
    """duper() with its slime side row on +z (side=1) or -z (side=-1)."""
    b, points = duper()
    if side == 1:
        return b, points
    m = Build()
    for (x, y, z), (name, props) in b.blocks.items():
        p = dict(props)
        if p.get("facing") in ("north", "south"):
            p["facing"] = "south" if p["facing"] == "north" else "north"
        m.set(x, y, -z, name, **p)
    return m, points


def shaft(height):
    """Feed from a duper down into a propellant cell. Local frame = duper frame.

    y=-2: funnel. Duped TNT appears anywhere in x 0..2; water on the floor under x 1..2
    carries it west to x=0. From there a 1x1 column drops `height` blocks straight onto
    the propellant cell (the block below the column, points['cell']).

    The column is tall on purpose. Propellant that is already waiting in the cell explodes
    every few ticks and kicks falling TNT straight back up; with a short shaft it flew up
    into the duper and blew it up (test server). After a long fall it is faster than the
    kick, so it still lands.
    """
    b = Build()
    bottom = -1 - height
    for x in range(-1, 4):  # funnel walls and rim round the duper's TNT layer
        for y in (-1, -2):
            b.set(x, y, -1, "obsidian")
        b.set(x, -2, 1, "obsidian")
    for y in (-1, -2):
        b.set(-1, y, 0, "obsidian")
        b.set(3, y, 0, "obsidian")
    for x in (1, 2):
        b.set(x, -3, 0, "obsidian")
    b.set(2, -2, 0, "water", level=0)
    for y in range(bottom, -2):  # the column
        for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if (dx, dz) == (1, 0) and y == -3:
                continue  # that is the funnel floor
            b.set(dx, y, dz, "obsidian")
    return b, {"cell": (0, bottom - 1, 0)}
