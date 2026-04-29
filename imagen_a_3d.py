#!/usr/bin/env python3
"""
Convierte una imagen a modelo 3D importable en Blender usando TripoSR (local, sin API).

Ejemplos:
    python3 imagen_a_3d.py foto.png
    python3 imagen_a_3d.py foto.png --bake-texture
    python3 imagen_a_3d.py foto.png --bake-texture --resolution 512
    python3 imagen_a_3d.py foto.png --texture mi_textura.png
    python3 imagen_a_3d.py foto.png --output-dir ~/modelos/silla
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from triposr_tools import install, generate, find_mesh, create_blender_script


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convierte una imagen a modelo 3D para Blender usando TripoSR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "imagen",
        metavar="IMAGEN",
        nargs="?",
        help="Imagen de entrada (.png, .jpg)",
    )
    parser.add_argument(
        "--solo-blender",
        metavar="MESH",
        default=None,
        help="Regenerar solo el script de Blender sobre un mesh existente (.obj o .glb), sin reprocesar la imagen",
    )
    parser.add_argument(
        "--output-dir", "-o",
        metavar="DIR",
        default=None,
        help="Directorio de salida (default: output_3d/ junto a la imagen)",
    )

    # --- Textura ---
    tex = parser.add_argument_group("textura")
    tex.add_argument(
        "--bake-texture",
        action="store_true",
        help="Generar textura UV automáticamente con TripoSR",
    )
    tex.add_argument(
        "--texture", "-t",
        metavar="IMAGEN",
        default=None,
        help="Imagen de textura personalizada a aplicar en Blender (tiene prioridad sobre --bake-texture)",
    )
    tex.add_argument(
        "--texture-resolution",
        metavar="N",
        type=int,
        default=2048,
        help="Resolución del atlas de textura en píxeles (default: 2048, solo con --bake-texture)",
    )

    # --- Malla ---
    mesh = parser.add_argument_group("malla")
    mesh.add_argument(
        "--resolution", "-r",
        metavar="N",
        type=int,
        default=256,
        help="Resolución del marching cubes (default: 256, mejor calidad: 384; 512 requiere >8GB RAM)",
    )
    mesh.add_argument(
        "--chunk-size",
        metavar="N",
        type=int,
        default=8192,
        help="Tamaño de chunk para evaluación del modelo (default: 8192, reducir si hay OOM)",
    )
    mesh.add_argument(
        "--format",
        metavar="FMT",
        choices=["obj", "glb"],
        default="obj",
        help="Formato del mesh exportado: obj o glb (default: obj)",
    )

    # --- Preprocesado de imagen ---
    pre = parser.add_argument_group("preprocesado de imagen")
    pre.add_argument(
        "--foreground-ratio",
        metavar="F",
        type=float,
        default=0.85,
        help="Proporción del objeto en la imagen tras remover fondo (default: 0.85)",
    )
    pre.add_argument(
        "--no-remove-bg",
        action="store_true",
        help="No remover el fondo automáticamente (la imagen ya debe tener fondo gris)",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.solo_blender:
        mesh_path = os.path.abspath(args.solo_blender)
        if not os.path.exists(mesh_path):
            print(f"Error: no se encontró el mesh '{mesh_path}'")
            sys.exit(1)
        texture = os.path.abspath(args.texture) if args.texture else ""
        blender_script = create_blender_script(mesh_path=mesh_path, custom_texture=texture)
        print(f"Script de Blender regenerado: {blender_script}")
        print("\nPara abrir en Blender ejecutá:")
        print(f"  blender --python {blender_script}")
        return

    if not args.imagen:
        print("Error: se requiere una imagen o --solo-blender MESH")
        sys.exit(1)

    image_path = os.path.abspath(args.imagen)
    if not os.path.exists(image_path):
        print(f"Error: no se encontró '{image_path}'")
        sys.exit(1)

    if args.texture and not os.path.exists(args.texture):
        print(f"Error: no se encontró la textura '{args.texture}'")
        sys.exit(1)

    output_dir = args.output_dir or str(Path(image_path).parent / "output_3d")
    os.makedirs(output_dir, exist_ok=True)

    install()

    print(f"Procesando: {Path(image_path).name}")
    generate(
        image_path=image_path,
        output_dir=output_dir,
        bake_texture=args.bake_texture,
        mc_resolution=args.resolution,
        texture_resolution=args.texture_resolution,
        foreground_ratio=args.foreground_ratio,
        no_remove_bg=args.no_remove_bg,
        model_save_format=args.format,
        chunk_size=args.chunk_size,
    )

    mesh_path = find_mesh(output_dir)
    if not mesh_path:
        print(f"Error: no se encontró el modelo generado en: {output_dir}")
        sys.exit(1)

    print(f"\nModelo generado: {mesh_path}")

    blender_script = create_blender_script(
        mesh_path=mesh_path,
        custom_texture=os.path.abspath(args.texture) if args.texture else "",
    )

    print("\n--- LISTO ---")
    print("Para abrir en Blender ejecutá:")
    print(f"  blender --python {blender_script}")
    print(f"\nArchivo 3D : {mesh_path}")
    if args.texture:
        print(f"Textura    : {args.texture} (personalizada)")
    elif (Path(mesh_path).parent / "texture.png").exists():
        print(f"Textura    : {Path(mesh_path).parent / 'texture.png'} (generada por TripoSR)")


if __name__ == "__main__":
    main()
