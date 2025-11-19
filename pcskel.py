# LemonHaze - 2025

import struct
import os
from enum import IntEnum
from pathlib import Path

class NalComponentType(IntEnum):
    ArbitraryPO = 0xC5E45DCF
    Generic = 0xEC4755BD
    FakerootEntropyCompressed = 0xB916E121
    TorsoHead_TwoNeck_Compressed = 0x7E916D6A
    TorsoHead_OneNeck_Compressed = 0x70EA5DF2
    LegsFeet_Compressed = 0x47CBEBDB
    LegsFeet_IK_Compressed = 0xA556994F
    ArmsHands_Compressed = 0xE01F4F4D
    ArmsHands_IK_Compressed = 0xF0AD5C8E
    Tentacles_Compressed = 0x464A04D8
    FiveFinger_Top2KnuckleCurl = 0xE7D9A8D3
    FiveFinger_IndividualCurl = 0xE7A8F925
    FiveFinger_ReducedAngular = 0xE78254B9
    FiveFinger_FullRotational = 0xAFEB6A28

class FingerBones(IntEnum):
    L_FINGER_0 = 0; R_FINGER_0 = 1; L_FINGER_1 = 2; L_FINGER_2 = 3; L_FINGER_3 = 4; L_FINGER_4 = 5
    R_FINGER_1 = 6; R_FINGER_2 = 7; R_FINGER_3 = 8; R_FINGER_4 = 9; L_FINGER_01 = 10; R_FINGER_01 = 11
    L_FINGER_11 = 12; L_FINGER_21 = 13; L_FINGER_31 = 14; L_FINGER_41 = 15; R_FINGER_11 = 16
    R_FINGER_21 = 17; R_FINGER_31 = 18; R_FINGER_41 = 19; L_FINGER_02 = 20; R_FINGER_02 = 21
    L_FINGER_12 = 22; L_FINGER_22 = 23; L_FINGER_32 = 24; L_FINGER_42 = 25; R_FINGER_12 = 26
    R_FINGER_22 = 27; R_FINGER_32 = 28; R_FINGER_42 = 29; L_HAND_PARENT = 30; R_HAND_PARENT = 31

class TorsoHeadBones(IntEnum):
    PELVIS = 0; SPINE = 1; SPINE1 = 2; SPINE2 = 3; NECK = 4; HEAD = 5; NECK_AUX = 6

class LegsBones(IntEnum):
    L_TOE = 0; R_TOE = 1; L_FOOT = 2; R_FOOT = 3; L_THIGH = 4; L_CALF = 5; R_THIGH = 6; R_CALF = 7; PELVIS = 8

class ArmHandsCompressedBones(IntEnum):
    L_CLAVICLE = 0; L_UPPERARM = 1; L_FOREARM = 2; L_HAND = 3; R_CLAVICLE = 4; R_UPPERARM = 5; R_FOREARM = 6
    R_HAND = 7; L_FORE_TWIST_0 = 8; L_FORE_TWIST_1 = 9; R_FORE_TWIST_0 = 10; R_FORE_TWIST_1 = 11; NECK_PARENT = 12

class ArmsHandsIKBones(IntEnum):
    L_CLAVICLE = 0; R_CLAVICLE = 1; L_HAND = 2; R_HAND = 3; L_UPPERARM = 4; R_UPPERARM = 5
    L_FOREARM = 6; R_FOREARM = 7; L_FORE_TWIST_0 = 8; L_FORE_TWIST_1 = 9; R_FORE_TWIST_0 = 10
    R_FORE_TWIST_1 = 11; NECK_PARENT = 12; PELVIS = 13

class ComponentFlags(IntEnum):
    ENABLED = 1
    HAS_SKEL_DATA = 4

def read_vec3(f): return struct.unpack('<3f', f.read(12))
def read_vec4(f): return struct.unpack('<4f', f.read(16))

def read_ik_skel_data(f):
    data = struct.unpack('<6f', f.read(24))
    return {
        "fUpperIKc": data[0], "fUpperIKInvc": data[1],
        "fLowerIKc": data[2], "fLowerIKInvc": data[3],
        "fUpperArmLength": data[4], "fLowerArmLength": data[5]
    }

def read_fixed_string(f):
    data = f.read(32)
    if len(data) < 32: return 0, ""
    hash_val, name_bytes = struct.unpack('<I28s', data)
    return hash_val, name_bytes.decode('latin-1').split('\x00')[0]

def get_enum_name(enum_cls, value):
    try: return enum_cls(value).name
    except ValueError: return f"Unknown_{value}"

class NalSkeletonParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.bone_map = {} 
        self.parent_map = {}
        self.component_bone_names = {}

        self.result = {
            "header": {},
            "components": [],
            "bone_map": self.bone_map,
            "parent_map": self.parent_map,
            "component_bone_names": self.component_bone_names,
        }
    def parse(self):
        with open(self.filepath, 'rb') as f:
            cls, version = struct.unpack('<II', f.read(8))
            _, name_str = read_fixed_string(f)
            _, cat_str = read_fixed_string(f)
            
            self.result["header"] = {
                "class": cls, "version": version, 
                "name": name_str, "category": cat_str
            }

            if "generic" in cat_str or "panel" in cat_str:
                return self.result

            #mind gap 
            num_skel_data = struct.unpack('<i', f.read(4))[0]
            f.read(24)
            
            header_rest = struct.unpack('<Iiiiii', f.read(24))
            num_components = header_rest[0]
            components_offs = header_rest[3]
            per_skel_data_int_offs = header_rest[4]

            component_meta = []

            if num_components > 0 and components_offs > 0:
                f.seek(components_offs)
                for _ in range(num_components):
                    c_idx, c_type, c_flags = struct.unpack('<iIi', f.read(12))
                    component_meta.append({'index': c_idx, 'type': c_type, 'flags': c_flags})

            if per_skel_data_int_offs > 0:
                f.seek(per_skel_data_int_offs)
                num_blocks = struct.unpack('<i', f.read(4))[0]
                block_offsets = []
                for _ in range(num_blocks):
                    block_offsets.append(struct.unpack('<i', f.read(4))[0])

                if num_components > 0:
                    indices = [i for i, comp in enumerate(component_meta) 
                               if comp['flags'] & ComponentFlags.HAS_SKEL_DATA]

                    block_base = per_skel_data_int_offs
                    
                    for block_index in range(min(len(block_offsets), len(indices))):
                        comp_idx = indices[block_index]
                        meta = component_meta[comp_idx]
                        comp_type = meta['type']
                        
                        comp_block_start = block_base + block_offsets[block_index]
                        f.seek(comp_block_start)

                        data = None
                        
                        if comp_type in [NalComponentType.TorsoHead_TwoNeck_Compressed, NalComponentType.TorsoHead_OneNeck_Compressed]:
                            data = self.parse_torso_head(f)
                        elif comp_type == NalComponentType.LegsFeet_IK_Compressed:
                            data = self.parse_legs_ik(f)
                        elif comp_type == NalComponentType.ArmsHands_Compressed:
                            data = self.parse_arms_hands_compressed(f)
                        elif comp_type == NalComponentType.ArmsHands_IK_Compressed:
                            data = self.parse_arms_hands_ik(f)
                        elif comp_type == NalComponentType.FiveFinger_Top2KnuckleCurl:
                            data = self.parse_five_finger(f)
                        elif comp_type == NalComponentType.ArbitraryPO:
                            data = self.parse_arbitrary_po(f, comp_block_start)
                        
                        if data:
                            data["type_id"] = comp_type
                            data["type_name"] = NalComponentType(comp_type).name if comp_type in list(NalComponentType) else "Unknown"
                            self.result["components"].append(data)

        return self.result

    def _map_bones(self, indices, enum_cls, count):
        for i in range(count):
            bone_id = indices[i]
            if bone_id == -1:
                continue

            role_name = get_enum_name(enum_cls, i)
            if bone_id not in self.component_bone_names:
                self.component_bone_names[bone_id] = role_name

    def parse_torso_head(self, f):
        empty_neck_orient = read_vec4(f)
        empty_neck_pos = read_vec3(f)
        offset_locs = [read_vec3(f) for _ in range(5)]
        bone_ixs = struct.unpack('<6I', f.read(24))
        other_matrix_ixs = struct.unpack('<I', f.read(4))[0]

        self._map_bones(bone_ixs, TorsoHeadBones, 6)

        return {
            "empty_neck_orient": empty_neck_orient,
            "empty_neck_pos": empty_neck_pos,
            "offset_locs": offset_locs,
            "bone_indices": bone_ixs,
            "other_matrix_indices": [other_matrix_ixs]
        }

    def parse_legs_ik(self, f):
        offset_locs = [read_vec3(f) for _ in range(8)]
        ik_data = [read_ik_skel_data(f) for _ in range(2)]
        bone_ixs = struct.unpack('<8I', f.read(32))
        other_matrix_ixs = struct.unpack('<I', f.read(4))[0]
        
        self._map_bones(bone_ixs, LegsBones, 8)

        return {
            "offset_locs": offset_locs,
            "ik_data": ik_data,
            "bone_indices": bone_ixs,
            "other_matrix_indices": [other_matrix_ixs]
        }

    def parse_arms_hands_compressed(self, f):
        vectors = [read_vec4(f) for _ in range(9)]
        bone_ixs = struct.unpack('<16I', f.read(64))

        self._map_bones(bone_ixs, ArmHandsCompressedBones, 15)

        return {
            "vectors": vectors,
            "bone_indices": bone_ixs
        }

    def parse_arms_hands_ik(self, f):
        offset_locs = [read_vec3(f) for _ in range(8)]
        fore_twist_locs = [read_vec3(f) for _ in range(4)]
        ik_data = [read_ik_skel_data(f) for _ in range(2)]
        bone_ixs = struct.unpack('<8I', f.read(32))
        other_matrix_ixs = struct.unpack('<6I', f.read(24))
        
        self._map_bones(bone_ixs, ArmsHandsIKBones, 8)
        for i, bone_id in enumerate(other_matrix_ixs):
            if bone_id == -1:
                continue
            role_index = 8 + i
            role_name = get_enum_name(ArmsHandsIKBones, role_index)
            if bone_id not in self.component_bone_names:
                self.component_bone_names[bone_id] = role_name

        return {
            "offset_locs": offset_locs,
            "fore_twist_locs": fore_twist_locs,
            "ik_data": ik_data,
            "bone_indices": bone_ixs,
            "other_matrix_indices": other_matrix_ixs
        }

    def parse_five_finger(self, f):
        vectors = [read_vec4(f) for _ in range(22)]
        aa = struct.unpack('<2f', f.read(8))
        bone_ixs = struct.unpack('<32I', f.read(128))
        
        self._map_bones(bone_ixs, FingerBones, 30)

        return {
            "vectors": vectors,
            "aa": aa,
            "bone_indices": bone_ixs
        }

    def parse_arbitrary_po(self, f, block_start):
        data = struct.unpack('<8I', f.read(32))
        bone_count = data[0]
        block_data_offset = data[6]

        nodes = []
        node_list_offset = block_start + block_data_offset
        f.seek(node_list_offset)
        
        for _ in range(bone_count):
            node_data = f.read(48)
            _, node_name = struct.unpack('<I28s', node_data[:32])
            node_name_str = node_name.decode('latin-1').split('\x00')[0]
            
            indices = struct.unpack('<HHhh', node_data[32:40])
            my_matrix_ix = indices[2] # iMyMatrixIx
            parent_matrix_ix = indices[3] # iParentMatrixIx
            
            flags = struct.unpack('<HHi', node_data[40:48])

            # Update bone map
            if node_name_str:
                self.bone_map[my_matrix_ix] = node_name_str
            
            # Update parent map
            self.parent_map[my_matrix_ix] = parent_matrix_ix

            nodes.append({
                "name": node_name_str,
                "id": my_matrix_ix,
                "parent_id": parent_matrix_ix,
                "indices": indices,
                "flags": flags
            })
            
        return {
            "bone_count": bone_count,
            "nodes": nodes
        }

def open_pcskel(filepath: str) -> dict:
    """
      header, components
      bone_map       { bone_id (int) -> bone_name (str) }
      parent_map     { child_id (int) -> parent_id (int) }
    """
    parser = NalSkeletonParser(filepath)
    return parser.parse()
    
    
def get_bone_name(skel_data: dict, bone_idx: int) -> str:
    bone_map = skel_data.get('bone_map', {})
    comp_names = skel_data.get('component_bone_names', {})

    if bone_idx in bone_map:
        return bone_map[bone_idx]

    if bone_idx in comp_names:
        return comp_names[bone_idx]

    return f"Bone_{int(bone_idx)}"
    
def get_parent_bone_name(skel_data: dict, bone_idx: int) -> str:
    parent_map = skel_data.get('parent_map', {})
    bone_map = skel_data.get('bone_map', {})
    parent_id = parent_map.get(bone_idx)
    if parent_id is None:
        return "None" 
    if parent_id == -1:
        return "ROOT" 
    return bone_map.get(parent_id, f"Bone_{parent_id}")
    
def apply_torso_head_chains(skel_data, idx_to_bone, root_eb):
    for comp in skel_data.get("components", []):
        t = comp.get("type_id")
        if t not in (
            NalComponentType.TorsoHead_TwoNeck_Compressed,
            NalComponentType.TorsoHead_OneNeck_Compressed,
        ):
            continue

        bone_ixs = comp["bone_indices"]

        pelvis_id = bone_ixs[TorsoHeadBones.PELVIS.value]
        spine_id  = bone_ixs[TorsoHeadBones.SPINE.value]
        spine1_id = bone_ixs[TorsoHeadBones.SPINE1.value]
        spine2_id = bone_ixs[TorsoHeadBones.SPINE2.value]
        neck_id   = bone_ixs[TorsoHeadBones.NECK.value]
        head_id   = bone_ixs[TorsoHeadBones.HEAD.value]

        chain = [pelvis_id, spine_id, spine1_id, spine2_id, neck_id, head_id]

        # pelvis under ROOT
        if pelvis_id in idx_to_bone:
            idx_to_bone[pelvis_id].parent = root_eb

        # spine chain
        for parent_id, child_id in zip(chain, chain[1:]):
            if parent_id in idx_to_bone and child_id in idx_to_bone:
                idx_to_bone[child_id].parent = idx_to_bone[parent_id]
                
        other_ixs = comp.get("other_matrix_indices")
        if other_ixs:
            other_id = other_ixs[0]
            if other_id in idx_to_bone and pelvis_id in idx_to_bone:
                idx_to_bone[other_id].parent = idx_to_bone[pelvis_id]    
                
def apply_leg_chains(skel_data, idx_to_bone):
    pelvis_id = None
    for comp in skel_data.get("components", []):
        t = comp.get("type_id")
        if t in (
            NalComponentType.TorsoHead_TwoNeck_Compressed,
            NalComponentType.TorsoHead_OneNeck_Compressed,
        ):
            bone_ixs = comp["bone_indices"]
            pelvis_id = bone_ixs[TorsoHeadBones.PELVIS.value]
            break

    for comp in skel_data.get("components", []):
        if comp.get("type_id") != NalComponentType.LegsFeet_IK_Compressed:
            continue

        bone_ixs = comp["bone_indices"]

        l_toe_id   = bone_ixs[LegsBones.L_TOE.value]
        r_toe_id   = bone_ixs[LegsBones.R_TOE.value]
        l_foot_id  = bone_ixs[LegsBones.L_FOOT.value]
        r_foot_id  = bone_ixs[LegsBones.R_FOOT.value]
        l_thigh_id = bone_ixs[LegsBones.L_THIGH.value]
        l_calf_id  = bone_ixs[LegsBones.L_CALF.value]
        r_thigh_id = bone_ixs[LegsBones.R_THIGH.value]
        r_calf_id  = bone_ixs[LegsBones.R_CALF.value]


        legs_parent = None
        if pelvis_id is not None and pelvis_id in idx_to_bone:
            legs_parent = idx_to_bone[pelvis_id]
            
        if legs_parent is not None:
            if r_thigh_id in idx_to_bone:
                idx_to_bone[r_thigh_id].parent = legs_parent
            if l_thigh_id in idx_to_bone:
                idx_to_bone[l_thigh_id].parent = legs_parent

        # thigh to calf -> foot -> toe
        chains = [
            (l_thigh_id, l_calf_id),
            (l_calf_id,  l_foot_id),
            (l_foot_id,  l_toe_id),

            (r_thigh_id, r_calf_id),
            (r_calf_id,  r_foot_id),
            (r_foot_id,  r_toe_id),
        ]

        for parent_id, child_id in chains:
            if parent_id in idx_to_bone and child_id in idx_to_bone:
                idx_to_bone[child_id].parent = idx_to_bone[parent_id]
                
def apply_arm_chains(skel_data, idx_to_bone):
    spine2_id = None
    for comp in skel_data.get("components", []):
        t = comp.get("type_id")
        if t in (
            NalComponentType.TorsoHead_TwoNeck_Compressed,
            NalComponentType.TorsoHead_OneNeck_Compressed,
        ):
            bone_ixs = comp["bone_indices"]
            spine2_id = bone_ixs[TorsoHeadBones.SPINE2.value]
            break

    has_arms_ik = False
    for comp in skel_data.get("components", []):
        if comp.get("type_id") != NalComponentType.ArmsHands_IK_Compressed:
            continue

        has_arms_ik = True
        bone_ixs = comp["bone_indices"]

        l_clav_id    = bone_ixs[ArmsHandsIKBones.L_CLAVICLE.value]
        r_clav_id    = bone_ixs[ArmsHandsIKBones.R_CLAVICLE.value]
        l_hand_id    = bone_ixs[ArmsHandsIKBones.L_HAND.value]
        r_hand_id    = bone_ixs[ArmsHandsIKBones.R_HAND.value]
        l_upper_id   = bone_ixs[ArmsHandsIKBones.L_UPPERARM.value]
        r_upper_id   = bone_ixs[ArmsHandsIKBones.R_UPPERARM.value]
        l_forearm_id = bone_ixs[ArmsHandsIKBones.L_FOREARM.value]
        r_forearm_id = bone_ixs[ArmsHandsIKBones.R_FOREARM.value]

        if spine2_id is not None and spine2_id in idx_to_bone:
            spine2_bone = idx_to_bone[spine2_id]
            if l_clav_id in idx_to_bone:
                idx_to_bone[l_clav_id].parent = spine2_bone
            if r_clav_id in idx_to_bone:
                idx_to_bone[r_clav_id].parent = spine2_bone

        chains = [
            (l_clav_id,    l_upper_id),
            (l_upper_id,   l_forearm_id),
            (l_forearm_id, l_hand_id),

            (r_clav_id,    r_upper_id),
            (r_upper_id,   r_forearm_id),
            (r_forearm_id, r_hand_id),
        ]

        for parent_id, child_id in chains:
            if parent_id in idx_to_bone and child_id in idx_to_bone:
                idx_to_bone[child_id].parent = idx_to_bone[parent_id]

        other_ixs = comp.get("other_matrix_indices", ())
        if len(other_ixs) >= 4:
            l_twist0_id, l_twist1_id, r_twist0_id, r_twist1_id = other_ixs[:4]

            # left twists: forearm -> twist0 -> twist1
            if l_forearm_id in idx_to_bone and l_twist0_id in idx_to_bone:
                idx_to_bone[l_twist0_id].parent = idx_to_bone[l_forearm_id]
            if l_twist1_id in idx_to_bone and l_twist0_id in idx_to_bone:
                idx_to_bone[l_twist1_id].parent = idx_to_bone[l_twist0_id]

            # right twists: forearm -> twist0 -> twist1
            if r_forearm_id in idx_to_bone and r_twist0_id in idx_to_bone:
                idx_to_bone[r_twist0_id].parent = idx_to_bone[r_forearm_id]
            if r_twist1_id in idx_to_bone and r_twist0_id in idx_to_bone:
                idx_to_bone[r_twist1_id].parent = idx_to_bone[r_twist0_id]

    if has_arms_ik:
        return

    for comp in skel_data.get("components", []):
        if comp.get("type_id") != NalComponentType.ArmsHands_Compressed:
            continue

        bone_ixs = comp["bone_indices"]

        l_clav_id    = bone_ixs[ArmHandsCompressedBones.L_CLAVICLE.value]
        r_clav_id    = bone_ixs[ArmHandsCompressedBones.R_CLAVICLE.value]
        l_upper_id   = bone_ixs[ArmHandsCompressedBones.L_UPPERARM.value]
        r_upper_id   = bone_ixs[ArmHandsCompressedBones.R_UPPERARM.value]
        l_forearm_id = bone_ixs[ArmHandsCompressedBones.L_FOREARM.value]
        r_forearm_id = bone_ixs[ArmHandsCompressedBones.R_FOREARM.value]
        l_hand_id    = bone_ixs[ArmHandsCompressedBones.L_HAND.value]
        r_hand_id    = bone_ixs[ArmHandsCompressedBones.R_HAND.value]

        l_twist0_id  = bone_ixs[ArmHandsCompressedBones.L_FORE_TWIST_0.value]
        l_twist1_id  = bone_ixs[ArmHandsCompressedBones.L_FORE_TWIST_1.value]
        r_twist0_id  = bone_ixs[ArmHandsCompressedBones.R_FORE_TWIST_0.value]
        r_twist1_id  = bone_ixs[ArmHandsCompressedBones.R_FORE_TWIST_1.value]

        neck_parent_id = bone_ixs[ArmHandsCompressedBones.NECK_PARENT.value]

        clav_parent = None
        if spine2_id is not None and spine2_id in idx_to_bone:
            clav_parent = idx_to_bone[spine2_id]
        elif neck_parent_id in idx_to_bone:
            clav_parent = idx_to_bone[neck_parent_id]

        if clav_parent is not None:
            if l_clav_id in idx_to_bone:
                idx_to_bone[l_clav_id].parent = clav_parent
            if r_clav_id in idx_to_bone:
                idx_to_bone[r_clav_id].parent = clav_parent

        # clavicle -> upper -> forearm -> hand
        chains = [
            (l_clav_id,    l_upper_id),
            (l_upper_id,   l_forearm_id),
            (l_forearm_id, l_hand_id),

            (r_clav_id,    r_upper_id),
            (r_upper_id,   r_forearm_id),
            (r_forearm_id, r_hand_id),
        ]

        for parent_id, child_id in chains:
            if parent_id in idx_to_bone and child_id in idx_to_bone:
                idx_to_bone[child_id].parent = idx_to_bone[parent_id]

        # twist chains: forearm -> twist0 -> twist1
        if l_forearm_id in idx_to_bone and l_twist0_id in idx_to_bone:
            idx_to_bone[l_twist0_id].parent = idx_to_bone[l_forearm_id]
        if l_twist1_id in idx_to_bone and l_twist0_id in idx_to_bone:
            idx_to_bone[l_twist1_id].parent = idx_to_bone[l_twist0_id]

        if r_forearm_id in idx_to_bone and r_twist0_id in idx_to_bone:
            idx_to_bone[r_twist0_id].parent = idx_to_bone[r_forearm_id]
        if r_twist1_id in idx_to_bone and r_twist0_id in idx_to_bone:
            idx_to_bone[r_twist1_id].parent = idx_to_bone[r_twist0_id]
      
def apply_finger_chains(skel_data, idx_to_bone):
    for comp in skel_data.get("components", []):
        if comp.get("type_id") != NalComponentType.FiveFinger_Top2KnuckleCurl:
            continue

        bone_ixs = comp["bone_indices"]

        def bid(role: FingerBones):
            return bone_ixs[role.value]

        # Left thumb: 0 -> 01 -> 02
        thumb_chain = [
            (bid(FingerBones.L_FINGER_0),  bid(FingerBones.L_FINGER_01)),
            (bid(FingerBones.L_FINGER_01), bid(FingerBones.L_FINGER_02)),
        ]

        # base -> mid -> tip
        left_finger_chains = []
        for base, mid, tip in [
            (FingerBones.L_FINGER_1,  FingerBones.L_FINGER_11, FingerBones.L_FINGER_12),
            (FingerBones.L_FINGER_2,  FingerBones.L_FINGER_21, FingerBones.L_FINGER_22),
            (FingerBones.L_FINGER_3,  FingerBones.L_FINGER_31, FingerBones.L_FINGER_32),
            (FingerBones.L_FINGER_4,  FingerBones.L_FINGER_41, FingerBones.L_FINGER_42),
        ]:
            b = bid(base); m = bid(mid); t = bid(tip)
            left_finger_chains.extend([(b, m), (m, t)])

        # Right thumb: 0 -> 01 -> 02
        right_thumb_chain = [
            (bid(FingerBones.R_FINGER_0),  bid(FingerBones.R_FINGER_01)),
            (bid(FingerBones.R_FINGER_01), bid(FingerBones.R_FINGER_02)),
        ]

        right_finger_chains = []
        for base, mid, tip in [
            (FingerBones.R_FINGER_1,  FingerBones.R_FINGER_11, FingerBones.R_FINGER_12),
            (FingerBones.R_FINGER_2,  FingerBones.R_FINGER_21, FingerBones.R_FINGER_22),
            (FingerBones.R_FINGER_3,  FingerBones.R_FINGER_31, FingerBones.R_FINGER_32),
            (FingerBones.R_FINGER_4,  FingerBones.R_FINGER_41, FingerBones.R_FINGER_42),
        ]:
            b = bid(base); m = bid(mid); t = bid(tip)
            right_finger_chains.extend([(b, m), (m, t)])

        for parent_id, child_id in (
            thumb_chain
            + left_finger_chains
            + right_thumb_chain
            + right_finger_chains
        ):
            if parent_id in idx_to_bone and child_id in idx_to_bone:
                idx_to_bone[child_id].parent = idx_to_bone[parent_id]

        l_hand_parent_id = bid(FingerBones.L_HAND_PARENT)
        r_hand_parent_id = bid(FingerBones.R_HAND_PARENT)

        left_bases = [
            bid(FingerBones.L_FINGER_0),
            bid(FingerBones.L_FINGER_1),
            bid(FingerBones.L_FINGER_2),
            bid(FingerBones.L_FINGER_3),
            bid(FingerBones.L_FINGER_4),
        ]
        right_bases = [
            bid(FingerBones.R_FINGER_0),
            bid(FingerBones.R_FINGER_1),
            bid(FingerBones.R_FINGER_2),
            bid(FingerBones.R_FINGER_3),
            bid(FingerBones.R_FINGER_4),
        ]

        if l_hand_parent_id in idx_to_bone:
            hp = idx_to_bone[l_hand_parent_id]
            for b_id in left_bases:
                if b_id in idx_to_bone:
                    idx_to_bone[b_id].parent = hp

        if r_hand_parent_id in idx_to_bone:
            hp = idx_to_bone[r_hand_parent_id]
            for b_id in right_bases:
                if b_id in idx_to_bone:
                    idx_to_bone[b_id].parent = hp