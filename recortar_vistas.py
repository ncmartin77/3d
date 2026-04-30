#!/usr/bin/env python3
"""
Recorta una imagen con 3 vistas horizontales en archivos separados
y lanza TripoSR sobre cada una.

Uso:
    python3 recortar_vistas.py estatua-san-la-muerte-05.jpg
    python3 recortar_vistas.py estatua-san-la-muerte-05.jpg --solo-recortar
"""

import argparse
import subprocess
import sys
from pathlib import Path
from PIL import Image


CORTES = [0, 600, 950, 1549]
NOMBRES = ["vista_frontal", "vista_lateral", "vista_posterior"]


def recortar(imagen_path: str, output_dir: Path) -> list[str]:
    img = Image.open(imagen_path)
    w, h = img.size
    output_dir.mkdir(parents=True, exist_ok=True)
    archivos = []

    for i, nombre in enumerate(NOMBRES):
        x0 = CORTES[i]
        x1 = CORTES[i + 1]
        recorte = img.crop((x0, 0, x1, h))
        dest = output_dir / f"{nombre}.png"
        recorte.save(dest)
        print(f"  {nombre}: x={x0}–{x1} → {dest}")
        archivos.append(str(dest))

    return archivos


def main():
    parser = argparse.ArgumentParser(description="Recorta vistas y genera modelos 3D.")
    parser.add_argument("imagen", help="Imagen con 3 vistas horizontales")
    parser.add_argument("--solo-recortar", action="store_true",
                        help="Solo recortar, sin lanzar TripoSR")
    parser.add_argument("--resolution", type=int, default=384)
    parser.add_argument("--chunk-size", type=int, default=2048)
    args = parser.parse_args()

    imagen_path = Path(args.imagen).resolve()
    if not imagen_path.exists():
        print(f"Error: no se encontró '{imagen_path}'")
        sys.exit(1)

    output_dir = imagen_path.parent / "vistas_recortadas"
    print(f"Recortando vistas de: {imagen_path.name}")
    archivos = recortar(str(imagen_path), output_dir)

    if args.solo_recortar:
        print("\nVistas guardadas en:", output_dir)
        return

    script = Path(__file__).parent / "imagen_a_3d.py"
    for archivo in archivos:
        nombre = Path(archivo).stem
        out = imagen_path.parent / f"output_3d_{nombre}"
        print(f"\n{'='*50}")
        print(f"Procesando: {nombre}")
        print(f"{'='*50}")
        subprocess.run([
            sys.executable, str(script),
            archivo,
            "--output-dir", str(out),
            "--resolution", str(args.resolution),
            "--chunk-size", str(args.chunk_size),
        ], check=True)


if __name__ == "__main__":
    main()
