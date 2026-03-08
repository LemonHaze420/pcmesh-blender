import io
import json
import os
import struct

try:
    from .pcanim_codec import (
        PCANIMCodecError,
        _decode_component_frames,
        _get_num_bytes_for_comp,
        _get_num_tracks_for_comp,
        _has_track,
    )
except Exception:
    from pcanim_codec import (  # type: ignore
        PCANIMCodecError,
        _decode_component_frames,
        _get_num_bytes_for_comp,
        _get_num_tracks_for_comp,
        _has_track,
    )


ANIM_CONTAINER = 0x00010101
CHAR_ANIM = 0x00010003
GEN_ANIM = 0x00010200

FLAG_LOOPING = 0x00000001
FLAG_SCENE_ANIM = 0x00020000

HAS_TRACK_DATA = 0x1
HAS_PER_ANIM_DATA = 0x2


# iComponentID
COMP_ARBITRARY_PO = 0
COMP_GENERIC = 1
COMP_FAKEROOT_STD = 2
COMP_TORSO_HEAD = 3
COMP_TORSO_HEAD_STD = 4
COMP_LEGS = 5
COMP_LEGS_IK = 6
COMP_ARMS = 7
COMP_ARMS_IK = 8
COMP_TENTACLE = 9
COMP_FING52 = 10
COMP_FING5_CURL = 11
COMP_FING5_REDUCED = 12
COMP_FING5 = 13


# nalComponentType hashes
NAL_ARBITRARY_PO = 0xC5E45DCF
NAL_GENERIC = 0xEC4755BD
NAL_FAKEROOT = 0xB916E121
NAL_TORSO_TWO_NECK = 0x7E916D6A
NAL_TORSO_ONE_NECK = 0x70EA5DF2
NAL_LEGS = 0x47CBEBDB
NAL_LEGS_IK = 0xA556994F
NAL_ARMS = 0xE01F4F4D
NAL_ARMS_IK = 0xF0AD5C8E
NAL_TENTACLES = 0x464A04D8
NAL_FING52 = 0xE7D9A8D3
NAL_FING5_CURL = 0xE7A8F925
NAL_FING5_REDUCED = 0xE78254B9
NAL_FING5 = 0xAFEB6A28

NAL_TO_COMP_ID = {
    NAL_ARBITRARY_PO: COMP_ARBITRARY_PO,
    NAL_GENERIC: COMP_GENERIC,
    NAL_FAKEROOT: COMP_FAKEROOT_STD,
    NAL_TORSO_TWO_NECK: COMP_TORSO_HEAD,
    NAL_TORSO_ONE_NECK: COMP_TORSO_HEAD,
    NAL_LEGS: COMP_LEGS,
    NAL_LEGS_IK: COMP_LEGS_IK,
    NAL_ARMS: COMP_ARMS,
    NAL_ARMS_IK: COMP_ARMS_IK,
    NAL_TENTACLES: COMP_TENTACLE,
    NAL_FING52: COMP_FING52,
    NAL_FING5_CURL: COMP_FING5_CURL,
    NAL_FING5_REDUCED: COMP_FING5_REDUCED,
    NAL_FING5: COMP_FING5,
}

DEFAULT_COMP_ORDER = [
    COMP_ARBITRARY_PO,
    COMP_GENERIC,
    COMP_FAKEROOT_STD,
    COMP_TORSO_HEAD,
    COMP_TORSO_HEAD_STD,
    COMP_LEGS,
    COMP_LEGS_IK,
    COMP_ARMS,
    COMP_ARMS_IK,
    COMP_TENTACLE,
    COMP_FING52,
    COMP_FING5_CURL,
    COMP_FING5_REDUCED,
    COMP_FING5,
]

ROOT_BONE_TRACK_ID = -1

try:
    from .pcanim_comps import _components_to_bone_tracks
except Exception:
    from pcanim_comps import _components_to_bone_tracks  # type: ignore


class PCANIMParseError(Exception):
    pass


def _decode_cstr(data):
    return data.split(b"\x00", 1)[0].decode("latin-1", errors="ignore")


def _read_fixed_string(blob, offset):
    if offset + 32 > len(blob):
        raise PCANIMParseError(f"Fixed string out of range at 0x{offset:X}")
    h, raw = struct.unpack_from("<I28s", blob, offset)
    return h, _decode_cstr(raw)


def _read_i32(blob, offset):
    if offset < 0 or offset + 4 > len(blob):
        raise PCANIMParseError(f"i32 out of range at 0x{offset:X}")
    return struct.unpack_from("<i", blob, offset)[0]


def _read_u32(blob, offset):
    if offset < 0 or offset + 4 > len(blob):
        raise PCANIMParseError(f"u32 out of range at 0x{offset:X}")
    return struct.unpack_from("<I", blob, offset)[0]


def _parse_debug_frame_set(raw_value):
    frames = set()
    text = str(raw_value or "").strip()
    if not text:
        return frames

    text = text.replace(";", ",")
    for token in text.split(","):
        part = str(token).strip()
        if not part:
            continue

        if "-" in part:
            left, right = part.split("-", 1)
            try:
                start = int(left.strip())
                end = int(right.strip())
            except Exception:
                continue
            if end < start:
                start, end = end, start
            for frame_no in range(start, end + 1):
                if frame_no > 0:
                    frames.add(int(frame_no))
            continue

        try:
            frame_no = int(part)
        except Exception:
            continue
        if frame_no > 0:
            frames.add(int(frame_no))

    return frames


def _read_anim_header(blob, base):
    if base + 60 > len(blob):
        raise PCANIMParseError(f"Anim header out of range at 0x{base:X}")

    vtbl, next_anim = struct.unpack_from("<ii", blob, base)
    name_hash, name = _read_fixed_string(blob, base + 8)
    skel_ix, version, duration, flags, t_scale = struct.unpack_from("<iifif", blob, base + 40)

    out = {
        "offset": base,
        "vtbl": vtbl,
        "next_anim_rel": next_anim,
        "name_hash": name_hash,
        "name": name,
        "skel_index": skel_ix,
        "version": version,
        "duration": duration,
        "flags": flags,
        "t_scale": t_scale,
        "is_looping": bool(flags & FLAG_LOOPING),
        "is_scene_anim": bool(flags & FLAG_SCENE_ANIM),
    }

    if version == GEN_ANIM and base + 120 <= len(blob):
        (
            generic_unknown_0,
            generic_fps,
            generic_frame_count,
            generic_component_word_count,
            generic_pose_data_size,
            generic_data_align,
            generic_header_words_size,
            generic_chunk_align,
            generic_unknown_1,
            generic_packed_frame_data,
            generic_chunk_count,
            generic_frames_per_chunk,
            generic_packed_chunk_offsets,
            generic_frame_stride,
            generic_frame_align,
        ) = struct.unpack_from("<ifiiiiiiiiiiiii", blob, base + 60)
        out.update(
            {
                "instance_count": 0,
                "comp_list_offset": 0,
                "anim_user_data_offset": 0,
                "track_data_offset": 0,
                "internal_offset": 0,
                "frame_count": int(generic_frame_count),
                "current_time": 0.0,
                "anim_track_count": 0,
                "generic_fps": float(generic_fps),
                "generic_component_word_count": int(generic_component_word_count),
                "generic_pose_data_size": int(generic_pose_data_size),
                "generic_data_align": int(generic_data_align),
                "generic_header_words_size": int(generic_header_words_size),
                "generic_chunk_align": int(generic_chunk_align),
                "generic_chunk_count": int(generic_chunk_count),
                "generic_frames_per_chunk": int(generic_frames_per_chunk),
                "generic_frame_stride": int(generic_frame_stride),
                "generic_frame_align": int(generic_frame_align),
                "generic_unknown_0": int(generic_unknown_0),
                "generic_unknown_1": int(generic_unknown_1),
                "generic_packed_frame_data": int(generic_packed_frame_data),
                "generic_packed_chunk_offsets": int(generic_packed_chunk_offsets),
            }
        )
    elif base + 164 <= len(blob):
        (
            instance_count,
            comp_list_offs,
            anim_user_data_offs,
            track_data_offs,
            internal_offs,
            frame_count,
            current_time,
        ) = struct.unpack_from("<iiiiiif", blob, base + 60)
        anim_track_count = struct.unpack_from("<i", blob, base + 128)[0]
        out.update(
            {
                "instance_count": instance_count,
                "comp_list_offset": comp_list_offs,
                "anim_user_data_offset": anim_user_data_offs,
                "track_data_offset": track_data_offs,
                "internal_offset": internal_offs,
                "frame_count": frame_count,
                "current_time": current_time,
                "anim_track_count": anim_track_count,
            }
        )
    else:
        out.update(
            {
                "instance_count": 0,
                "comp_list_offset": 0,
                "anim_user_data_offset": 0,
                "track_data_offset": 0,
                "internal_offset": 0,
                "frame_count": 0,
                "current_time": 0.0,
                "anim_track_count": 0,
            }
        )

    return out


def _build_component_slots(skel_data):
    if not skel_data:
        return [
            {
                "slot_ix": int(comp_ix),
                "name_id": -1,
                "type_hash": 0,
                "flags": 0,
                "comp_ix": int(comp_ix),
            }
            for comp_ix in DEFAULT_COMP_ORDER
        ]

    meta = skel_data.get("component_meta") or []
    if meta:
        slots = []
        for slot_ix, comp in enumerate(meta):
            ctype = int(comp.get("type", 0))
            slots.append(
                {
                    "slot_ix": int(slot_ix),
                    "name_id": int(comp.get("index", -1)),
                    "type_hash": int(ctype),
                    "flags": int(comp.get("flags", 0)),
                    "comp_ix": int(NAL_TO_COMP_ID.get(ctype, -1)),
                }
            )
        if slots:
            return slots

    components = skel_data.get("components") or []
    if components:
        slots = []
        for comp in components:
            ctype = int(comp.get("type_id", 0))
            slots.append(
                {
                    "slot_ix": int(comp.get("component_index", len(slots))),
                    "name_id": int(comp.get("component_name_id", comp.get("component_index", -1))),
                    "type_hash": int(ctype),
                    "flags": int(comp.get("component_flags", 0)),
                    "comp_ix": int(NAL_TO_COMP_ID.get(ctype, -1)),
                }
            )
        if slots:
            return sorted(slots, key=lambda x: int(x.get("slot_ix", 0)))

    return [
        {
            "slot_ix": int(comp_ix),
            "name_id": -1,
            "type_hash": 0,
            "flags": 0,
            "comp_ix": int(comp_ix),
        }
        for comp_ix in DEFAULT_COMP_ORDER
    ]


def _decode_anim_components(blob, anim, comp_slots):
    components = []
    warnings = []

    base = int(anim.get("offset", 0))
    comp_list_abs = base + int(anim.get("comp_list_offset", 0))
    anim_list_abs = base + int(anim.get("anim_user_data_offset", 0))
    track_list_abs = base + int(anim.get("track_data_offset", 0))

    if comp_list_abs < 0 or anim_list_abs < 0 or track_list_abs < 0:
        return components, ["Invalid component table offsets"]

    anim_user_data_ix = 0
    track_ix = 0

    frame_count = max(1, int(anim.get("frame_count", 1)))
    current_time = float(anim.get("current_time", 0.0))
    is_scene_anim = bool(int(anim.get("flags", 0)) & FLAG_SCENE_ANIM)

    for slot in comp_slots:
        slot_ix = int(slot.get("slot_ix", 0))
        comp_ix = int(slot.get("comp_ix", -1))
        name_id = int(slot.get("name_id", -1))
        type_hash = int(slot.get("type_hash", 0))

        flag_off = comp_list_abs + slot_ix * 4
        if flag_off < 0 or flag_off + 4 > len(blob):
            continue

        flags = struct.unpack_from("<I", blob, flag_off)[0]
        if (flags & HAS_TRACK_DATA) == 0:
            continue

        per_anim_data_offs = anim_list_abs
        if flags & HAS_PER_ANIM_DATA:
            table_entry = anim_list_abs + (anim_user_data_ix + 1) * 4
            if table_entry + 4 <= len(blob):
                elem_offset = struct.unpack_from("<i", blob, table_entry)[0]
                per_anim_data_offs += int(elem_offset)
            anim_user_data_ix += 1

        if not _has_track(flags):
            continue

        if comp_ix < 0:
            warnings.append(
                f"Anim '{anim.get('name', '')}' slot {slot_ix}: unknown component type 0x{type_hash & 0xFFFFFFFF:08X}"
            )
            track_ix += 1
            continue

        try:
            mask = _read_u32(blob, per_anim_data_offs)
        except PCANIMParseError as e:
            warnings.append(str(e))
            track_ix += 1
            continue

        ntracks = _get_num_tracks_for_comp(comp_ix, mask)
        codec_ixs_abs = per_anim_data_offs + 4
        if codec_ixs_abs < 0 or codec_ixs_abs + ntracks > len(blob):
            warnings.append(
                f"Anim '{anim.get('name', '')}' slot {slot_ix} comp {comp_ix}: codec table out of bounds"
            )
            track_ix += 1
            continue

        codec_ixs = list(blob[codec_ixs_abs : codec_ixs_abs + ntracks])

        encoded_size = _get_num_bytes_for_comp(comp_ix, mask)
        if encoded_size < 0:
            warnings.append(
                f"Anim '{anim.get('name', '')}' slot {slot_ix} comp {comp_ix}: unsupported encoded size formula"
            )
            track_ix += 1
            continue

        track_data_abs = -1
        if encoded_size > 0:
            track_entry_offset = track_list_abs + (track_ix + 1) * 4
            if track_entry_offset < 0 or track_entry_offset + 4 > len(blob):
                warnings.append(
                    f"Anim '{anim.get('name', '')}' slot {slot_ix} comp {comp_ix}: track table entry out of bounds"
                )
                track_ix += 1
                continue

            track_offset = struct.unpack_from("<i", blob, track_entry_offset)[0]
            track_data_abs = track_list_abs + int(track_offset)

            if track_data_abs < 0 or track_data_abs + encoded_size > len(blob):
                warnings.append(
                    f"Anim '{anim.get('name', '')}' slot {slot_ix} comp {comp_ix}: encoded track data out of bounds"
                )
                track_ix += 1
                continue

        encoded_data = bytes(blob[track_data_abs : track_data_abs + encoded_size]) if encoded_size > 0 else b""

        frames = []
        decode_error = None
        try:
            frames = _decode_component_frames(
                comp_ix=comp_ix,
                codec_ixs=codec_ixs,
                encoded_data=encoded_data,
                mask=mask,
                frame_count=frame_count,
                current_time=current_time,
                is_scene_anim=is_scene_anim,
            )
        except PCANIMCodecError as e:
            decode_error = str(e)
            warnings.append(
                f"Anim '{anim.get('name', '')}' slot {slot_ix} comp {comp_ix}: {decode_error}"
            )

        components.append(
            {
                "comp_ix": int(comp_ix),
                "slot_ix": int(slot_ix),
                "name_id": int(name_id),
                "type_hash": int(type_hash),
                "flags": int(flags),
                "mask": int(mask),
                "ntracks": int(ntracks),
                "codec_ixs": codec_ixs,
                "track_data_offset": int(track_data_abs),
                "encoded_size": int(encoded_size),
                "frames": frames,
                "decode_error": decode_error,
            }
        )

        track_ix += 1

    return components, warnings


def open_pcanim(
    filepath,
    skel_data=None,
    decode_tracks=True,
    apply_root_motion=False,
    solve_ik=False,
    use_full_arm_tracks=True,
    rest_local_quats_by_bone=None,
):
    with io.open(filepath, "rb") as f:
        blob = f.read()

    if len(blob) < 64:
        raise PCANIMParseError("File is too small for a PCANIM header")

    debug_frames = _parse_debug_frame_set(os.environ.get("PCANIM_DEBUG_FRAMES", ""))
    debug_anim_filter = str(os.environ.get("PCANIM_DEBUG_ANIM", "")).strip().lower()
    debug_out_dir = str(os.environ.get("PCANIM_DEBUG_DIR", "")).strip()
    if debug_frames and not debug_out_dir:
        debug_out_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), "debug")

    version, flags, size_string_table, num_skeletons = struct.unpack_from("<IIii", blob, 0)
    name_hash, name = _read_fixed_string(blob, 16)
    num_anims, first_anim, file_buf, ref_count = struct.unpack_from("<iIii", blob, 48)

    if version != ANIM_CONTAINER:
        raise PCANIMParseError(f"Unsupported PCANIM version 0x{version:08X}")

    out = {
        "header": {
            "version": version,
            "flags": flags,
            "size_string_table": size_string_table,
            "num_skeletons": num_skeletons,
            "name_hash": name_hash,
            "name": name,
            "num_anims": num_anims,
            "first_anim": first_anim,
            "file_buf": file_buf,
            "ref_count": ref_count,
        },
        "skeletons": [],
        "animations": [],
    }

    skel_base = 64
    for i in range(max(0, num_skeletons)):
        off = skel_base + i * 32
        if off + 32 > len(blob):
            break
        p0, p1, skel_hash, raw_name = struct.unpack_from("<iii20s", blob, off)
        out["skeletons"].append(
            {
                "offset": off,
                "hash": skel_hash,
                "name": _decode_cstr(raw_name),
                "p": [p0, p1],
            }
        )

    seen = set()
    cur = int(first_anim)
    limit = max(4096, int(num_anims) if num_anims > 0 else 0)

    while cur and cur not in seen and len(out["animations"]) < limit:
        if cur < 0 or cur >= len(blob):
            break
        seen.add(cur)

        anim = _read_anim_header(blob, cur)
        out["animations"].append(anim)

        nxt = int(anim["next_anim_rel"])
        if nxt == 0:
            break
        cur = cur + nxt

    if not decode_tracks:
        return out

    comp_slots = _build_component_slots(skel_data)

    all_warnings = []
    for anim in out["animations"]:
        anim_version = int(anim.get("version", 0)) & 0xFFFFFFFF
        if anim_version not in (CHAR_ANIM, GEN_ANIM):
            anim["decoded_components"] = []
            anim["bone_tracks"] = {}
            anim["runtime_frame_world_engine"] = {}
            anim["runtime_default_world_engine"] = {}
            anim["runtime_parent_by_bone"] = {}
            anim["decode_warnings"] = [
                f"Anim '{anim.get('name', '')}' has unsupported version 0x{anim_version:08X}"
            ]
            all_warnings.extend(anim["decode_warnings"])
            continue

        if anim_version == GEN_ANIM:
            anim["decoded_components"] = []
            anim["decode_warnings"] = []
            anim["runtime_frame_world_engine"] = {}
            anim["runtime_default_world_engine"] = {}
            anim["runtime_parent_by_bone"] = {}
            anim["bone_tracks"] = {}
            anim["generic_animation_wip"] = True
            continue

        components, warnings = _decode_anim_components(blob, anim, comp_slots)
        anim["decoded_components"] = components
        anim["decode_warnings"] = warnings
        if warnings:
            all_warnings.extend(warnings)

        debug_capture = None
        if debug_frames:
            anim_name = str(anim.get("name", "")).strip()
            if not debug_anim_filter or anim_name.lower() == debug_anim_filter:
                debug_capture = {
                    "anim_name": anim_name,
                    "frames": sorted(debug_frames),
                }

        anim["runtime_frame_world_engine"] = {}
        anim["runtime_default_world_engine"] = {}
        anim["runtime_parent_by_bone"] = {}
        runtime_capture = {}

        if skel_data:
            anim["bone_tracks"] = _components_to_bone_tracks(
                components,
                skel_data,
                apply_root_motion=bool(apply_root_motion),
                solve_ik=bool(solve_ik),
                use_full_arm_tracks=bool(use_full_arm_tracks),
                rest_local_quats_by_bone=rest_local_quats_by_bone,
                debug_capture=debug_capture,
                runtime_capture=runtime_capture,
            )
            anim["runtime_frame_world_engine"] = runtime_capture.get("frame_world_engine", {})
            anim["runtime_default_world_engine"] = runtime_capture.get("default_world_engine", {})
            anim["runtime_parent_by_bone"] = runtime_capture.get("parent_by_bone", {})
        else:
            anim["bone_tracks"] = {}

        if debug_capture is not None:
            anim["debug_capture"] = debug_capture
            try:
                if debug_out_dir:
                    os.makedirs(debug_out_dir, exist_ok=True)
                    safe_name = "".join(
                        ch if (ch.isalnum() or ch in ("-", "_")) else "_"
                        for ch in str(debug_capture.get("anim_name", "anim"))
                    )
                    if not safe_name:
                        safe_name = "anim"
                    out_path = os.path.join(debug_out_dir, f"{safe_name}_torso_debug.json")
                    with io.open(out_path, "w", encoding="utf-8") as f_out:
                        json.dump(debug_capture, f_out, indent=2)
                    anim["debug_capture_path"] = out_path
            except Exception as e:
                msg = f"Anim '{anim.get('name', '')}' debug dump failed: {e}"
                warnings = anim.setdefault("decode_warnings", [])
                warnings.append(msg)
                all_warnings.append(msg)

    out["decode_warnings"] = all_warnings
    return out
