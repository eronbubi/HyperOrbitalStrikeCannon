"""Nether post: a control panel somewhere else presses the cannon's counter buttons.

Every button on the panel drops one item of its own kind into a nether portal. In the nether a
hopper line carries it to a second portal that leads to the cannon; there a row of item
filters sits above the counters, and the filter that takes the item pulses its counter bit.
No wire in the overworld. Facing conventions as everywhere here: hopper/dropper = output,
comparator/repeater = input side.
"""
from build import Build

WOOL = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray", "cyan", "purple",
        "blue", "brown", "green", "red", "black"]
# one item kind per button: counter LEFT (ne) bits 0..14, STRAIGHT (e) bits 0..13, RIGHT (se) bits 0..14, START
ITEMS = {("ne", k): f"{WOOL[k]}_wool" for k in range(15)}
ITEMS.update({("e", k): f"{WOOL[k]}_concrete" for k in range(14)})
ITEMS.update({("se", k): f"{WOOL[k]}_terracotta" for k in range(15)})
ITEMS[("start", 0)] = "black_wool"
FILLER = "stick"  # never sent; keeps the other four slots of a filter hopper occupied
PERIOD = 5  # four-tick repeaters in the gate's loop: one item every 84 gt


def filter_items(item):
    """18 of the item + 4 single fillers = comparator strength 1; one more item makes it 2."""
    slots = [f'{{Slot:0b,id:"minecraft:{item}",count:18}}']
    slots += [f'{{Slot:{i}b,id:"minecraft:{FILLER}",count:1}}' for i in range(1, 5)]
    return "Items:[" + ",".join(slots) + "]"


def tile(item, floor="smooth_stone"):
    """Item filter above one counter bit. Local origin = the copper bulb, +z = south.

    Column over the bulb: block (a wall button on its north face replaces the old button),
    dust, output block, block, comparator. North of it: lock torch, release hopper, filter
    hopper; the input hopper line runs above the filter hopper at (0, 6, -1).
    A matching item raises the filter hopper to strength 2. Two dust later that is strength 1,
    enough for the repeater: it powers the output block, which (a) lights the dust below it and
    so pulses the bulb, (b) switches the torch off, which lets the release hopper take one item.
    """
    b = Build()
    b.set(0, 1, 0, floor)
    b.set(0, 1, -1, "stone_button", face="wall", facing="north", powered=False)
    b.set(0, 2, 0, "redstone_wire")
    b.set(0, 3, 0, floor)
    b.set(0, 3, -1, "redstone_wall_torch", facing="north", lit=True)
    b.set(0, 4, 0, floor)
    b.set(0, 5, 0, "comparator", facing="north", mode="compare")
    b.set(0, 5, -1, "hopper", facing="north", enabled=True, nbt=filter_items(item))
    b.set(0, 4, -1, "hopper", facing="north", enabled=False)
    b.set(0, 4, -2, "barrel", facing="up", open=False)
    b.set(0, 2, 1, floor)
    b.set(0, 3, 1, "repeater", facing="south", delay=1)
    b.set(0, 4, 1, floor)
    b.set(0, 5, 1, "redstone_wire")
    b.set(0, 3, 2, floor)
    b.set(0, 4, 2, "redstone_wire")
    return b


def inbox(out="east"):
    """Portal that only receives: frame, portal, catch box, hoppers to one output hopper.

    Same frame as modules.station(): portal in the x/y plane at z=0, x 0..1, y 1..3; items fly
    out southwards into the box. out='east': last hopper at (2, 0, 1) facing east;
    out='west': last hopper at (-1, 0, 1) facing west.
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
    east = out == "east"
    b.set(0, 0, 2, "hopper", facing="north")
    b.set(1, 0, 2, "hopper", facing="north")
    b.set(0, 0, 1, "hopper", facing="east" if east else "west")
    b.set(1, 0, 1, "hopper", facing="east" if east else "west")
    b.set(2 if east else -1, 0, 1, "hopper", facing="east" if east else "west")
    b.set(-1 if east else 2, 0, 1, "obsidian")
    for x in (-1, 2):
        b.set(x, 0, 2, "obsidian")
        for y in (1, 2):
            for z in (1, 2):
                b.set(x, y, z, "obsidian")
    for x in (-1, 0, 1, 2):
        for y in (0, 1, 2):
            b.set(x, y, 3, "obsidian")
    return b, {"out": (2 if east else -1, 0, 1)}


def receiver(w, info, xc, rows, bits, deck):
    """Everything the cannon needs to be driven by the post. `w` = cannon3.Safe, design coordinates.

    - a filter tile above every counter bit (the floor buttons move to the north face of a block)
    - one more tile for START: a copper bulb that stands in for the lever
    - the receiving portal, a gate that lets one item through every 84 gt (a borrow has to
      ripple through a counter before its next button is pressed), and the hopper line
      over the three rows of filters
    """
    b = w.b
    w.net = "post"
    info["post_buttons"] = {}
    for name, z0 in rows.items():
        for k in range(bits[name]):
            x = xc + 3 * k
            del b.blocks[(x, deck + 1, z0)]  # the floor button
            w.add(tile(ITEMS[(name, k)]), x, deck, z0, net=f"tile_{name}{k}")
        info["post_buttons"][name] = (xc, deck + 1, z0 - 1)
    # START: bulb, filter tile, comparator -> under the deck -> into the start of the departure delay
    sx, sz = xc + 42, rows["e"]
    w.floor(sx, deck - 1, sz)
    w.put(sx, deck, sz, "waxed_copper_bulb", lit=False, powered=False)
    w.add(tile(ITEMS[("start", 0)]), sx, deck, sz, net="tile_start")
    w.net = "start"
    w.comparator(sx + 1, deck, sz, "west", mode="compare")
    w.dust(sx + 2, deck, sz)
    end, n = w.stairs((sx + 3, deck, sz), 0, -1, 3)
    assert end == (sx + 3, deck - 3, sz - 3), end
    w.run([(sx + 3, deck - 3, sz - 4), (sx + 3, deck - 3, 0), (26, deck - 3, 0)], since=n)
    w.dust(25, deck - 3, 0)
    w.repeater(25, deck - 3, 1, "north")
    info["start_bulb"] = (sx, deck, sz)
    info["post_buttons"]["start"] = (sx, deck + 1, sz - 1)

    # receiving portal and gate (north-west, above the master clock)
    my = deck + 7
    ib, ip = inbox("east")
    origin = (28, my, -3)
    w.add(ib, *origin)
    info["om"] = origin
    gx, gz = origin[0] + ip["out"][0] + 1, origin[2] + ip["out"][2]  # dropper right after the last hopper of the inbox
    w.put(gx, my, gz, "dropper", facing="east", triggered=False)
    w.put(gx + 1, my, gz, "hopper", facing="down", enabled=True)
    w.net = "gate"
    w.comparator(gx, my, gz - 1, "south", mode="compare")  # anything in the dropper?
    w.repeater(gx, my, gz - 2, "south")
    w.dust(gx, my, gz - 3)
    w.comparator(gx + 1, my, gz - 3, "west")  # oscillator: on while the dropper holds something
    w.net = "gate_clock"
    w.dust(gx + 2, my, gz - 3)
    w.dust(gx + 3, my, gz - 3)
    loop = [(gx + 3, gz - 4, "south"), (gx + 3, gz - 5, "south"), (gx + 2, gz - 6, "east"), (gx + 1, gz - 5, "north"),
            (gx + 1, gz - 4, "north")]
    assert len(loop) == PERIOD
    w.net = "gate_loop"
    for x, z, facing in loop:
        w.repeater(x, my, z, facing, delay=4)
    w.dust(gx + 3, my, gz - 6)
    w.dust(gx + 1, my, gz - 6)
    w.net = "gate_clock"  # the same pulses fire the dropper: dust over two blocks onto its top
    w.dust(gx + 3, my, gz - 2)
    w.dust(gx + 3, my, gz - 1)
    w.put(gx + 2, my, gz - 1, "smooth_stone")
    w.dust(gx + 2, my + 1, gz - 1)
    w.put(gx + 1, my, gz - 1, "smooth_stone")
    w.dust(gx + 1, my + 1, gz - 1)
    w.dust(gx + 1, my + 1, gz)
    w.dust(gx, my + 1, gz)

    # hopper line: down one level, then over the three rows of filters (z0 - 1), there and back
    hy = deck + 6
    order = list(rows.items())  # ne, e, se from north to south
    chain = [(gx + 1, z, "south") for z in range(gz, order[0][1] - 1)]
    x_lo, x_hi = xc - 1, xc + 44
    assert gx + 1 == x_lo, (gx, x_lo)
    east = True
    for i, (name, z0) in enumerate(order):
        z = z0 - 1
        xs = range(x_lo, x_hi + 1) if east else range(x_hi, x_lo - 1, -1)
        row = [(x, z, "east" if east else "west") for x in xs]
        if i + 1 < len(order):
            nz = order[i + 1][1] - 1
            row[-1] = (row[-1][0], z, "south")
            row += [(row[-1][0], zz, "south") for zz in range(z + 1, nz)]
        chain += row
        east = not east
    for x, z, facing in chain:
        w.put(x, hy, z, "hopper", facing=facing, enabled=True)
    lx, lz, _ = chain[-1]
    w.put(lx + 1, hy, lz, "barrel", facing="up", open=False)  # anything no filter wanted
    info["post_trash"] = (lx + 1, hy, lz)
    info["gate_dropper"] = (gx, my, gz)


def nether_link(nm, length=41):
    """Nether side for a west-firing cannon. nm = origin of the station that sends to the cannon.

    `length` blocks east of it: the portal the items of the panel arrive through (panel = 8 x
    that far east of the receiving portal of the cannon). A hopper line carries them over.
    Returns (build, origin of the arrival portal).
    """
    b = Build()
    ib, ip = inbox("west")
    origin = (nm[0] + length, nm[1], nm[2])
    b.merge(ib, *origin)
    for x in range(nm[0] + 3, origin[0] + ip["out"][0]):
        b.set(x, nm[1], nm[2] + 1, "hopper", facing="west", enabled=True)
    return b, origin


PANEL_ROWS = (("ne", 5), ("e", 8), ("se", 11))  # row -> z, seen from the station of the panel


def panel():
    """Control panel. Local origin = its sending station (modules.station frame).

    Three rows of droppers, a button on each; bit 0 is the one next to the collector line at
    x = 3. A pressed dropper puts one item into the hopper line beside it, which ends in the
    station; the station shoots it through the portal. Droppers stand two apart: a powered
    dropper would fire its neighbour.
    """
    from modules import station
    b = Build()
    sb, sp = station()
    b.merge(sb)
    buttons = {}
    for z in range(1, PANEL_ROWS[-1][1] + 2):
        b.set(3, 0, z, "hopper", facing="west" if z == 1 else "north", enabled=True)
    for name, z in PANEL_ROWS:
        n = 15
        for x in range(4, 4 + 2 * n - 1):
            b.set(x, 0, z + 1, "hopper", facing="west", enabled=True)
        for k in range(n):
            key = (name, k) if (name, k) in ITEMS else ("start", 0)
            # STRAIGHT is mirrored: at the cannon its filters are passed from the high bit down, and an
            # item pressed later must never arrive earlier (see order())
            x = 4 + 2 * (13 - k if key[0] == "e" else k)
            stack = '{Slot:%db,id:"minecraft:' + ITEMS[key] + '",count:64}'
            # beside the hopper line, not above it: a hopper empties any container on top of it
            b.set(x, 0, z, "dropper", facing="south", triggered=False, nbt="Items:[" + stack % 0 + "," + stack % 1 + "]")
            b.set(x, 1, z, "stone_button", face="floor", facing="north", powered=False)
            buttons[key] = (x, 1, z)
    for z in (4, 7, 10, 13):  # somewhere to stand
        for x in range(2, 34):
            if (x, 0, z) not in b.blocks:
                b.set(x, 0, z, "smooth_stone")
    return b, {"buttons": buttons, "send": sp["send"]}


def order(presses):
    """Order in which to press. presses = {"ne": [bits], "e": [bits], "se": [bits]}.

    Row by row, each row from the collector line outwards. The gate at the cannon lets one item
    through every 84 gt, and in this order every later item also has the longer way along the
    filters, so two pulses never reach one counter within a borrow's ripple time.
    Pressed the other way round, two buttons of the STRAIGHT counter arrived 12 gt apart and
    the count came out wrong.
    """
    out = [("ne", k) for k in sorted(presses.get("ne", []))]
    out += [("e", k) for k in sorted(presses.get("e", []), reverse=True)]
    out += [("se", k) for k in sorted(presses.get("se", []))]
    return out
