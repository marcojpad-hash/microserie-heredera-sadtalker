#!/usr/bin/env python3
"""Genera los clips SadTalker del episodio 1 de "La heredera que vendieron".

Lee manifiesto_clips.json y, por cada línea, convierte la foto lock .webp a .png
(PIL; SadTalker no acepta webp de forma fiable en todas sus rutas de lectura) y
corre SadTalker inference.py en CPU:

    python inference.py --driven_audio <wav> --source_image <png>
        --checkpoint_dir <SadTalker/checkpoints> --result_dir <tmp>
        --preprocess full --still --expression_scale 0.8 --size 256
        --batch_size 1 --cpu --verbose

Parámetros del manifiesto (ver manifiesto_clips.json > parametros_sadtalker):
- preprocess full + still: el retrato es de cuerpo/cabeza completa; full procesa
  la cara y la vuelve a pegar en la imagen original, still mantiene la pose.
- size 256: el render 512 es 4x más lento en CPU y no aporta nada al montaje
  9:16 (los clips se reescalan en ffmpeg).
- Sin --enhancer: GFPGAN por frame en CPU es prohibitivo y no hace falta
  para el montaje.
- batch_size 1: el runner tiene 7 GB de RAM; no hay margen para lotes.

Robustez (el job tiene límite de 6 h y la CPU es lenta):
- Resume: si el mp4 de salida ya existe y pesa > 0, el clip se salta.
  Así, un re-disparo del workflow continúa donde quedó (los clips se
  conservan entre corridas vía caché de GitHub Actions; ver workflow).
- Reintento: 1 reintento por clip (2 intentos en total).
- Timeout por clip: 1200 s (20 min). Si un clip lo supera, se marca como
  fallido y se sigue con el siguiente; el job NO muere por un clip.
- El reporte (logs/reporte_clips.json y .md) se reescribe después de cada
  clip, así que aunque el job se corte queda constancia de lo hecho.
- Código de salida: 0 si todos los clips quedaron, 1 si alguno falló
  (el workflow sube los artifacts igualmente con `if: always()`).

Uso:
    python scripts/generar_clips.py --manifiesto manifiesto_clips.json \
        --sadtalker-dir SadTalker [--solo-sync] [--max-clips N]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

# Parámetros SadTalker (deben coincidir con manifiesto_clips.json).
SADTALKER_ARGS = [
    "--preprocess", "full",
    "--still",
    "--expression_scale", "0.8",
    "--size", "256",
    "--batch_size", "1",
    "--cpu",
    "--verbose",
]
CLIP_TIMEOUT_S = 1200  # 20 min por clip, por intento.
MAX_INTENTOS = 2


def wav_duracion(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def mp4_duracion(path: Path) -> float | None:
    """Duración real del mp4 vía ffprobe (None si ffprobe no está o falla)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    try:
        return float(r.stdout.strip())
    except (ValueError, TypeError):
        return None


def convertir_webp_a_png(origen: Path, destino: Path) -> None:
    from PIL import Image
    img = Image.open(origen).convert("RGB")
    img.save(destino, "PNG")


def correr_sadtalker(sadtalker_dir: Path, png: Path, wav: Path,
                     ckpt_dir: Path, result_dir: Path,
                     timeout_s: int) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "inference.py",
        "--driven_audio", str(wav),
        "--source_image", str(png),
        "--checkpoint_dir", str(ckpt_dir),
        "--result_dir", str(result_dir),
        *SADTALKER_ARGS,
    ]
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "2"
    env["MKL_NUM_THREADS"] = "2"
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.run(cmd, cwd=str(sadtalker_dir), env=env,
                          timeout=timeout_s)


def escribir_reporte(ruta_json: Path, ruta_md: Path, filas: list[dict],
                     inicio: float) -> None:
    ok = sum(1 for f in filas if f["estado"] == "ok")
    datos = {
        "generado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(filas),
        "ok": ok,
        "fallidos": len(filas) - ok,
        "segundos_totales": round(time.time() - inicio, 1),
        "clips": filas,
    }
    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    ruta_json.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    lineas = ["# Reporte de clips — Episodio 1", "",
              f"OK: **{ok}/{len(filas)}** · "
              f"tiempo total: {datos['segundos_totales']:.0f} s", "",
              "| Escena | Personaje | Canal | Audio (s) | Clip (s) | Estado |",
              "|---|---|---|---|---|---|"]
    for f in filas:
        lineas.append(
            f"| {f['escena']:02d} | {f['personaje']} | {f['canal']} | "
            f"{f['audio_s']:.2f} | "
            f"{f['clip_s'] if f['clip_s'] is not None else '—'} | "
            f"{f['estado']} |")
    ruta_md.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", default="manifiesto_clips.json")
    ap.add_argument("--sadtalker-dir", default="SadTalker")
    ap.add_argument("--solo-sync", action="store_true",
                    help="solo clips con canal sync (17-18); salta los VO")
    ap.add_argument("--max-clips", type=int, default=0,
                    help="límite de clips a generar (0 = todos)")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    manifiesto = json.loads((root / args.manifiesto).read_text(encoding="utf-8"))
    clips = manifiesto["clips"]
    if args.solo_sync:
        clips = [c for c in clips if c["canal"] == "sync"]
    if args.max_clips > 0:
        clips = clips[:args.max_clips]

    sadtalker_dir = (root / args.sadtalker_dir).resolve()
    ckpt_dir = sadtalker_dir / "checkpoints"
    tmp_dir = root / "tmp_sadtalker"
    tmp_dir.mkdir(exist_ok=True)
    (root / "clips").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)

    # Validación previa: fallar rápido si falta un asset o un checkpoint.
    faltantes = []
    for c in clips:
        for clave in ("foto", "wav"):
            if not (root / c[clave]).is_file():
                faltantes.append(c[clave])
    for necesario in ("SadTalker_V0.0.2_256.safetensors",
                      "mapping_00109-model.pth.tar"):
        if not (ckpt_dir / necesario).is_file():
            faltantes.append(f"checkpoints/{necesario}")
    if not (ckpt_dir / "BFM_Fitting").is_dir():
        faltantes.append("checkpoints/BFM_Fitting/")
    if faltantes:
        print("FALTAN ARCHIVOS:", file=sys.stderr)
        for f in sorted(set(faltantes)):
            print(f"  - {f}", file=sys.stderr)
        return 2

    inicio = time.time()
    filas: list[dict] = []
    for c in clips:
        salida = root / c["salida"]
        fila = {
            "escena": c["escena"],
            "personaje": c["personaje"],
            "canal": c["canal"],
            "texto": c["texto"],
            "audio_s": c["audio_s"],
            "salida": c["salida"],
            "estado": "pendiente",
            "intentos": 0,
            "clip_s": None,
            "tamano_bytes": None,
            "segundos": None,
        }
        if salida.is_file() and salida.stat().st_size > 0:
            fila["estado"] = "ok (ya existía)"
            fila["tamano_bytes"] = salida.stat().st_size
            fila["clip_s"] = mp4_duracion(salida)
            print(f"[salto] escena {c['escena']:02d} {c['personaje']}: "
                  f"ya existe {c['salida']}")
            filas.append(fila)
            escribir_reporte(root / "logs/reporte_clips.json",
                             root / "logs/reporte_clips.md", filas, inicio)
            continue

        t0 = time.time()
        png = tmp_dir / f"escena{c['escena']:02d}-{c['personaje']}.png"
        convertir_webp_a_png(root / c["foto"], png)
        result_dir = tmp_dir / f"escena{c['escena']:02d}"
        result_dir.mkdir(exist_ok=True)

        exito = False
        for intento in range(1, MAX_INTENTOS + 1):
            fila["intentos"] = intento
            print(f"[escena {c['escena']:02d} {c['personaje']}] intento "
                  f"{intento}/{MAX_INTENTOS} — audio {c['audio_s']:.2f} s",
                  flush=True)
            try:
                r = correr_sadtalker(
                    sadtalker_dir, png, root / c["wav"], ckpt_dir,
                    result_dir, CLIP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                print(f"  TIMEOUT {CLIP_TIMEOUT_S}s en intento {intento}",
                      flush=True)
                continue
            print(f"  inference.py exit={r.returncode}", flush=True)
            if r.returncode != 0:
                continue
            mp4s = sorted(result_dir.rglob("*.mp4"))
            if not mp4s:
                print("  sin mp4 en result_dir", flush=True)
                continue
            shutil.move(str(mp4s[0]), str(salida))
            if salida.stat().st_size > 0:
                exito = True
                break

        fila["segundos"] = round(time.time() - t0, 1)
        if exito:
            fila["estado"] = "ok"
            fila["tamano_bytes"] = salida.stat().st_size
            fila["clip_s"] = mp4_duracion(salida)
            print(f"  OK {c['salida']} ({fila['clip_s']} s, "
                  f"{fila['tamano_bytes']} bytes, {fila['segundos']} s)",
                  flush=True)
        else:
            fila["estado"] = "FALLO"
            print(f"  FALLO escena {c['escena']:02d} tras "
                  f"{MAX_INTENTOS} intentos", flush=True)
        filas.append(fila)
        escribir_reporte(root / "logs/reporte_clips.json",
                         root / "logs/reporte_clips.md", filas, inicio)

    ok = sum(1 for f in filas if f["estado"].startswith("ok"))
    print(f"\nResumen: {ok}/{len(filas)} clips OK en "
          f"{time.time() - inicio:.0f} s")
    return 0 if ok == len(filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
