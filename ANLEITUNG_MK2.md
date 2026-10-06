# Orbital Strike Cannon MK.2 – Bauanleitung

Eigenes Design, Stück für Stück auf einem Vanilla-Server 1.21.11 getestet.
Ein Modul deckt einen Kegel von **± 44°** um seine Schussrichtung ab. Es gibt vier Varianten: Westen, Norden, Osten, Süden.

## Was MK.2 anders macht

| | v2 | MK.2 |
|---|---|---|
| Einschlag | 6 TNT auf einem Punkt | **16 TNT als Ring**, Größe einstellbar |
| Größe | 69 × 52 × 49, 4134 Blöcke | **65 × 15 × 43, 3066 Blöcke** |
| Zähler | 4 (drei Richtungen + Timer) | **3**, kein Timer mehr |
| Abschuss | wenn der Timer abgelaufen ist | automatisch, sobald keine Treibladung mehr explodiert |

Kein Turm mehr: die drei Duper sitzen 8 Blöcke über ihren Zellen, alles liegt auf einem flachen Deck.

## Dateien

| Datei | Inhalt |
|---|---|
| `out/osc2_west_overworld.litematic` usw. | Kanone je Richtung, 3066 Blöcke |
| `out/osc2_west_nether.litematic` usw. | zwei Portal-Stationen je Richtung, 118 Blöcke |
| `out/positionen_mk2.txt` | alle Positionen je Richtung (Hebel, Zähler, Loren, Dropper) |
| `tools/aim2.py` | Zielrechner |

## Voraussetzungen

- Java Edition 1.21.11, Vanilla oder Fabric. **Nicht** Paper, Spigot, Purpur, Folia: dort ist TNT-Duping gepatcht und die Physik anders.
- Freier Luftraum: von der Payload-Zelle aus 50 Blöcke in Schussrichtung muss ein Gang frei sein, 3 breit und 2 hoch.
- In 130 Blöcken Umkreis (Overworld) kein anderes Netherportal. Portale verbinden sich immer mit dem nächsten.

## Platzieren

Die Kanone hängt an den Chunk-Grenzen. Für den Eckpunkt der Schematic (kleinstes x, y, z) gilt je Richtung eine Regel, sie steht in `out/positionen_mk2.txt`. Für Westen:

- **x mod 16 = 13**, **z mod 16 = 9**
- **y frei wählbar.** Die Payload fliegt auf Eck-y + 3 und fällt nach der Ankunft noch, bevor sie zündet: die ersten TNT etwa 2 Blöcke, die letzten etwa 60. Der Zielboden sollte also 10 bis 50 Blöcke unter Eck-y + 3 liegen.

Nether-Schematic für Westen, Eckpunkt:

- **x = (Overworld-Eck-x − 13) / 8**, **y = Overworld-Eck-y + 1**, **z = (Overworld-Eck-z + 7) / 8**

Im Nether beide Stationen in einen geschlossenen Raum setzen. Lava oder Kies zerstören sonst das Redstone.

## Nach dem Einfügen

Positionen relativ zum Overworld-Eckpunkt, hier für Westen (andere Richtungen: `positionen_mk2.txt`):

1. **3 Loren** auf die drei Sensorschienen der Duper: `+8 / +11 / +15`, `+7 / +11 / +12`, `+7 / +11 / +18`.
2. **2 beliebige Items** in den Dropper der Dauer-Station: `+28 / +3 / +30`. Sie pendeln ab jetzt durch das Portal und halten die Kanone geladen.
3. **4 beliebige Items** in den Dropper der Auslöse-Station: `+5 / +11 / +36`.
4. Das TNT der drei Duper ist in der Schematic schon drin (je ein Block neben dem Slot). Nicht umsetzen.
5. Die sechs Spender (einer über der Zelle, vier um den Wasserblock darunter, einer ganz unten) sind mit TNT gefüllt. Der über der Zelle verbraucht 16 pro Schuss, die vier seitlichen je 1.

## Zielen

```bash
python tools/aim2.py ZELLE_X ZELLE_Z ZIEL_X ZIEL_Z west --ring 12
```

- Zelle = Weltkoordinate des Pulverschnee-Blocks (Westen: Eckpunkt `+2 / +3 / +15`).
- Das Wort nach den Koordinaten ist die Schussrichtung des Moduls: `west`, `north`, `east` oder `south`.
- `--ring R`: gewünschter Ringradius in Blöcken. Ohne die Angabe rechnet er den schnellsten Schuss.
- `--noring`: wenn der Hebel „ohne Ringladung" an ist (Ring wird etwa 2,5-mal kleiner).

Der Rechner gibt drei Zahlen aus (GERADE, LINKS, RECHTS), welche Knöpfe zu drücken sind, wie groß der Ring wird und wie lange es dauert.

Zähler auf dem Deck (Westen), von Norden nach Süden:

| Zähler | Bit 0 | weitere Bits |
|---|---|---|
| LINKS | `+20 / +11 / +9` | je 3 Blöcke nach Osten, 15 Bits |
| GERADE | `+20 / +11 / +15` | je 3 Blöcke nach Osten, 14 Bits |
| RECHTS | `+20 / +11 / +21` | je 3 Blöcke nach Osten, 15 Bits |

LINKS und RECHTS heißen so, weil ihre Zahl den Einschlag in Schussrichtung gesehen nach links bzw. rechts schiebt.

Jeder Knopfdruck zieht 2^Bit ab. Deshalb die vom Rechner genannten Knöpfe drücken, nicht die Bits der Zahl selbst. Danach zeigen die leuchtenden Birnen die Zahl binär; der Rechner nennt sie zur Kontrolle.

**Langsam drücken:** nach jedem Knopf warten, bis sich keine Birne mehr ändert (bis zu 8 Sekunden).

## Der Ring

Die 16 TNT liegen in der Zelle auf einem winzigen Kreis. Jede Explosion der mittleren Zelle (GERADE) drückt sie etwas weiter auseinander, die beiden seitlichen Zellen zusammen fast gar nicht. Daraus folgt:

- **GERADE bestimmt die Ringgröße**, LINKS und RECHTS machen den Rest der Strecke.
- Ein kleiner Ring auf große Distanz heißt: wenig GERADE, viel LINKS + RECHTS. Das dauert länger, weil dann nur zwei statt drei Duper schieben.
- Liegt das Ziel neben der Achse, braucht eine Seite mehr als die andere. Das zieht den Ring zu einer Ellipse; der Rechner nennt beide Halbachsen.
- Der Hebel **„ohne Ringladung"** (Westen: `+36 / +11 / +35`) schaltet die vier Spender unter der Zelle ab. Der Startkreis ist dann 0,038 statt 0,096 Blöcke groß, der Ring entsprechend kleiner.

## Feuern

1. Alle drei Zähler einstellen. Hebel „ohne Ringladung" so stellen, wie beim Rechner angegeben.
2. Start-Hebel umlegen (Westen: `+8 / +11 / +9`, Nordwest-Ecke des Decks).
3. **Sofort weg.** Nach 80 Sekunden startet der Ablauf. Bis dahin musst du weiter entfernt sein als die Simulationsdistanz des Servers (bei 10 Chunks: über 180 Blöcke).
4. Die Kanone lädt allein und schießt von selbst, etwa 2 Sekunden nach der letzten Treibladung.
5. Die Payload bleibt am Ziel in der Luft stehen, bis der Ziel-Chunk geladen wird, dann fällt sie und explodiert. Wer am Ziel steht, löst sie also selbst aus.
6. Zurück, Hebel wieder aus. **Danach 2 Minuten warten**, bevor du Zähler neu stellst.

## Was du nicht tun darfst

- **Nicht in der Nähe bleiben**, während sie lädt. Ein Spieler lässt alle Chunks ticken, dann explodiert die Payload in der eigenen Kammer.
- **Start-Hebel nicht zurücklegen**, bevor der Schuss raus ist. Dann bleibt Payload in der Kammer, und Treibladung, die noch unterwegs ist, explodiert außerhalb des Wassers.
- **Nie mit drei Nullen feuern.** Die Payload bleibt dann in der Kammer.
- Keine Blöcke neben den Pulverschnee setzen. Die Zelle muss seitlich offen sein, sonst entsteht kein Ring.
- Keine Wolle zwischen den Sculk-Sensor (Westen: `+9 / +11 / +21`) und die Kammer. Er hört die Explosionen und löst danach den Schuss aus.

## Ringgröße und Dauer (gerade Schüsse)

Ringradius in Blöcken (kleinster bis größter Abstand vom Zentrum) und Zeit vom Hebel bis zum Schuss:

| Distanz | schnellster Schuss, mit Ringladung | schnellster Schuss, ohne Ringladung | kleinster Ring (GERADE = 0, ohne Ringladung) |
|---|---|---|---|
| 500 | 5–6, 5 min | 2, 5 min | unter 1, 7 min |
| 1000 | 9–12, 8 min | 4–5, 8 min | 1, 13 min |
| 2000 | 18–24, 15 min | 7–9, 15 min | 1–2, 24 min |
| 4000 | 37–47, 27 min | 14–18, 27 min | 2–3, 47 min |
| 8000 | 73–95, 53 min | 29–36, 53 min | 5–7, 91 min |

Dazwischen ist alles einstellbar: `--ring R` sucht die Zähler für den gewünschten Radius.
Schräge Ziele: der Ring wird größer und länglich, je weiter das Ziel neben der Achse liegt (4000 Blöcke weit und 1500 daneben: mindestens 17–23 statt 2–3).

## Grenzen

**Weit und schräg nach Norden.** Beim Abschuss prüft das Spiel Kollisionen in einem Quader aus Flugweite × Flugbreite × Fallweg; ab 2^31 Blöcken bricht die Prüfung ab und die Payload geht verloren. Bei v2 gemessen; für MK.2 nicht neu vermessen, der Rechner verweigert solche Ziele nach derselben Formel. Erlaubte Abweichung nach Norden (Ziel bei kleinerem z als die Kanone):

| Distanz entlang der Achse | erlaubte Abweichung nach Norden |
|---|---|
| bis 3000 | voller Kegel, 44° |
| 4000 | 3620 Blöcke (42°) |
| 5000 | 2580 Blöcke (27°) |
| 6000 | 1840 Blöcke (17°) |
| 8000 | 1020 Blöcke (7°) |

Nach Süden gilt immer der volle Kegel.

**Die 16 TNT zünden nacheinander**, je 4 Ticks versetzt, über 3 Sekunden. Der Spender über der Zelle gibt eine pro 4 Ticks ab, und mehr als 16 passen nicht in die Lebenszeit einer TNT.

**Der Ring ist bei schnellen Weitschüssen groß.** Seine Größe wächst mit der Strecke, die der mittlere Duper beiträgt. Wer auf 8000 Blöcke einen engen Ring will, zahlt mit Zeit (Tabelle oben).

## Gemessene Genauigkeit

Alle Schüsse mit echten Portal-Loadern, nichts von Hand geladen. Der Rechner benutzt nur die Explosionsformel des Spiels, ohne angepasste Konstanten.

| Schuss (GERADE / LINKS / RECHTS) | Rechner | Ringzentrum gemessen |
|---|---|---|
| 600 / 0 / 0 | −270,61 / 0,00 | −270,61 / +0,03 |
| 0 / 1200 / 0 | −358,67 / +359,87 | −358,68 / +359,87 |
| 0 / 1200 / 1200 | −717,34 / 0,00 | −717,26 / −0,03 |
| 1200 / 1200 / 0 | −899,89 / +359,87 | −899,84 / +359,89 |
| 1500 / 1500 / 1500 | −1573,20 / 0,00 | −1573,22 / +0,02 |
| 200 / 0 / 700 | −299,43 / −209,92 | −299,43 / −209,89 |
| 6672 / 10004 / 1 (6700 Blöcke bei 27°) | −5999,61 / +2999,81 | −5999,36 / +2999,73 |
| 8 / 13376 / 13376 (8000 gerade, mit Ringladung) | −7999,55 / 0,00 | Mittel der 16 TNT −8000,06 / −1,99, Ring 8–19 |

Zahlen sind die Verschiebung ab Zellenmitte. Ohne Ringladung liegen die 16 TNT exakt auf einer Ellipse, deren Zentrum sich auf Hundertstel bestimmen lässt; mit Ringladung ist der Startkreis leicht unrund, das Zentrum deshalb nur auf etwa 2 Blöcke.

## Material je Modul

smooth stone 1396, Redstone 652, Repeater 469, Obsidian 261, Komparator 97, gewachste Kupferbirne 44, Steinknopf 44, Schleimblock 27, Trichter 16, Eisenfalltür 7, Spender 6 (mit TNT), klebriger Kolben 6, Dropper 4, Sensorschiene 3, tote Korallen-Wandfächer 3, Redstone-Block 2, Hebel 2, Wasserkessel 2, kalibrierter Sculk-Sensor 1, Eisengitter 1, Pulverschnee 1, 7 Wassereimer, 3 Loren, 3 TNT. Dazu die Nether-Stationen (118 Blöcke) und zwei Portale.

Norden, Osten und Süden wurden je mit einem Schuss geprüft (300 / 200 / 100, ohne Ringladung): Ringzentrum jeweils unter 0,04 Blöcke neben dem Rechner. Ein Schuss lief zur Kontrolle in echter Spielgeschwindigkeit (20 Ticks/s) statt im Zeitraffer: gleiches Ergebnis.
