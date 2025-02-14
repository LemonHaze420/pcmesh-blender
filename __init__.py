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
from mathutils import Vector
from mathutils import Matrix
from os import listdir
from os.path import isfile, isdir, join, dirname, splitext

from .pcmesh import *

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

def assign_texture_to_object(texture_path, object_name, mat=0):
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
        texture_image = bpy.data.images.load(texture_path)
    except RuntimeError:
        print("Cannot load texture ", texture_path)
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



def create_mesh(path, mesh_data):
    armature = bpy.data.armatures.new(f"{mesh_data.name}_Armature")
    armature_name = f"{mesh_data.name}_Armature"
    armature_object = bpy.data.objects.new(armature_name, armature)
    armature_object.rotation_euler[0] = 90 * (3.1415927 / 180)
    bpy.context.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    
    # create all bones first
    bpy.ops.object.mode_set(mode='EDIT')
    bone_map = {}
    root_bone = armature.edit_bones.new("Root")
    root_bone.head = Vector((0, 0, 0))
    root_bone.tail = Vector((0, 0.1, 0))
    for bone_idx, matrix in enumerate(mesh_data.bones):
        bn_name =f"Bone_{bone_idx}"
        if bn_name not in bone_map:
            bone = armature.edit_bones.new(bn_name)
            pos = Vector((matrix[3][0], matrix[3][1], matrix[3][2]))
            bone.head = pos
            rotation_matrix = matrix.to_3x3()
            direction = rotation_matrix @ Vector((0, 1, 0))
            bone.tail = bone.head + (direction * 0.1)
            bone.parent = root_bone
            bone_map[bn_name] = bone
    bpy.ops.object.mode_set(mode='OBJECT')

    for section in mesh_data.sections:
        mesh = bpy.data.meshes.new(section['name'])
        obj = bpy.data.objects.new(section['name'], mesh)
        bpy.context.collection.objects.link(obj)

        vertices = [Vector(v) for v in section['vertices']]
        indices = section['indices']
        primitive_type = section['primitive_type']

        # Faces
        faces = create_faces_from_indices(indices, primitive_type)
        if not faces:
            continue

        mesh.from_pydata(vertices, [], faces)
        mesh.update()

        # UVs
        if section['uvs']:
            if len(section['uvs']) == len(vertices):
                uv_layer = mesh.uv_layers.new(name="UVMap")
                for loop in mesh.loops:
                    loop_uv = uv_layer.data[loop.index]
                    loop_uv.uv = [ section['uvs'][loop.vertex_index][0], 1.0 - section['uvs'][loop.vertex_index][1] ]

        # Materials
        section0 = mesh_data.sections[0]
        if section0.get('materials'):
            assign_texture_to_object(os.path.join(os.path.dirname(path), section0['materials'][0]), section['name'])
            
        # Normals
        #if section['normals']:
        #   if len(section['normals']) == len(vertices):
        #       mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        #       mesh.normals_split_custom_set_from_vertices(section['normals'])
        #       mesh.use_auto_smooth = True

        obj.parent = armature_object

        # Bones
        if section.get('bones'):
            for vtx_idx, bone_data in enumerate(section['bones']):
                bone_indices = bone_data['indices']
                bone_weights = bone_data['weights']
                for i in range(4):
                    weight = bone_weights[i]
                    bone_idx = bone_indices[i]
                    if weight > 0:
                        bone_name = f"Bone_{int(bone_idx)}"
                        if bone_name in obj.vertex_groups:
                            group = obj.vertex_groups[bone_name]
                        else:
                            group = obj.vertex_groups.new(name=bone_name)
                        group.add([vtx_idx], weight, 'ADD')

    print(f"Finished importing {mesh_data.name}")
    
    

class PCMESHImporter(bpy.types.Operator):
    bl_idname = "import_scene.pcmesh"
    bl_label = "Import PCMESH"
    bl_options = {'PRESET', 'UNDO'}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    def execute(self, context):
        current_path = self.filepath
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
                indices = []
                weights = []
                for group in v.groups:
                        group_index = group.group
                        weight = group.weight
                        if group_index < len(vertex_groups):
                                indices.append(group_index)
                                weights.append(weight)
                while len(indices) < 4:
                        indices.append(0)
                        weights.append(0.0)
                if len(indices) > 4:
                        indices = indices[:4]
                        weights = weights[:4]
                bone_indices.append(tuple(indices))
                bone_weights.append(tuple(weights))
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
