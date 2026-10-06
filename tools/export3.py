"""MK.3: writes the schematics for all four firing directions and a list of the positions that matter."""
from cannon3 import DIRECTION, nether_turned, overworld_turned

OUT = "../out/"
GERMAN = {"west": "Westen", "north": "Norden", "east": "Osten", "south": "Sueden"}
AXIS = {(1, 0): "+x (Osten)", (-1, 0): "-x (Westen)", (0, 1): "+z (Sueden)", (0, -1): "-z (Norden)"}
LABEL = {"e": "GERADE", "ne": "LINKS", "se": "RECHTS"}  # where the count moves the impact, seen along the shot


def rel(p, corner):
    return f"{p[0] - corner[0]:+d} / {p[1] - corner[1]:+d} / {p[2] - corner[2]:+d}"


def main():
    lines = ["OSC MK.3 - Positionen relativ zum Eckpunkt der Overworld-Schematic (kleinstes x / y / z).", ""]
    for turns, name in DIRECTION.items():
        b, info = overworld_turned(turns)
        for g in info["dupers"]:
            # TNT waits in the 'prime' cell: not powered there, the first piston cycle takes it in
            b.set(*info[f"duper_{g}"]["prime"], "tnt")
        nb, ninfo = nether_turned(turns)
        o = b.to_litematic(f"{OUT}osc3_{name}_overworld.litematic", f"OSC MK.3 {name} overworld")
        n = nb.to_litematic(f"{OUT}osc3_{name}_nether.litematic", f"OSC MK.3 {name} nether")
        c, nc = o["origin"], n["origin"]
        lines += [
            f"=== Schussrichtung {GERMAN[name]} ({name}) ===",
            f"Dateien: osc3_{name}_overworld.litematic ({o['size'][0]} x {o['size'][1]} x {o['size'][2]}, {o['blocks']} Bloecke), "
            f"osc3_{name}_nether.litematic ({n['blocks']} Bloecke)",
            f"Overworld-Eckpunkt: x mod 16 = {c[0] % 16}, z mod 16 = {c[2] % 16}",
            f"Nether-Eckpunkt:    x = (Overworld-Eck-x {-(c[0] - 8 * nc[0]):+d}) / 8,  y = Overworld-Eck-y {nc[1] - c[1]:+d},  "
            f"z = (Overworld-Eck-z {-(c[2] - 8 * nc[2]):+d}) / 8",
            f"Flugzelle (Pulverschnee, nichts darueber): {rel(info['cell'], c)}",
            f"Stapelzelle (Pulverschnee unter dem Spender): {rel(info['stack'], c)}",
            f"Start-Hebel: {rel(info['lever'], c)}",
            "Loren auf die Sensorschienen: " + ",  ".join(rel(info[f"duper_{g}"]["rail"], c) for g in info["dupers"]),
            f"Dropper Dauer-Station (2 Items): {rel(info['o1_send'], c)}",
            f"Dropper Weck-Station (4 Items): {rel(info['oa_send'], c)}",
            f"Dropper Ausloese-Station (4 Items): {rel(info['ob_send'], c)}",
            f"Sculk-Sensor: {rel(info['sensor'], c)}",
        ]
        for g in ("e", "ne", "se"):
            k = info[f"counter_{g}"]
            sx, _, sz = k["step"]
            unit = (sx // abs(sx) if sx else 0, sz // abs(sz) if sz else 0)
            lines.append(f"Zaehler {LABEL[g]:6s}: Bit 0 bei {rel(k['bit0'], c)}, weitere Bits je 3 Bloecke Richtung {AXIS[unit]}, {k['bits']} Bits")
        lines.append("")
        print(name, o, n)
    with open(OUT + "positionen_mk3.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
