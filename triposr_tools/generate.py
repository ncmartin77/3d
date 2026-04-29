import subprocess
import sys
from pathlib import Path

from .install import TRIPOSR_PYTHON, TRIPOSR_DIR


def generate(
    image_path: str,
    output_dir: str,
    bake_texture: bool = False,
    mc_resolution: int = 256,
    texture_resolution: int = 2048,
    foreground_ratio: float = 0.85,
    no_remove_bg: bool = False,
    model_save_format: str = "obj",
    chunk_size: int = 8192,
):
    run_script = TRIPOSR_DIR / "run_nossl.py"
    print(f"Generando modelo 3D (resolución: {mc_resolution})...")

    cmd = [
        str(TRIPOSR_PYTHON), str(run_script),
        image_path,
        "--output-dir", output_dir,
        "--device", "cpu",
        "--mc-resolution", str(mc_resolution),
        "--chunk-size", str(chunk_size),
        "--foreground-ratio", str(foreground_ratio),
        "--model-save-format", model_save_format,
    ]

    if bake_texture:
        cmd += ["--bake-texture", "--texture-resolution", str(texture_resolution)]

    if no_remove_bg:
        cmd.append("--no-remove-bg")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Error al ejecutar TripoSR.")
        sys.exit(1)


def find_mesh(output_dir: str) -> str:
    for ext in ["*.obj", "*.glb"]:
        matches = list(Path(output_dir).rglob(ext))
        if matches:
            return str(matches[0])
    return ""
