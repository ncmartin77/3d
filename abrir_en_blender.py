import bpy

# Limpiar escena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

# Importar modelo generado
bpy.ops.wm.obj_import(filepath=r"/home/20258944020/Documentos/output_3d/0/mesh.obj")

# Centrar en escena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
bpy.ops.object.location_clear()

# Aplicar textura
obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None
if obj:
    mat = bpy.data.materials.new(name="TripoSR_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(r"/home/20258944020/Documentos/output_3d/0/texture.png")
    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print("Textura aplicada.")

print("Modelo importado correctamente.")
