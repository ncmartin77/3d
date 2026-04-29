import os
import sys
import subprocess
from pathlib import Path

TRIPOSR_DIR = Path.home() / ".triposr"
TRIPOSR_VENV = TRIPOSR_DIR / "venv"
TRIPOSR_PYTHON = TRIPOSR_VENV / "bin" / "python"
TRIPOSR_REPO = "https://github.com/VAST-AI-Research/TripoSR.git"
TRIPOSR_SENTINEL = TRIPOSR_VENV / "triposr_ok"


def install():
    if TRIPOSR_SENTINEL.exists():
        return

    print("Instalando TripoSR (primera vez, puede tardar unos minutos)...")

    if not TRIPOSR_DIR.exists():
        subprocess.check_call(["git", "clone", TRIPOSR_REPO, str(TRIPOSR_DIR)])

    if not TRIPOSR_PYTHON.exists():
        print("Creando entorno virtual...")
        subprocess.check_call([sys.executable, "-m", "venv", str(TRIPOSR_VENV)])

    subprocess.check_call([str(TRIPOSR_PYTHON), "-m", "pip", "install", "--upgrade", "pip"])

    print("Instalando PyTorch CPU-only (paso 1/3)...")
    subprocess.check_call([
        str(TRIPOSR_PYTHON), "-m", "pip", "install", "torch",
        "--index-url", "https://download.pytorch.org/whl/cpu",
        "--trusted-host", "download.pytorch.org",
    ])

    env = os.environ.copy()
    env["CMAKE_ARGS"] = "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"

    print("Compilando torchmcubes (paso 2/3)...")
    subprocess.check_call([
        str(TRIPOSR_PYTHON), "-m", "pip", "install",
        "git+https://github.com/tatsy/torchmcubes.git",
    ], env=env)

    print("Instalando dependencias restantes (paso 3/3)...")
    _patch_and_install_requirements()

    _write_ssl_wrapper()
    TRIPOSR_SENTINEL.touch()
    print("TripoSR instalado.\n")


def _patch_and_install_requirements():
    req_orig = TRIPOSR_DIR / "requirements.txt"
    req_fixed = TRIPOSR_DIR / "requirements_fixed.txt"

    contenido = req_orig.read_text()
    contenido = contenido.replace("Pillow==10.1.0", "Pillow>=10.3.0")
    contenido = contenido.replace("rembg\n", "rembg[cpu]\n")
    contenido = contenido.replace("rembg\r\n", "rembg[cpu]\r\n")

    excluir = {
        "gradio",
        "git+https://github.com/tatsy/torchmcubes.git",
        "xatlas",
        "moderngl",
    }
    lineas = [
        l for l in contenido.splitlines()
        if not any(l.strip().startswith(ex) or l.strip() == ex for ex in excluir)
    ]
    req_fixed.write_text("\n".join(lineas) + "\n")
    subprocess.check_call([str(TRIPOSR_PYTHON), "-m", "pip", "install", "-r", str(req_fixed)])


def _write_ssl_wrapper():
    # La red del Senado intercepta HTTPS con certificado propio; este wrapper
    # deshabilita la verificación SSL antes de que TripoSR descargue el modelo.
    wrapper = TRIPOSR_DIR / "run_nossl.py"
    wrapper.write_text(
        "import ssl, warnings, os\n"
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
