# HyperOrbitalStrikeCannon MK.1

**MK.1**, die erste Version: Orbital Strike Cannon für Minecraft Java 1.21.11 als `.litematic`. Eigenes Design, auf einem Vanilla-Server Schuss für Schuss gemessen.

- Reichweite über 8000 Blöcke, gemessen bis 8530.
- Ziel wird an einem Zähler-Panel eingestellt (Richtung und Weite), ein Rechner sagt, welche Knöpfe zu drücken sind.
- Einschlag bei allen Messschüssen höchstens 0.35 Blöcke neben der Rechnung.
- Lädt sich selbst über Netherportal-Chunkloader, kein Spieler muss in der Nähe sein.
- Nur Vanilla-Mechaniken: TNT-Duper, Lazy-Chunk-Beschleunigung, Pulverschnee-Stopp.

## Benutzen

Pro Schussrichtung zwei Dateien aus `out/`: eine für die Overworld, eine für den Nether. Wer nur nach Westen schießen will, braucht nur `osc_west_overworld.litematic` und `osc_west_nether.litematic`.

Alles Weitere steht in der [Anleitung](ANLEITUNG.md): Platzieren, Bestücken, Zielen, Feuern, Grenzen, Messwerte.

Zielrechner (braucht nur Python 3):

```bash
python tools/aim.py ZELLE_X ZELLE_Z ZIEL_X ZIEL_Z west
```

## Bekannte Schwächen der MK.1

- **Groß:** 69 × 52 × 49 Blöcke, 4134 Blöcke pro Modul.
- **Kleine Payload:** 6 TNT, die kurz nacheinander zünden. Kein Ring-Muster wie bei bekannten Orbital Strike Cannons.
- **Langsam:** 8000 Blöcke geradeaus dauern etwa 54 Minuten Ladezeit.
- **Weit und schräg nach Norden geht nicht:** bei 8000 Blöcken nur 4° Abweichung nach Norden möglich. Details in der Anleitung.
- Ein Modul deckt ± 44° ab; für alle Richtungen braucht es vier Module.
- Nicht für Paper, Spigot, Purpur oder Folia.
- Das Einfügen mit Litematica in einem echten Client ist nicht getestet; die Tests liefen mit denselben Blöcken per Befehl auf einem Vanilla-Server.

## Quelltext

`tools/` enthält den Generator, mit dem die Schematics erzeugt und getestet wurden:

| Datei | Inhalt |
|---|---|
| `cannon.py`, `modules.py` | das Design: Duper, Kammer, Zähler, Stationen, Verkabelung |
| `build.py` | Block-Container, Drehung, Export als `.litematic` (braucht `litemapy`) |
| `export.py` | schreibt alle acht Schematics und `positionen.txt` |
| `aim.py` | Zielrechner, an 13 echte Schüsse angepasst |
| `rcon.py`, `lab.py` | Steuerung eines Testservers über RCON |
| `exp_*.py`, `probe_*.py`, `trace_*.py` | die Experimente und Messungen |
| `prepare_server.py` | baut Kanone und Zielscheibe auf dem Testserver und stellt die Zähler |
| `*_v1.py` | ältere Fassung mit einem Duper pro Richtung |

Der Generator und die Experimente erwarten daneben einen Vanilla-Server 1.21.11 mit aktiviertem RCON in `server/` und den Block-Report des Servers in `gen/reports/blocks.json` (erzeugt mit `java -DbundlerMainClass=net.minecraft.data.Main -jar server.jar --reports`). Beides liegt nicht im Repository.
