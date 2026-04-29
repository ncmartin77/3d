from pathlib import Path


def create_blender_script(mesh_path: str, custom_texture: str = "") -> str:
    ext = Path(mesh_path).suffix.lower()
    mesh_escaped = mesh_path.replace("\\", "/")

    # Prioridad: textura custom > textura generada por TripoSR > sin textura
    auto_texture = Path(mesh_path).parent / "texture.png"
    texture_file = custom_texture or (str(auto_texture) if auto_texture.exists() else "")

    if ext in (".glb", ".gltf"):
        import_cmd = f'bpy.ops.import_scene.gltf(filepath=r"{mesh_escaped}")'
        texture_block = ""
    else:
        # Blender 4.x renombró import_scene.obj → wm.obj_import
        import_cmd = f'bpy.ops.wm.obj_import(filepath=r"{mesh_escaped}")'
        texture_block = _build_texture_block(texture_file) if texture_file else ""

    script = f"""import bpy

# Limpiar escena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

# Importar modelo
{import_cmd}

# Centrar en escena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
bpy.ops.object.location_clear()
{texture_block}
# Suavizado del mesh
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj

        # Shade smooth (sombreado sin coste)
        bpy.ops.object.shade_smooth()

        # Smooth corrective: suaviza irregularidades del marching cubes
        smooth = obj.modifiers.new(name="Smooth", type='SMOOTH')
        smooth.factor = 0.5
        smooth.iterations = 5

        # Subdivision Surface nivel 1: nivel 2+ causa OOM con mesh de 384 (~500K tris)
        subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
        subsurf.subdivision_type = 'CATMULL_CLARK'
        subsurf.levels = 1
        subsurf.render_levels = 1

print("Modelo importado correctamente.")
"""

    script_path = Path(mesh_path).parent / "abrir_en_blender.py"
    script_path.write_text(script, encoding="utf-8")
    return str(script_path)


def _build_texture_block(texture_path: str) -> str:
    tex_escaped = texture_path.replace("\\", "/")
    return f"""
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
    print("Textura aplicada: {tex_escaped}")
"""
