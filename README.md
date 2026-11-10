# Microserie "La heredera que vendieron" — Pipeline SadTalker en CPU

Genera los 25 clips de video del episodio 1 ("La boda que no fue", 90 s)
con **SadTalker en un runner de GitHub Actions, solo CPU, sin GPU, sin
secretos y sin login**. Es el plan B sin Kaggle.

Cada clip = una foto lock del personaje + su línea de narración Kokoro
(ya generada). El montaje final a 9:16 se hace después con ffmpeg
(ver "Después de descargar los artifacts").

## Contenido del paquete

| Archivo | Qué es |
|---|---|
| `.github/workflows/sadtalker-cpu.yml` | El workflow (disparo manual). |
| `scripts/generar_clips.py` | Lee el manifiesto y corre SadTalker por línea, con reintento y resume. |
| `manifiesto_clips.json` | Las 25 líneas: escena, personaje, foto, wav, salida. |
| `storyboard.json` | Copia del storyboard del episodio 1 (referencia). |
| `assets/LEEME_ASSETS.md` | Qué 4 fotos y qué 25 wavs van en `assets/`. |
| `assets/faces/` | Vacío (solo `.gitkeep`): aquí van las 4 fotos lock. |
| `assets/narracion/` | Vacío (solo `.gitkeep`): aquí van los 25 wavs. |
| `clips/`, `logs/` | Vacíos: el workflow los llena (salidas y reporte). |

**Las voces no se tocan.** Los wavs ya están generados con los locks
cerrados (Elena ef_dora 1.0, Adrián em_santa 1.0, Camila ef_dora 1.05,
Carmen ef_dora 0.9). Este pipeline solo genera video; no regenera audio.

## Cómo se sube (por navegador)

La API de GitHub no puede subir workflows ni binarios, así que todo esto
va por la interfaz web:

1. Crear un **repo nuevo PÚBLICO** en GitHub (nombre sugerido:
   `microserie-heredera-sadtalker`).
2. Subir por la web (Add file > Upload files) todo este paquete:
   `.github/workflows/sadtalker-cpu.yml`, `scripts/generar_clips.py`,
   `manifiesto_clips.json`, `storyboard.json`, `README.md`,
   `assets/LEEME_ASSETS.md`.
3. Subir los binarios según `assets/LEEME_ASSETS.md`: las 4 fotos a
   `assets/faces/` (renombradas a `elena.webp`, `adrian.webp`,
   `camila.webp`, `carmen.webp`) y los 25 wavs a `assets/narracion/`
   (sin renombrar). Son ~3.4 MB en total; la subida web los acepta.
4. Ir a la pestaña **Actions** del repo y aceptar que los workflows
   corran (en repos nuevos GitHub pide un clic la primera vez).

## Cómo se dispara

Actions > **SadTalker CPU — Episodio 1** > Run workflow.

- **Primero, prueba rápida:** `max_clips: 2` (genera solo las escenas 02
  y 03, ~10-20 min). Revisa que los 2 mp4 se vean y se oigan bien.
- **Después, corrida completa:** `max_clips: 0` (los 25 clips).
- **Solo lip-sync:** `solo_sync: true` genera solo los 18 clips `sync`
  (personaje en cámara). Los 7 clips `vo` son voz en off y en montaje
  sirven como plano de apoyo; saltárselos ahorra ~30% del tiempo.

Los artifacts se suben **siempre** (`if: always()`), aunque fallen
algunos clips o se acabe el tiempo: `clips-episodio-01` (los mp4) y
`logs-episodio-01` (reporte por clip). **Bajarlos antes de 7 días**:
los artifacts caducan (`retention-days: 7`).

Si el job se corta por tiempo, se re-dispara y **continúa donde quedó**:
el script salta los clips que ya existen (se conservan en caché entre
corridas) y el reporte se reescribe tras cada clip.

## Tiempo estimado

Cálculo honesto, con las cifras publicadas de SadTalker en CPU:

| Fase | Estimación |
|---|---|
| Setup (Python 3.8, torch CPU, requirements incl. compilación de dlib, descarga de checkpoints) | 30–50 min (primera vez; con caché ~10 min) |
| Generación: 45.46 s de audio × 25 fps ≈ 1,137 frames a 4–8 s/frame en CPU + carga del modelo por clip (~1–2 min × 25) | 100–200 min |
| **Total primera corrida** | **~2.5–4.5 h** |

El límite del job es 6 h (`timeout-minutes: 360`). Cabe, pero la
primera corrida va justa: si el runner es lento, puede cortarse y hay
que re-disparar (ver arriba: continúa donde quedó).

Minutos gratis: un repo público tiene 2,000 min/mes. Una corrida
completa gasta ~150–270 min. Caben ~7–13 corridas completas al mes.

## Después de descargar los artifacts

Los clips salen en 1600×1600 (el tamaño de la foto lock; SadTalker con
`--preprocess full` devuelve la imagen completa con la cara animada).
En montaje con ffmpeg se reescalan/recortan a 1080×1920 y se colocan
según los tiempos del `storyboard.json` (los 34 s `silent` se cubren
con holds del último frame, como prevé el storyboard).

Ejemplo para ver un clip ya recortado a vertical:

```bash
ffmpeg -i clips/escena02-camila.mp4 -vf "crop=900:1600:350:0,scale=1080:1920" \
  -c:v libx264 -pix_fmt yuv420p escena02-vertical.mp4
```

El script de montaje completo del episodio (90 s) es el siguiente paso;
no está en este paquete.

## Banderas rojas (verificado, no escondido)

1. **CPU es MUY lento para SadTalker.** Las fuentes lo dicen sin
   rodeos: "CPU-only mode is extremely slow and not recommended" y
   "4–8 seconds per frame with CPU optimizations". En GPU un video de
   10 s tarda ~30 s; en este runner de 2 vCPU, los 25 clips tardan
   horas. Kaggle con GPU T4 seguiría siendo mucho más rápido; esto es
   solo el plan B que funciona sin login.
2. **Python 3.8, no 3.10.** SadTalker exige oficialmente Python 3.8;
   Python 3.10+ rompe sus C-extensiones (basicsr, dlib, torchvision
   legacy). Por eso el workflow usa `ubuntu-22.04` + Python 3.8
   (setup-python no ofrece 3.8 en ubuntu-24.04) y torch 1.12.1 CPU.
3. **dlib se compila desde el código fuente** (no hay wheel para Linux):
   15–25 min de la fase de setup, en cada primera corrida. Con caché
   de pip se reutiliza la rueda ya compilada en re-corridas.
4. **Disco justo.** El runner tiene ~14 GB libres. Presupuesto:
   torch CPU + dependencias ~2 GB, checkpoints ~2.5–3.5 GB (el script
   oficial baja también el modelo 512 y los pesos GFPGAN aunque no se
   usen), build de dlib ~1 GB, repo y salidas ~0.5 GB. Total ~7–8 GB.
   Cabe, pero no sobra. El workflow muestra `df -h` en dos puntos.
5. **Watermark de SadTalker.** La versión 0.0.2 añade un logo de
   SadTalker al video generado. Sale en una esquina del clip; en el
   montaje 9:16 se puede recortar con el `crop` de ffmpeg si estorba.
6. **Licencia de los checkpoints.** El código de SadTalker es
   Apache 2.0, pero los checkpoints preentrenados (modelo 3DMM/BFM)
   incorporan modelos de investigación no comerciales. Para el piloto
   y pruebas no hay problema; si la serie se monetiza, hay que revisar
   este punto antes de publicar (o usar pesos reentrenados).
7. **Sin enhancer a propósito.** No se usa `--enhancer gfpgan`: en CPU
   pasaría cada frame por GFPGAN y el tiempo se dispararía. La cara
   sale algo más suave a 256 px; el montaje 9:16 lo disimula.
