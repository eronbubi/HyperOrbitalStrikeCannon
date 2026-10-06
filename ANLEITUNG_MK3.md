# Orbital Strike Cannon MK.3 – Bauanleitung

Eigenes Design, auf einem Vanilla-Server 1.21.11 getestet. Ein Modul deckt **± 44°** um seine Schussrichtung ab; es gibt vier Varianten (Westen, Norden, Osten, Süden).

## Was MK.3 anders macht

| | MK.2 | MK.3 |
|---|---|---|
| Payload | 16 TNT | **65 TNT** |
| Zündung | nacheinander über 3 Sekunden | **alle im selben Tick** |
| Form | Ring, aber zeitlich verschmiert | **geschlossener Ring** |
| Größe | 65 × 15 × 43, 3066 Blöcke | 67 × 22 × 54, 3189 Blöcke |
| Portal-Stationen | 2 | 3 |

## Wie der Ring entsteht

1. Die Payload wird in eine Zelle gespendet, deren Chunk schläft. Dort bewegt sich nichts und kein Zünder läuft: alle 65 TNT liegen auf einem Punkt, jede mit ihrem eigenen Zufallsstoß (0,02 Blöcke/Tick in beliebige Richtung).
2. Die Weck-Station lässt den Chunk ticken. Alle TNT machen gleichzeitig ihren ersten Schritt: ein Kreis mit Radius 0,0376, ein gemeinsamer Zünder.
3. 20 Ticks später wirft eine Sprungladung (3 TNT) den ganzen Kreis in die Flugzelle im Nachbar-Chunk, der weiter schläft. Zünder eingefroren.
4. Die Treibladung vergrößert den Kreis mit jedem Schuss der mittleren Zelle. Abschuss, Ankunft, alle fallen und zünden gemeinsam.

## Dateien

| Datei | Inhalt |
|---|---|
| `out/osc3_west_overworld.litematic` usw. | Kanone je Richtung, 3189 Blöcke |
| `out/osc3_west_nether.litematic` usw. | drei Portal-Stationen je Richtung, 177 Blöcke |
| `out/positionen_mk3.txt` | alle Positionen je Richtung |
| `app/index.html` | Zielrechner (im Browser öffnen, läuft ohne Internet) |
| `tools/aim3.py` | derselbe Rechner für die Kommandozeile |

## Voraussetzungen

- Java Edition 1.21.11, Vanilla oder Fabric. **Nicht** Paper, Spigot, Purpur, Folia.
- Von der Flugzelle aus 50 Blöcke in Schussrichtung frei, 3 breit und 2 hoch.
- In 130 Blöcken Umkreis kein anderes Netherportal.

## Platzieren (Westen; andere Richtungen: `positionen_mk3.txt`)

- Overworld-Eckpunkt: **x mod 16 = 9**, **z mod 16 = 6**, y frei.
- Nether-Eckpunkt: **x = (Overworld-Eck-x − 1) / 8**, **y gleich**, **z = (Overworld-Eck-z − 14) / 8**. Die drei Stationen stehen übereinander; den Raum mit Obsidian schließen.

## Nach dem Einfügen (relativ zum Overworld-Eckpunkt, Westen)

1. **3 Loren** auf die Sensorschienen: `+10 / +18 / +26`, `+9 / +18 / +23`, `+9 / +18 / +29`.
2. **2 Items** in den Dropper der Dauer-Station: `+32 / +2 / +17`.
3. **4 Items** in den Dropper der Weck-Station: `+16 / +18 / +2`.
4. **4 Items** in den Dropper der Auslöse-Station: `+20 / +10 / +36`.
5. Das TNT der Duper ist in der Schematic. Der Spender über der Stapelzelle hat 576 TNT, das reicht für 8 Schüsse; die drei Spender der Sprungladung brauchen je 1 pro Schuss.

## Zielen und Feuern

1. `app/index.html` öffnen. Flugzelle (Westen: Eckpunkt `+4 / +10 / +26`), Richtung, Ziel und auf Wunsch Ringradius eingeben.
2. Die rot markierten Knöpfe auf den drei Zählern drücken (LINKS `+22 / +18 / +20`, GERADE `+22 / +18 / +26`, RECHTS `+22 / +18 / +32`, je 3 Blöcke nach Osten pro Bit). **Langsam:** nach jedem Knopf warten, bis sich keine Birne mehr ändert.
3. Start-Hebel umlegen (`+10 / +18 / +20`) und **sofort weg**: nach 80 Sekunden beginnt der Ablauf, bis dahin musst du außerhalb der Simulationsdistanz sein.
4. Die Kanone schießt von selbst, sobald keine Treibladung mehr explodiert.
5. Die Payload wartet am Ziel in der Luft, bis der Chunk geladen wird. Dann fällt sie etwa 55 Blöcke (oder bis zum Boden) und zündet.
6. Hebel zurück, 2 Minuten warten.

## Ringgröße

Der Ring ist eine Ellipse und wächst mit der Strecke, die der mittlere Duper (GERADE) beiträgt. Die beiden seitlichen heben sich fast auf. Beispiele gerade Schüsse, schnellste Einstellung: 500 Blöcke → 1,5–4; 2000 → 6–16; 8000 → 22–62. Mit `Ringradius` im Rechner lässt sich das kleiner stellen, kostet aber Zeit.

## Was du nicht tun darfst

- **Nicht in der Nähe bleiben.** Ein Spieler weckt alle Chunks: die Payload bekommt dann verschiedene Zünder und explodiert in der Kammer.
- **Start-Hebel nicht zurücklegen**, bevor der Schuss raus ist.
- **Nie mit drei Nullen feuern.**
- Keine Blöcke neben die beiden Pulverschnee-Zellen setzen, keine Wolle zwischen Sculk-Sensor (`+11 / +18 / +32`) und Kammer.

## Gemessen

Echte Portal-Lader, nichts von Hand geladen. Der Rechner benutzt nur die Explosionsformel des Spiels.

| Schuss (GERADE / LINKS / RECHTS) | Abweichung Ringzentrum | Ring gemessen | Zünder |
|---|---|---|---|
| 300 / 300 / 300 | 0,04 / 0,00 | 0,85–2,28 | alle 60 |
| 600 / 0 / 0 | 0,30 / 0,09 | 1,59–3,88 | alle 56 |
| 400 / 100 / 600 | 0,04 / 0,06 | 1,64–4,63 | alle 55 |
| 0 / 600 / 0 | 0,01 / 0,09 | 1,66–3,15 | alle 57 |
| 0 / 0 / 600 | 0,02 / 0,08 | 1,51–4,08 | alle 58 |
| 0 / 1200 / 1200 | 0,14 / 0,04 | 0,09–2,47 | alle 58 |

**Nicht getestet:** Norden, Osten, Süden (nur Westen geschossen; MK.2 lief in allen vier mit demselben Drehverfahren). Schüsse über 800 Blöcke. Einfügen mit Litematica im echten Client. Die Nord-schräg-Grenze aus MK.2 gilt weiter; mit 65 statt 16 TNT dürfte der Server-Hänger bei weiten schrägen Schüssen länger werden.

## Material je Modul

smooth stone 1371, Redstone 688, Repeater 469, Obsidian 357, Komparator 97, gewachste Kupferbirne 44, Steinknopf 44, Schleimblock 27, Trichter 25, Eisenfalltür 7, klebriger Kolben 6, Dropper 6, Spender 4 (mit TNT), Sensorschiene 3, tote Korallen-Wandfächer 3, Wasserkessel 3, Pulverschnee 2, Eisengitter 2, Redstone-Block 2, Hebel 1, kalibrierter Sculk-Sensor 1, 6 Wassereimer, 3 Loren, 3 TNT. Dazu die Nether-Stationen (177 Blöcke) und drei Portale.

## Funk-Variante: Bedienpult über Nether-Post

Nur für die West-Kanone. Dateien: `out/osc3funk_west_overworld.litematic` (4231 Blöcke), `out/osc3funk_west_nether.litematic` (317), `out/osc3funk_pult.litematic` (373), Positionen in `out/positionen_mk3_funk.txt`.

**Prinzip.** Echtes Wireless-Redstone über beliebige Distanz gibt es in Vanilla nicht. Stattdessen wirft jeder Knopf am Pult ein eigenes Item (Wolle = LINKS, Beton = GERADE, Terrakotta = RECHTS, schwarze Wolle = START) durch ein Netherportal. Im Nether trägt eine Trichterleitung es zu einem zweiten Portal, das zur Kanone führt. Dort sitzt über jedem Zählerbit ein Item-Filter, der bei seinem Item den Zähler pulst. Eine Taktschleuse lässt nur ein Item alle 84 Ticks durch.

**Reichweite.** Getestet mit dem Pult 340 Blöcke östlich der Kanone (41 Blöcke Trichterleitung im Nether). Mehr ist nicht ausprobiert.

**Bedienen.** In der App unter „Kanone und Optionen" „Funk-Pult" wählen. Knöpfe in der angezeigten Reihenfolge drücken: Reihe für Reihe, jeweils von der Sammelleitung am Portal nach außen. Die GERADE-Reihe ist am Pult gespiegelt, die App zeigt es richtig. 15 Sekunden warten, dann START (letzter Knopf der GERADE-Reihe). Nach dem Schuss START noch einmal.

**Stand der Tests.**

- Per Skript: 32 Knöpfe gedrückt, Zähler exakt, START per Funk, 65 TNT geladen und abgefeuert.
- In falscher Reihenfolge gedrückt kamen zwei Pulse 12 Ticks auseinander an, der Zähler stand auf 311 statt 301.
- **Von Hand am Pult: ein Versuch, gescheitert.** Die Zähler standen nicht auf den Werten der App, und die Payload war beim Nachsehen nicht mehr in der Flugzelle. Vermutung, nicht belegt: START kam an, bevor die Zähler standen; dann löst der Sculk-Sensor aus, ehe Treibladung explodiert. Es gibt keine Sperre dagegen und am Pult keine Rückmeldung.
- Nach dem Einfügen prüfen: jeder Filter-Trichter hat 18 Items + 4 Stöcke, der Trichter darunter ist leer.
