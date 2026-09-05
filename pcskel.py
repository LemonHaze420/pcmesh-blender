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
    HAS_TRACK_DATA = 1
    HAS_PER_ANIM_DATA = 2
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

def _normalize_generic_lookup_name(value):
    return str(value or "").strip().casefold()

_GENERIC_HELPER_NODE_NAMES = frozenset({
    "bip01_prop_free",
    "shake_root",
    "fakeroot",
    "camera_root",
    "camera",
})

_GENERIC_VALUE_TYPE_BY_ENCODING = {
    "nal_entropyfloat3": "nalVector3",
    "nal_packed16entropyquaternion": "nalQuaternion",
    "nal_entropypositionorientation": "nalPositionOrientation",
    "nal_entropytrajectorypositionorientation": "nalPositionOrientation",
    "nal_entropyfloat1": "float",
    "usmevent": "unsigned char",
}

_GENERIC_RUNTIME_HANDLE_ACCESS = {
    ("camera_root", "ae_base_bone"): ("nalPositionOrientation", "const"),
    ("shake_root", "ae_base_bone"): ("nalPositionOrientation", "const"),
    ("fakeroot", "ae_floor_offset"): ("float", "mutable"),
    ("fakeroot", "nal_trajectory"): ("nalPositionOrientation", "mutable"),
    ("fakeroot", "usmevent"): ("unsigned char", "mutable"),
    ("camera", "maxparamfloat.fov"): ("float", "const"),
    ("camera", "maxparamfloat.far env range"): ("float", "const"),
    ("fakeroot", "maxparamfloat.tentacle base diameter"): ("float", "const"),
    ("fakeroot", "maxparamfloat.subtentacle activity"): ("float", "const"),
    ("fakeroot", "maxparamfloat.pull factor"): ("float", "const"),
}

class NalSkeletonParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.bone_map = {} 
        self.parent_map = {}
        self.component_bone_names = {}

        self.result = {
            "header": {},
            "components": [],
            "component_meta": [],
            "default_poses": {},
            "warnings": [],
            "generic_nodes": [],
            "generic_targets": [],
            "generic_target_name_to_index": {},
            "generic_components": [],
            "generic_component_summary": [],
            "generic_component_infos": [],
            "generic_component_info_blocks": [],
            "generic_playback_families": [],
            "generic_handle_map": {},
            "generic_runtime_handles": [],
            "generic_scalar_tail": [],
            "generic_scalar_tail_off": 0,
            "generic_scalar_layout": [],
            "bone_map": self.bone_map,
            "parent_map": self.parent_map,
            "component_bone_names": self.component_bone_names,
        }

    def parse(self):
        with open(self.filepath, 'rb') as f:
            cls, version = struct.unpack('<II', f.read(8))
            _, name_str = read_fixed_string(f)
            _, cat_str = read_fixed_string(f)
            
            cat_lower = cat_str.casefold()
            self.result["header"] = {
                "class": cls,
                "version": version,
                "name": name_str,
                "category": cat_str,
                "skeleton_kind": "character",
            }

            if "generic" in cat_lower or int(version) == 0x10200:
                self.result["header"]["skeleton_kind"] = "generic"
                self._parse_generic_skeleton(f)
                return self.result

            if "panel" in cat_lower:
                self.result["header"]["skeleton_kind"] = "panel"
                self.result["warnings"].append("Panel skeleton parsing is not implemented")
                return self.result
            #mind gap 
            num_skel_data = struct.unpack('<i', f.read(4))[0]
            f.read(24)
            
            header_rest = struct.unpack('<Iiiiii', f.read(24))
            num_components = header_rest[0]
            pose_data_align = header_rest[1]
            pose_data_size = header_rest[2]
            components_offs = header_rest[3]
            per_skel_data_int_offs = header_rest[4]
            default_pose_offsets_offs = header_rest[5]

            self.result["header"].update({
                "num_components": int(num_components),
                "pose_data_align": int(pose_data_align),
                "pose_data_size": int(pose_data_size),
                "components_offs": int(components_offs),
                "per_skel_data_int_offs": int(per_skel_data_int_offs),
                "default_pose_offsets_offs": int(default_pose_offsets_offs),
            })

            component_meta = []
            component_records = {}

            if num_components > 0 and components_offs > 0:
                f.seek(components_offs)
                for slot_ix in range(num_components):
                    c_idx, c_type, c_flags = struct.unpack('<iIi', f.read(12))
                    component_meta.append({'index': c_idx, 'type': c_type, 'flags': c_flags})

                    type_name = "Unknown"
                    if c_type in list(NalComponentType):
                        type_name = NalComponentType(c_type).name

                    component_records[int(slot_ix)] = {
                        "component_index": int(slot_ix),
                        "component_name_id": int(c_idx),
                        "component_flags": int(c_flags),
                        "type_id": int(c_type),
                        "type_name": type_name,
                    }

            self.result["component_meta"] = component_meta

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
                        elif comp_type == NalComponentType.LegsFeet_Compressed:
                            data = self.parse_legs_compressed(f)
                        elif comp_type == NalComponentType.FiveFinger_Top2KnuckleCurl:
                            data = self.parse_five_finger(f)
                        elif comp_type in (
                            NalComponentType.FiveFinger_IndividualCurl,
                            NalComponentType.FiveFinger_ReducedAngular,
                            NalComponentType.FiveFinger_FullRotational,
                        ):
                            data = self.parse_five_finger(f)
                        elif comp_type == NalComponentType.FakerootEntropyCompressed:
                            data = self.parse_fakeroot_per_skel(f)
                        elif comp_type == NalComponentType.Tentacles_Compressed:
                            data = self.parse_tentacles_per_skel(f)
                        elif comp_type == NalComponentType.ArbitraryPO:
                            data = self.parse_arbitrary_po(f, comp_block_start)

                        if data:
                            rec = component_records.get(int(comp_idx), {
                                "component_index": int(comp_idx),
                                "component_name_id": int(meta.get("index", comp_idx)),
                                "component_flags": int(meta.get("flags", 0)),
                                "type_id": int(comp_type),
                                "type_name": NalComponentType(comp_type).name if comp_type in list(NalComponentType) else "Unknown",
                            })
                            rec.update(data)
                            component_records[int(comp_idx)] = rec

            if default_pose_offsets_offs > 0 and num_components > 0:
                try:
                    f.seek(default_pose_offsets_offs)
                    num_pose_blocks = struct.unpack('<i', f.read(4))[0]
                    if 0 < num_pose_blocks < 4096:
                        pose_offsets = list(struct.unpack(f'<{num_pose_blocks}I', f.read(4 * num_pose_blocks)))
                        total_pose_bytes = int(pose_data_size)
                        max_pose_offset = int(pose_offsets[-1]) if pose_offsets else 0

                        if total_pose_bytes <= 0:
                            total_pose_bytes = max_pose_offset
                        elif max_pose_offset > total_pose_bytes:
                            total_pose_bytes = max_pose_offset

                        file_size = os.fstat(f.fileno()).st_size
                        max_available = max(0, int(file_size - default_pose_offsets_offs))
                        if total_pose_bytes <= 0 or total_pose_bytes > max_available:
                            total_pose_bytes = max_available

                        if total_pose_bytes > 0:
                            f.seek(default_pose_offsets_offs)
                            pose_blob = f.read(total_pose_bytes)

                            self.result["default_pose_layout"] = {
                                "num_pose_blocks": int(num_pose_blocks),
                                "pose_offsets": [int(v) for v in pose_offsets],
                                "pose_blob_size": int(total_pose_bytes),
                            }

                            default_poses = self._parse_default_poses(
                                component_meta=component_meta,
                                pose_offsets=pose_offsets,
                                pose_blob=pose_blob,
                            )
                            self.result["default_poses"] = default_poses

                            for cix, pose in default_poses.items():
                                rec = component_records.get(int(cix), {
                                    "component_index": int(cix),
                                    "component_name_id": -1,
                                    "component_flags": 0,
                                    "type_id": int(pose.get("component_type", 0)),
                                    "type_name": "Unknown",
                                })
                                rec["default_pose"] = pose
                                component_records[int(cix)] = rec
                except Exception as e:
                    self.result["warnings"].append(f"Default pose parse failed: {e}")

            if component_records:
                self.result["components"] = [
                    component_records[idx]
                    for idx in sorted(component_records.keys())
                ]

        return self.result

    def _parse_generic_skeleton(self, f):
        generic_header = struct.unpack('<14I', f.read(56))
        field_64 = int(generic_header[7])
        field_6c = int(generic_header[9])
        node_count = int(generic_header[11])
        component_record_count = int(generic_header[13])

        data_region_off = 0xE0
        node_record_size = 48
        component_record_size = 40
        lookup_a_off = data_region_off
        lookup_b_off = lookup_a_off + field_64
        node_records_off = (lookup_b_off + field_6c + 3) & ~3
        component_records_off = (node_records_off + node_record_size * node_count + 3) & ~3
        file_size = os.fstat(f.fileno()).st_size

        self.result["header"].update({
            "generic_lookup_a_size": int(field_64),
            "generic_lookup_b_size": int(field_6c),
            "generic_node_count": int(node_count),
            "generic_component_record_count": int(component_record_count),
        })
        self.result["generic_layout"] = {
            "data_region_off": int(data_region_off),
            "lookup_a_off": int(lookup_a_off),
            "lookup_b_off": int(lookup_b_off),
            "node_records_off": int(node_records_off),
            "component_records_off": int(component_records_off),
        }

        nodes = []
        for node_ix in range(node_count):
            record_off = node_records_off + node_ix * node_record_size
            if record_off < 0 or record_off + node_record_size > file_size:
                self.result["warnings"].append(
                    f"Generic node table truncated at record {node_ix} (offset 0x{record_off:X})"
                )
                break
            f.seek(record_off)
            name_hash, name = read_fixed_string(f)
            kind, pose_offset, data_offset, parent_index = struct.unpack('<iiii', f.read(16))
            nodes.append({
                "node_index": int(node_ix),
                "name_hash": int(name_hash),
                "name": name,
                "kind": int(kind),
                "pose_offset": int(pose_offset),
                "data_offset": int(data_offset),
                "parent_index": int(parent_index),
            })
        self.result["generic_nodes"] = nodes

        blob = Path(self.filepath).read_bytes()
        lookup_info = self._parse_generic_lookup_a(blob, lookup_a_off, field_64)
        lookup_summary = self._summarize_generic_lookup_a(nodes, lookup_info)
        self.result["generic_lookup_a_counts"] = lookup_info["counts"]
        self.result["generic_lookup_a_ops"] = lookup_info["ops"]
        self.result["generic_lookup_a_unsupported_ops"] = lookup_info["unsupported_ops"]
        self.result["generic_lookup_a_supported"] = bool(lookup_summary["supports_direct_local_pose"])
        self.result["generic_lookup_b_bytes"] = blob[lookup_b_off : lookup_b_off + field_6c]
        self.result["generic_matrix_parent_pairs"] = lookup_summary["parent_pairs"]
        self.result["generic_matrix_target_modes"] = lookup_summary["target_modes"]

        generic_components = []
        for comp_ix in range(component_record_count):
            record_off = component_records_off + comp_ix * component_record_size
            if record_off < 0 or record_off + 40 > file_size:
                self.result["warnings"].append(
                    f"Generic component table truncated at record {comp_ix} (offset 0x{record_off:X})"
                )
                break
            f.seek(record_off)
            name_hash, name = read_fixed_string(f)
            target_index, flags = struct.unpack('<ii', f.read(8))
            generic_components.append({
                "component_index": int(comp_ix),
                "name_hash": int(name_hash),
                "name": name,
                "target_index": int(target_index),
                "flags": int(flags),
            })
        self.result["generic_components"] = generic_components
        info_blocks, info_entries = self._parse_generic_component_infos(
            component_records_off=component_records_off,
            component_record_count=component_record_count,
            generic_components=generic_components,
        )
        self.result["generic_component_info_blocks"] = info_blocks
        self.result["generic_component_infos"] = info_entries
        scalar_tail_off, scalar_tail, scalar_layout = self._parse_generic_scalar_tail(
            info_blocks=info_blocks,
            info_entries=info_entries,
        )
        self.result["generic_scalar_tail_off"] = int(scalar_tail_off)
        self.result["generic_scalar_tail"] = scalar_tail
        self.result["generic_scalar_layout"] = scalar_layout

        self._build_generic_playback_contract(
            nodes=nodes,
            generic_components=generic_components,
            info_entries=info_entries,
            scalar_layout=scalar_layout,
        )

    def _parse_generic_lookup_a(self, blob, lookup_a_off, lookup_a_size):
        op_defs = {
            0: ("copy_translation", 1),
            1: ("copy_rotation", 1),
            2: ("copy_transform", 1),
            3: ("scale_axes", 1),
            5: ("ik_solve", 18),
            12: ("local_to_world", 2),
            14: ("skip_bytes", 1),
        }
        end = int(lookup_a_off) + int(lookup_a_size)
        cursor = int(lookup_a_off)
        ops = []
        counts = {}
        unsupported_ops = []
        parse_ok = True

        while cursor < end:
            op_off = int(cursor)
            op_byte = int(blob[cursor])
            cursor += 1
            source = "pose" if op_byte < 0x80 else "default"
            opcode = op_byte & 0x7F
            op_info = op_defs.get(opcode)
            if op_info is None:
                parse_ok = False
                unsupported_ops.append({
                    "offset": int(op_off),
                    "source": source,
                    "opcode": int(opcode),
                    "op_name": "unknown",
                })
                break

            op_name, arg_len = op_info
            if cursor + arg_len > end:
                parse_ok = False
                unsupported_ops.append({
                    "offset": int(op_off),
                    "source": source,
                    "opcode": int(opcode),
                    "op_name": op_name,
                    "error": "truncated",
                })
                break

            args = [int(v) for v in blob[cursor : cursor + arg_len]]
            cursor += arg_len
            counts_key = f"{source}:{op_name}"
            counts[counts_key] = int(counts.get(counts_key, 0) + 1)
            ops.append({
                "offset": int(op_off),
                "source": source,
                "opcode": int(opcode),
                "op_name": op_name,
                "args": args,
            })
            if opcode not in (0, 1, 2, 12):
                unsupported_ops.append({
                    "offset": int(op_off),
                    "source": source,
                    "opcode": int(opcode),
                    "op_name": op_name,
                })

        return {
            "parse_ok": bool(parse_ok),
            "ops": ops,
            "counts": counts,
            "unsupported_ops": unsupported_ops,
        }

    def _summarize_generic_lookup_a(self, nodes, lookup_info):
        nodes_by_index = {int(node.get("node_index", -1)): node for node in nodes}
        target_modes = {
            int(node_ix): {
                "target_index": int(node_ix),
                "target_name": str(node.get("name", f"Bone_{int(node_ix)}")),
                "translation_source": "none",
                "translation_op": "none",
                "rotation_source": "none",
                "rotation_op": "none",
            }
            for node_ix, node in nodes_by_index.items()
        }
        parent_pairs = []
        supports_direct_local_pose = bool(lookup_info.get("parse_ok", False)) and not lookup_info.get("unsupported_ops")

        for op in list(lookup_info.get("ops", ())):
            op_name = str(op.get("op_name", ""))
            source = str(op.get("source", "pose"))
            args = [int(v) for v in list(op.get("args", ()))]
            if op_name == "copy_translation" and args:
                target_ix = int(args[0])
                target = target_modes.setdefault(
                    target_ix,
                    {
                        "target_index": int(target_ix),
                        "target_name": str(nodes_by_index.get(target_ix, {}).get("name", f"Bone_{target_ix}")),
                        "translation_source": "none",
                        "translation_op": "none",
                        "rotation_source": "none",
                        "rotation_op": "none",
                    },
                )
                target["translation_source"] = source
                target["translation_op"] = op_name
            elif op_name == "copy_rotation" and args:
                target_ix = int(args[0])
                target = target_modes.setdefault(
                    target_ix,
                    {
                        "target_index": int(target_ix),
                        "target_name": str(nodes_by_index.get(target_ix, {}).get("name", f"Bone_{target_ix}")),
                        "translation_source": "none",
                        "translation_op": "none",
                        "rotation_source": "none",
                        "rotation_op": "none",
                    },
                )
                target["rotation_source"] = source
                target["rotation_op"] = op_name
            elif op_name == "copy_transform" and args:
                target_ix = int(args[0])
                target = target_modes.setdefault(
                    target_ix,
                    {
                        "target_index": int(target_ix),
                        "target_name": str(nodes_by_index.get(target_ix, {}).get("name", f"Bone_{target_ix}")),
                        "translation_source": "none",
                        "translation_op": "none",
                        "rotation_source": "none",
                        "rotation_op": "none",
                    },
                )
                target["translation_source"] = source
                target["translation_op"] = op_name
                target["rotation_source"] = source
                target["rotation_op"] = op_name
            elif op_name == "local_to_world" and len(args) == 2:
                parent_pairs.append({
                    "parent_index": int(args[0]),
                    "child_index": int(args[1]),
                    "parent_name": str(nodes_by_index.get(int(args[0]), {}).get("name", f"Bone_{int(args[0])}")),
                    "child_name": str(nodes_by_index.get(int(args[1]), {}).get("name", f"Bone_{int(args[1])}")),
                })

        return {
            "supports_direct_local_pose": bool(supports_direct_local_pose),
            "parent_pairs": parent_pairs,
            "target_modes": [target_modes[idx] for idx in sorted(target_modes)],
        }
    
    def _parse_generic_component_infos(self, component_records_off, component_record_count, generic_components):
        blob = Path(self.filepath).read_bytes()
        file_size = len(blob)
        scan_off = (component_records_off + component_record_count * 40 + 3) & ~3

        known_encodings = {
            0x6359B214: ("nal_entropyfloat3", 12, "<3f"),
            0xD4D958C0: ("nal_packed16entropyquaternion", 16, "<4f"),
            0xAD61B94C: ("nal_entropypositionorientation", 28, "<7f"),
            0x07FFCAF3: ("nal_entropytrajectorypositionorientation", 28, "<7f"),
            0x6359B212: ("nal_entropyfloat1", 4, "<f"),
            0x9427FDF7: ("usmevent", 4, "<I"),
        }

        def parse_record(off):
            if off < 0 or off + 48 > file_size:
                return None
            name_hash = struct.unpack_from("<I", blob, off)[0]
            info = known_encodings.get(int(name_hash))
            if info is None:
                return None
            raw_name = blob[off + 4 : off + 32].split(b"\x00", 1)[0].decode("latin-1", errors="ignore")
            unk0, comp_base, comp_count, data_offset = struct.unpack_from("<IIII", blob, off + 32)
            if unk0 != 0 or comp_count <= 0:
                return None
            if comp_base + comp_count > component_record_count:
                return None
            return {
                "off": int(off),
                "name_hash": int(name_hash),
                "encoding_name": info[0],
                "raw_name": raw_name,
                "unk0": int(unk0),
                "component_index_base": int(comp_base),
                "component_count": int(comp_count),
                "data_offset": int(data_offset),
                "elem_size": int(info[1]),
                "fmt": info[2],
            }

        records = []
        off = scan_off
        while off + 48 <= file_size:
            rec = parse_record(off)
            if rec is None:
                off += 4
                continue
            records.append(rec)
            off += 48

        if not records:
            return [], []

        blocks = []
        current = [records[0]]
        for rec in records[1:]:
            if rec["off"] == current[-1]["off"] + 48:
                current.append(rec)
                continue
            blocks.append(current)
            current = [rec]
        blocks.append(current)

        out_blocks = []
        out_infos = []
        for block in blocks:
            block_start = int(block[0]["off"])
            block_data_base = block_start + 48 * len(block)
            block_out = {
                "info_off": block_start,
                "data_base_off": int(block_data_base),
                "count": int(len(block)),
                "encodings": [],
            }
            for rec in block:
                data_off = block_data_base + int(rec["data_offset"])
                target_slice = generic_components[rec["component_index_base"] : rec["component_index_base"] + rec["component_count"]]
                values = []
                elem_size = int(rec["elem_size"])
                fmt = rec["fmt"]
                for idx in range(int(rec["component_count"])):
                    entry_off = data_off + idx * elem_size
                    if entry_off < 0 or entry_off + elem_size > file_size:
                        break
                    raw_vals = struct.unpack_from(fmt, blob, entry_off)
                    if len(raw_vals) == 1:
                        values.append(float(raw_vals[0]) if fmt == "<f" else int(raw_vals[0]))
                    else:
                        values.append(tuple(float(v) for v in raw_vals))
                info_out = {
                    "info_off": int(rec["off"]),
                    "data_off": int(data_off),
                    "encoding_name": rec["encoding_name"],
                    "raw_name": rec["raw_name"],
                    "name_hash": int(rec["name_hash"]),
                    "component_index_base": int(rec["component_index_base"]),
                    "component_count": int(rec["component_count"]),
                    "data_offset": int(rec["data_offset"]),
                    "elem_size": int(elem_size),
                    "target_indices": [int(comp.get("target_index", -1)) for comp in target_slice],
                    "component_indices": [int(comp.get("component_index", -1)) for comp in target_slice],
                    "default_values": values,
                }
                block_out["encodings"].append(info_out)
                out_infos.append(info_out)
            out_blocks.append(block_out)

        return out_blocks, out_infos


    def _parse_generic_scalar_tail(self, info_blocks, info_entries):
        blob = Path(self.filepath).read_bytes()
        file_size = len(blob)
        if not info_blocks:
            return 0, [], []

        tail_start = 0
        for block in info_blocks:
            for info in block.get("encodings", []):
                data_off = int(info.get("data_off", 0))
                elem_size = int(info.get("elem_size", 0))
                comp_count = int(info.get("component_count", 0))
                tail_start = max(tail_start, data_off + elem_size * comp_count)

        if tail_start <= 0 or tail_start >= file_size:
            return 0, [], []

        tail_bytes = blob[tail_start:]
        scalar_count = len(tail_bytes) // 4
        scalar_tail = [
            float(v)
            for v in struct.unpack_from(f"<{scalar_count}f", tail_bytes, 0)
        ]

        layout = []
        cursor = 0
        for info in info_entries:
            enc_name = str(info.get("encoding_name", ""))
            comp_count = int(info.get("component_count", 0))
            if enc_name in ("nal_entropypositionorientation", "nal_entropytrajectorypositionorientation"):
                scalar_width = 2
            elif enc_name in ("nal_entropyfloat3", "nal_packed16entropyquaternion", "nal_entropyfloat1"):
                scalar_width = 1
            else:
                continue
            total = comp_count * scalar_width
            layout.append({
                "encoding_name": enc_name,
                "component_index_base": int(info.get("component_index_base", 0)),
                "component_count": comp_count,
                "scalar_width": scalar_width,
                "scalar_start": int(cursor),
                "scalar_end": int(cursor + total),
                "values": scalar_tail[cursor : cursor + total],
            })
            cursor += total

        return int(tail_start), scalar_tail, layout


    def _make_generic_handle_key(self, target_name, component_name):
        target_key = _normalize_generic_lookup_name(target_name)
        component_key = _normalize_generic_lookup_name(component_name)
        if not target_key or not component_key:
            return ""
        return f"{target_key}::{component_key}"

    def _infer_generic_handle_contract(self, target_name, component_name, encoding_name):
        handle_info = _GENERIC_RUNTIME_HANDLE_ACCESS.get(
            (_normalize_generic_lookup_name(target_name), _normalize_generic_lookup_name(component_name))
        )
        value_type = _GENERIC_VALUE_TYPE_BY_ENCODING.get(str(encoding_name), "unknown")
        if handle_info is None:
            return value_type, "unknown"
        return str(handle_info[0]), str(handle_info[1])

    def _build_generic_playback_contract(self, nodes, generic_components, info_entries, scalar_layout):
        target_records = []
        target_by_index = {}
        target_name_to_index = {}
        known_node_ids = set()

        for node in nodes:
            node_ix = int(node.get("node_index", -1))
            name = str(node.get("name", "")).strip()
            if node_ix < 0 or not name:
                continue

            is_helper = name in _GENERIC_HELPER_NODE_NAMES
            target_record = {
                "node_index": int(node_ix),
                "name": name,
                "name_key": _normalize_generic_lookup_name(name),
                "parent_index": int(node.get("parent_index", -1)),
                "node_kind": int(node.get("kind", 0)),
                "pose_offset": int(node.get("pose_offset", 0)),
                "data_offset": int(node.get("data_offset", 0)),
                "is_helper": bool(is_helper),
                "target_kind": "helper" if is_helper else "bind",
                "imports_to_blender": True,
            }
            target_records.append(target_record)
            target_by_index[node_ix] = target_record
            if target_record["name_key"] and target_record["name_key"] not in target_name_to_index:
                target_name_to_index[target_record["name_key"]] = int(node_ix)
            if is_helper:
                self.component_bone_names[node_ix] = name
            else:
                self.bone_map[node_ix] = name
            known_node_ids.add(node_ix)

        for target_record in target_records:
            node_ix = int(target_record.get("node_index", -1))
            parent_index = int(target_record.get("parent_index", -1))
            self.parent_map[node_ix] = parent_index if parent_index in known_node_ids else -1

        summary = {}
        summary_order = []
        for comp in generic_components:
            name = str(comp.get("name", "")).strip() or "Unknown"
            if name not in summary:
                summary[name] = {
                    "name": name,
                    "count": 0,
                    "target_indices": [],
                    "target_names": [],
                }
                summary_order.append(name)
            entry = summary[name]
            target_ix = int(comp.get("target_index", -1))
            target_name = str(target_by_index.get(target_ix, {}).get("name", f"Bone_{target_ix}"))
            entry["count"] += 1
            entry["target_indices"].append(target_ix)
            entry["target_names"].append(target_name)
        self.result["generic_component_summary"] = [summary[name] for name in summary_order]

        scalar_by_base = {
            int(entry.get("component_index_base", -1)): entry
            for entry in scalar_layout
        }
        matrix_mode_by_target = {
            int(entry.get("target_index", -1)): entry
            for entry in self.result.get("generic_matrix_target_modes", [])
        }

        family_records = []
        handle_map = {}
        runtime_handles = []
        for info in info_entries:
            encoding_name = str(info.get("encoding_name", "Unknown"))
            comp_base = int(info.get("component_index_base", 0))
            comp_count = int(info.get("component_count", 0))
            scalar_entry = scalar_by_base.get(comp_base)
            scalar_width = int((scalar_entry or {}).get("scalar_width", 0) or 0)
            scalar_values = list((scalar_entry or {}).get("values", []))
            default_values = list(info.get("default_values", []))
            target_indices = [int(v) for v in info.get("target_indices", [])]
            component_indices = [int(v) for v in info.get("component_indices", [])]
            family_entries = []

            for local_ix in range(comp_count):
                component_ix = int(component_indices[local_ix]) if local_ix < len(component_indices) else int(comp_base + local_ix)
                target_ix = int(target_indices[local_ix]) if local_ix < len(target_indices) else -1
                component = generic_components[component_ix] if 0 <= component_ix < len(generic_components) else {}
                target_record = target_by_index.get(target_ix, {})
                target_name = str(target_record.get("name", f"Bone_{target_ix}"))
                component_name = str(component.get("name", "")).strip()
                handle_key = self._make_generic_handle_key(target_name, component_name)
                value_type, handle_access = self._infer_generic_handle_contract(
                    target_name,
                    component_name,
                    encoding_name,
                )

                component_scalar_values = []
                if scalar_width > 0:
                    scalar_start = local_ix * scalar_width
                    scalar_end = scalar_start + scalar_width
                    component_scalar_values = list(scalar_values[scalar_start:scalar_end])

                target_matrix_mode = matrix_mode_by_target.get(int(target_ix), {})
                component_entry = {
                    "component_index": int(component_ix),
                    "component_name": component_name,
                    "component_key": _normalize_generic_lookup_name(component_name),
                    "component_flags": int(component.get("flags", 0)),
                    "target_index": int(target_ix),
                    "target_name": target_name,
                    "target_key": _normalize_generic_lookup_name(target_name),
                    "target_is_helper": bool(target_record.get("is_helper", False)),
                    "target_kind": str(target_record.get("target_kind", "unknown")),
                    "parent_index": int(target_record.get("parent_index", -1)),
                    "encoding_name": encoding_name,
                    "value_type": value_type,
                    "handle_access": handle_access,
                    "default_value": default_values[local_ix] if local_ix < len(default_values) else None,
                    "scalar_values": component_scalar_values,
                    "handle_key": handle_key,
                    "matrix_translation_source": str(target_matrix_mode.get("translation_source", "unknown")),
                    "matrix_translation_op": str(target_matrix_mode.get("translation_op", "unknown")),
                    "matrix_rotation_source": str(target_matrix_mode.get("rotation_source", "unknown")),
                    "matrix_rotation_op": str(target_matrix_mode.get("rotation_op", "unknown")),
                }
                family_entries.append(component_entry)

                if handle_key and handle_key not in handle_map:
                    handle_record = {
                        "target_index": int(target_ix),
                        "target_name": target_name,
                        "target_is_helper": bool(target_record.get("is_helper", False)),
                        "target_kind": str(target_record.get("target_kind", "unknown")),
                        "parent_index": int(target_record.get("parent_index", -1)),
                        "component_index": int(component_ix),
                        "component_name": component_name,
                        "component_flags": int(component.get("flags", 0)),
                        "encoding_name": encoding_name,
                        "value_type": value_type,
                        "handle_access": handle_access,
                        "default_value": component_entry["default_value"],
                        "scalar_values": component_scalar_values,
                        "matrix_translation_source": component_entry["matrix_translation_source"],
                        "matrix_translation_op": component_entry["matrix_translation_op"],
                        "matrix_rotation_source": component_entry["matrix_rotation_source"],
                        "matrix_rotation_op": component_entry["matrix_rotation_op"],
                    }
                    handle_map[handle_key] = handle_record
                    if handle_access != "unknown":
                        runtime_handles.append(handle_record)

            family_records.append({
                "encoding_name": encoding_name,
                "component_index_base": int(comp_base),
                "component_count": int(comp_count),
                "info_off": int(info.get("info_off", 0)),
                "data_off": int(info.get("data_off", 0)),
                "value_type": _GENERIC_VALUE_TYPE_BY_ENCODING.get(encoding_name, "unknown"),
                "entries": family_entries,
            })

        self.result["generic_targets"] = target_records
        self.result["generic_target_name_to_index"] = target_name_to_index
        self.result["generic_playback_families"] = family_records
        self.result["generic_handle_map"] = handle_map
        self.result["generic_runtime_handles"] = runtime_handles


    def _get_pose_index_for_comp_index(self, component_meta, comp_index):
        if comp_index < 0 or comp_index >= len(component_meta):
            return -1
        if int(component_meta[comp_index].get('flags', 0)) & int(ComponentFlags.HAS_TRACK_DATA):
            return -1

        pose_ix = -1
        for i in range(comp_index + 1):
            if (int(component_meta[i].get('flags', 0)) & int(ComponentFlags.HAS_TRACK_DATA)) == 0:
                pose_ix += 1
        return pose_ix

    def _parse_default_pose_bytes(self, comp_type, pose_bytes):
        def unpack_quat_list(blob, count):
            vals = struct.unpack(f'<{count * 4}f', blob[: count * 16])
            out = []
            for i in range(count):
                x, y, z, w = vals[i * 4 : i * 4 + 4]
                out.append((float(w), float(x), float(y), float(z)))
            return out

        comp_type = int(comp_type)

        if comp_type in (int(NalComponentType.TorsoHead_TwoNeck_Compressed), int(NalComponentType.TorsoHead_OneNeck_Compressed)):
            if len(pose_bytes) < 112:
                return None
            quats = unpack_quat_list(pose_bytes, 6)
            px, py, pz = struct.unpack('<3f', pose_bytes[96:108])
            return {
                'kind': 'torso_pose',
                'quats': quats,
                'pelvis_pos': (float(px), float(py), float(pz)),
            }

        if comp_type == int(NalComponentType.LegsFeet_IK_Compressed):
            if len(pose_bytes) < 96:
                return None
            quats = unpack_quat_list(pose_bytes, 4)
            lx, ly, lz, rx, ry, rz = struct.unpack('<6f', pose_bytes[64:88])
            lk, rk = struct.unpack('<2f', pose_bytes[88:96])
            return {
                'kind': 'legs_ik_pose',
                'quats': quats,
                'foot_pos': ((float(lx), float(ly), float(lz)), (float(rx), float(ry), float(rz))),
                'knee_spin': (float(lk), float(rk)),
            }

        if comp_type == int(NalComponentType.LegsFeet_Compressed):
            if len(pose_bytes) >= 128:
                quats = unpack_quat_list(pose_bytes, 8)
            elif len(pose_bytes) >= 64:
                quats = unpack_quat_list(pose_bytes, 4)
            else:
                return None
            return {
                'kind': 'legs_pose',
                'quats': quats,
            }

        if comp_type == int(NalComponentType.ArmsHands_Compressed):
            if len(pose_bytes) < 128:
                return None
            quats = unpack_quat_list(pose_bytes, 8)
            return {
                'kind': 'arms_pose',
                'quats': quats,
            }

        if comp_type == int(NalComponentType.ArmsHands_IK_Compressed):
            if len(pose_bytes) < 96:
                return None
            q_tracks = unpack_quat_list(pose_bytes, 2)
            q_hands = unpack_quat_list(pose_bytes[32:], 2)
            lx, ly, lz, rx, ry, rz = struct.unpack('<6f', pose_bytes[64:88])
            ls, rs = struct.unpack('<2f', pose_bytes[88:96])
            return {
                'kind': 'arms_ik_pose',
                'track_quats': q_tracks,
                'hand_quats': q_hands,
                'hand_pos': ((float(lx), float(ly), float(lz)), (float(rx), float(ry), float(rz))),
                'elbow_spin': (float(ls), float(rs)),
            }

        if comp_type == int(NalComponentType.FakerootEntropyCompressed):
            if len(pose_bytes) < 48:
                return None
            q = unpack_quat_list(pose_bytes, 1)[0]
            px, py, pz, floor = struct.unpack('<4f', pose_bytes[16:32])
            sig_start, sig_count = struct.unpack('<2I', pose_bytes[32:40])
            return {
                'kind': 'fakeroot_pose',
                'quat': q,
                'pos': (float(px), float(py), float(pz)),
                'floor_offset': float(floor),
                'signal_start': int(sig_start),
                'num_signals': int(sig_count),
            }

        if comp_type == int(NalComponentType.Tentacles_Compressed):
            if len(pose_bytes) < 60:
                return None
            vals = struct.unpack('<15f', pose_bytes[:60])
            return {
                'kind': 'tentacles_pose',
                'values': [float(v) for v in vals],
            }

        if comp_type == int(NalComponentType.ArbitraryPO):
            if len(pose_bytes) < 16:
                return None
            quat_count, total_count, field_8, field_C = struct.unpack('<4I', pose_bytes[:16])
            quat_count = int(quat_count)
            total_count = int(total_count)
            if quat_count < 0 or total_count < quat_count:
                return None
            position_count = total_count - quat_count
            expected_size = 16 + quat_count * 16 + position_count * 12
            if expected_size > len(pose_bytes):
                return None
            quats = unpack_quat_list(pose_bytes[16:], quat_count) if quat_count > 0 else []
            positions = []
            pos_off = 16 + quat_count * 16
            for i in range(position_count):
                px, py, pz = struct.unpack_from('<3f', pose_bytes, pos_off + i * 12)
                positions.append((float(px), float(py), float(pz)))
            return {
                'kind': 'arbitrary_po_pose',
                'quat_count': quat_count,
                'total_count': total_count,
                'position_count': position_count,
                'field_8': int(field_8),
                'field_C': int(field_C),
                'quats': quats,
                'positions': positions,
            }

        if comp_type == int(NalComponentType.FiveFinger_Top2KnuckleCurl):
            if len(pose_bytes) < 192:
                return None
            thumb_quats = unpack_quat_list(pose_bytes, 2)
            packed_tracks = struct.unpack('<34f', pose_bytes[:136])
            other = struct.unpack('<10f', pose_bytes[144:184])
            available_tracks = struct.unpack('<I', pose_bytes[184:188])[0]
            return {
                'kind': 'fing52_pose',
                'thumb_quats': thumb_quats,
                'base_y_tracks': [float(v) for v in packed_tracks[8:16]],
                'base_z_tracks': [float(v) for v in packed_tracks[16:24]],
                'hinge_tracks': [float(v) for v in packed_tracks[24:34]],
                'other_tracks': [float(v) for v in other],
                'available_tracks': int(available_tracks),
            }

        if comp_type == int(NalComponentType.FiveFinger_ReducedAngular):
            if len(pose_bytes) < 176:
                return None
            quats = unpack_quat_list(pose_bytes, 11)
            return {
                'kind': 'fing5_reduced_pose',
                'quats': quats,
            }

        if comp_type == int(NalComponentType.FiveFinger_IndividualCurl):
            if len(pose_bytes) < 112:
                return None
            quats = unpack_quat_list(pose_bytes, 4)
            curls = struct.unpack('<10f', pose_bytes[64:104])
            return {
                'kind': 'fing5_curl_pose',
                'quats': quats,
                'finger_curl': [float(v) for v in curls],
            }

        if comp_type == int(NalComponentType.FiveFinger_FullRotational):
            if len(pose_bytes) < 480:
                return None
            quats = unpack_quat_list(pose_bytes, 30)
            return {
                'kind': 'fing5_full_pose',
                'quats': quats,
            }

        return None

    def _parse_default_poses(self, component_meta, pose_offsets, pose_blob):
        def expected_pose_size(comp_type):
            comp_type = int(comp_type)
            size_map = {
                int(NalComponentType.TorsoHead_TwoNeck_Compressed): 112,
                int(NalComponentType.TorsoHead_OneNeck_Compressed): 112,
                int(NalComponentType.LegsFeet_Compressed): 128,
                int(NalComponentType.LegsFeet_IK_Compressed): 96,
                int(NalComponentType.ArmsHands_Compressed): 128,
                int(NalComponentType.ArmsHands_IK_Compressed): 96,
                int(NalComponentType.FakerootEntropyCompressed): 48,
                int(NalComponentType.Tentacles_Compressed): 60,
                int(NalComponentType.FiveFinger_Top2KnuckleCurl): 192,
                int(NalComponentType.FiveFinger_ReducedAngular): 176,
                int(NalComponentType.FiveFinger_IndividualCurl): 112,
                int(NalComponentType.FiveFinger_FullRotational): 480,
            }
            return int(size_map.get(comp_type, 0))

        def infer_end_from_offsets(start, offsets, total_size):
            higher = [int(v) for v in offsets if int(v) > int(start)]
            if higher:
                return min(higher)
            return int(total_size)

        default_poses = {}
        num_pose_blocks = len(pose_offsets)
        total_pose_bytes = len(pose_blob)

        for comp_ix, meta in enumerate(component_meta):
            pose_ix = self._get_pose_index_for_comp_index(component_meta, comp_ix)
            if pose_ix < 0 or pose_ix >= num_pose_blocks:
                continue

            start = int(pose_offsets[pose_ix])
            expected = expected_pose_size(meta.get('type', 0))
            if expected > 0:
                end = start + expected
            else:
                end = infer_end_from_offsets(start, pose_offsets, total_pose_bytes)

            if start < 0 or end <= start or end > total_pose_bytes:
                continue

            pose_bytes = pose_blob[start:end]
            parsed = self._parse_default_pose_bytes(meta.get('type', 0), pose_bytes)
            if parsed is None:
                continue

            parsed['component_index'] = int(comp_ix)
            parsed['component_type'] = int(meta.get('type', 0))
            parsed['raw_size'] = int(len(pose_bytes))
            default_poses[int(comp_ix)] = parsed

        return default_poses

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
        bone_ixs = struct.unpack('<6i', f.read(24))
        other_matrix_ixs = struct.unpack('<i', f.read(4))[0]

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
        bone_ixs = struct.unpack('<8i', f.read(32))
        other_matrix_ixs = struct.unpack('<i', f.read(4))[0]
        
        self._map_bones(bone_ixs, LegsBones, 8)

        return {
            "offset_locs": offset_locs,
            "ik_data": ik_data,
            "bone_indices": bone_ixs,
            "other_matrix_indices": [other_matrix_ixs]
        }

    def parse_legs_compressed(self, f):
        vectors = [read_vec4(f) for _ in range(9)]
        bone_ixs = struct.unpack('<9i', f.read(36))

        flat = [float(c) for v in vectors for c in v]
        offset_locs = []
        if len(flat) >= 24:
            offset_locs = [tuple(flat[i * 3 : i * 3 + 3]) for i in range(8)]

        other_matrix_ixs = [int(bone_ixs[8])] if len(bone_ixs) >= 9 else []

        self._map_bones(bone_ixs, LegsBones, 9)

        return {
            "vectors": vectors,
            "offset_locs": offset_locs,
            "bone_indices": bone_ixs,
            "other_matrix_indices": other_matrix_ixs,
        }

    def parse_arms_hands_compressed(self, f):
        vectors = [read_vec4(f) for _ in range(9)]
        bone_ixs = struct.unpack('<16i', f.read(64))

        flat = [float(c) for v in vectors for c in v]
        offset_locs = []
        fore_twist_locs = []
        if len(flat) >= 36:
            offset_locs = [tuple(flat[i * 3 : i * 3 + 3]) for i in range(8)]
            fore_twist_locs = [tuple(flat[24 + i * 3 : 24 + i * 3 + 3]) for i in range(4)]

        other_matrix_ixs = list(bone_ixs[8:13])

        self._map_bones(bone_ixs, ArmHandsCompressedBones, 13)

        return {
            "vectors": vectors,
            "offset_locs": offset_locs,
            "fore_twist_locs": fore_twist_locs,
            "bone_indices": bone_ixs,
            "other_matrix_indices": other_matrix_ixs,
        }

    def parse_arms_hands_ik(self, f):
        offset_locs = [read_vec3(f) for _ in range(8)]
        fore_twist_locs = [read_vec3(f) for _ in range(4)]
        ik_data = [read_ik_skel_data(f) for _ in range(2)]
        bone_ixs = struct.unpack('<8i', f.read(32))
        other_matrix_ixs = struct.unpack('<6i', f.read(24))
        
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
        bone_ixs = struct.unpack('<32i', f.read(128))

        flat = [float(c) for v in vectors for c in v]
        flat.extend((float(aa[0]), float(aa[1])))
        offset_locs = []
        if len(flat) >= 90:
            offset_locs = [tuple(flat[i * 3 : i * 3 + 3]) for i in range(30)]

        other_matrix_ixs = list(bone_ixs[30:32])
        
        self._map_bones(bone_ixs, FingerBones, 30)

        return {
            "vectors": vectors,
            "aa": aa,
            "offset_locs": offset_locs,
            "bone_indices": bone_ixs,
            "other_matrix_indices": other_matrix_ixs,
        }

    def parse_fakeroot_per_skel(self, f):
        del f
        return {
            "per_skel_present": True,
        }

    def parse_tentacles_per_skel(self, f):
        del f
        return {
            "per_skel_present": True,
        }

    def parse_arbitrary_po(self, f, block_start):
        data = struct.unpack('<8I', f.read(32))
        bone_count = int(data[0])
        quat_track_count = int(data[1])
        vector_track_count = int(data[2])
        layout_flags = int(data[3])
        quat_table_offset = int(data[4])
        position_table_offset = int(data[5])
        node_list_offset = int(data[6])
        node_order_offset = int(data[7])

        per_skel_quats = []
        if (
            quat_table_offset > 0
            and position_table_offset > quat_table_offset
            and ((position_table_offset - quat_table_offset) % 16) == 0
        ):
            f.seek(block_start + quat_table_offset)
            quat_blob = f.read(position_table_offset - quat_table_offset)
            for i in range(len(quat_blob) // 16):
                x, y, z, w = struct.unpack_from('<4f', quat_blob, i * 16)
                per_skel_quats.append((float(w), float(x), float(y), float(z)))

        per_skel_positions = []
        if (
            position_table_offset > 0
            and node_list_offset > position_table_offset
            and ((node_list_offset - position_table_offset) % 12) == 0
        ):
            f.seek(block_start + position_table_offset)
            pos_blob = f.read(node_list_offset - position_table_offset)
            for i in range(len(pos_blob) // 12):
                px, py, pz = struct.unpack_from('<3f', pos_blob, i * 12)
                per_skel_positions.append((float(px), float(py), float(pz)))

        node_order = []
        if node_order_offset > 0 and bone_count > 0:
            f.seek(block_start + node_order_offset)
            order_blob = f.read(bone_count * 4)
            if len(order_blob) == bone_count * 4:
                node_order = [int(v) for v in struct.unpack(f'<{bone_count}I', order_blob)]

        nodes = []
        node_list_abs = block_start + node_list_offset
        f.seek(node_list_abs)

        for _ in range(bone_count):
            node_data = f.read(48)
            _, node_name = struct.unpack('<I28s', node_data[:32])
            node_name_str = node_name.decode('latin-1').split('\x00')[0]

            quat_ix, pos_ix, my_matrix_ix, parent_matrix_ix = struct.unpack('<HHhh', node_data[32:40])
            use_std_pose_quat, use_std_pose_pos, runtime_flags = struct.unpack('<HHi', node_data[40:48])

            if node_name_str:
                self.bone_map[int(my_matrix_ix)] = node_name_str

            self.parent_map[int(my_matrix_ix)] = int(parent_matrix_ix)

            nodes.append({
                'name': node_name_str,
                'id': int(my_matrix_ix),
                'parent_id': int(parent_matrix_ix),
                'quat_index': int(quat_ix),
                'pos_index': int(pos_ix),
                'use_std_pose_quat': bool(use_std_pose_quat),
                'use_std_pose_pos': bool(use_std_pose_pos),
                'runtime_flags': int(runtime_flags),
                'indices': (int(quat_ix), int(pos_ix), int(my_matrix_ix), int(parent_matrix_ix)),
                'flags': (int(use_std_pose_quat), int(use_std_pose_pos), int(runtime_flags)),
            })

        return {
            'bone_count': bone_count,
            'quat_track_count': quat_track_count,
            'vector_track_count': vector_track_count,
            'layout_flags': layout_flags,
            'quat_table_offset': quat_table_offset,
            'position_table_offset': position_table_offset,
            'node_list_offset': node_list_offset,
            'node_order_offset': node_order_offset,
            'per_skel_quats': per_skel_quats,
            'per_skel_positions': per_skel_positions,
            'node_order': node_order,
            'nodes': nodes,
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
            other_id = int(other_ixs[0])
            if (
                other_id != -1
                and other_id in idx_to_bone
                and spine2_id in idx_to_bone
            ):
                idx_to_bone[other_id].parent = idx_to_bone[spine2_id]
                if t == NalComponentType.TorsoHead_TwoNeck_Compressed and neck_id in idx_to_bone:
                    idx_to_bone[neck_id].parent = idx_to_bone[other_id]
                
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

    has_legs_ik = False
    for comp in skel_data.get("components", []):
        if comp.get("type_id") != NalComponentType.LegsFeet_IK_Compressed:
            continue

        has_legs_ik = True

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

    if has_legs_ik:
        return

    for comp in skel_data.get("components", []):
        if comp.get("type_id") != NalComponentType.LegsFeet_Compressed:
            continue

        bone_ixs = comp.get("bone_indices", ())
        if len(bone_ixs) < 8:
            continue

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

        other_ixs = comp.get("other_matrix_indices", ())
        neck_parent_id = other_ixs[4] if len(other_ixs) > 4 else None

        clav_parent = None
        if neck_parent_id is not None and neck_parent_id in idx_to_bone:
            clav_parent = idx_to_bone[neck_parent_id]
        elif spine2_id is not None and spine2_id in idx_to_bone:
            clav_parent = idx_to_bone[spine2_id]

        if clav_parent is not None:
            if l_clav_id in idx_to_bone:
                idx_to_bone[l_clav_id].parent = clav_parent
            if r_clav_id in idx_to_bone:
                idx_to_bone[r_clav_id].parent = clav_parent

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
        if neck_parent_id in idx_to_bone:
            clav_parent = idx_to_bone[neck_parent_id]
        elif spine2_id is not None and spine2_id in idx_to_bone:
            clav_parent = idx_to_bone[spine2_id]

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
        if comp.get("type_id") not in (
            NalComponentType.FiveFinger_Top2KnuckleCurl,
            NalComponentType.FiveFinger_IndividualCurl,
            NalComponentType.FiveFinger_ReducedAngular,
            NalComponentType.FiveFinger_FullRotational,
        ):
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
