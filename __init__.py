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
import json
import math
import mathutils

from pathlib import Path
from mathutils import Vector
from mathutils import Matrix
from os import listdir
from os.path import isfile, isdir, join, dirname, splitext
from .pcskel import *
from .pcmesh import *
from .pcanim import open_pcanim, FLAG_LOOPING, FLAG_SCENE_ANIM

created_first = False
requested_pcmesh = ""
skel_data = {}
loaded_skel_path = ""

_ENGINE_TO_BLENDER_BASIS = Matrix.Rotation(math.radians(90.0), 4, 'X')
_BLENDER_TO_ENGINE_BASIS = _ENGINE_TO_BLENDER_BASIS.inverted()
_ENGINE_TO_BLENDER_BASIS_3 = _ENGINE_TO_BLENDER_BASIS.to_3x3()
_BLENDER_TO_ENGINE_BASIS_3 = _BLENDER_TO_ENGINE_BASIS.to_3x3()


def _engine_to_blender_vec3(v):
    return _ENGINE_TO_BLENDER_BASIS_3 @ Vector((float(v[0]), float(v[1]), float(v[2])))


def _blender_to_engine_vec3(v):
    return _BLENDER_TO_ENGINE_BASIS_3 @ Vector((float(v[0]), float(v[1]), float(v[2])))


def _engine_to_blender_matrix4(m):
    return _ENGINE_TO_BLENDER_BASIS @ m @ _BLENDER_TO_ENGINE_BASIS

class OT_OpenFileBrowser(bpy.types.Operator):
    bl_idname = "wm.open_pcskel"
    bl_label = "Select a skeleton"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        global requested_pcmesh
        import_pcmesh(requested_pcmesh, self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def import_pcmesh(pcmesh_path, skel_path=None):
    global skel_data
    global loaded_skel_path
    skel_data = {}
    loaded_skel_path = skel_path or ""

    if skel_path is not None:
        skel_data = open_pcskel(skel_path)
        print(f"Loaded {skel_data['header']['name']}")

    created_meshes = []
    for mesh_data in read_meshfile(pcmesh_path):
        obj = create_mesh(pcmesh_path, mesh_data)
        if obj is not None:
            created_meshes.append(obj)

    if len(created_meshes) <= 1:
        return

    keep = set()
    first_mesh = created_meshes[0]
    keep.add(first_mesh)
    first_arm = first_mesh.parent if first_mesh.parent and first_mesh.parent.type == 'ARMATURE' else None
    if first_arm is not None:
        keep.add(first_arm)

    def hide(obj):
        try:
            obj.hide_set(True)
            obj.hide_viewport = True
            obj.hide_render = True
        except Exception:
            pass

    for mesh_obj in created_meshes[1:]:
        if mesh_obj in keep:
            continue
        hide(mesh_obj)
        arm_obj = mesh_obj.parent if mesh_obj.parent and mesh_obj.parent.type == 'ARMATURE' else None
        if arm_obj is not None and arm_obj not in keep:
            hide(arm_obj)


def create_faces_from_indices(indices, primitive_type):
    faces = []
    if primitive_type == 5:
        if len(indices) < 3:
            print("Not enough indices for a triangle strip")
            return faces

        for i in range(len(indices) - 2):
            a, b, c = indices[i], indices[i + 1], indices[i + 2]
            if i % 2 == 1:
                a, b = b, a
            if len({a, b, c}) == 3:
                faces.append((a, b, c))
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

    game_path = parent.parent / "GAME" / filename
    if game_path.is_file():
        return str(game_path)
    try:
        root = parent.parent
        if root.exists():
            for child in root.iterdir():
                if child.is_dir():
                    found = next(child.rglob(filename), None)
                    if found and found.is_file():
                        return str(found)
    except PermissionError:
        pass

    return None

def _create_material_for_section(mat_path, name):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    links.new(principled.outputs["BSDF"], output_node.inputs["Surface"])
    if mat_path:
        found = load_asset(os.path.join(os.path.dirname(mat_path), name))
        if found:
            try:
                img = bpy.data.images.load(found)
            except Exception:
                pass
            else:
                img_node = nodes.new(type="ShaderNodeTexImage")
                img_node.image = img
                links.new(img_node.outputs["Color"], principled.inputs["Base Color"])
    return mat

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


def _set_edit_bone_from_bind_matrix(eb, mat, length=0.1):
    head = mat.to_translation()
    rot = mat.to_3x3()

    axis_y = rot @ Vector((-1.0, 0.0, 0.0))
    if axis_y.length <= 1e-8:
        axis_y = Vector((0.0, 1.0, 0.0))
    else:
        axis_y.normalize()

    eb.head = head
    eb.tail = head + axis_y * length

    roll_ref = rot @ Vector((0.0, 0.0, 1.0))
    if roll_ref.length <= 1e-8:
        roll_ref = rot @ Vector((0.0, 1.0, 0.0))
    if roll_ref.length <= 1e-8:
        roll_ref = Vector((0.0, 0.0, 1.0))

    roll_ref = roll_ref - axis_y * roll_ref.dot(axis_y)
    if roll_ref.length <= 1e-8:
        alt = Vector((0.0, 1.0, 0.0))
        if abs(axis_y.dot(alt)) > 0.95:
            alt = Vector((1.0, 0.0, 0.0))
        roll_ref = alt - axis_y * alt.dot(axis_y)

    if roll_ref.length > 1e-8:
        roll_ref.normalize()
        eb.roll = 0.0
        eb.align_roll(roll_ref)
    else:
        eb.roll = 0.0

def create_mesh(path, mesh_data):
    
    # create all bones first
    armature = bpy.data.armatures.new(f"{mesh_data.name}_Armature")
    armature_name = f"{mesh_data.name}_Armature"
    armature_object = bpy.data.objects.new(armature_name, armature)
    bpy.context.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    
    bpy.ops.object.mode_set(mode='EDIT')
    idx_to_bone = {}      # { bone_id (int) -> edit_bone }
    arm = armature_object
    edit_bones = arm.data.edit_bones
    
    # ROOT for all (for now)
    root_name = "ROOT"
    if root_name in edit_bones:
        root_eb = edit_bones[root_name]
    else:
        root_eb = edit_bones.new(root_name)
        root_eb.head = Vector((0.0, 0.0, 0.0))
        root_eb.tail = Vector((0.0, 0.1, 0.0))
        root_eb.roll = 0.0
    

    if mesh_data.bones and skel_data:
        bone_map_skel = skel_data['bone_map']      # { id -> name }
        parent_map    = skel_data['parent_map']    # { id -> parent_id }
        
        mesh_indices = set(range(len(mesh_data.bones)))
        skel_indices = set(bone_map_skel.keys())
        all_indices  = sorted(mesh_indices | skel_indices)
        
        for bone_idx in all_indices:
            bone_name = get_bone_name(skel_data, bone_idx)
        
            eb = edit_bones.get(bone_name)
            if eb is None:
                eb = edit_bones.new(bone_name)

                if 0 <= bone_idx < len(mesh_data.bones):
                    mat = _engine_to_blender_matrix4(Matrix(mesh_data.bones[bone_idx]).transposed())
                    _set_edit_bone_from_bind_matrix(eb, mat)
                else:
                    parent_id = parent_map.get(bone_idx, -1)
                    if parent_id == -1 or parent_id is None:
                        parent_eb = root_eb
                    else:
                        parent_name = get_bone_name(skel_data, parent_id)
                        parent_eb = edit_bones.get(parent_name, root_eb)
                    if parent_eb is not None:
                        eb.head = parent_eb.tail.copy()
                    else:
                        eb.head = Vector((0.0, 0.0, 0.0))
        
                    eb.tail = eb.head + Vector((0.0, 0.1, 0.0))
                    eb.roll = 0.0
        
            idx_to_bone[bone_idx] = eb
        
        for bone_idx, eb in idx_to_bone.items():
            parent_id = parent_map.get(bone_idx, -1)
            if parent_id == -1 or parent_id is None:
                eb.parent = root_eb
            else:
                parent_eb = idx_to_bone.get(parent_id, root_eb)
                eb.parent = parent_eb    
            
        
        # remapping chain
        apply_torso_head_chains(skel_data, idx_to_bone, root_eb)
        apply_leg_chains(skel_data, idx_to_bone)
        apply_arm_chains(skel_data, idx_to_bone)
        apply_finger_chains(skel_data, idx_to_bone)


    # collect geom
    all_vertices = []
    all_normals = []
    all_tangents = []
    all_faces = []
    all_uvs = []
    all_section_bone_data = []
    section_face_ranges = []
    section_materials = []
    vertex_offset = 0
    
    bpy.ops.object.mode_set(mode='OBJECT')
    for section in mesh_data.sections:
        verts = [_engine_to_blender_vec3(v) for v in section['vertices']]
        sec_normals = section.get("normals")
        sec_tangents = section.get("tangents")
        prim = section['primitive_type']

        faces = create_faces_from_indices(indices=section['indices'], primitive_type=prim)
        section_face_ranges.append((len(all_faces), len(faces), section))        
        faces = [tuple(v + vertex_offset for v in face) for face in faces]

        all_vertices.extend(verts)
        if sec_normals and len(sec_normals) == len(verts):
            for n in sec_normals:
                nv = _engine_to_blender_vec3(n)
                if nv.length > 1e-12:
                    nv.normalize()
                all_normals.append((float(nv.x), float(nv.y), float(nv.z)))
        else:
            all_normals.extend([None] * len(verts))

        if sec_tangents and len(sec_tangents) == len(verts):
            for t in sec_tangents:
                tv = _engine_to_blender_vec3(t[:3] if len(t) >= 3 else (0.0, 0.0, 1.0))
                if tv.length > 1e-12:
                    tv.normalize()
                all_tangents.append((float(tv.x), float(tv.y), float(tv.z)))
        else:
            all_tangents.extend([None] * len(verts))

        all_faces.extend(faces)
        print(section['section_name'])
        mats = section.get('materials', [])
        selected_mat = None
        for mat_name, tex_name in mats:
            if isinstance(mat_name, (bytes, bytearray)):
                mat_name_dec = mat_name.decode("utf-8").rstrip("\x00")
            else:
                mat_name_dec = str(mat_name)
            if mat_name_dec == section['section_name']:
                selected_mat = tex_name
                print(selected_mat)
                break
        section_materials.append(selected_mat)
        section["resolved_material"] = selected_mat

        if section.get("uvs"):
            all_uvs.extend(section["uvs"])
        else:
            all_uvs.extend([None] * len(verts))

        if section.get("bones"):
            all_section_bone_data.append((vertex_offset, section["bones"]))

        vertex_offset += len(verts)

    mesh = bpy.data.meshes.new(mesh_data.name)
    obj = bpy.data.objects.new(mesh_data.name, mesh)
    bpy.context.collection.objects.link(obj)

    mesh.from_pydata(all_vertices, [], all_faces)
    mesh.update()

    face_section_attr = mesh.attributes.get("pcmesh_section_index")
    if face_section_attr is None:
        face_section_attr = mesh.attributes.new(name="pcmesh_section_index", type='INT', domain='FACE')
    for start, count, section in section_face_ranges:
        section_idx = mesh_data.sections.index(section)
        for poly_idx in range(start, start + count):
            face_section_attr.data[poly_idx].value = section_idx
    
    if any(all_uvs):
        uv_layer = mesh.uv_layers.new()
        for loop in mesh.loops:
            idx = loop.vertex_index
            uv = all_uvs[idx]
            if uv:
                uv_layer.data[loop.index].uv = (uv[0], 1.0 - uv[1])

    if all_normals and len(all_normals) == len(all_vertices) and all(n is not None for n in all_normals):
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.normals_split_custom_set_from_vertices(all_normals)

    if all_tangents and len(all_tangents) == len(all_vertices) and all(t is not None for t in all_tangents):
        tangent_attr = mesh.attributes.get("pcmesh_tangent")
        if tangent_attr is None:
            tangent_attr = mesh.attributes.new(name="pcmesh_tangent", type='FLOAT_VECTOR', domain='POINT')
        for i, t in enumerate(all_tangents):
            tangent_attr.data[i].vector = t

    # map sections
    for vertex_offset, section_bones in all_section_bone_data:
        for local_idx, bone_data in enumerate(section_bones):
            for bone_idx, weight in zip(bone_data["indices"], bone_data["weights"]):
                bone_name = get_bone_name(skel_data, bone_idx)

                if bone_name not in obj.vertex_groups:
                    obj.vertex_groups.new(name=bone_name)

                obj.vertex_groups[bone_name].add(
                    [vertex_offset + local_idx], weight, 'ADD'
                )
    mod = obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = armature_object
    
    section0 = mesh_data.sections[0]
    #if section0.get('materials'):       # @todo: multiple mats
        #assign_texture_to_object(os.path.join(os.path.dirname(path), section0['materials'][0]), mesh_data.name)#section['name'])                
        
    mesh.materials.clear()
    for sec_idx, section in enumerate(mesh_data.sections):
        tex_name = section.get("resolved_material")
        mat_name = f"{mesh_data.name}_sec_{sec_idx}"
        mat = _create_material_for_section(path, tex_name if tex_name else mat_name)
        mesh.materials.append(mat)

    for start, count, section in section_face_ranges:
        sec_idx = mesh_data.sections.index(section)
        for poly_idx in range(start, start + count):
            mesh.polygons[poly_idx].material_index = sec_idx

    bone_name_to_id = {}
    if mesh_data.bones:
        for bone_idx in range(len(mesh_data.bones)):
            bone_name_to_id[get_bone_name(skel_data, bone_idx)] = bone_idx

    obj["pcmesh_template_path"] = path
    obj["pcmesh_template_mesh_name"] = mesh_data.name
    obj["pcmesh_section_count"] = len(mesh_data.sections)
    obj["pcmesh_bone_name_to_id"] = json.dumps(bone_name_to_id)

    armature_object["pcmesh_template_path"] = path
    armature_object["pcmesh_template_mesh_name"] = mesh_data.name
    armature_object["pcmesh_section_count"] = len(mesh_data.sections)
    armature_object["pcmesh_bone_name_to_id"] = json.dumps(bone_name_to_id)
    if skel_data:
        armature_object["pcmesh_skel_name"] = skel_data.get("header", {}).get("name", "")
    if loaded_skel_path:
        armature_object["pcmesh_skel_path"] = loaded_skel_path
        
    obj.parent = armature_object
    
    print(f"Finished importing {mesh_data.name}")
    return obj
    
class PCMESHImporter(bpy.types.Operator):
    bl_idname = "import_scene.pcmesh"
    bl_label = "Import PCMESH"
    bl_options = {'PRESET', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        global requested_pcmesh
        requested_pcmesh = self.filepath

        has_bones = False
        for mesh_data in read_meshfile(requested_pcmesh):
            if mesh_data.bones:
                has_bones = True
                break

        if not has_bones:
            import_pcmesh(requested_pcmesh, skel_path=None)
            return {'FINISHED'}

        return bpy.ops.wm.open_pcskel('INVOKE_DEFAULT')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def _find_target_armature(context):
    obj = context.object
    if obj is None:
        return None

    if obj.type == 'ARMATURE':
        return obj

    if obj.type == 'MESH':
        if obj.parent and obj.parent.type == 'ARMATURE':
            return obj.parent
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object and mod.object.type == 'ARMATURE':
                return mod.object

    for sel in context.selected_objects:
        if sel.type == 'ARMATURE':
            return sel

    return None


def _find_matching_armatures(primary_armature):
    matches = [primary_armature]

    template_path = str(primary_armature.get("pcmesh_template_path", ""))
    skel_name = str(primary_armature.get("pcmesh_skel_name", ""))

    for obj in bpy.data.objects:
        if obj == primary_armature or obj.type != 'ARMATURE':
            continue

        if template_path:
            if str(obj.get("pcmesh_template_path", "")) != template_path:
                continue

        if skel_name:
            other_skel = str(obj.get("pcmesh_skel_name", ""))
            if other_skel and other_skel != skel_name:
                continue

        matches.append(obj)

    return matches


def _load_skel_for_armature(armature_obj):
    skel_path = armature_obj.get("pcmesh_skel_path", "")
    if not skel_path:
        return None, ""

    if not os.path.isfile(skel_path):
        return None, f"PCSKEL path not found: {skel_path}"

    try:
        return open_pcskel(skel_path), ""
    except Exception as e:
        return None, f"Failed to read PCSKEL '{skel_path}': {e}"


def _build_id_to_bone_name(armature_obj, skel_info=None):
    id_to_name = {}

    raw_map = armature_obj.get("pcmesh_bone_name_to_id", "{}")
    try:
        parsed = json.loads(raw_map) if isinstance(raw_map, str) else {}
    except Exception:
        parsed = {}

    if isinstance(parsed, dict):
        for bone_name, bone_id in parsed.items():
            try:
                id_to_name[int(bone_id)] = str(bone_name)
            except Exception:
                continue

    if skel_info:
        for k, v in skel_info.get("bone_map", {}).items():
            try:
                kid = int(k)
            except Exception:
                continue
            if kid not in id_to_name and v:
                id_to_name[kid] = str(v)

        for k, v in skel_info.get("component_bone_names", {}).items():
            try:
                kid = int(k)
            except Exception:
                continue
            if kid not in id_to_name and v:
                id_to_name[kid] = str(v)

    try:
        if armature_obj and armature_obj.data:
            bones = armature_obj.data.bones

            mapped_root = id_to_name.get(-1)
            if mapped_root and mapped_root not in bones:
                mapped_root = None

            if not mapped_root:
                for root_name in ("ROOT", "Root", "root"):
                    if root_name in bones:
                        mapped_root = root_name
                        break

            if not mapped_root:
                for b in bones:
                    if b.parent is None and "root" in b.name.lower():
                        mapped_root = b.name
                        break

            if not mapped_root:
                for b in bones:
                    if b.parent is None:
                        mapped_root = b.name
                        break

            if mapped_root:
                id_to_name[-1] = mapped_root
    except Exception:
        pass

    return id_to_name


def _quat_normalize_wxyz(q):
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    n2 = w * w + x * x + y * y + z * z
    if n2 <= 1e-20:
        return (1.0, 0.0, 0.0, 0.0)
    inv = 1.0 / (n2 ** 0.5)
    return (w * inv, x * inv, y * inv, z * inv)


def _quat_inverse_wxyz(q):
    w, x, y, z = _quat_normalize_wxyz(q)
    return (w, -x, -y, -z)


def _quat_mul_wxyz(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return _quat_normalize_wxyz((
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ))


def _quat_dot_wxyz(a, b):
    return float(a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3])


def _apply_bone_tracks_action(armature_obj, action, bone_tracks, id_to_name, normalize_rot_from_first_frame=False):
    armature_obj.animation_data_create()
    armature_obj.animation_data.action = action

    pose = armature_obj.pose
    if pose is None:
        return 0

    global_rot_inv = None
    if normalize_rot_from_first_frame:
        ref_ids = [0, 1, 2, 3]
        seen = set(ref_ids)
        ref_ids.extend([int(k) for k in sorted(bone_tracks.keys(), key=lambda x: int(x)) if int(k) not in seen])

        for ref_id in ref_ids:
            ref_tracks = bone_tracks.get(ref_id)
            if not isinstance(ref_tracks, dict):
                continue
            ref_rot = ref_tracks.get("rotation", {})
            if not isinstance(ref_rot, dict) or not ref_rot:
                continue
            first_key = sorted(ref_rot.keys(), key=lambda x: int(x))[0]
            ref_q = ref_rot.get(first_key)
            if ref_q and len(ref_q) == 4:
                global_rot_inv = _quat_inverse_wxyz(ref_q)
                break

    keyed_bones = 0

    for bone_id, tracks in bone_tracks.items():
        try:
            bid = int(bone_id)
        except Exception:
            continue

        bone_name = id_to_name.get(bid)
        if not bone_name:
            continue

        pbone = pose.bones.get(bone_name)
        if pbone is None:
            continue

        if pbone.rotation_mode != 'QUATERNION':
            pbone.rotation_mode = 'QUATERNION'

        had_keys = False

        rot_tracks = tracks.get("rotation", {}) if isinstance(tracks, dict) else {}
        rot_items = sorted(rot_tracks.items(), key=lambda kv: int(kv[0]))
        prev_q = None
        for frame_no, q in rot_items:
            if not q or len(q) != 4:
                continue
            fno = float(int(frame_no))
            qv = _quat_normalize_wxyz((float(q[0]), float(q[1]), float(q[2]), float(q[3])))
            if global_rot_inv is not None:
                qv = _quat_mul_wxyz(global_rot_inv, qv)
            if prev_q is not None and _quat_dot_wxyz(prev_q, qv) < 0.0:
                qv = (-qv[0], -qv[1], -qv[2], -qv[3])
            prev_q = qv
            pbone.rotation_quaternion = qv
            pbone.keyframe_insert(data_path="rotation_quaternion", frame=fno, group=pbone.name)
            had_keys = True

        loc_tracks = tracks.get("location", {}) if isinstance(tracks, dict) else {}
        for frame_no in sorted(loc_tracks.keys(), key=lambda x: int(x)):
            loc = loc_tracks[frame_no]
            if not loc or len(loc) != 3:
                continue
            fno = float(int(frame_no))
            locv = _engine_to_blender_vec3((float(loc[0]), float(loc[1]), float(loc[2])))
            pbone.location = (float(locv.x), float(locv.y), float(locv.z))
            pbone.keyframe_insert(data_path="location", frame=fno, group=pbone.name)
            had_keys = True

        if had_keys:
            keyed_bones += 1

    for fcurve in action.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = 'LINEAR'

    return keyed_bones


def _bake_rest_pose_action(armature_obj, action, frame_end):
    armature_obj.animation_data_create()
    armature_obj.animation_data.action = action
    pose = armature_obj.pose
    if pose is None:
        return

    start = 1
    end = max(1, int(frame_end))

    for pbone in pose.bones:
        if pbone.rotation_mode != 'QUATERNION':
            pbone.rotation_mode = 'QUATERNION'

        pbone.keyframe_insert(data_path="location", frame=start, group=pbone.name)
        pbone.keyframe_insert(data_path="rotation_quaternion", frame=start, group=pbone.name)
        pbone.keyframe_insert(data_path="scale", frame=start, group=pbone.name)

        if end != start:
            pbone.keyframe_insert(data_path="location", frame=end, group=pbone.name)
            pbone.keyframe_insert(data_path="rotation_quaternion", frame=end, group=pbone.name)
            pbone.keyframe_insert(data_path="scale", frame=end, group=pbone.name)


class PCANIMImporter(bpy.types.Operator):
    bl_idname = "import_scene.pcanim"
    bl_label = "Import PCANIM"
    bl_options = {'PRESET', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.PCANIM;*.pcanim", options={'HIDDEN'})
    apply_root_motion: bpy.props.BoolProperty(
        name="Apply Root Motion",
        description="Apply decoded pelvis/root translation tracks (pelvis rotation is always applied for torso pose fidelity)",
        default=False,
    )
    normalize_rot_from_first_frame: bpy.props.BoolProperty(
        name="Normalize Rotation Offsets",
        description="Use first keyed frame as rotational reference to remove constant orientation offsets",
        default=False,
    )
    apply_to_matching_lods: bpy.props.BoolProperty(
        name="Apply To Matching LODs",
        description="Assign imported action to all matching armatures from same PCMESH/skeleton",
        default=True,
    )
    solve_ik_chains: bpy.props.BoolProperty(
        name="Experimental IK Solve",
        description="Use runtime-style IK solve reconstruction for upper/lower limb chains (work in progress)",
        default=False,
    )
    use_full_arm_tracks: bpy.props.BoolProperty(
        name="Direct Arm Tracks",
        description="Apply runtime-style direct arm quaternions for all arm tracks (disable for legacy clavicle/hand-only fallback)",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "apply_root_motion")
        layout.prop(self, "normalize_rot_from_first_frame")
        layout.prop(self, "apply_to_matching_lods")
        layout.prop(self, "solve_ik_chains")
        layout.prop(self, "use_full_arm_tracks")

    def execute(self, context):
        armature_obj = _find_target_armature(context)
        if armature_obj is None:
            self.report({'ERROR'}, "Select an imported PCMESH armature or skinned mesh first")
            return {'CANCELLED'}

        target_armatures = [armature_obj]
        if self.apply_to_matching_lods:
            target_armatures = _find_matching_armatures(armature_obj)

        skel_info, skel_err = _load_skel_for_armature(armature_obj)
        if skel_err:
            self.report({'WARNING'}, skel_err)

        try:
            parsed = open_pcanim(
                self.filepath,
                skel_data=skel_info,
                apply_root_motion=self.apply_root_motion,
                solve_ik=self.solve_ik_chains,
                use_full_arm_tracks=self.use_full_arm_tracks,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to parse PCANIM: {e}")
            return {'CANCELLED'}

        anims = parsed.get("animations", [])
        if not anims:
            self.report({'ERROR'}, "No animations found in PCANIM")
            return {'CANCELLED'}

        skel_names = [s.get("name", "") for s in parsed.get("skeletons", []) if s.get("name")]
        arm_skel_name = armature_obj.get("pcmesh_skel_name", "")
        if not arm_skel_name:
            self.report({'WARNING'}, "Armature has no imported PCSKEL metadata; proceeding anyway")
        if arm_skel_name and skel_names and arm_skel_name not in skel_names:
            self.report({'WARNING'}, f"Skeleton mismatch: armature '{arm_skel_name}' not in PCANIM skeleton table")

        created = 0
        decoded_actions = 0
        max_end = 1
        first_action = None
        source_name = os.path.basename(self.filepath)
        id_to_name = _build_id_to_bone_name(armature_obj, skel_info)

        for idx, anim in enumerate(anims):
            anim_name = anim.get("name") or f"anim_{idx:03d}"
            action = bpy.data.actions.new(name=f"{source_name}:{anim_name}")
            action.use_fake_user = True

            frame_count = max(1, int(anim.get("frame_count", 1)))
            max_end = max(max_end, frame_count)

            action["pcanim_source"] = self.filepath
            action["pcanim_duration"] = float(anim.get("duration", 0.0))
            action["pcanim_frame_count"] = frame_count
            action["pcanim_flags"] = int(anim.get("flags", 0))
            action["pcanim_loop"] = bool(int(anim.get("flags", 0)) & FLAG_LOOPING)
            action["pcanim_scene_anim"] = bool(int(anim.get("flags", 0)) & FLAG_SCENE_ANIM)
            action["pcanim_skel_index"] = int(anim.get("skel_index", -1))
            action["pcanim_version"] = int(anim.get("version", 0))
            action["pcanim_decoded_component_count"] = int(len(anim.get("decoded_components", [])))
            action["pcanim_import_options"] = (
                f"root_motion={int(bool(self.apply_root_motion))};"
                f"normalize_rot={int(bool(self.normalize_rot_from_first_frame))};"
                f"apply_to_lods={int(bool(self.apply_to_matching_lods))};"
                f"solve_ik={int(bool(self.solve_ik_chains))};"
                f"full_arm_tracks={int(bool(self.use_full_arm_tracks))}"
            )

            decoded_components = anim.get("decoded_components", [])
            comp_ids = [int(c.get("comp_ix", -1)) for c in decoded_components]
            action["pcanim_component_ids"] = ",".join(str(i) for i in comp_ids)
            applied_ids = sorted({
                int(c.get("comp_ix", -1))
                for c in decoded_components
                if str(c.get("apply_mode", "")) == "applied"
            })
            noop_ids = sorted({
                int(c.get("comp_ix", -1))
                for c in decoded_components
                if str(c.get("apply_mode", "")) != "applied"
            })
            action["pcanim_applied_component_ids"] = ",".join(str(i) for i in applied_ids)
            action["pcanim_noop_component_ids"] = ",".join(str(i) for i in noop_ids)
            action["pcanim_has_legs_ik"] = bool(6 in comp_ids)
            action["pcanim_has_arms"] = bool(7 in comp_ids)
            action["pcanim_has_arms_ik"] = bool(8 in comp_ids)

            decode_warnings = anim.get("decode_warnings", [])
            if decode_warnings:
                action["pcanim_decode_warning_count"] = int(len(decode_warnings))
                action["pcanim_decode_warning_head"] = " | ".join(str(w) for w in decode_warnings[:3])

            keyed_bones = 0
            bone_tracks = anim.get("bone_tracks", {})
            root_tracks = bone_tracks.get(-1, {}) if isinstance(bone_tracks, dict) else {}
            root_rot_count = len(root_tracks.get("rotation", {})) if isinstance(root_tracks, dict) else 0
            root_loc_count = len(root_tracks.get("location", {})) if isinstance(root_tracks, dict) else 0
            action["pcanim_root_rot_keys"] = int(root_rot_count)
            action["pcanim_root_loc_keys"] = int(root_loc_count)
            if isinstance(bone_tracks, dict) and bone_tracks:
                keyed_bones = _apply_bone_tracks_action(
                    armature_obj=armature_obj,
                    action=action,
                    bone_tracks=bone_tracks,
                    id_to_name=id_to_name,
                    normalize_rot_from_first_frame=self.normalize_rot_from_first_frame,
                )

            if keyed_bones == 0:
                _bake_rest_pose_action(armature_obj, action, frame_count)
            else:
                decoded_actions += 1

            action["pcanim_keyed_bones"] = int(keyed_bones)

            if first_action is None:
                first_action = action
            created += 1

        if first_action is not None:
            context.scene.pcmesh_pcanim_action_name = first_action.name
            for arm_obj in target_armatures:
                arm_obj.animation_data_create()
                arm_obj.animation_data.action = first_action

        context.scene.frame_start = 1
        if first_action is not None:
            try:
                active_end = int(round(float(first_action.frame_range[1])))
            except Exception:
                active_end = int(first_action.get("pcanim_frame_count", max_end))
            context.scene.frame_end = max(1, active_end)
        else:
            context.scene.frame_end = max(1, int(max_end))

        total_decode_warnings = len(parsed.get("decode_warnings", []))
        opts = (
            f"root_motion={int(bool(self.apply_root_motion))}, "
            f"normalize_rot={int(bool(self.normalize_rot_from_first_frame))}, "
            f"solve_ik={int(bool(self.solve_ik_chains))}, "
            f"full_arm_tracks={int(bool(self.use_full_arm_tracks))}"
        )
        if total_decode_warnings > 0:
            self.report({'WARNING'}, f"Imported {created} animations ({decoded_actions} with decoded tracks), {total_decode_warnings} decode warnings, applied to {len(target_armatures)} armatures [{opts}]")
        else:
            self.report({'INFO'}, f"Imported {created} animations ({decoded_actions} with decoded tracks), applied to {len(target_armatures)} armatures [{opts}]")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PCMESHApplyPCANIMAction(bpy.types.Operator):
    bl_idname = "pcmesh.apply_pcanim_action"
    bl_label = "Apply PCANIM Action"
    bl_options = {'UNDO'}

    apply_to_matching_lods: bpy.props.BoolProperty(
        name="Apply To Matching LODs",
        description="Assign action to all matching armatures from same PCMESH/skeleton",
        default=True,
    )

    def execute(self, context):
        armature_obj = _find_target_armature(context)
        if armature_obj is None:
            self.report({'ERROR'}, "Select an imported PCMESH armature or skinned mesh first")
            return {'CANCELLED'}

        action_name = str(getattr(context.scene, "pcmesh_pcanim_action_name", "")).strip()
        if not action_name:
            self.report({'ERROR'}, "No action selected")
            return {'CANCELLED'}

        action = bpy.data.actions.get(action_name)
        if action is None:
            self.report({'ERROR'}, f"Action '{action_name}' not found")
            return {'CANCELLED'}

        targets = [armature_obj]
        if self.apply_to_matching_lods:
            targets = _find_matching_armatures(armature_obj)

        for arm_obj in targets:
            arm_obj.animation_data_create()
            arm_obj.animation_data.action = action

        frame_count = int(action.get("pcanim_frame_count", 0))
        if frame_count > 0:
            context.scene.frame_start = 1
            context.scene.frame_end = max(context.scene.frame_end, frame_count)

        self.report({'INFO'}, f"Applied action '{action_name}' to {len(targets)} armatures")
        return {'FINISHED'}


class PCMESHPTPCANIMTools(bpy.types.Panel):
    bl_label = "PCANIM"
    bl_idname = "VIEW3D_PT_pcmesh_pcanim"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PCMESH'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.label(text="Import Options")
        col.prop(scene, "pcmesh_pcanim_apply_root_motion")
        col.prop(scene, "pcmesh_pcanim_normalize_rot")
        col.prop(scene, "pcmesh_pcanim_apply_to_lods")
        col.prop(scene, "pcmesh_pcanim_solve_ik")
        col.prop(scene, "pcmesh_pcanim_full_arm_tracks")
        op_import = col.operator(PCANIMImporter.bl_idname, text="Import PCANIM")
        op_import.apply_root_motion = bool(scene.pcmesh_pcanim_apply_root_motion)
        op_import.normalize_rot_from_first_frame = bool(scene.pcmesh_pcanim_normalize_rot)
        op_import.apply_to_matching_lods = bool(scene.pcmesh_pcanim_apply_to_lods)
        op_import.solve_ik_chains = bool(scene.pcmesh_pcanim_solve_ik)
        op_import.use_full_arm_tracks = bool(scene.pcmesh_pcanim_full_arm_tracks)

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Action")
        col.prop_search(scene, "pcmesh_pcanim_action_name", bpy.data, "actions", text="")
        op = col.operator(PCMESHApplyPCANIMAction.bl_idname, text="Apply Action")
        op.apply_to_matching_lods = bool(scene.pcmesh_pcanim_apply_to_lods)

class PCMESHExporter(bpy.types.Operator):
    bl_idname = "export_scene.pcmesh"
    bl_label = "Export PCMESH"
    bl_options = {'PRESET', 'UNDO'}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def _collect_vertex_weights(self, obj, vertex, bone_name_to_id):
        influences = []
        for group in vertex.groups:
            group_index = group.group
            if group_index >= len(obj.vertex_groups):
                continue
            name = obj.vertex_groups[group_index].name
            if name not in bone_name_to_id:
                continue
            influences.append((bone_name_to_id[name], float(group.weight)))

        influences.sort(key=lambda x: x[1], reverse=True)
        influences = influences[:4]
        while len(influences) < 4:
            influences.append((0, 0.0))

        total = sum(w for _, w in influences)
        if total > 1e-8:
            influences = [(idx, w / total) for idx, w in influences]
        else:
            influences = [(0, 1.0), (0, 0.0), (0, 0.0), (0, 0.0)]

        return tuple(idx for idx, _ in influences), tuple(w for _, w in influences)

    def _build_export_sections(self, obj):
        mesh = obj.data
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.calc_loop_triangles()
        mesh.calc_normals_split()

        section_count = int(obj.get("pcmesh_section_count", 1))
        section_count = max(1, section_count)

        section_attr = mesh.attributes.get("pcmesh_section_index")
        uv_layer = mesh.uv_layers.active

        try:
            bone_name_to_id = json.loads(obj.get("pcmesh_bone_name_to_id", "{}"))
        except Exception:
            bone_name_to_id = {}

        tri_per_section = [[] for _ in range(section_count)]
        for tri in mesh.loop_triangles:
            if section_attr is not None:
                section_idx = int(section_attr.data[tri.polygon_index].value)
            else:
                section_idx = int(mesh.polygons[tri.polygon_index].material_index)
            section_idx = max(0, min(section_count - 1, section_idx))
            tri_per_section[section_idx].append(tri)

        result = []
        for section_idx in range(section_count):
            dedup = {}
            vertices = []
            normals = []
            uvs = []
            bone_indices = []
            bone_weights = []
            triangles = []

            for tri in tri_per_section[section_idx]:
                tri_indices = []
                for loop_idx in tri.loops:
                    loop = mesh.loops[loop_idx]
                    v = mesh.vertices[loop.vertex_index]
                    pos_eng = _blender_to_engine_vec3((float(v.co.x), float(v.co.y), float(v.co.z)))
                    nrm_eng = _blender_to_engine_vec3((float(loop.normal.x), float(loop.normal.y), float(loop.normal.z)))
                    if nrm_eng.length > 1e-12:
                        nrm_eng.normalize()
                    pos = (float(pos_eng.x), float(pos_eng.y), float(pos_eng.z))
                    nrm = (float(nrm_eng.x), float(nrm_eng.y), float(nrm_eng.z))
                    if uv_layer is not None:
                        uv = (float(uv_layer.data[loop_idx].uv.x), float(uv_layer.data[loop_idx].uv.y))
                    else:
                        uv = (0.0, 0.0)

                    if bone_name_to_id:
                        bidx, bw = self._collect_vertex_weights(obj, v, bone_name_to_id)
                    else:
                        bidx, bw = (0, 0, 0, 0), (1.0, 0.0, 0.0, 0.0)

                    key = (pos, nrm, uv, bidx, bw)
                    if key not in dedup:
                        dedup[key] = len(vertices)
                        vertices.append(pos)
                        normals.append(nrm)
                        uvs.append(uv)
                        bone_indices.append(bidx)
                        bone_weights.append(bw)
                    tri_indices.append(dedup[key])
                triangles.append(tuple(tri_indices))

            result.append(SectionExportData(
                vertices=vertices,
                triangles=triangles,
                uvs=uvs,
                normals=normals,
                bone_indices=bone_indices,
                bone_weights=bone_weights,
            ))

        return result

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected!")
            return {'CANCELLED'}

        template_mesh_name = obj.get("pcmesh_template_mesh_name", obj.name)
        section_payloads = self._build_export_sections(obj)
        export_data = MeshExportData(section_payloads)

        write_meshfile(self.filepath, export_data, mesh_name=template_mesh_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func_import(self, context):
    self.layout.operator(PCMESHImporter.bl_idname, text="PCMESH (.pcmesh)")
    self.layout.operator(PCANIMImporter.bl_idname, text="PCANIM (.pcanim)")

def menu_func_export(self, context):
    self.layout.operator(PCMESHExporter.bl_idname, text="PCMESH (.pcmesh)")

def register():
    bpy.utils.register_class(OT_OpenFileBrowser)
    bpy.utils.register_class(PCMESHImporter)
    bpy.utils.register_class(PCANIMImporter)
    bpy.utils.register_class(PCMESHApplyPCANIMAction)
    bpy.utils.register_class(PCMESHPTPCANIMTools)
    bpy.utils.register_class(PCMESHExporter)

    bpy.types.Scene.pcmesh_pcanim_apply_root_motion = bpy.props.BoolProperty(
        name="Apply Root Motion",
        default=False,
    )
    bpy.types.Scene.pcmesh_pcanim_normalize_rot = bpy.props.BoolProperty(
        name="Normalize Rotation Offsets",
        default=False,
    )
    bpy.types.Scene.pcmesh_pcanim_apply_to_lods = bpy.props.BoolProperty(
        name="Apply To Matching LODs",
        default=True,
    )
    bpy.types.Scene.pcmesh_pcanim_solve_ik = bpy.props.BoolProperty(
        name="Experimental IK Solve",
        default=False,
    )
    bpy.types.Scene.pcmesh_pcanim_full_arm_tracks = bpy.props.BoolProperty(
        name="Direct Arm Tracks",
        default=True,
    )
    bpy.types.Scene.pcmesh_pcanim_action_name = bpy.props.StringProperty(
        name="PCANIM Action",
        default="",
    )

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    init()

def unregister():
    if hasattr(bpy.types.Scene, "pcmesh_pcanim_action_name"):
        del bpy.types.Scene.pcmesh_pcanim_action_name
    if hasattr(bpy.types.Scene, "pcmesh_pcanim_full_arm_tracks"):
        del bpy.types.Scene.pcmesh_pcanim_full_arm_tracks
    if hasattr(bpy.types.Scene, "pcmesh_pcanim_solve_ik"):
        del bpy.types.Scene.pcmesh_pcanim_solve_ik
    if hasattr(bpy.types.Scene, "pcmesh_pcanim_apply_to_lods"):
        del bpy.types.Scene.pcmesh_pcanim_apply_to_lods
    if hasattr(bpy.types.Scene, "pcmesh_pcanim_normalize_rot"):
        del bpy.types.Scene.pcmesh_pcanim_normalize_rot
    if hasattr(bpy.types.Scene, "pcmesh_pcanim_apply_root_motion"):
        del bpy.types.Scene.pcmesh_pcanim_apply_root_motion

    bpy.utils.unregister_class(PCMESHPTPCANIMTools)
    bpy.utils.unregister_class(PCMESHApplyPCANIMAction)
    bpy.utils.unregister_class(PCANIMImporter)
    bpy.utils.unregister_class(PCMESHImporter)
    bpy.utils.unregister_class(PCMESHExporter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(OT_OpenFileBrowser)
if __name__ == "__main__":
    register()
