bl_info = {
    "name": "PCMESH Tools",
    "author": "LemonHaze",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "File > Import-Export",
    "description": "Imports/exports PCMESH files from USM",
    "category": "Import-Export",
}

import bpy
import sys
import io
import os
import mathutils

from pathlib import Path
from mathutils import Vector
from mathutils import Matrix
from os import listdir
from os.path import isfile, isdir, join, dirname, splitext

from .pcmesh import *

created_first = False

def create_faces_from_indices(indices, primitive_type):
    faces = []
    if primitive_type == 5:
        if len(indices) < 3:
            print("Not enough indices for a triangle strip")
            return faces

        face = [indices[0], indices[1], indices[2]]
        if len(set(face)) == 3:
            faces.append(tuple(face))

        for idx in indices[3:]:
            face = [face[1], face[2], idx]
            if len(set(face)) == 3:
                faces.append(tuple(face))
    elif primitive_type == 4: 
        if len(indices) % 3 != 0:
            indices = indices[:len(indices) - (len(indices) % 3)] 
        faces = [tuple(indices[i:i + 3]) for i in range(0, len(indices), 3)]
    else:
        print(f"Unsupported primitive type: {primitive_type}")
    return faces
   
def load_asset(asset_path):
    p = Path(asset_path).expanduser()
    if p.is_file():
        return str(p)

    parent = p.parent
    if not parent.exists():
        parent = Path.cwd()

    filename = p.name

    game_path = parent / "GAME" / filename
    if game_path.is_file():
        return str(game_path)
    try:
        for child in parent.iterdir():
            if child.is_dir():
                found = next(child.rglob(filename), None)
                if found and found.is_file():
                    return str(found)
    except PermissionError:
        pass
    return None

def assign_texture_to_object(texture_path, object_name, mat=0):
    found_path = load_asset(texture_path)
    if not found_path:
        print(f"Can't find texture {texture_path}")
        return
    
    material = bpy.data.materials.new(name=f"{object_name}_Material{mat}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    nodes.clear()
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    output_node.location = (400, 0)

    principled_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled_bsdf.location = (0, 0)

    links.new(principled_bsdf.outputs["BSDF"], output_node.inputs["Surface"])

    image_texture = nodes.new(type="ShaderNodeTexImage")
    image_texture.location = (-400, 0)

    try:
        texture_image = bpy.data.images.load(found_path)
    except RuntimeError:
        print("Cannot load texture ", found_path)
        return
    else:
        image_texture.image = texture_image
        links.new(image_texture.outputs["Color"], principled_bsdf.inputs["Base Color"])

    def apply_material_recursive(obj):
        if len(obj.data.materials) > 0:
            obj.data.materials[mat] = material
        else:
            obj.data.materials.append(material)

        for child in obj.children:
            if child.type == 'MESH':
                apply_material_recursive(child)

    obj = bpy.data.objects.get(object_name)
    if obj is not None:
        if obj.type == 'MESH':
            apply_material_recursive(obj)
    else:
        print(f"Object '{object_name}' not found")

bone_ids = {
    -1: "NO_BONE",
     0: "BONE_PS",
     1: "BONE_S",
     2: "BONE_S1",
     3: "BONE_S2",
     4: "BONE_N",
     5: "BONE_H",           #
     6: "BONE_LC",     #
     7: "BONE_LU",     #
     8: "BONE_LF",      #
     9: "BONE_LH",         #
    10: "BONE_RC",     #
    11: "BONE_RU",     #
} 
def get_bone_name(bone_idx: int) -> str:
    return bone_ids.get(bone_idx, f"Bone_{int(bone_idx)}")


def create_mesh(path, mesh_data):
    # create all bones first
    armature = bpy.data.armatures.new(f"{mesh_data.name}_Armature")
    armature_name = f"{mesh_data.name}_Armature"
    armature_object = bpy.data.objects.new(armature_name, armature)
    armature_object.rotation_euler[0] = 90 * (3.1415927 / 180)
    bpy.context.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    
    bpy.ops.object.mode_set(mode='EDIT')
    bone_map = {}
    arm = armature_object
    edit_bones = arm.data.edit_bones
    for bone_idx, mat_data in enumerate(mesh_data.bones):
        bone_name = get_bone_name(bone_idx)
        mat = Matrix(mat_data).transposed()
        eb = edit_bones.new(bone_name)
        eb.head = mat.to_translation()
        eb.tail = eb.head + (mat.to_3x3() @ Vector((-1, 0, 0))) * 0.1
        eb.roll = 0.0
        bone_map[bone_name] = eb
    all_vertices = []
    all_faces = []
    all_uvs = []
    all_section_bone_data = []
    vertex_offset = 0
    
    # collect geom
    bpy.ops.object.mode_set(mode='OBJECT')
    for section in mesh_data.sections:
        verts = [Vector(v) for v in section['vertices']]
        prim = section['primitive_type']

        faces = create_faces_from_indices(indices=section['indices'], primitive_type=prim)
        faces = [tuple(v + vertex_offset for v in face) for face in faces]

        all_vertices.extend(verts)
        all_faces.extend(faces)

        if section.get("uvs"):
            all_uvs.extend(section["uvs"])
        else:
            all_uvs.extend([None] * len(verts))

        if section.get("bones"):
            all_section_bone_data.append((vertex_offset, section["bones"]))

        vertex_offset += len(verts)

    mesh = bpy.data.meshes.new(mesh_data.name)
    obj = bpy.data.objects.new(mesh_data.name, mesh)
    global created_first
    if created_first:
        armature_object.hide_viewport = True
        obj.hide_viewport = True
    else:
        created_first = True

    bpy.context.collection.objects.link(obj)

    mesh.from_pydata(all_vertices, [], all_faces)
    mesh.update()

    if any(all_uvs):
        uv_layer = mesh.uv_layers.new()
        for loop in mesh.loops:
            idx = loop.vertex_index
            uv = all_uvs[idx]
            if uv:
                uv_layer.data[loop.index].uv = (uv[0], 1.0 - uv[1])

    # map sections
    for vertex_offset, section_bones in all_section_bone_data:
        for local_idx, bone_data in enumerate(section_bones):
            for bone_idx, weight in zip(bone_data["indices"], bone_data["weights"]):
                bone_name = get_bone_name(bone_idx)

                if bone_name not in obj.vertex_groups:
                    obj.vertex_groups.new(name=bone_name)

                obj.vertex_groups[bone_name].add(
                    [vertex_offset + local_idx], weight, 'ADD'
                )
    mod = obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = armature_object
    
    section0 = mesh_data.sections[0]
    if section0.get('materials'):       # @todo: multiple mats
        assign_texture_to_object(os.path.join(os.path.dirname(path), section0['materials'][0]), mesh_data.name)#section['name'])                
    obj.parent = armature_object
    
    """
        # Normals
        #if section['normals']:
        #   if len(section['normals']) == len(vertices):
        #       mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        #       mesh.normals_split_custom_set_from_vertices(section['normals'])
        #       mesh.use_auto_smooth = True
    """
    print(f"Finished importing {mesh_data.name}")
    return obj

class PCMESHImporter(bpy.types.Operator):
    bl_idname = "import_scene.pcmesh"
    bl_label = "Import PCMESH"
    bl_options = {'PRESET', 'UNDO'}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    def execute(self, context):
        current_path = self.filepath
        global created_first
        created_first = False
        for mesh_data in read_meshfile(self.filepath):
                create_mesh(self.filepath, mesh_data)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class PCMESHExporter(bpy.types.Operator):
    bl_idname = "export_scene.pcmesh"
    bl_label = "Export PCMESH"
    bl_options = {'PRESET', 'UNDO'}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    def execute(self, context):
        current_path = self.filepath
        
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected!")
            return {'CANCELLED'}
        
        mesh = obj.data
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.calc_loop_triangles()
        
        vertices = [tuple(v.co) for v in mesh.vertices]
        indices = [tuple(tri.vertices) for tri in mesh.loop_triangles]
        normals =  [tuple(tri.normal) for tri in mesh.loop_triangles]
        uv_layer = mesh.uv_layers.active
        uvs = [tuple(uv_layer.data[loop.index].uv) for loop in mesh.loops]
        vertex_groups = obj.vertex_groups
        bone_indices = []
        bone_weights = []
        bones = [] # @todo: fill names
        for v in mesh.vertices:
                bindices = []
                bweights = []
                for group in v.groups:
                        group_index = group.group
                        weight = group.weight
                        if group_index < len(vertex_groups):
                                bindices.append(group_index)
                                bweights.append(weight)
                while len(indices) < 4:
                        bindices.append(0)
                        bweights.append(0.0)
                if len(indices) > 4:
                        bindices = bindices[:4]
                        bweights = bweights[:4]
                bone_indices.append(tuple(bindices))
                bone_weights.append(tuple(bweights))
        write_meshfile(self.filepath, UserMeshData(vertices, indices, normals, uvs, bones, bone_indices, bone_weights))
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func_import(self, context):
    self.layout.operator(PCMESHImporter.bl_idname, text="PCMESH (.pcmesh)")

def menu_func_export(self, context):
    self.layout.operator(PCMESHExporter.bl_idname, text="PCMESH (.pcmesh)")

def register():
    bpy.utils.register_class(PCMESHImporter)
    bpy.utils.register_class(PCMESHExporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    init()

def unregister():
    bpy.utils.unregister_class(PCMESHImporter)
    bpy.utils.unregister_class(PCMESHExporter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
