"""MK.2 modules. Coordinates are module-local; +x east, +z south.

What MK.2 does differently, all measured on the test server (exp_ring2.py):
- The payload is dispensed into an OPEN powder snow cell. Every TNT drifts 0.0376 blocks in
  a random direction before the snow stops it, so the payload sits on a tiny circle.
- A propellant explosion four blocks away pushes each payload TNT along its own line from
  the blast, so the circle is magnified with every explosion: the payload lands as a ring.
- A "ring charge" under the cell blows the tiny circle up before the shot. The larger the
  circle, the fewer propellant explosions a ring of a given size needs.
"""
from build import Build, items

TRAP = dict(half="top", open=False, facing="north", powered=False, waterlogged=False)
SOURCES = {"e": (4, 0), "ne": (3, -3), "se": (3, 3)}  # propellant cells, x/z from the payload cell
CHARGES = {"west": (-1, -2, 0), "east": (1, -2, 0), "north": (0, -2, -1), "south": (0, -2, 1), "up": (0, -3, 0)}
_INWARD = {"west": "east", "east": "west", "north": "south", "south": "north", "up": "up"}


def chamber2():
    """Firing chamber. Local origin = payload cell; the chunk border lies between x=0 and x=1.

    Payload cell: powder snow with nothing solid beside it (a wall would stop the drift).
    Ceiling = the payload dispenser, floor = one iron bar post. The post carries the TNT and
    lets the blast of the ring charge through from below.
    Ring charge: a water block two below the cell, walled in by five dispensers.
    Propellant cells: water, top-half iron trapdoors round them (they hold TNT and water but
    explosion rays pass underneath). East cell = 4 blocks away; the two diagonal cells push
    south-west and north-west.
    """
    b = Build()
    b.set(0, 0, 0, "powder_snow")
    b.set(0, 1, 0, "dispenser", facing="down", nbt=items("tnt"))
    b.set(0, -1, 0, "iron_bars", north=False, east=False, south=False, west=False, waterlogged=False)
    b.set(0, -2, 0, "water", level=0)
    for name, pos in CHARGES.items():
        b.set(*pos, "dispenser", facing=_INWARD[name], nbt=items("tnt"))
    for dx, dz in SOURCES.values():
        b.set(dx, -1, dz, "obsidian")
        for ox, oz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            b.set(dx + ox, 0, dz + oz, "iron_trapdoor", **TRAP)
            b.set(dx + ox, -1, dz + oz, "obsidian")
        b.set(dx, 0, dz, "water", level=0)
    points = {"payload": (0, 0, 0), "payload_dispenser": (0, 1, 0)}
    points.update({f"charge_{k}": v for k, v in CHARGES.items()})
    points.update({f"prop_{k}": (dx, 0, dz) for k, (dx, dz) in SOURCES.items()})
    return b, points
