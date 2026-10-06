# HyperOrbitalStrikeCannon

Orbital Strike Cannon für Minecraft Java 1.21.11 als `.litematic`. Eigenes Design, auf einem Vanilla-Server Schuss für Schuss gemessen. Nur Vanilla-Mechaniken: TNT-Duper, schlafende Chunks, Pulverschnee-Stopp, Netherportal-Chunkloader.

Drei Versionen liegen hier nebeneinander:

| | MK.1 | MK.2 | MK.3 |
|---|---|---|---|
| Payload | 6 TNT | 16 TNT | **65 TNT** |
| Zündung | nacheinander | nacheinander, über 3 s | **alle im selben Tick** |
| Einschlag | ein Punkt | Ring, zeitlich verschmiert | **geschlossener Ring** |
| Größe | 69 × 52 × 49 | 65 × 15 × 43 | 67 × 22 × 54 |
| Blöcke je Modul | 4134 | 3066 | 3189 |
| Abschuss | Timer-Zähler | automatisch (Sculk-Sensor) | automatisch (Sculk-Sensor) |
| Getestet | 4 Richtungen, bis 8530 Blöcke | 4 Richtungen, bis 8000 Blöcke | **nur Westen, bis 800 Blöcke** |
| Anleitung | [ANLEITUNG.md](ANLEITUNG.md) | [ANLEITUNG_MK2.md](ANLEITUNG_MK2.md) | [ANLEITUNG_MK3.md](ANLEITUNG_MK3.md) |
| Dateien in `out/` | `osc_*` | `osc2_*` | `osc3_*` |

## MK.3

- 65 TNT werden in einem schlafenden Chunk auf einen Punkt gestapelt. Beim Wecken öffnen sie sich zu einem Kreis und haben einen gemeinsamen Zünder; eine Sprungladung wirft den Kreis in die Flugzelle. Am Ziel kommt ein Ring an, der gleichzeitig zündet.
- Der Zielrechner benutzt nur die Explosionsformel des Spiels. 11 echte Schüsse lagen höchstens 0,3 Blöcke daneben.
- Der Ring ist eine Ellipse und wächst mit der Distanz: 500 Blöcke → 1,5–4, 2000 → 6–16, 8000 → 22–62 (gerechnet). Kleiner geht, kostet Ladezeit.

**Zielrechner:** [`app/index.html`](app/index.html) im Browser öffnen, läuft ohne Internet. Kanone einmal eintragen, dann nur noch Ziel X und Z. Er zeigt, welche Knöpfe zu drücken sind. Auf der Kommandozeile: `python tools/aim3.py ZELLE_X ZELLE_Z ZIEL_X ZIEL_Z west`.

### Funk-Variante (Nether-Post)

Ein Bedienpult an anderer Stelle stellt die Zähler und startet den Schuss, ohne Kabel in der Overworld: jeder Knopf schickt ein eigenes Item durch ein Netherportal, an der Kanone drückt ein Item-Filter den passenden Zählerknopf. Dateien `out/osc3funk_*`, nur für die West-Kanone, Details am Ende der [MK.3-Anleitung](ANLEITUNG_MK3.md).

Per Skript hat das mit dem Pult 340 Blöcke entfernt funktioniert, bis zum Schuss. **Der einzige Versuch von Hand ist gescheitert**, Ursache nicht sicher geklärt. Als Experiment zu verstehen.

## Bekannte Schwächen

- **MK.3 ist wenig getestet:** nur Schussrichtung Westen, nur bis 800 Blöcke. Norden, Osten und Süden sind exportiert, aber nie geschossen.
- Ein Spieler in der Nähe der ladenden Kanone weckt die Chunks; die Payload explodiert dann in der Kammer.
- Weit und schräg nach Norden geht bei keiner Version: das Spiel verliert die Payload. Die Rechner verweigern solche Ziele.
- Ein Modul deckt ± 44° ab; für alle Richtungen braucht es vier Module.
- Nicht für Paper, Spigot, Purpur oder Folia.
- Das Einfügen mit Litematica in einem echten Client ist nicht getestet; die Tests liefen mit denselben Blöcken per Befehl auf einem Vanilla-Server.

## Quelltext

`tools/` enthält die Generatoren, mit denen die Schematics erzeugt und getestet wurden:

| Datei | Inhalt |
|---|---|
| `cannon.py`, `modules.py` | MK.1: Duper, Kammer, Zähler, Stationen, Verkabelung |
| `cannon2.py`, `modules2.py` | MK.2: Ringkammer, Master-Takt, Sculk-Auslöser |
| `cannon3.py` | MK.3: Stapelzelle, Sprungladung, drei Stationen |
| `post.py` | Nether-Post: Item-Filter, Empfänger, Nether-Leitung, Pult |
| `aim.py`, `aim2.py`, `aim3.py` | Zielrechner je Version |
| `export.py`, `export2.py`, `export3.py` | schreiben die Schematics und Positionslisten |
| `build.py` | Block-Container, Drehung, Export als `.litematic` (braucht `litemapy`) |
| `rcon.py`, `lab.py` | Steuerung eines Testservers über RCON |
| `exp_*.py`, `probe_*.py`, `trace_*.py` | die Experimente und Messungen |
| `prepare_server*.py` | bauen Kanone und Zielscheibe auf dem Testserver |

Die Generatoren und Experimente erwarten daneben einen Vanilla-Server 1.21.11 mit aktiviertem RCON in `server/` und den Block-Report des Servers in `gen/reports/blocks.json` (erzeugt mit `java -DbundlerMainClass=net.minecraft.data.Main -jar server.jar --reports`). Beides liegt nicht im Repository.
