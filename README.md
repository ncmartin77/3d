# imagen-a-3D

Convierte una foto a modelo 3D importable en Blender usando [TripoSR](https://github.com/VAST-AI-Research/TripoSR) — sin API de pago ni conexión a internet obligatoria (salvo la primera vez que descarga el modelo).

## Requisitos

- Python 3.10 o superior
- Git
- Blender 4.x (para abrir el modelo)
- ~3GB de espacio en disco (modelo de TripoSR)
- 8GB de RAM mínimo recomendado

## Instalación

No requiere instalación manual. La primera vez que se ejecuta, el script descarga e instala TripoSR automáticamente en `~/.triposr/`.

```bash
git clone https://github.com/ncmartin77/3d.git
cd 3d
```

## Uso básico

```bash
python3 imagen_a_3d.py foto.png
```

Genera `mesh.obj` (colores de vértice) y un script `abrir_en_blender.py` en la carpeta `output_3d/`.

## Uso con textura UV

```bash
python3 imagen_a_3d.py foto.png --bake-texture
```

Genera `mesh.obj` + `texture.png` (atlas UV 2048×2048).

## Todos los parámetros

```
python3 imagen_a_3d.py IMAGEN [opciones]
```

### Textura

| Parámetro | Descripción | Default |
|---|---|---|
| `--bake-texture` | Genera textura UV automáticamente con TripoSR | desactivado |
| `--texture IMAGEN` / `-t` | Imagen de textura personalizada a aplicar en Blender | — |
| `--texture-resolution N` | Resolución del atlas UV en píxeles | `2048` |

> Si se pasan `--bake-texture` y `--texture` juntos, la textura personalizada tiene prioridad en el script de Blender.

### Malla

| Parámetro | Descripción | Default |
|---|---|---|
| `--resolution N` / `-r` | Resolución del marching cubes | `256` |
| `--chunk-size N` | Tamaño de chunk para evaluación (reducir si hay error de memoria) | `8192` |
| `--format obj\|glb` | Formato del archivo 3D exportado | `obj` |

**Guía de resoluciones:**

| Resolución | Calidad | RAM requerida | Tiempo (CPU) |
|---|---|---|---|
| `256` | Base | ~2GB | ~40 seg |
| `384` | Buena | ~5GB | ~2 min |
| `512` | Alta | >8GB | — |

### Preprocesado de imagen

| Parámetro | Descripción | Default |
|---|---|---|
| `--foreground-ratio F` | Proporción del objeto en la imagen tras remover fondo | `0.85` |
| `--no-remove-bg` | No remover el fondo (la imagen ya debe tener fondo gris) | desactivado |

### Salida

| Parámetro | Descripción | Default |
|---|---|---|
| `--output-dir DIR` / `-o` | Directorio de salida | `output_3d/` junto a la imagen |

## Ejemplos

```bash
# Modelo básico
python3 imagen_a_3d.py foto.png

# Con textura UV y mejor resolución
python3 imagen_a_3d.py foto.png --bake-texture --resolution 384

# Si hay error de memoria con resolución alta
python3 imagen_a_3d.py foto.png --bake-texture --resolution 384 --chunk-size 2048

# Con textura personalizada (editada externamente)
python3 imagen_a_3d.py foto.png --texture mi_textura.png

# Guardar en carpeta específica
python3 imagen_a_3d.py foto.png --bake-texture --output-dir ~/modelos/silla

# Exportar en formato GLB
python3 imagen_a_3d.py foto.png --format glb
```

## Abrir en Blender

Al terminar, el script genera `abrir_en_blender.py` en el directorio de salida.

**Opción 1 — desde la terminal:**
```bash
blender --python output_3d/0/abrir_en_blender.py
```

**Opción 2 — desde Blender:**
1. Abrir Blender
2. `Scripting` → abrir `abrir_en_blender.py` → ejecutar

El script limpia la escena, importa el modelo y aplica la textura automáticamente.

## Estructura del proyecto

```
imagen_a_3d.py          ← CLI principal
triposr_tools/
    install.py          ← instalación automática de TripoSR
    generate.py         ← generación del modelo 3D
    blender_export.py   ← generación del script de Blender
    __init__.py
output_3d_512/0/
    mesh.obj            ← modelo de ejemplo (resolución 384)
    texture.png         ← textura UV 2048×2048
    abrir_en_blender.py ← script listo para usar en Blender
```

## Notas

- La primera ejecución descarga el modelo de TripoSR (~1.7GB) desde HuggingFace.
- Si la red usa un proxy con certificado propio (como redes corporativas), el script maneja la verificación SSL automáticamente.
- TripoSR se instala en `~/.triposr/` con su propio entorno virtual, sin afectar el sistema.
