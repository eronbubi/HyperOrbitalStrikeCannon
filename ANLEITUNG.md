# Orbital Strike Cannon – Bauanleitung

Eigenes Design, Stück für Stück auf einem Vanilla-Server 1.21.11 getestet.
Ein Modul deckt einen Kegel von **± 44°** um seine Schussrichtung ab. Es gibt vier Varianten: Westen, Norden, Osten, Süden. Zusammen decken sie alle Richtungen ab, jede steht für sich an einem eigenen Platz.

## Dateien

| Datei | Inhalt |
|---|---|
| `out/osc_west_overworld.litematic` usw. | Kanone je Richtung, 4134 Blöcke, 69 × 52 × 49 |
| `out/osc_west_nether.litematic` usw. | zwei Portal-Stationen je Richtung, 118 Blöcke |
| `out/positionen.txt` | alle Positionen je Richtung (Hebel, Zähler, Loren, Dropper) |
| `tools/aim.py` | Zielrechner |

## Voraussetzungen

- Java Edition 1.21.11, Vanilla oder Fabric. **Nicht** Paper, Spigot, Purpur, Folia: dort ist TNT-Duping gepatcht und die Physik anders.
- Freier Luftraum: von der Payload-Zelle aus 50 Blöcke in Schussrichtung muss die Reihe (1 breit, 1 hoch) frei sein.
- In 130 Blöcken Umkreis (Overworld) kein anderes Netherportal. Portale verbinden sich immer mit dem nächsten.

## Platzieren

Die Kanone hängt an den Chunk-Grenzen. Für den Eckpunkt der Schematic (kleinstes x, y, z) gilt je Richtung eine Regel, sie steht in `out/positionen.txt`. Für Westen:

- **x mod 16 = 11**, **z mod 16 = 14**
- **y zwischen 60 und 76** (Standard 72). Die Payload fliegt auf Eck-y + 12 und fällt nach der Ankunft noch etwa 15 bis 45 Blöcke, bevor sie zündet. Der Zielboden sollte also 15 bis 40 Blöcke unter Eck-y + 12 liegen.

Nether-Schematic für Westen, Eckpunkt:

- **x = (Overworld-Eck-x − 11) / 8**, **y gleich**, **z = (Overworld-Eck-z + 2) / 8**

Beispiel: Overworld-Ecke 1035 / 72 / 2062 → Nether-Ecke 128 / 72 / 258.

Im Nether beide Stationen in einen geschlossenen Raum setzen. Lava oder Kies zerstören sonst das Redstone.

## Nach dem Einfügen

Positionen relativ zum Overworld-Eckpunkt, hier für Westen (andere Richtungen: `positionen.txt`):

1. **5 Loren** auf die fünf Sensorschienen der Duper: `+7 / +51 / +10`, `+7 / +43 / +14`, `+7 / +43 / +6`, `+7 / +47 / +12`, `+7 / +47 / +8`.
2. **2 beliebige Items** in den Dropper der Dauer-Station: `+30 / +2 / +25`. Sie pendeln ab jetzt durch das Portal und halten die Kanone geladen.
3. **4 beliebige Items** in den Dropper der Auslöse-Station: `+7 / +42 / +31`.
4. Das TNT der fünf Duper ist in der Schematic schon drin (je ein Block neben dem Slot). Nicht umsetzen.

## Zielen

```bash
python tools/aim.py ZELLE_X ZELLE_Z ZIEL_X ZIEL_Z west
```

Letztes Wort ist die Schussrichtung des Moduls: `west`, `north`, `east` oder `south`.
Zelle = Weltkoordinate des Pulverschnee-Blocks (Westen: Eckpunkt `+4 / +12 / +10`).
Der Rechner gibt vier Zahlen aus (W, NW, SW, TIMER) und dazu, welche Knöpfe zu drücken sind.

Zähler auf dem Deck (Westen):

| Zähler | Bit 0 | weitere Bits |
|---|---|---|
| SW | `+22 / +42 / 0` | je 3 Blöcke nach Osten |
| W | `+22 / +42 / +10` | je 3 Blöcke nach Osten |
| NW | `+22 / +42 / +16` | je 3 Blöcke nach Osten |
| TIMER | `+57 / +42 / +46` | je 3 Blöcke nach **Westen** |

Jeder Knopfdruck zieht 2^Bit ab. Deshalb die vom Rechner genannten Knöpfe drücken, nicht die Bits der Zahl selbst. Danach zeigen die leuchtenden Birnen die Zahl binär; der Rechner nennt sie zur Kontrolle.

**Langsam drücken:** nach jedem Knopf warten, bis sich keine Birne mehr ändert (bis zu 8 Sekunden).

## Feuern

1. Alle vier Zähler einstellen.
2. Hebel auf der unteren Plattform umlegen (Westen: `+14 / +37 / +14`).
3. **Sofort weg.** Nach 80 Sekunden startet der Ablauf. Bis dahin musst du weiter entfernt sein als die Simulationsdistanz des Servers (bei 10 Chunks: über 180 Blöcke).
4. Die Kanone lädt allein und schießt, sobald der Timer bei null ist. Geradeaus: 500 Blöcke ≈ 5 Minuten, 1000 ≈ 8, 4000 ≈ 28, 8000 ≈ 54 Minuten. Je schräger, desto länger: nahe 44° braucht dieselbe Distanz rund das Anderthalbfache (7800 Blöcke ≈ 83 Minuten). Siehe auch „Grenzen" unten.
5. Die Payload bleibt am Ziel in der Luft stehen, bis der Ziel-Chunk geladen wird, dann fällt sie und explodiert. Wer am Ziel steht, löst sie also selbst aus.
6. Zurück, Hebel wieder aus. **Danach 2 Minuten warten**, bevor du Zähler neu stellst: so lange laufen die Zähler noch, und neue Zahlen würden sofort wieder heruntergezählt.

## Was du nicht tun darfst

- **Nicht in der Nähe bleiben**, während sie lädt. Ein Spieler lässt alle Chunks ticken, dann explodiert die Payload in der eigenen Kammer.
- **Hebel nicht zurücklegen**, bevor der Schuss raus ist. Sonst bleibt Payload in der Kammer liegen und zerstört sie beim nächsten Scharfschalten.
- **Nie mit W = NW = SW = 0 feuern.** Die Payload bleibt dann in der Kammer.
- Keine Redstone-Signale an die Eisenfalltüren der Kammer legen.

## Grenzen, die du kennen musst

**Nordwärts schräg und weit geht nicht.** Schüsse mit Nordanteil (Ziel liegt bei kleinerem z als die Kanone), die zugleich weit und stark schräg sind, verliert das Spiel: beim Abschuss prüft es Kollisionen in einem Quader aus Flugweite × Flugbreite × Fallweg, und ab 2^31 Blöcken bricht diese Prüfung ab, bevor sie den Kammerboden erreicht. Die Payload fällt dann durch den Boden ins Nichts.

- Gemessen: 4600 Blöcke bei 40° nach Nordwest kommen an, 7800 Blöcke bei 40° nach Nordwest nicht (zweimal verloren).
- Derselbe Schuss nach **Südwest** kommt an, im Zielblock.
- Gerade Schüsse und alles mit Südanteil sind nicht betroffen.
- Der Zielrechner verweigert betroffene Ziele mit einer Meldung, statt die Payload zu verlieren.

Wie weit ein Ziel nach **Norden** von der Schussachse abweichen darf (Modul West; für die anderen Module gilt dasselbe sinngemäß, entscheidend ist immer der Nordanteil):

| Distanz entlang der Achse | erlaubte Abweichung nach Norden |
|---|---|
| bis 3000 Blöcke | voller Kegel, 44° |
| 4000 | 2390 Blöcke (31°) |
| 5000 | 1530 Blöcke (17°) |
| 6000 | 1060 Blöcke (10°) |
| 8000 | 590 Blöcke (4°) |
| 10 000 | 380 Blöcke (2°) |

Nach Süden gilt immer der volle Kegel. Praktisch heißt das: weit entfernte Ziele im Norden triffst du nur nahe einer Achse; im Süden überall.

**Server hängt beim Abschuss schräger Weitschüsse.** Derselbe Kollisions-Quader kostet Rechenzeit: bei 7800 Blöcken und 40° stand der Testserver beim Abschuss 46 bis 80 Sekunden still, bei 4600 Blöcken und 40° bis zu 2 Minuten, wenn das Ziel geladen war. Gerade Schüsse: kein spürbarer Hänger.

## Gemessene Genauigkeit

Alle Schüsse mit echten Portal-Loadern, nichts von Hand geladen. Der W-Zähler steuert drei Duper zugleich (geradeaus plus zwei seitliche, deren Seitenkräfte sich aufheben); ein W-Zählerschritt sind etwa 1.03 Blöcke.

| Schuss | Distanz | Rechner | Einschlag |
|---|---|---|---|
| 4000 W | 4111 | −4095.97 / 0.83 | −4095.97 / 0.83 |
| 7768 W + 37 SW | 8000 gerade | −7984.20 / 8.73 | −7984.20 / 8.55 |
| 4838 W + 7347 SW | 8530 bei 21° | −7985.35 / 3002.34 | −7985.51 / 3002.23 |
| 953 W + 12164 SW | 7800 bei 40° Süd | −5984.48 / 5000.50 | −5984.83 / 5000.33 |
| 600 W + 7200 NW | 4600 bei 40° Nord | −3549.84 / −2955.16 | −3549.85 / −2955.16 |
| 300 W + 3600 SW | 2300 bei 40° | −1778.67 / 1485.79 | −1778.67 / 1485.79 |

Der Rechner ist an 13 echte Schüsse angepasst und weicht bei keinem um mehr als 0.17 Blöcke ab. Der 7800-Blöcke-Schuss nach Südwest war nicht Teil der Anpassung und landete 0.35 Blöcke daneben, im Zielblock.
Norden, Osten und Süden wurden je mit einem Schuss geprüft, bei dem alle fünf Duper feuern (100 W + 60 NW + 40 SW): Einschlag jeweils 128.2 Blöcke in Schussrichtung, Abweichung unter 0.2 Blöcken.

## Material je Modul

smooth stone 1748, Redstone 802, Obsidian 791, Repeater 500, Komparator 127, gewachste Kupferbirne 59, Steinknopf 59, Schleimblock 40, Trichter 30, Eisenfalltür 15, Dropper 8, smooth-stone-Stufe 8, klebriger Kolben 6, Sensorschiene 5, tote Korallen-Wandfächer 5, Wasserkessel 4, Redstone-Fackel 3, dazu Pulverschnee, Spender mit TNT, Hebel, 10 Wassereimer, 5 Loren, 5 TNT.
