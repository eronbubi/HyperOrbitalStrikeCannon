"""Block model for the cannon: validated block states, rotation, .litematic and mcfunction export.

Every block state is checked against the block report generated from the real 1.21.11
jar (gen/reports/blocks.json), so a wrong property name, a wrong value or a facing that
the block does not have fails here instead of in the game.

Orientation convention used everywhere: +x east, -x west, +z south, -z north, +y up.
"""
import gzip
import json
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_VERSION = 4671  # 1.21.11
_REPORT = None


def report():
    global _REPORT
    if _REPORT is None:
        _REPORT = json.loads((ROOT / "gen" / "reports" / "blocks.json").read_text())
    return _REPORT


def canon(name, props=None):
    """Full, validated state: (namespaced name, sorted tuple of every property)."""
    if ":" not in name:
        name = "minecraft:" + name
    spec = report().get(name)
    if spec is None:
        raise ValueError(f"unknown block {name}")
    allowed = spec.get("properties") or {}
    default = next(s for s in spec["states"] if s.get("default")).get("properties", {})
    full = dict(default)
    for key, value in (props or {}).items():
        value = str(value).lower() if isinstance(value, bool) else str(value)
        if key not in allowed:
            raise ValueError(f"{name} has no property '{key}' (has: {sorted(allowed)})")
        if value not in allowed[key]:
            raise ValueError(f"{name}[{key}={value}] invalid (allowed: {allowed[key]})")
        full[key] = value
    return name, tuple(sorted(full.items()))


# --- rotation about the Y axis, clockwise seen from above: north -> east -> south -> west

_CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
_RAIL_CW = {
    "north_south": "east_west", "east_west": "north_south",
    "ascending_north": "ascending_east", "ascending_east": "ascending_south",
    "ascending_south": "ascending_west", "ascending_west": "ascending_north",
    "north_east": "south_east", "south_east": "south_west",
    "south_west": "north_west", "north_west": "north_east",
}


def _rot_props_cw(name, props):
    src = dict(props)
    out = dict(src)
    for key, value in src.items():
        if key in ("facing", "horizontal_facing") and value in _CW:
            out[key] = _CW[value]
        elif key == "axis" and value in ("x", "z"):
            out[key] = "z" if value == "x" else "x"
        elif key == "rotation":
            out[key] = str((int(value) + 4) % 16)
        elif key == "shape" and value in _RAIL_CW:
            out[key] = _RAIL_CW[value]
        elif key == "orientation":  # crafter / jigsaw: e.g. north_up, up_north
            out[key] = "_".join(_CW.get(part, part) for part in value.split("_"))
    if all(side in src for side in _CW):  # wire, fences, panes, walls: per-side connections
        for side, target in _CW.items():
            out[target] = src[side]
    return tuple(sorted(out.items()))


class Build:
    """Sparse block volume. Later writes replace earlier ones."""

    def __init__(self):
        self.blocks = {}  # (x, y, z) -> (name, props tuple)
        self.nbt = {}  # (x, y, z) -> SNBT body for the block entity, without braces

    def set(self, x, y, z, name, nbt=None, **props):
        pos = (int(x), int(y), int(z))
        self.blocks[pos] = canon(name, props)
        if nbt:
            self.nbt[pos] = nbt
        else:
            self.nbt.pop(pos, None)
        return self

    def fill(self, x1, y1, z1, x2, y2, z2, name, **props):
        state = canon(name, props)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.blocks[(x, y, z)] = state
                    self.nbt.pop((x, y, z), None)
        return self

    def get(self, x, y, z):
        return self.blocks.get((x, y, z))

    def rotated(self, quarter_turns):
        """Copy rotated clockwise (seen from above) about the Y axis through the origin."""
        out = Build()
        out.blocks, out.nbt = dict(self.blocks), dict(self.nbt)
        for _ in range(quarter_turns % 4):
            nxt = Build()
            for (x, y, z), (name, props) in out.blocks.items():
                pos = (-z, y, x)
                nxt.blocks[pos] = canon(name, dict(_rot_props_cw(name, props)))
                if (x, y, z) in out.nbt:
                    nxt.nbt[pos] = out.nbt[(x, y, z)]
            out = nxt
        return out

    def merge(self, other, dx=0, dy=0, dz=0):
        for (x, y, z), state in other.blocks.items():
            pos = (x + dx, y + dy, z + dz)
            self.blocks[pos] = state
            if (x, y, z) in other.nbt:
                self.nbt[pos] = other.nbt[(x, y, z)]
            else:
                self.nbt.pop(pos, None)
        return self

    def bounds(self):
        xs, ys, zs = zip(*self.blocks)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    # --- exports

    @staticmethod
    def state_string(state):
        name, props = state
        return name + ("[" + ",".join(f"{k}={v}" for k, v in props) + "]" if props else "")

    def to_commands(self, ox=0, oy=0, oz=0):
        """setblock commands, solid support first so attached blocks do not pop off."""
        def order(item):
            (x, y, z), (name, _) = item
            fragile = any(word in name for word in _FRAGILE)
            return (1 if fragile else 0, y, x, z)

        cmds = []
        for (x, y, z), state in sorted(self.blocks.items(), key=order):
            body = self.nbt.get((x, y, z))
            cmds.append(f"setblock {x + ox} {y + oy} {z + oz} {self.state_string(state)}" + (f"{{{body}}}" if body else ""))
        return cmds

    def to_litematic(self, path, name="OSC", author="Claude"):
        (x0, y0, z0), (x1, y1, z1) = self.bounds()
        sx, sy, sz = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1
        air = canon("air")
        palette = [air]
        index = {air: 0}
        for state in self.blocks.values():
            if state not in index:
                index[state] = len(palette)
                palette.append(state)
        bits = max(2, (len(palette) - 1).bit_length())
        volume = sx * sy * sz
        packed = 0  # Litematica packs entries back to back, spanning long boundaries
        for (x, y, z), state in self.blocks.items():
            i = ((y - y0) * sz + (z - z0)) * sx + (x - x0)
            packed |= index[state] << (i * bits)
        n_longs = (volume * bits + 63) // 64
        longs = [(packed >> (64 * i)) & 0xFFFFFFFFFFFFFFFF for i in range(n_longs)]
        longs = [v - (1 << 64) if v >= (1 << 63) else v for v in longs]

        tiles = []
        for (x, y, z), body in self.nbt.items():
            tiles.append(Snbt(f"x:{x - x0},y:{y - y0},z:{z - z0},{body}"))

        solid = sum(1 for s in self.blocks.values() if s != air)
        now = int(time.time() * 1000)
        root = {
            "MinecraftDataVersion": Int(DATA_VERSION),
            "Version": Int(6),
            "SubVersion": Int(1),
            "Metadata": {
                "Name": name, "Author": author, "Description": "",
                "RegionCount": Int(1), "TimeCreated": Long(now), "TimeModified": Long(now),
                "TotalBlocks": Int(solid), "TotalVolume": Int(volume),
                "EnclosingSize": {"x": Int(sx), "y": Int(sy), "z": Int(sz)},
            },
            "Regions": {
                name: {
                    "Position": {"x": Int(0), "y": Int(0), "z": Int(0)},
                    "Size": {"x": Int(sx), "y": Int(sy), "z": Int(sz)},
                    "BlockStatePalette": [
                        ({"Name": n, "Properties": {k: v for k, v in p}} if p else {"Name": n}) for n, p in palette
                    ],
                    "BlockStates": LongArray(longs),
                    "TileEntities": tiles,
                    "Entities": [], "PendingBlockTicks": [], "PendingFluidTicks": [],
                }
            },
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wb") as fh:
            fh.write(b"\x0a\x00\x00" + _payload(root))
        return {"size": (sx, sy, sz), "blocks": solid, "palette": len(palette), "origin": (x0, y0, z0)}


# Blocks that need a neighbour to exist first.
_FRAGILE = (
    "redstone_wire", "repeater", "comparator", "torch", "lever", "button", "rail", "pressure_plate",
    "carpet", "ladder", "tripwire", "sign", "portal", "fan", "coral", "door", "banner", "lantern",
    "sweet_berry", "bell", "scaffolding", "snow", "water", "lava", "fire", "target",
)


# --- minimal NBT writer

class Int(int):
    pass


class Long(int):
    pass


class LongArray(list):
    pass


class Snbt(str):
    """Compound body given as SNBT text; parsed by the small parser below."""


def _tag_id(value):
    if isinstance(value, Snbt):
        return 10
    if isinstance(value, Long):
        return 4
    if isinstance(value, Int):
        return 3
    if isinstance(value, Byte):
        return 1
    if isinstance(value, Short):
        return 2
    if isinstance(value, float):
        return 6
    if isinstance(value, str):
        return 8
    if isinstance(value, LongArray):
        return 12
    if isinstance(value, list):
        return 9
    if isinstance(value, dict):
        return 10
    raise TypeError(type(value))


class Byte(int):
    pass


class Short(int):
    pass


def _string(text):
    raw = text.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def _payload(value):
    if isinstance(value, Snbt):
        return _payload(parse_snbt("{" + value + "}"))
    kind = _tag_id(value)
    if kind == 1:
        return struct.pack(">b", value)
    if kind == 2:
        return struct.pack(">h", value)
    if kind == 3:
        return struct.pack(">i", value)
    if kind == 4:
        return struct.pack(">q", value)
    if kind == 6:
        return struct.pack(">d", value)
    if kind == 8:
        return _string(value)
    if kind == 12:
        return struct.pack(">i", len(value)) + b"".join(struct.pack(">q", v) for v in value)
    if kind == 9:
        inner = _tag_id(value[0]) if value else 0
        return struct.pack(">bi", inner, len(value)) + b"".join(_payload(v) for v in value)
    out = b""
    for key, item in value.items():
        out += struct.pack(">b", _tag_id(item)) + _string(key) + _payload(item)
    return out + b"\x00"


def parse_snbt(text):
    """Small SNBT subset: compounds, lists, strings, ints, and b/s/L suffixed numbers."""
    pos = 0

    def ws():
        nonlocal pos
        while pos < len(text) and text[pos] in " \n\t":
            pos += 1

    def value():
        nonlocal pos
        ws()
        ch = text[pos]
        if ch == "{":
            pos += 1
            out = {}
            ws()
            while text[pos] != "}":
                ws()
                start = pos
                while text[pos] not in ":":
                    pos += 1
                key = text[start:pos].strip().strip('"')
                pos += 1
                out[key] = value()
                ws()
                if text[pos] == ",":
                    pos += 1
                ws()
            pos += 1
            return out
        if ch == "[":
            pos += 1
            out = []
            ws()
            while text[pos] != "]":
                out.append(value())
                ws()
                if text[pos] == ",":
                    pos += 1
                ws()
            pos += 1
            return out
        if ch == '"':
            end = text.index('"', pos + 1)
            out = text[pos + 1:end]
            pos = end + 1
            return out
        start = pos
        while pos < len(text) and text[pos] not in ",}]":
            pos += 1
        token = text[start:pos].strip()
        if token in ("true", "false"):
            return Byte(token == "true")
        if token[-1] in "bB" and token[:-1].lstrip("-").isdigit():
            return Byte(int(token[:-1]))
        if token[-1] in "sS" and token[:-1].lstrip("-").isdigit():
            return Short(int(token[:-1]))
        if token[-1] in "lL" and token[:-1].lstrip("-").isdigit():
            return Long(int(token[:-1]))
        if token.lstrip("-").isdigit():
            return Int(int(token))
        return token

    return value()


def items(item, count=64, slots=9):
    """SNBT body for a container filled with `item` in every slot."""
    return "Items:[" + ",".join(f'{{Slot:{i}b,id:"minecraft:{item}",count:{count}}}' for i in range(slots)) + "]"
