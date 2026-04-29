#!/usr/bin/env python3
"""
Script que analiza una imagen con Claude Vision y genera un modelo 3D para Blender.

Uso:
    python3 image_to_blender.py [carpeta]

Si no se indica carpeta, usa la carpeta del propio script.
Requiere: ANTHROPIC_API_KEY como variable de entorno.
"""

import anthropic
import base64
import httpx
import os
import sys
from pathlib import Path


def encode_image(image_path: str) -> tuple[str, str]:
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "image/png")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def describe_image(client: anthropic.Anthropic, image_path: str) -> str:
    print(f"\nAnalizando imagen: {Path(image_path).name}")

    image_data, media_type = encode_image(image_path)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="Eres un experto en modelado 3D. Describes objetos con precisión técnica para facilitar su recreación en software 3D.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Describe detalladamente este objeto para recrearlo en 3D. Incluye:\n"
                            "- Tipo de objeto y función\n"
                            "- Forma general y proporciones (alto/ancho/profundidad relativos)\n"
                            "- Componentes principales con dimensiones relativas\n"
                            "- Materiales y texturas visibles\n"
                            "- Detalles estructurales: ángulos, curvas, ensambles\n"
                            "- Colores predominantes\n"
                            "Sé específico y técnico para facilitar la modelación 3D."
                        ),
                    },
                ],
            }
        ],
    )

    description = message.content[0].text
    print("\n--- DESCRIPCIÓN ---")
    print(description)
    print("-------------------\n")
    return description


def generate_blender_script(client: anthropic.Anthropic, description: str) -> str:
    print("Generando script para Blender...")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=(
            "Eres un experto en scripting de Blender con la API bpy. "
            "Generas scripts Python completos, funcionales y bien comentados en español. "
            "Usas bmesh o mesh primitives según corresponda. "
            "Siempre limpias la escena al inicio y usas materiales con colores apropiados."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Basándote en esta descripción, genera un script Python completo para Blender "
                    f"que cree el objeto 3D usando la API bpy.\n\n"
                    f"DESCRIPCIÓN:\n{description}\n\n"
                    f"REQUISITOS:\n"
                    f"1. Limpiar escena al inicio (eliminar objetos y materiales por defecto)\n"
                    f"2. Crear el objeto con mesh primitives (cubos, cilindros) o bmesh\n"
                    f"3. Aplicar escala, rotación y posición correctas\n"
                    f"4. Asignar materiales con colores/roughness apropiados\n"
                    f"5. Nombrar todos los objetos de forma descriptiva\n"
                    f"6. Comentarios en español explicando cada sección\n"
                    f"7. Ejecutable directamente desde el editor de texto de Blender\n"
                    f"8. Unidades en metros (escala realista)\n\n"
                    f"Genera SOLO el código Python, sin explicaciones ni bloques markdown."
                ),
            }
        ],
    )

    script = message.content[0].text

    # Eliminar bloques markdown si los hay
    if "```python" in script:
        script = script.split("```python")[1].split("```")[0].strip()
    elif "```" in script:
        script = script.split("```")[1].split("```")[0].strip()

    return script


def find_images(folder: str) -> list[str]:
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    return [
        str(p)
        for p in Path(folder).iterdir()
        if p.suffix.lower() in extensions
    ]


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: falta la variable de entorno ANTHROPIC_API_KEY.")
        print("Configúrala con:  export ANTHROPIC_API_KEY='tu-api-key'")
        sys.exit(1)

    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(folder):
        print(f"Error: '{folder}' no es una carpeta válida.")
        sys.exit(1)

    images = find_images(folder)

    if not images:
        print(f"No se encontraron imágenes en: {folder}")
        sys.exit(1)

    print(f"Imágenes encontradas ({len(images)}):")
    for i, img in enumerate(images):
        print(f"  [{i + 1}] {Path(img).name}")

    if len(images) == 1:
        selected = images[0]
        print(f"\nUsando: {Path(selected).name}")
    else:
        while True:
            try:
                idx = int(input("\nSeleccioná el número de imagen a procesar: ")) - 1
                if 0 <= idx < len(images):
                    selected = images[idx]
                    break
                print("Número inválido.")
            except ValueError:
                print("Ingresá un número.")

    client = anthropic.Anthropic(
        api_key=api_key,
        http_client=httpx.Client(verify=False),
    )

    # Paso 1: describir imagen
    description = describe_image(client, selected)

    # Paso 2: generar script Blender
    blender_script = generate_blender_script(client, description)

    # Paso 3: guardar script
    output_path = Path(folder) / f"{Path(selected).stem}_blender.py"
    output_path.write_text(blender_script, encoding="utf-8")

    print(f"Script guardado en: {output_path.name}")
    print("\nCómo usarlo en Blender:")
    print("  1. Abrí Blender")
    print("  2. Ir a la pestaña 'Scripting' en el menú superior")
    print(f"  3. Clic en 'Open' y seleccioná '{output_path.name}'")
    print("  4. Clic en 'Run Script' (o Alt+P)")


if __name__ == "__main__":
    main()
