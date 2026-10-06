"""Isometric picture of a Build (drawn from the block data, not an in-game screenshot)."""
from PIL import Image, ImageDraw, ImageFont

from build import Build

COLORS = {
    "obsidian": (38, 28, 58), "slime_block": (112, 192, 91), "sticky_piston": (120, 150, 90),
    "smooth_stone": (160, 160, 160), "detector_rail": (150, 110, 80), "powder_snow": (250, 252, 255),
    "iron_trapdoor": (205, 205, 205), "water": (60, 110, 220), "dead_tube_coral_wall_fan": (130, 125, 120),
    "tnt": (210, 50, 40), "minecart": (90, 90, 100),
}
# drawn as (x0, x1, y0, y1, z0, z1) inside the block cell
SHAPES = {
    "iron_trapdoor": (0, 1, 0.8125, 1, 0, 1),
    "detector_rail": (0, 1, 0, 0.12, 0.15, 0.85),
    "dead_tube_coral_wall_fan": (0.1, 0.9, 0.3, 0.7, 0.55, 1),
    "minecart": (0.1, 0.9, -0.88, -0.4, 0.2, 0.8),
}
S = 52  # pixels per block edge


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def render(parts, path, title):
    """parts: list of (label, {pos: name}) drawn side by side."""
    font = ImageFont.load_default()
    tiles = []
    for label, cells in parts:
        xs, ys, zs = zip(*cells)
        tiles.append((label, cells, (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))))

    def project(x, y, z):
        return ((x - z) * S * 0.866, (x + z) * S * 0.5 - y * S)

    images = []
    for label, cells, lo, hi in tiles:
        corners = [project(x, y, z) for x in (lo[0], hi[0] + 1) for y in (lo[1], hi[1] + 1) for z in (lo[2], hi[2] + 1)]
        minx, miny = min(c[0] for c in corners), min(c[1] for c in corners)
        w = int(max(c[0] for c in corners) - minx) + 40
        h = int(max(c[1] for c in corners) - miny) + 70
        img = Image.new("RGB", (w, h), (24, 26, 32))
        d = ImageDraw.Draw(img, "RGBA")

        def pt(x, y, z):
            px, py = project(x, y, z)
            return (px - minx + 20, py - miny + 20)

        for (x, y, z), name in sorted(cells.items(), key=lambda kv: (kv[0][0] + kv[0][2], kv[0][1], kv[0][0])):
            base = COLORS.get(name, (200, 0, 200))
            x0, x1, y0, y1, z0, z1 = SHAPES.get(name, (0, 1, 0, 1, 0, 1))
            alpha = 170 if name == "water" else 255
            top = [pt(x + x0, y + y1, z + z0), pt(x + x1, y + y1, z + z0), pt(x + x1, y + y1, z + z1), pt(x + x0, y + y1, z + z1)]
            south = [pt(x + x0, y + y1, z + z1), pt(x + x1, y + y1, z + z1), pt(x + x1, y + y0, z + z1), pt(x + x0, y + y0, z + z1)]
            east = [pt(x + x1, y + y1, z + z0), pt(x + x1, y + y1, z + z1), pt(x + x1, y + y0, z + z1), pt(x + x1, y + y0, z + z0)]
            for poly, f in ((south, 0.72), (east, 0.55), (top, 1.0)):
                d.polygon(poly, fill=shade(base, f) + (alpha,), outline=(0, 0, 0, 200))
        d.text((10, h - 22), label, fill=(230, 230, 230), font=font)
        images.append(img)

    names = sorted({n for _, cells, _, _ in tiles for n in cells.values()})
    legend_w = 190
    W = sum(i.width for i in images) + legend_w + 20
    H = max(max(i.height for i in images), 24 + 18 * len(names)) + 36
    out = Image.new("RGB", (W, H), (24, 26, 32))
    d = ImageDraw.Draw(out)
    d.text((12, 10), title, fill=(255, 255, 255), font=font)
    x = 10
    for img in images:
        out.paste(img, (x, 32))
        x += img.width
    for i, n in enumerate(names):
        d.rectangle((x + 10, 40 + 18 * i, x + 22, 52 + 18 * i), fill=COLORS.get(n, (200, 0, 200)), outline=(0, 0, 0))
        d.text((x + 28, 40 + 18 * i), n.replace("dead_tube_coral_wall_fan", "dead coral fan").replace("_", " "), fill=(220, 220, 220), font=font)
    out.save(path)
    return out.size


def cells_of(build, extra=None):
    cells = {pos: state[0].replace("minecraft:", "") for pos, state in build.blocks.items()}
    cells.update(extra or {})
    return cells


if __name__ == "__main__":
    from modules import chamber, duper

    db, dp = duper()
    cb, cp = chamber()
    duper_cells = cells_of(db, {dp["slot"]: "tnt", (1, 2, 0): "minecart"})
    chamber_cells = cells_of(cb, {(0, 0, 0): "tnt"})
    del chamber_cells[(0, 0, 0)]
    chamber_cells[(0, 0, 0)] = "powder_snow"
    print(render(
        [("TNT duper (tested, 1 TNT per cycle)", duper_cells),
         ("Firing chamber (tested): snow = payload cell, water = propellant cells", chamber_cells)],
        "../out/osc_stand.png", "OSC - built so far (rendered from block data, view from south-east above)"))
