#!/usr/bin/env python3
"""
Convierte una imagen a modelo 3D usando TripoSR (local, sin API).

Uso:
    python3 imagen_a_3d.py <imagen.png>

Primera ejecución descarga el modelo (~1.5GB). Requiere: git, pip.
"""

import os
import sys
import subprocess
from pathlib import Path

TRIPOSR_DIR = Path.home() / ".triposr"
TRIPOSR_VENV = TRIPOSR_DIR / "venv"
TRIPOSR_PYTHON = TRIPOSR_VENV / "bin" / "python"
TRIPOSR_REPO = "https://github.com/VAST-AI-Research/TripoSR.git"


TRIPOSR_SENTINEL = TRIPOSR_VENV / "triposr_ok"


def instalar_triposr():
    if TRIPOSR_SENTINEL.exists():
        return
    print("Instalando TripoSR (primera vez, puede tardar unos minutos)...")
    if not TRIPOSR_DIR.exists():
        subprocess.check_call(["git", "clone", TRIPOSR_REPO, str(TRIPOSR_DIR)])

    # Recrear venv limpio si quedó incompleto
    if not TRIPOSR_PYTHON.exists():
        print("Creando entorno virtual...")
        subprocess.check_call([sys.executable, "-m", "venv", str(TRIPOSR_VENV)])

    subprocess.check_call([str(TRIPOSR_PYTHON), "-m", "pip", "install", "--upgrade", "pip"])

    # 1. Torch CPU-only primero — torchmcubes lo necesita para compilar.
    #    La versión por defecto en PyPI incluye CUDA y su cmake falla sin CUDA.
    print("Instalando PyTorch CPU-only (paso 1/4)...")
    subprocess.check_call([
        str(TRIPOSR_PYTHON), "-m", "pip", "install", "torch",
        "--index-url", "https://download.pytorch.org/whl/cpu",
        "--trusted-host", "download.pytorch.org",
    ])

    # Env con fix de política CMake para torchmcubes y xatlas
    env = os.environ.copy()
    env["CMAKE_ARGS"] = "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"

    # 2. torchmcubes (requiere torch ya instalado para cmake)
    print("Compilando torchmcubes (paso 2/4)...")
    subprocess.check_call([
        str(TRIPOSR_PYTHON), "-m", "pip", "install",
        "git+https://github.com/tatsy/torchmcubes.git"
    ], env=env)

    # 3. Resto de dependencias sin gradio ni xatlas (no requeridos para CLI)
    print("Instalando dependencias restantes (paso 3/3)...")
    req_orig = TRIPOSR_DIR / "requirements.txt"
    req_fixed = TRIPOSR_DIR / "requirements_fixed.txt"
    contenido = req_orig.read_text()
    contenido = contenido.replace("Pillow==10.1.0", "Pillow>=10.3.0")
    # rembg[cpu] incluye onnxruntime (necesario para remoción de fondo)
    contenido = contenido.replace("rembg\n", "rembg[cpu]\n").replace("rembg\r\n", "rembg[cpu]\r\n")
    # xatlas, moderngl: solo para --bake-texture (texturizado), no necesario para .glb básico
    excluir = {"gradio", "git+https://github.com/tatsy/torchmcubes.git", "xatlas", "moderngl"}
    lineas = [l for l in contenido.splitlines()
              if not any(l.strip().startswith(ex) or l.strip() == ex for ex in excluir)]
    req_fixed.write_text("\n".join(lineas) + "\n")
    subprocess.check_call([str(TRIPOSR_PYTHON), "-m", "pip", "install", "-r", str(req_fixed)])

    # Crear wrapper que deshabilita SSL (red del Senado intercepta HTTPS)
    wrapper = TRIPOSR_DIR / "run_nossl.py"
    wrapper.write_text(
        "import ssl, warnings, os, sys\n"
        "warnings.filterwarnings('ignore')\n"
        "ssl._create_default_https_context = ssl._create_unverified_context\n"
        "os.environ['CURL_CA_BUNDLE'] = ''\n"
        "os.environ['REQUESTS_CA_BUNDLE'] = ''\n"
        "try:\n"
        "    import requests, urllib3\n"
        "    urllib3.disable_warnings()\n"
        "    _orig = requests.adapters.HTTPAdapter.send\n"
        "    def _send(self, *a, **kw): kw['verify'] = False; return _orig(self, *a, **kw)\n"
        "    requests.adapters.HTTPAdapter.send = _send\n"
        "except ImportError:\n"
        "    pass\n"
        "import runpy\n"
        "_run = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run.py')\n"
        "runpy.run_path(_run, run_name='__main__')\n"
    )

    TRIPOSR_SENTINEL.touch()
    print("TripoSR instalado.\n")


def generar_modelo(image_path: str, output_dir: str, bake_texture: bool = False):
    run_script = TRIPOSR_DIR / "run_nossl.py"
    print("Generando modelo 3D (puede tardar 2-5 min en CPU)...")
    cmd = [
        str(TRIPOSR_PYTHON), str(run_script),
        image_path,
        "--output-dir", output_dir,
        "--device", "cpu",
    ]
    if bake_texture:
        cmd.append("--bake-texture")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Error al ejecutar TripoSR.")
        sys.exit(1)


def encontrar_mesh(output_dir: str) -> str:
    for ext in ["*.glb", "*.obj"]:
        archivos = list(Path(output_dir).rglob(ext))
        if archivos:
            return str(archivos[0])
    return ""


def crear_script_blender(mesh_path: str) -> str:
    ext = Path(mesh_path).suffix.lower()
    mesh_path_escaped = mesh_path.replace("\\", "/")
    texture_path = Path(mesh_path).parent / "texture.png"

    if ext in (".glb", ".gltf"):
        import_cmd = f'bpy.ops.import_scene.gltf(filepath=r"{mesh_path_escaped}")'
        texture_block = ""
    else:
        # Blender 4.x usa wm.obj_import en lugar de import_scene.obj
        import_cmd = f'bpy.ops.wm.obj_import(filepath=r"{mesh_path_escaped}")'
        if texture_path.exists():
            tex_escaped = str(texture_path).replace("\\", "/")
            texture_block = f"""
# Aplicar textura
obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None
if obj:
    mat = bpy.data.materials.new(name="TripoSR_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(r"{tex_escaped}")
    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print("Textura aplicada.")
"""
        else:
            texture_block = ""

    script = f"""import bpy

# Limpiar escena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

# Importar modelo generado
{import_cmd}

# Centrar en escena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
bpy.ops.object.location_clear()
{texture_block}
print("Modelo importado correctamente.")
"""
    script_path = Path(mesh_path).parent / "abrir_en_blender.py"
    script_path.write_text(script, encoding="utf-8")
    return str(script_path)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 imagen_a_3d.py <imagen.png>")
        sys.exit(1)

    image_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(image_path):
        print(f"Error: no se encontró '{image_path}'")
        sys.exit(1)

    output_dir = str(Path(image_path).parent / "output_3d")
    os.makedirs(output_dir, exist_ok=True)

    instalar_triposr()

    bake = "--bake-texture" in sys.argv
    print(f"Procesando: {Path(image_path).name}")
    generar_modelo(image_path, output_dir, bake_texture=bake)

    mesh_path = encontrar_mesh(output_dir)
    if not mesh_path:
        print("No se encontró el modelo generado en:", output_dir)
        sys.exit(1)

    print(f"\nModelo generado: {mesh_path}")

    blender_script = crear_script_blender(mesh_path)

    print("\n--- LISTO ---")
    print("Para abrir en Blender ejecutá:")
    print(f"  blender --python {blender_script}")
    print("\nO manualmente en Blender:")
    print("  File → Import → glTF 2.0 → seleccioná el .glb")
    print(f"  Archivo: {mesh_path}")


if __name__ == "__main__":
    main()
