# Assets — qué va aquí y de dónde se copia

Los binarios NO están en este paquete (la API de GitHub no sube binarios y
este paquete se entrega como archivos de texto). Se suben por la interfaz web
de GitHub al crear el repo. Son 4 fotos + 25 wavs, ~3.4 MB en total.

## `assets/faces/` — 4 rostros lock (1600×1600, .webp)

Renombrar al copiar (el manifiesto usa estos nombres cortos):

| Archivo en el repo | Copiar desde (en la VM de Pecas) |
|---|---|
| `elena.webp` | `~/workspace/microseries/piloto/la-heredera-que-vendieron/media-generation-elena-referencia-0-90ed1ba5-3718-4724-b71f-5b8e5adf9bd4.webp` |
| `adrian.webp` | `~/workspace/microseries/piloto/la-heredera-que-vendieron/media-generation-adrian-referencia-0-db63c1cd-2ae5-481a-b892-d2cd35292133.webp` |
| `camila.webp` | `~/workspace/microseries/piloto/la-heredera-que-vendieron/media-generation-camila-referencia-0-b3aaa63f-4895-45f2-9217-b027ded28f5d.webp` |
| `carmen.webp` | `~/workspace/microseries/piloto/la-heredera-que-vendieron/media-generation-carmen-referencia-0-05eaa1db-32e7-4712-8024-c204869777d8.webp` |

Son retratos frontales generados por IA, ficticios, de nadie real
(fondo gris neutro). No cambiarlos: son los locks de la BIBLIA.md.

## `assets/narracion/` — 25 wavs (24 kHz, mono)

Copiar tal cual, sin renombrar, desde:

`~/workspace/microseries/piloto/la-heredera-que-vendieron/episodio-01/narracion/`

- escena02-camila.wav (2.65 s)
- escena03-elena.wav (1.47 s)
- escena04-elena.wav (1.88 s)
- escena05-elena.wav (3.52 s)
- escena06-elena.wav (2.09 s)
- escena08-camila.wav (2.13 s)
- escena09-elena.wav (1.62 s)
- escena10-camila.wav (1.69 s)
- escena11-elena.wav (2.65 s)
- escena12-camila.wav (1.37 s)
- escena14-elena.wav (2.28 s)
- escena15-carmen.wav (1.75 s)
- escena16-camila.wav (1.45 s)
- escena18-adrian.wav (0.64 s)
- escena19-elena.wav (1.19 s)
- escena20-adrian.wav (1.75 s)
- escena21-elena.wav (2.37 s)
- escena22-adrian.wav (1.60 s)
- escena23-adrian.wav (1.24 s)
- escena24-elena.wav (1.07 s)
- escena25-adrian.wav (2.11 s)
- escena26-camila.wav (2.35 s)
- escena27-adrian.wav (1.13 s)
- escena29-elena.wav (2.30 s)
- escena30-elena.wav (1.17 s)

Total: 45.46 s de audio, ~2.1 MB. Son la narración Kokoro ya generada con
las voces lock (Elena ef_dora 1.0, Adrián em_santa 1.0, Camila ef_dora 1.05,
Carmen ef_dora 0.9). **No se regeneran ni se tocan: los locks de voz están
cerrados** (regla de Marco 2026-11-10). Este pipeline solo genera video.

## Qué NO va aquí

- Los checkpoints de SadTalker (~2.5-3.5 GB): los descarga el workflow
  en el job con el script oficial (`bash scripts/download_models.sh`).
- Los clips generados: salen como artifacts del workflow, no se suben
  al repo (salvo que se quiera reanudar una corrida cortada; ver README).
