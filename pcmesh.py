import io
import os
import struct
import ctypes
import mathutils

from ctypes import *
from enum import IntEnum

class generic_mash_data_ptrs():

    def __init__(self, arg0, arg1):
        self.field_0 = arg0
        self.field_4 = arg1

    def rebase(self, i: int):
        v8 = i - self.field_0.tell() % i
        if v8 < i:
            self.field_0.seek(v8, 1)

    def get(self, t, num = 1):
        array_t = (t * num)
        newObj = array_t()

        newObj = array_t.from_buffer_copy(self.field_0.read(sizeof(array_t)))
        return newObj


    def __repr__(self):
        return f'generic_mash_data_ptrs(field_0 = {hex(self.field_0.tell())}, field_4 = {hex(self.field_4.tell())})'



class generic_mash_header(Structure):
    _fields_ = [("safety_key", c_int),
                ("field_4", c_int),
                ("field_8", c_int),
                ("class_id", c_short),
                ("field_E", c_short)
                ]

    def __repr__(self):
        return f'generic_mash_header(safety_key = {hex(self.safety_key)}, field_4={self.field_4}, field_8={hex(self.field_8)})'

    def generate_safety_key(self):
        return (self.field_8 + 0x7BADBA5D - (self.field_4 & 0xFFFFFFF) + self.class_id + self.field_E) & 0xFFFFFFF | 0x70000000

    def is_flagged(self, f: c_int):
        return (f & self.field_4) != 0

    def get_mash_data(self) -> c_char_p:
        return cast(this, c_char_p) + self.field_8

assert(sizeof(generic_mash_header) == 0x10)

class resource_versions(Structure):
    _fields_ = [("field_0", c_int),
                ("field_4", c_int),
                ("field_8", c_int),
                ("field_C", c_int),
                ("field_10", c_int)]

assert(sizeof(resource_versions) == 0x14)

class resource_pack_header(Structure):
    _fields_ = [("field_0", resource_versions),
                ("field_14", c_int),
                ("directory_offset", c_int),
                ("res_dir_mash_size", c_int),
                ("field_20", c_int),
                ("field_24", c_int),
                ("field_28", c_int)
                ]

assert(sizeof(resource_pack_header) == 0x2C)



class string_hash(Structure):
    _fields_ = [("source_hash_code", c_int)]

    def __init__(self):
        self.source_hash_code = 0

    def __eq__(self, a2):
        return self.source_hash_code != a2.source_hash_code;

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.source_hash_code < other.source_hash_code

    def __gt__(self, other):
        return self.source_hash_code > other.source_hash_code

    def to_string(self) -> str:
        return "{:#X}".format(self.source_hash_code)

    def __repr__(self):
        hash_code = "0x%08X" % self.source_hash_code
        return f'string_hash(name = {hash_code}'




def tohex(val, nbits):
  return hex((val + (1 << nbits)) % (1 << nbits))


string_hash_dictionary = {}



resource_key_type_ext = [".NONE", ".PCANIM", ".PCSKEL", ".ALS", ".ENT", ".ENTEXT", ".DDS", ".DDSMP", ".IFL", ".DESC", ".ENS", ".SPL", ".AB", ".QP", ".TRIG", ".PCSX", ".INST", ".FDF", ".PANEL", ".TXT", ".ICN",
                            ".PCMESH", ".PCMORPH", ".PCMAT", ".COLL", ".PCPACK", ".PCSANIM", ".MSN", ".MARKER", ".HH", ".WAV", ".WBK",
                            ".M2V", "M2V", ".PFX", ".CSV", ".CLE", ".LIT", ".GRD", ".GLS", ".LOD", ".SIN",
                            ".GV", ".SV", ".TOKENS", ".DSG", ".PATH", ".PTRL", ".LANG", ".SLF", ".VISEME", ".PCMESHDEF", ".PCMORPHDEF", ".PCMATDEF", ".MUT", ".ASG", ".BAI", ".CUT", ".INTERACT", ".CSV", ".CSV", "._ENTID_", "._ANIMID_", "._REGIONID_", "._AI_GENERIC_ID_", "._RADIOMSG_", "._GOAL_", "._IFC_ATTRIBUTE_", "._SIGNAL_", "._PACKGROUP_",
                        ]
assert(resource_key_type_ext[25] == ".PCPACK")
assert(resource_key_type_ext[48] == ".LANG")
assert(resource_key_type_ext[49] == ".SLF")

class resource_key(Structure):
    _fields_ = [("m_hash", string_hash),
                ("m_type", c_int)
                ]

    def is_set(self):
        undefined = string_hash()
        return self.m_hash != undefined

    def get_type(self):
        return self.m_type

    def get_platform_ext(self) -> str:
        return resource_key_type_ext[self.m_type]

    def get_platform_string(self) -> str:
        h = int(tohex(self.m_hash.source_hash_code, 32), 16)
        name = string_hash_dictionary.get(h, tohex(self.m_hash.source_hash_code, 32))
        ext = self.get_platform_ext()
        return (name + ext)

    def __repr__(self):
        return f'resource_key(m_hash = {self.m_hash}, m_type = {self.m_type}) => {self.get_platform_string()}'




class resource_location(Structure):
    _fields_ = [("field_0", resource_key),
                ("m_offset", c_int),
                ("m_size", c_int)
                ]

    def __repr__(self):
        return f'resource_location(field_0 = {self.field_0}, m_offset = {hex(self.m_offset)}, m_size = {hex(self.m_size)})'




class tlresource_location(Structure):
    _fields_ = [("name", string_hash),
                ("type", c_char),
                ("offset", c_int)
                ]

    def get_type(self) -> int:
        return int.from_bytes(self.type, "little")

    def __repr__(self):
        return f'tlresource_location(name = {self.name}, type = {self.get_type()}, offset={hex(self.offset)})'



class mashable_vector(Structure):
    _fields_ = [("m_data", POINTER(c_int)),
               ("m_size", c_short),
               ("m_shared", c_bool),
               ("field_7", c_bool)
                ]

    def __repr__(self):
        return f'mashable_vector(m_size={self.m_size}, m_shared={self.m_shared}, ' \
                f'm_shared={self.from_mash()})'

    def from_mash(self) -> bool:
        return self.field_7

    def size(self):
        return self.m_size

    def empty(self) -> bool:
        return self.size() == 0

    def custom_un_mash(self, a4: generic_mash_data_ptrs) -> generic_mash_data_ptrs:
        print("custom_un_mash")

        a4.rebase(4)
        a4.rebase(4)

        array_data = a4.get(c_int, int(self.m_size))
        self.m_data = cast(array_data, POINTER(c_int))

        a4.rebase(4)

        return a4

    def un_mash(self, a4: generic_mash_data_ptrs) -> generic_mash_data_ptrs:
        assert(self.from_mash())
        return self.custom_un_mash(a4)

class mashable_vector__resource_location(Structure):
    _fields_ = [("m_data", POINTER(resource_location)),
               ("m_size", c_short),
               ("m_shared", c_bool),
               ("field_7", c_bool)
                ]

    def __repr__(self):
        return f'mashable_vector(m_size={self.m_size}, m_shared={self.m_shared}, ' \
                f'm_shared={self.from_mash()})'

    def from_mash(self) -> bool:
        return self.field_7

    def size(self):
        return self.m_size

    def empty(self) -> bool:
        return self.size() == 0

    def custom_un_mash(self, a4: generic_mash_data_ptrs) -> generic_mash_data_ptrs:
        print("custom_un_mash<resource_location>")

        a4.rebase(8)
        a4.rebase(4)

        offset = int(a4.field_0.tell())
        print("0x%08X" % offset)

        array_data = a4.get(resource_location, int(self.m_size))
        self.m_data = cast(array_data, POINTER(resource_location))

        a4.rebase(4)

        return a4


class mashable_vector__tlresource_location(Structure):
    _fields_ = [("m_data", POINTER(tlresource_location)),
               ("m_size", c_short),
               ("m_shared", c_bool),
               ("field_7", c_bool)
                ]

    def __repr__(self):
        return f'mashable_vector(m_size={self.m_size}, m_shared={self.m_shared}, ' \
                f'm_shared={self.from_mash()})'

    def from_mash(self) -> bool:
        return self.field_7

    def size(self):
        return self.m_size

    def empty(self) -> bool:
        return self.size() == 0

    def custom_un_mash(self, a4: generic_mash_data_ptrs) -> generic_mash_data_ptrs:
        print("custom_un_mash<tlresource_location>")

        a4.rebase(8)
        a4.rebase(4)

        offset = int(a4.field_0.tell())
        print("0x%08X" % offset)

        array_data = a4.get(tlresource_location, int(self.m_size))
        self.m_data = cast(array_data, POINTER(tlresource_location))

        a4.rebase(4)
        return a4

    def un_mash(self, a4: generic_mash_data_ptrs) -> generic_mash_data_ptrs:
        assert(self.from_mash())
        return self.custom_un_mash(a4)



TLRESOURCE_TYPE_NONE = 0
TLRESOURCE_TYPE_TEXTURE = 1
TLRESOURCE_TYPE_MESH_FILE = 2
TLRESOURCE_TYPE_MESH = 3
TLRESOURCE_TYPE_MORPH_FILE = 4
TLRESOURCE_TYPE_MORPH = 5
TLRESOURCE_TYPE_MATERIAL_FILE = 6
TLRESOURCE_TYPE_MATERIAL = 7
TLRESOURCE_TYPE_ANIM_FILE = 8
TLRESOURCE_TYPE_ANIM = 9
TLRESOURCE_TYPE_SCENE_ANIM = 10
TLRESOURCE_TYPE_SKELETON = 11
TLRESOURCE_TYPE_Z = 12


RESOURCE_KEY_TYPE_NONE = 0
RESOURCE_KEY_TYPE_MESH_FILE_STRUCT = 51
RESOURCE_KEY_TYPE_MATERIAL_FILE_STRUCT = 53
RESOURCE_KEY_TYPE_Z = 70

class resource_directory(Structure):
    _fields_ = [("parents", mashable_vector),
                ("resource_locations", mashable_vector__resource_location),
                ("texture_locations", mashable_vector__tlresource_location),
                ("mesh_file_locations", mashable_vector__tlresource_location),
                ("mesh_locations", mashable_vector__tlresource_location),
                ("morph_file_locations", mashable_vector__tlresource_location),
                ("morph_locations", mashable_vector__tlresource_location),
                ("material_file_locations", mashable_vector__tlresource_location),
                ("material_locations", mashable_vector__tlresource_location),
                ("anim_file_locations", mashable_vector__tlresource_location),
                ("anim_locations", mashable_vector__tlresource_location),
                ("scene_anim_locations", mashable_vector__tlresource_location),
                ("skeleton_locations", mashable_vector__tlresource_location),
                ("field_68", mashable_vector),
                ("field_70", mashable_vector),
                ("pack_slot", c_int),
                ("base", c_int),
                ("field_80", c_int),
                ("field_84", c_int),
                ("field_88", c_int),
                ("type_start_idxs", c_int * 70),
                ("type_end_idxs", c_int * 70)
                ]

    def __repr__(self):
        return f'resource_directory:\n\tparents = {self.parents},\n\tresource_locations = {self.resource_locations},\n\t' \
               f'texture_locations = {self.texture_locations}, \n\t' \
               f'mesh_file_locations = {self.mesh_file_locations},\n\tmesh_locations = {self.mesh_locations},\n\t' \
               f'morph_file_locations = {self.morph_file_locations},\n\tmorph_locations = {self.morph_locations},\n\t' \
               f'material_file_locations = {self.material_file_locations},\n\tmaterial_locations = {self.material_locations},\n\t' \
               f'anim_file_locations = {self.anim_file_locations},\n\tanim_locations = {self.anim_locations},\n\t' \
               f'scene_anim_locations = {self.scene_anim_locations},\n\tskeleton_locations = {self.skeleton_locations}\n )'


    def constructor_common(self, a3: int, a5: int, a6: int, a7: int):
        self.base = a3
        self.field_80 = a5
        self.field_84 = a6
        self.field_88 = a7

    def get_resource_location(self, i: int) -> resource_location:
        #print("get_resource_location", i)

        assert(i < self.resource_locations.size())

        res = self.resource_locations.m_data[i]
        return res

    def get_mash_data(self, offset: int) -> int:
        assert(self.base != 0)
        return (offset + self.base);

    def get_type_start_idxs(self, p_type: int):
        assert(p_type > RESOURCE_KEY_TYPE_NONE and p_type < RESOURCE_KEY_TYPE_Z)

        return self.type_start_idxs[p_type];

    def get_resource(self, loc: resource_location):
        assert(not self.resource_locations.empty())

        v5 = self.get_mash_data(loc.m_offset)
        return v5

    def get_resource1(self, resource_id: resource_key):
        assert(resource_id.is_set())

        assert(resource_id.get_type() != RESOURCE_KEY_TYPE_NONE)

        v7 = 0
        mash_data_size: int = 0

        is_found, found_dir, found_loc = self.find_resource(resource_id)
        if is_found:
            mash_data_size = found_loc.m_size
            v7 = found_dir.get_resource(found_loc, a4)

        return v7, mash_data_size

    def tlresource_type_to_vector(self, a2: int):
        match a2:
            case 1:
                return self.texture_locations;
            case 2:
                return self.mesh_file_locations;
            case 3:
                return self.mesh_locations;
            case 4:
                return self.morph_file_locations;
            case 5:
                return self.morph_locations;
            case 6:
                return self.material_file_locations;
            case 7:
                return self.material_locations;
            case 8:
                return self.anim_file_locations;
            case 9:
                return self.anim_locations;
            case 10:
                return self.scene_anim_locations;
            case 11:
                return self.skeleton_locations;
            case 13:
                return self.texture_locations;
            case 14:
                return self.texture_locations;
            case 15:
                return self.texture_locations;
            case _:
                assert(0 and "invalid tlresource type");

    def get_resource_count(self, p_type: int):
        assert(p_type > RESOURCE_KEY_TYPE_NONE and p_type < RESOURCE_KEY_TYPE_Z)
        return self.type_end_idxs[p_type]

    def get_tlresource_count(self, a1: int) -> int:
        locations = self.tlresource_type_to_vector(a1);
        return locations.size();

    def un_mash_start(self, a4: generic_mash_data_ptrs) -> generic_mash_data_ptrs:
        a4.rebase(8)

        a4 = self.parents.un_mash(a4)

        a4 = self.resource_locations.custom_un_mash(a4)

        a4 = self.texture_locations.custom_un_mash(a4)

        a4 = self.mesh_file_locations.custom_un_mash(a4)

        a4 = self.mesh_locations.custom_un_mash(a4)

        a4 = self.morph_file_locations.custom_un_mash(a4)

        a4 = self.morph_locations.custom_un_mash(a4)

        a4 = self.material_file_locations.custom_un_mash(a4)

        a4 = self.material_locations.custom_un_mash(a4)

        a4 = self.anim_file_locations.custom_un_mash(a4)

        a4 = self.anim_locations.custom_un_mash(a4)

        a4 = self.scene_anim_locations.custom_un_mash(a4)

        a4 = self.skeleton_locations.custom_un_mash(a4)

        def validate(vector, tlresource_type):
            for i in range(vector.m_size):
                tlres_loc = vector.m_data[i]

                if tlresource_type == TLRESOURCE_TYPE_TEXTURE:
                    print(tlres_loc)

                assert(tlres_loc.get_type() == tlresource_type)

        validate(self.texture_locations, TLRESOURCE_TYPE_TEXTURE)

        validate(self.mesh_file_locations, TLRESOURCE_TYPE_MESH_FILE)

        validate(self.mesh_locations, TLRESOURCE_TYPE_MESH)

        validate(self.morph_file_locations, TLRESOURCE_TYPE_MORPH_FILE)

        validate(self.morph_locations, TLRESOURCE_TYPE_MORPH)

        validate(self.material_file_locations, TLRESOURCE_TYPE_MATERIAL_FILE)

        validate(self.material_locations, TLRESOURCE_TYPE_MATERIAL)

        validate(self.anim_file_locations, TLRESOURCE_TYPE_ANIM_FILE)

        validate(self.anim_locations, TLRESOURCE_TYPE_ANIM)

        validate(self.scene_anim_locations, TLRESOURCE_TYPE_SCENE_ANIM)

        validate(self.skeleton_locations, TLRESOURCE_TYPE_SKELETON)

        return a4



def init():
        script_dir = os.path.dirname(__file__)
        string_path = os.path.join(script_dir, "string_hash_dictionary.txt")
        try:
            with io.open(string_path, mode="r") as dictionary_file:
                for i, line in enumerate(dictionary_file):
                    if i > 1:

                        arr = line.split()
                        #print(line)

                        if len(arr) != 2:
                            continue

                        h = int(arr[0], 16)
                        string_hash_dictionary[h] = arr[1]

                keys = string_hash_dictionary.keys()
                #print(type(keys))

        except IOError:
            input("Could not open file!")

        assert(len(string_hash_dictionary) != 0)


class vector4d(Structure):
    _fields_ = [
                ("arr", c_float * 4),
                ]

assert(sizeof(vector4d) == 16)


class resource_pack_location(Structure):
    _fields_ = [("loc", resource_location),
                ("field_10", c_int),
                ("field_14", c_int),
                ("field_18", c_int),
                ("field_1C", c_int),
                ("prerequisite_offset", c_int),
                ("prerequisite_count", c_int),
                ("field_28", c_int),
                ("field_2C", c_int),
                ("m_name", c_char * 32)
                ]

assert(sizeof(resource_pack_location) == 0x50)

class TypeDirectoryEntry(IntEnum):
    MATERIAL = 1
    MESH = 2


class nglDirectoryEntry(Structure):
    _fields_ = [("field_0", c_char),
                ("field_1", c_char),
                ("field_2", c_char),
                ("typeDirectoryEntry", c_char),
                ("field_4", c_int), # <--- this is pointer to the resource (texture, mesh)
                ("field_8", c_int),
                ]

assert(sizeof(nglDirectoryEntry) == 0xC)

class Lod(Structure):
    _fields_ = [
                ("field_0", c_int),
                ("field_4", c_float),
                ]

assert(sizeof(Lod) == 0x8)

class tlHashString(Structure):
    _fields_ = [
                ("field_0", c_int),
                ]

assert(sizeof(tlHashString) == 4)

class nglVertexBuffer(Structure):
    _fields_ = [
                ("m_vertexData", c_int),
                ("Size", c_int), # <---- size of vertex data in bytes
                ("m_vertexBuffer", c_int)
            ]

class nglMeshSection(Structure):
    _fields_ = [
                ("Name", c_int), # <----- tlFixedString
                ("Material", c_int), # <----- nglMaterialBase
                ("NBones", c_int),
                ("BonesIdx", c_int), # <----- u16
                ("SphereCenter", vector4d),
                ("SphereRadius", c_float),
                ("Flags", c_int),
                ("m_primitiveType", c_int),
                ("NIndices", c_int),
                ("m_indices", c_int), # <--- u16
                ("m_indexBuffer", c_int),
                ("NVertices", c_int),
                ("VertexBuffer", nglVertexBuffer),
                ("m_stride", c_int),
                ("field_4C", c_int),
                ("field_50", c_int),
                ("VertexDef", c_int),
                ("field_58", c_int),
                ("field_5C", c_int)
                ]

class Section(Structure):
    _fields_ = [
                ("field_0", c_int),
                ("Section", c_int), # <---- nglMeshSection
                ]

class nglMesh(Structure):
    _fields_ = [
                ("Name", c_int), # <----- tlFixedString
                ("Flags", c_int),
                ("NSections", c_int),
                ("Sections", c_int),
                ("NBones", c_int),
                ("Bones", c_int),
                ("NLODs", c_int),
                ("LODs", c_int),
                ("field_20", vector4d),
                ("SphereRadius", c_int),
                ("File", c_int),
                ("NextMesh", c_int),
                ("field_3C", c_int)
                ]


class nglMeshFileHeader(Structure):
    _fields_ = [
                ("Tag", c_char * 4),
                ("Version", c_int),
                ("NDirectoryEntries", c_int),
                ("DirectoryEntries", c_int),
                ("field_10", c_int)
                ]


class tlFixedString(Structure):
    _fields_ = [
                ("m_hash", c_int),
                ("field_4", c_char * 28)
                ]



class nglShader(Structure):
    _fields_ = [
                ("m_vtbl", c_int),
                ("field_4", c_int),
                ("field_8", c_int),
                ]

class nglTexture(Structure):
    _fields_ = [
                ("field_0", c_int),
                ]

class nglMaterialBase(Structure):
    _fields_ = [("Name", c_int),
                ("field_4", POINTER(nglShader)),
                ("File", c_int),
                ("NextMaterial", c_int),
                ("field_10", c_int),
                ("field_14", c_int),
                ("field_18", POINTER(tlFixedString)),
                ("field_1C", POINTER(nglTexture)),
                ("field_20", POINTER(nglTexture)),
                ("field_24", POINTER(nglTexture)),
                ("field_28", vector4d),
                ("field_38", c_float),
                ("field_3C", c_int),
                ("field_40", c_int),
                ("field_44", c_int),
                ("m_outlineFeature", c_int),
                ("m_blend_mode", c_int),
                ]

#assert(sizeof(nglMaterialBase) == 0x50)

DEV_MODE = 1

def write_indices(resource_file, indices, primitive_type, enable_normals: bool):
    if primitive_type == 5:
        face = [indices[0], indices[1], indices[2]]
        if enable_normals:
            resource_file.write("f " + ("%d/%d/%d %d/%d/%d %d/%d/%d\n" % (face[0], face[0], face[0],
                                                             face[1], face[1], face[1],
                                                             face[2], face[2], face[2])))
        else:
            resource_file.write("f " + ("%d/%d %d/%d %d/%d\n" % (face[0], face[0], face[1], face[1], face[2], face[2])))

        for idx in list(indices):
            face = [face[1], face[2], idx]
            if len(face) == len(set(face)):
                if enable_normals:
                    resource_file.write("f " + ("%d/%d/%d %d/%d/%d %d/%d/%d\n" % (face[0], face[0], face[0],
                                                                 face[1], face[1], face[1],
                                                             face[2], face[2], face[2])))
                else:
                    resource_file.write("f " + ("%d/%d %d/%d %d/%d\n" % (face[0], face[0], face[1], face[1], face[2], face[2])))


    elif primitive_type == 4:
        N: int = 3
        assert(len(indices) % 3 == 0)
        faces  = [indices[n:n+N] for n in range(0, len(indices), N)]

        for face in faces:

            if enable_normals:
                resource_file.write("f " + ("%d/%d/%d %d/%d/%d %d/%d/%d\n" % (face[0], face[0], face[0],
                                                             face[1], face[1], face[1],
                                                             face[2], face[2], face[2])))
            else:
                resource_file.write("f " + ("%d/%d %d/%d %d/%d\n" % (face[0], face[0], face[1], face[1], face[2], face[2])))

    else:
        assert(0)


class UserMeshData:
    """Class to store user mesh data."""
    def __init__(self, vertices, indices, normals, uvs, bones, bone_indices, bone_weights):
        self.vertices = vertices
        self.indices = indices
        self.normals = normals
        self.uvs = uvs
        self.bones= bones
        self.bone_indices = bone_indices
        self.bone_weights = bone_weights

    def __repr__(self):
        return f"UserMeshData(vertices={len(self.vertices)}, indices={len(self.indices)}, normals={len(self.normals)}, uvs={len(self.uvs)}, bones={len(self.bones)}, bone_indices={len(self.bone_indices)}, bone_weights={len(self.bone_weights)})"    

class MeshData:
    """Class to store parsed mesh data."""
    def __init__(self, name):
        self.name = name
        self.sections = []
        self.bones = []

    def add_section(self, name, primitive_type, vertices, uvs, normals, indices, materials, bones=None):
        section_data = {
            "name": name,
            "primitive_type": primitive_type,
            "vertices": vertices,
            "uvs": uvs,
            "normals": normals,
            "indices": indices,
            "bones": bones,
            "materials": materials
        }
        self.sections.append(section_data)


current_path = ""
DEV_MODE=1

def align_address(size, alignment):
    return (size + (alignment - 1)) & ~(alignment - 1)

def replace_mesh_data(buffer_bytes, offset, mesh, user_mesh):
    print("Updating mesh data...")

    offset = mesh.Sections
    sections_t = Section * int(mesh.NSections)
    sections = sections_t.from_buffer_copy(buffer_bytes[offset : offset + sizeof(sections_t)])

    for idx, section in enumerate(sections):
        offset = section.Section
        meshSection = nglMeshSection.from_buffer_copy(buffer_bytes[offset : offset + sizeof(nglMeshSection)])

        # update values
        struct.pack_into("I", buffer_bytes, offset + nglMeshSection.NVertices.offset, len(user_mesh.vertices))
        struct.pack_into("I", buffer_bytes, offset + nglMeshSection.NIndices.offset, len(user_mesh.indices))

        vertex_offset = meshSection.VertexBuffer.m_vertexData
        del buffer_bytes[vertex_offset:]

        index_offset = meshSection.m_indices
        index_end = index_offset + (meshSection.NIndices * 2)
        del buffer_bytes[index_offset:index_end]

        flattened_indices = []
        for idx_set in user_mesh.indices:
            if isinstance(idx_set, tuple):
                flattened_indices.extend(idx_set)
            else:
                flattened_indices.append(idx_set)

        new_bytes = b''.join(struct.pack("H", int(idx)) for idx in flattened_indices)
        new_size = len(new_bytes)
        new_end = index_offset + new_size
        diff = index_end - new_end 


        if DEV_MODE and diff != 0:
            if diff > 0:
                buffer_bytes[index_offset:index_offset] = new_bytes
                #buffer_bytes[new_end:new_end] = bytearray(diff)
                buffer_bytes.extend(b'\x00' * diff)
            elif diff < 0:
                diff = abs(diff)
                
                old = buffer_bytes[index_offset:]
                buffer_bytes[index_offset:new_end] = new_bytes
                buffer_bytes.extend(b'\x00' * diff)
                buffer_bytes[new_end:] = old
                
                
                vertex_offset += diff
                struct.pack_into("I", buffer_bytes, offset + nglMeshSection.VertexBuffer.offset + nglVertexBuffer.m_vertexData.offset, vertex_offset)
                
                struct.pack_into("I", buffer_bytes, offset, meshSection.Name + diff)
                if meshSection.Material:
                    struct.pack_into("I", buffer_bytes, offset + nglMeshSection.Material.offset, meshSection.Material + diff)
            
        if meshSection.m_stride == 64:
            class VertexData(Structure):
                _fields_ = [
                    ("pos", c_float * 3),
                    ("normal", c_float * 3),
                    ("uv", c_float * 2),
                    ("bone_indices", c_float * 4),
                    ("bone_weights", c_float * 4)
                ]
            assert(sizeof(VertexData) == 0x40)
        elif meshSection.m_stride in [32, 12, 24, 60]:
            class VertexData(Structure):
                _fields_ = [
                    ("pos", c_float * 3),
                    ("uv", c_float * 2),
                    ("ff", c_float * 1)
                ]
            assert(sizeof(VertexData) == 0x18)
        else:
            raise ValueError(f"Unsupported stride value: {meshSection.m_stride}")

        new_vertex_size = len(user_mesh.vertices) * meshSection.m_stride
        required_size = vertex_offset + new_vertex_size
        if len(buffer_bytes) < required_size:
            buffer_bytes.extend(b"\x00" * (required_size - len(buffer_bytes)))
            
        # write new vertex data
        for i, vtx in enumerate(user_mesh.vertices):
            vertex_data = VertexData()
            vertex_data.pos = (vtx[0], vtx[1], vtx[2])
            vertex_data.uv = (user_mesh.uvs[i][0], 1.0 - user_mesh.uvs[i][1])
            if hasattr(vertex_data, "ff"):
                bits = (ctypes.c_uint32 * 1)(0xFFFFFFFF)
                ctypes.memmove(ctypes.addressof(vertex_data.ff), bits, sizeof(bits))
            if hasattr(vertex_data, "normal"):
                vertex_data.normal = (user_mesh.normals[i][0], user_mesh.normals[i][1], user_mesh.normals[i][2])
            if hasattr(vertex_data, "bone_indices"):
                vertex_data.bone_indices = (user_mesh.bone_indices[i][0], user_mesh.bone_indices[i][1], user_mesh.bone_indices[i][2], user_mesh.bone_indices[i][3])
            if hasattr(vertex_data, "bone_weights"):
                vertex_data.bone_weights = (user_mesh.bone_weights[i][0], user_mesh.bone_weights[i][1], user_mesh.bone_weights[i][2], user_mesh.bone_weights[i][3])

            packed_data = bytearray(vertex_data)
            buffer_bytes[vertex_offset:vertex_offset + sizeof(VertexData)] = packed_data
            vertex_offset += sizeof(VertexData)

        # update vertex buffer
        expected_vertex_buffer_size = meshSection.m_stride * len(user_mesh.vertices)
        vertex_buffer_offset = offset + nglMeshSection.VertexBuffer.offset 
        size_offset = vertex_buffer_offset + nglVertexBuffer.Size.offset 
        struct.pack_into("I", buffer_bytes, size_offset, expected_vertex_buffer_size)
        
    # align data
    buffer_size = len(buffer_bytes)
    padding_size = (align_address(buffer_size, 0x1000)) - buffer_size

    if padding_size > 0:
        buffer_bytes.extend(b"\x00" * padding_size)
        
    print("Finished!")
    return diff


def write_meshfile(filepath, user_mesh):
    with io.open(filepath, "rb") as f:
        buffer_bytes = bytearray(f.read())

    Header = nglMeshFileHeader.from_buffer_copy(buffer_bytes[:sizeof(nglMeshFileHeader)])
    assert(Header.Tag == b'PCM ')
    assert(Header.Version == 0x601)

    materials = []
    modified = False
    diff = 0
        
    for i in range(Header.NDirectoryEntries):
        offset = Header.DirectoryEntries + i * sizeof(nglDirectoryEntry)
        entry = nglDirectoryEntry.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglDirectoryEntry))])

        type_dir_entry = int.from_bytes(entry.typeDirectoryEntry, byteorder='big')

        if type_dir_entry == int(TypeDirectoryEntry.MESH) and not modified:
            print(f"Replacing mesh at offset: 0x{entry.field_4:X}")

            offset = entry.field_4
            mesh = nglMesh.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglMesh))])
            diff = replace_mesh_data(buffer_bytes, offset, mesh, user_mesh)
            modified = True

    if not modified:
        print("No mesh found to replace.")
        return
    else:
        if DEV_MODE and diff != 0:
            #
            print(f"diff = 0x{diff:X}")
            for i in range(Header.NDirectoryEntries):
                offset = Header.DirectoryEntries + i * sizeof(nglDirectoryEntry)
                entry = nglDirectoryEntry.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglDirectoryEntry))])
                type_dir_entry = int.from_bytes(entry.typeDirectoryEntry, byteorder='big')
                
                name_offs = int.from_bytes(buffer_bytes[entry.field_8:entry.field_8+4], byteorder='little')
                if name_offs != 0:
                        struct.pack_into("I", buffer_bytes, entry.field_8, name_offs + diff)
                if entry.field_8 != 0:
                        struct.pack_into("I", buffer_bytes, offset + nglDirectoryEntry.field_8.offset, entry.field_8 + diff)
                if type_dir_entry == int(TypeDirectoryEntry.MESH):
                        offset = entry.field_4
                        mesh = nglMesh.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglMesh))])
                        struct.pack_into("I", buffer_bytes, offset + nglMesh.Name.offset, mesh.Name + diff)
                        offset = Header.DirectoryEntries + i * sizeof(nglDirectoryEntry)
                        toffs = int.from_bytes(buffer_bytes[offset+0x74:offset+0x74+4], byteorder='little')
                        struct.pack_into("I", buffer_bytes, offset+0x74, toffs + diff)
                if type_dir_entry == int(TypeDirectoryEntry.MATERIAL):
                        offset = entry.field_4
                        Material = nglMaterialBase.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglMaterialBase))])
                        if Material.Name:
                                struct.pack_into("I", buffer_bytes, offset + nglMaterialBase.Name.offset, Material.Name + diff)
                                toffs = int.from_bytes(buffer_bytes[offset + nglMaterialBase.Name.offset+4:offset + nglMaterialBase.Name.offset+8], byteorder='little')
                                struct.pack_into("I", buffer_bytes, offset + nglMaterialBase.Name.offset + 4, toffs + diff)



    with io.open(filepath + ".mod", "wb") as f:
        f.write(buffer_bytes)

    print(f"Successfully updated {filepath}")

def read_mesh(Mesh: nglMesh, buffer_bytes, materials, write_obj:bool = True):

    offset = Mesh.Name
    nameMesh = tlFixedString.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(tlFixedString))])
    ndisplay = nameMesh.field_4.decode("utf-8")
    if write_obj:
        folder = 'tmp'
        try:
                os.mkdir(folder)
        except OSError:
                print ("Creation of the directory %s failed" % folder)
        else:
                print ("Successfully created the directory %s " % folder)
        filepath = os.path.join('.', 'tmp', ndisplay + ".obj")
        filepath = ''.join(x for x in filepath if x.isprintable())
        resource_file = open(filepath, mode="w")

    #resource_file.write("MeshName = %s, NSections = %d\n" % (nameMesh.field_4, Mesh.NSections))
    offset = Mesh.Sections
    sections_t = Section * int(Mesh.NSections)
    sections = sections_t.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(sections_t))])

    prev_NVertices = 0
    mesh_data = MeshData(name=ndisplay) 
    
    offset = Mesh.Bones
    for _ in range(Mesh.NBones):
        mat = struct.unpack_from('16f', buffer_bytes, offset)
        matrix = [mat[i:i+4] for i in range(0, 16, 4)]
        mesh_data.bones.append(mathutils.Matrix(matrix))
        offset += 4 * 4 * 4
    
    
    for idx, section in enumerate(sections):
        offset = section.Section
        meshSection = nglMeshSection.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglMeshSection))])

        offset = meshSection.Name
        name = tlFixedString.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(tlFixedString))])
        
        if write_obj:
                resource_file.write("o " + ndisplay + '_' + str(idx) + '\n')

        #resource_file.write("\nidx_section = %d, name = %s, primitiveType = %d, stride = %d, NIndices = %d, NVertices = %d, SizeVertexDataInBytes = %d\n"
        #        % (idx, name.field_4, meshSection.m_primitiveType, meshSection.m_stride, meshSection.NIndices, meshSection.NVertices, meshSection.VertexBuffer.Size))

        primCount = 0
        if meshSection.m_primitiveType == 5:
            primCount = meshSection.NIndices - 2
        elif meshSection.m_primitiveType == 4:
            primCount = meshSection.NIndices / 3

        print("stride = %d" % meshSection.m_stride )
        #assert(meshSection.m_stride == 64)
        
        assert(meshSection.m_stride * meshSection.NVertices == meshSection.VertexBuffer.Size)

        #resource_file.write("NPrimitive = %d\n" % primCount)
        if meshSection.m_stride == 64:
            class VertexData(Structure):
                _fields_ = [
                    ("pos", c_float * 3),
                    ("normal", c_float * 3),
                    ("uv", c_float * 2),
                    ("bone_indices", c_float * 4),
                    ("bone_weights", c_float * 4)
                ]

                def __repr__(self):
                    return f'VertexData: pos = {list(self.pos)}, normal = {list(self.normal)}, uv = {list(self.uv)}, bone_indices = {list(self.bone_indices)}, bone_weights = {list(self.bone_weights)}'

            assert(sizeof(VertexData) == 0x40)
        elif meshSection.m_stride == 32 or meshSection.m_stride == 12 or meshSection.m_stride == 24 or meshSection.m_stride == 60:
            class VertexData(Structure):
                _fields_ = [
                    ("pos", c_float * 3),
                    ("uv", c_float * 2),
                    ("ff", c_float * 1)
                ]

                def __repr__(self):
                    return f'VertexData: pos = {list(self.pos)}, uv = {list(self.uv)}'

            assert(sizeof(VertexData) == 0x18)
        else:
            raise ValueError(f"Unsupported stride value: {meshSection.m_stride}")

        offset = meshSection.VertexBuffer.m_vertexData
        print(offset)
        vertex_data_t = VertexData * int(meshSection.NVertices)
        vertex_data = vertex_data_t.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(vertex_data_t))])

        if write_obj:
                for vtx in vertex_data:
                        resource_file.write("v " + ("%.6f %.6f %.6f" % (vtx.pos[0], vtx.pos[1], vtx.pos[2])) + '\n')
                        if meshSection.m_stride > 12:
                                resource_file.write("vt " + ("%.6f %.6f" % (vtx.uv[0], 1.0 - vtx.uv[1])) + '\n')
                        if meshSection.m_stride == 64:
                                resource_file.write("vn " + ("%.6f %.6f %.6f" % (vtx.normal[0], vtx.normal[1], vtx.normal[2])) + '\n')
                resource_file.write("s off\n")



        

        offset = meshSection.m_indices
        indices_data_t = c_short * int(meshSection.NIndices)
        indices = indices_data_t.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(indices_data_t))])

        #resource_file.write("\nIndices: ")

        print("NIndices = %d" % (meshSection.NIndices))

        if meshSection.NIndices != 0:

            num_vertices = int(meshSection.NVertices)
            max_index = max(list(indices))
            print("max_index = %d, NVertices = %d" % (max_index, num_vertices))

            for i, index in enumerate(indices):
                indices[i] = prev_NVertices + index + 1
                
            if write_obj:
                write_indices(resource_file, indices, meshSection.m_primitiveType, False)
        elif meshSection.NVertices == 6:
            if write_obj:
                resource_file.write("f " + ("%d %d %d\n" % (1, 2, 3)))
                resource_file.write("f " + ("%d %d %d\n" % (4, 5, 6)))
        else:

            print("\nidx_section = %d, name = %s, primitiveType = %d, stride = %d, NIndices = %d, NVertices = %d, SizeVertexDataInBytes = %d\n"
                % (idx, name.field_4, meshSection.m_primitiveType, meshSection.m_stride, meshSection.NIndices, meshSection.NVertices, meshSection.VertexBuffer.Size))
            #assert(0)

        prev_NVertices = meshSection.NVertices + prev_NVertices

        #resource_file.write(str(list(indices)) + '\n')
        if write_obj:
                resource_file.write("\n\n")
        vertices = []
        uvs = []
        normals = []
        indices = list(indices_data_t.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(indices_data_t))]))

        for vtx in vertex_data:
            vertices.append((
                round(vtx.pos[0], 6),
                round(vtx.pos[1], 6),
                round(vtx.pos[2], 6)
            ))
            if hasattr(vtx, 'uv'):
                uvs.append(tuple(vtx.uv))
            if hasattr(vtx, 'normal'):
                normals.append(tuple(vtx.normal))

        local_bones = []
        if meshSection.m_stride == 64:
            for vtx in vertex_data:
                local_bones.append({
                    "indices": [int(x) for x in vtx.bone_indices],
                    "weights": [float(x) for x in vtx.bone_weights]
                })
                
        section_bones_idx = []
        if meshSection.NBones and meshSection.BonesIdx:
            off_bones_idx = meshSection.BonesIdx
            bones_idx_t = c_ushort * int(meshSection.NBones)
            section_bones_idx = list(bones_idx_t.from_buffer_copy(buffer_bytes[off_bones_idx : (off_bones_idx + sizeof(bones_idx_t))]))

        bones_mapped = []
        if local_bones:
            for v in local_bones:
                local_idxs = [int(x) for x in v["indices"]]
                weights = [float(x) for x in v["weights"]]
                final_idxs = []
                if section_bones_idx:
                    for li in local_idxs:
                        if li < 0:
                            final_idxs.append(-1)
                        elif 0 <= li < len(section_bones_idx):
                            final_idxs.append(int(section_bones_idx[li]))
                        else:
                            final_idxs.append(int(li))
                else:
                    final_idxs = [int(li) for li in local_idxs]
                bones_mapped.append({"indices": final_idxs, "weights": weights})

        mesh_data.add_section(
            name=ndisplay + '_' + str(idx),
            primitive_type=meshSection.m_primitiveType,
            vertices=vertices,
            uvs=uvs,
            normals=normals,
            indices=indices,
            materials=materials,
            bones=bones_mapped
        )        
    return mesh_data

def read_meshfile(file, write_obj:bool = False):
    print("Resource pack:", file)
    current_path = file
    mesh_data = []
    with io.open(file, mode="rb") as rPack:
        buffer_bytes = rPack.read()

        print("0x%02X" % buffer_bytes[0])
        print("0x%02X" % buffer_bytes[1])
        print(len(buffer_bytes))

        rPack.seek(0, 2)
        numOfBytes = rPack.tell()
        print("Total Size:", numOfBytes, "bytes")

        Header = nglMeshFileHeader.from_buffer_copy(buffer_bytes[0:sizeof(nglMeshFileHeader)])
        assert(Header.Tag == b'PCM ')
        assert(Header.Version == 0x601)
        #assert(Header.NDirectoryEntries == 8)
        assert(Header.field_10 == 0)
        
        
        materials = []

        for i in range(Header.NDirectoryEntries):
            print("\nidx = %d" % i)

            offset = Header.DirectoryEntries + i * sizeof(nglDirectoryEntry)
            print("Offset = 0x%X" % offset);

            entry = nglDirectoryEntry.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglDirectoryEntry))])
            print("typeDirectoryEntry = %s" % ("MATERIAL" if int.from_bytes(entry.typeDirectoryEntry, byteorder='big') == 1 else "MESH") )
            print("0x%X 0x%X" % (entry.field_4, entry.field_8))

            type_dir_entry = int.from_bytes(entry.typeDirectoryEntry, byteorder='big')
            if type_dir_entry == int(TypeDirectoryEntry.MATERIAL):

                offset = entry.field_4
                Material = nglMaterialBase.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglMaterialBase))])
                print("0x%08X" % Material.Name)

                offset = Material.Name
                MaterialName = tlFixedString.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(tlFixedString))])
                print("%s" % MaterialName.field_4)
                
                offset += sizeof(tlFixedString)
                matFlag = tlFixedString.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(tlFixedString))])
                offset += sizeof(tlFixedString)
                
                texName = tlFixedString.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(tlFixedString))])
                texName = texName.field_4.decode("utf-8")
                texName = f"{texName.upper()}.DDS"
                print(f"Texture: {texName}")
                materials.append(texName)
                #assert(Material.field_44 == 1)

            elif type_dir_entry == int(TypeDirectoryEntry.MESH):

                offset = entry.field_4
                mesh = nglMesh.from_buffer_copy(buffer_bytes[offset : (offset + sizeof(nglMesh))])
                mesh_data.append(read_mesh(mesh, buffer_bytes, materials, write_obj))
    return mesh_data

