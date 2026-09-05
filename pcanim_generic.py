import math
import struct
try:
    from .pcanim_codec import (
        GENERIC_TRAJECTORY_FIXED_SCALE,
        _decode_generic_entropy_scalar_stream,
        _decode_generic_packed16_quat_stream,
        _generic_active_entries,
        _generic_playback_families,
        _walk_generic_position_orientation_control,
    )
    from .pcanim_transforms import (
        _mat_from_quat_pos,
        _mat_local_to_world,
        _mat_to_rows,
        _quat_mul_wxyz,
        _quat_normalize_wxyz,
    )
except Exception:
    from pcanim_codec import (  # type: ignore
        GENERIC_TRAJECTORY_FIXED_SCALE,
        _decode_generic_entropy_scalar_stream,
        _decode_generic_packed16_quat_stream,
        _generic_active_entries,
        _generic_playback_families,
        _walk_generic_position_orientation_control,
    )
    from pcanim_transforms import (  # type: ignore
        _mat_from_quat_pos,
        _mat_local_to_world,
        _mat_to_rows,
        _quat_mul_wxyz,
        _quat_normalize_wxyz,
    )


_GENERIC_SUPPORTED_ENCODINGS = (
    "nal_entropyfloat3",
    "nal_packed16entropyquaternion",
    "nal_entropypositionorientation",
    "nal_entropytrajectorypositionorientation",
    "nal_entropyfloat1",
    "usmevent",
)

# Runtime Generic float3 decode still feeds a later Convert/PoseByteCode stage.
# Until that stage is implemented, fail closed on clearly impossible decoded translations.
GENERIC_FLOAT3_SANITY_LIMIT = 100.0


def _float3(values):
    return (float(values[0]), float(values[1]), float(values[2]))


def _quat_wxyz_from_xyzw(values):
    quat_xyzw = tuple(float(v) for v in values[:4])
    return _quat_normalize_wxyz((quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]))


def _quat_wxyz_from_po_default(values):
    return _quat_wxyz_from_xyzw(values)

def _clamp_s8(value):
    ivalue = int(round(float(value)))
    if ivalue < -127:
        return -127
    if ivalue > 127:
        return 127
    return ivalue


def _store_frame_override(frame_map, frame_no, target_ix, value):
    frame_bucket = frame_map.setdefault(int(frame_no), {})
    frame_bucket[int(target_ix)] = tuple(float(v) for v in value)
    return frame_bucket


def _decode_generic_float3_pose_frames(entry, x_data, y_data, z_data, frame_count, block_shared_scale):
    scalar_values = list(entry.get("scalar_values", []))
    stream_scale = (float(scalar_values[0]) if scalar_values else 1.0) * block_shared_scale

    xs = _decode_generic_entropy_scalar_stream(x_data, frame_count, stream_scale)
    ys = _decode_generic_entropy_scalar_stream(y_data, frame_count, stream_scale)
    zs = _decode_generic_entropy_scalar_stream(z_data, frame_count, stream_scale)

    pose_frames = [
        (float(x_val), float(y_val), float(z_val))
        for x_val, y_val, z_val in zip(xs, ys, zs)
    ]
    raw_max_abs = max(
        max(abs(float(v)) for v in xs) if xs else 0.0,
        max(abs(float(v)) for v in ys) if ys else 0.0,
        max(abs(float(v)) for v in zs) if zs else 0.0,
    )
    return pose_frames, raw_max_abs, raw_max_abs


def _build_target_ids(skel_data):
    target_ids = set()
    for target in list((skel_data or {}).get("generic_targets", ())):
        try:
            target_ids.add(int(target.get("node_index", -1)))
        except Exception:
            continue
    for mode in list((skel_data or {}).get("generic_matrix_target_modes", ())):
        try:
            target_ids.add(int(mode.get("target_index", -1)))
        except Exception:
            continue
    target_ids.discard(-1)
    return sorted(target_ids)


def _build_parent_by_target(skel_data, target_ids):
    parent_by_target = {}
    target_set = set(int(v) for v in target_ids)

    for target in list((skel_data or {}).get("generic_targets", ())):
        try:
            target_ix = int(target.get("node_index", -1))
            parent_ix = int(target.get("parent_index", -1))
        except Exception:
            continue
        if target_ix < 0 or target_ix not in target_set:
            continue
        parent_by_target[target_ix] = parent_ix if parent_ix in target_set else -1

    for pair in list((skel_data or {}).get("generic_matrix_parent_pairs", ())):
        try:
            child_ix = int(pair.get("child_index", -1))
            parent_ix = int(pair.get("parent_index", -1))
        except Exception:
            continue
        if child_ix < 0 or child_ix not in target_set:
            continue
        parent_by_target[child_ix] = parent_ix if parent_ix in target_set else -1

    for target_ix in target_ids:
        parent_by_target.setdefault(int(target_ix), -1)
    return parent_by_target


def _build_target_mode_by_target(skel_data):
    out = {}
    for entry in list((skel_data or {}).get("generic_matrix_target_modes", ())):
        try:
            target_ix = int(entry.get("target_index", -1))
        except Exception:
            continue
        if target_ix < 0:
            continue
        out[target_ix] = {
            "translation_source": str(entry.get("translation_source", "none")),
            "translation_op": str(entry.get("translation_op", "none")),
            "rotation_source": str(entry.get("rotation_source", "none")),
            "rotation_op": str(entry.get("rotation_op", "none")),
        }
    return out


def _build_default_storage(skel_data, target_ids):
    default_translation = {int(target_ix): (0.0, 0.0, 0.0) for target_ix in target_ids}
    default_rotation = {int(target_ix): (1.0, 0.0, 0.0, 0.0) for target_ix in target_ids}

    for family in _generic_playback_families(skel_data, _GENERIC_SUPPORTED_ENCODINGS):
        encoding_name = str(family.get("encoding_name", ""))
        for entry in list((family or {}).get("entries", ())):
            try:
                target_ix = int(entry.get("target_index", -1))
            except Exception:
                continue
            if target_ix < 0 or target_ix not in default_translation:
                continue

            raw_default_value = entry.get("default_value")
            if encoding_name == "nal_entropyfloat3":
                default_value = list(raw_default_value or ())
                if len(default_value) >= 3:
                    default_translation[target_ix] = _float3(default_value)
                continue

            if encoding_name == "nal_packed16entropyquaternion":
                default_value = list(raw_default_value or ())
                if len(default_value) >= 4:
                    default_rotation[target_ix] = _quat_wxyz_from_xyzw(default_value)
                continue

            if encoding_name in ("nal_entropypositionorientation", "nal_entropytrajectorypositionorientation"):
                default_value = list(raw_default_value or ())
                if len(default_value) >= 7:
                    default_rotation[target_ix] = _quat_wxyz_from_po_default(default_value)
                    default_translation[target_ix] = _float3(default_value[4:7])

    return default_translation, default_rotation


def _build_pose_storage(default_translation, default_rotation, frame_count):
    # Runtime Generic evaluation copies the default pose first, then writes animated component data.
    pose_translation_by_frame = {
        int(frame_no): dict(default_translation)
        for frame_no in range(1, max(0, int(frame_count)) + 1)
    }
    pose_rotation_by_frame = {
        int(frame_no): dict(default_rotation)
        for frame_no in range(1, max(0, int(frame_count)) + 1)
    }
    return pose_translation_by_frame, pose_rotation_by_frame


def _decode_body_pose_storage(
    anim,
    skel_data,
    blob,
    frame_count,
    pose_translation_by_frame,
    pose_rotation_by_frame,
    pose_translation_overrides_by_frame,
    pose_rotation_overrides_by_frame,
    warnings,
 ):
    body_blocks = list(anim.get("generic_body_control_blocks", []))
    if not body_blocks:
        warnings.append("generic_body_control_missing")
        return set(), set(), set(), set(), False

    playback_families = _generic_playback_families(
        skel_data,
        ("nal_entropyfloat3", "nal_packed16entropyquaternion"),
    )
    family_by_base = {
        int(family.get("component_index_base", -1)): family
        for family in playback_families
    }
    active_components = set(int(v) for v in anim.get("generic_active_component_indices", []))
    shared_scales = list(anim.get("generic_shared_scalar_floats", []))
    shared_scale_ix = 0

    decoded_families = set()
    applied_families = set()
    float3_targets = set()
    float3_skipped_targets = set()
    had_body_blocks = False

    for block in body_blocks:
        encoding_name = str(block.get("encoding_name", ""))
        if encoding_name not in ("nal_entropyfloat3", "nal_packed16entropyquaternion"):
            continue
        had_body_blocks = True

        comp_base = int(block.get("component_index_base", -1))
        family = family_by_base.get(comp_base)
        if family is None:
            warnings.append(f"generic_block_missing_metadata:{encoding_name}:{comp_base}")
            continue

        block_shared_scale = 1.0
        if shared_scale_ix < len(shared_scales):
            block_shared_scale = float(shared_scales[shared_scale_ix])
        shared_scale_ix += 1

        entry_by_component = {
            int(entry.get("component_index", -1)): entry
            for entry in list(family.get("entries", []))
        }
        active_ids = [int(v) for v in block.get("active_component_indices", [])]
        control_entries = list(block.get("control_entries", []))
        if len(active_ids) != len(control_entries):
            warnings.append(f"generic_block_length_mismatch:{encoding_name}:{comp_base}")
            continue

        family_applied = False
        decoded_families.add(encoding_name)
        for active_idx, comp_ix in enumerate(active_ids):
            entry = entry_by_component.get(int(comp_ix))
            if entry is None:
                warnings.append(f"generic_component_metadata_missing:{encoding_name}:{comp_ix}")
                continue

            target_ix = int(entry.get("target_index", -1))
            scalar_values = list(entry.get("scalar_values", []))
            control = control_entries[active_idx]
            if target_ix < 0:
                warnings.append(f"generic_component_target_invalid:{encoding_name}:{comp_ix}:{target_ix}")
                continue
            if encoding_name == "nal_entropyfloat3":
                default_value = list(entry.get("default_value") or ())
                if len(default_value) < 3:
                    warnings.append(f"generic_component_oob:{encoding_name}:{comp_ix}")
                    continue
                x_data_off = int(control.get("x_data_off", 0))
                y_data_off = int(control.get("y_data_off", 0))
                z_data_off = int(control.get("z_data_off", 0))
                x_data = blob[x_data_off : x_data_off + int(control.get("len_x", 0))]
                y_data = blob[y_data_off : y_data_off + int(control.get("len_y", 0))]
                z_data = blob[z_data_off : z_data_off + int(control.get("len_z", 0))]
                try:
                    pose_frames, raw_max_abs, packed_max_abs = _decode_generic_float3_pose_frames(
                        entry,
                        x_data,
                        y_data,
                        z_data,
                        frame_count,
                        block_shared_scale,
                    )
                except Exception as exc:
                    warnings.append(f"generic_float3_decode_failed:{comp_ix}:{exc}")
                    continue

                if raw_max_abs > GENERIC_FLOAT3_SANITY_LIMIT and packed_max_abs >= 127.0:
                    float3_skipped_targets.add(int(target_ix))
                    warnings.append(f"generic_float3_sanity_skip:{comp_ix}:{target_ix}:{raw_max_abs:.3f}")
                    continue

                for frame_no, pose_value in enumerate(pose_frames, start=1):
                    pose_translation_by_frame[int(frame_no)][int(target_ix)] = pose_value
                    _store_frame_override(
                        pose_translation_overrides_by_frame,
                        frame_no,
                        target_ix,
                        pose_value,
                    )
                family_applied = True
                float3_targets.add(int(target_ix))
                continue

            default_quat = list(entry.get("default_value") or ())
            if len(default_quat) < 4 or len(scalar_values) < 1:
                warnings.append(f"generic_component_oob:{encoding_name}:{comp_ix}")
                continue
            scalar_scale = float(scalar_values[0]) * block_shared_scale
            quat_data_off = int(control.get("data_off", 0))
            quat_data = blob[quat_data_off : quat_data_off + int(control.get("len", 0))]
            try:
                decoded_quats = _decode_generic_packed16_quat_stream(quat_data, frame_count, scalar_scale)
            except Exception as exc:
                warnings.append(f"generic_quat_decode_failed:{comp_ix}:{exc}")
                continue

            if len(decoded_quats) != frame_count:
                warnings.append(f"generic_quat_length_mismatch:{comp_ix}:{len(decoded_quats)}")
                continue

            for frame_no, decoded_quat in enumerate(decoded_quats, start=1):
                pose_quat = tuple(float(v) for v in decoded_quat)
                pose_rotation_by_frame[int(frame_no)][int(target_ix)] = pose_quat
                _store_frame_override(
                    pose_rotation_overrides_by_frame,
                    frame_no,
                    target_ix,
                    pose_quat,
                )
            family_applied = True

        if family_applied:
            applied_families.add(encoding_name)

    return decoded_families, applied_families, float3_targets, float3_skipped_targets, had_body_blocks


def _apply_po_family_to_pose(
    entry,
    control,
    pos_scale,
    quat_scale,
    warning_prefix,
    blob,
    frame_count,
    pose_translation_by_frame,
    pose_rotation_by_frame,
    pose_translation_overrides_by_frame,
    pose_rotation_overrides_by_frame,
    warnings,
 ):
    comp_ix = int(entry.get("component_index", -1))
    target_ix = int(entry.get("target_index", -1))
    default_value = list(entry.get("default_value") or [])
    if len(default_value) < 7:
        warnings.append(f"{warning_prefix}_default_oob:{comp_ix}:{len(default_value)}")
        return False

    x_data_off = int(control.get("x_data_off", 0))
    y_data_off = int(control.get("y_data_off", 0))
    z_data_off = int(control.get("z_data_off", 0))
    q_data_off = int(control.get("q_data_off", 0))

    x_data = blob[x_data_off : x_data_off + int(control.get("len_x", 0))]
    y_data = blob[y_data_off : y_data_off + int(control.get("len_y", 0))]
    z_data = blob[z_data_off : z_data_off + int(control.get("len_z", 0))]
    q_data = blob[q_data_off : q_data_off + int(control.get("len_q", 0))]

    try:
        xs = _decode_generic_entropy_scalar_stream(x_data, frame_count, pos_scale)
        ys = _decode_generic_entropy_scalar_stream(y_data, frame_count, pos_scale)
        zs = _decode_generic_entropy_scalar_stream(z_data, frame_count, pos_scale)
        decoded_quats = _decode_generic_packed16_quat_stream(q_data, frame_count, quat_scale)
    except Exception as exc:
        warnings.append(f"{warning_prefix}_decode_failed:{comp_ix}:{exc}")
        return False

    if len(decoded_quats) != frame_count:
        warnings.append(f"{warning_prefix}_quat_length_mismatch:{comp_ix}:{len(decoded_quats)}")
        return False

    for frame_no, decoded_quat in enumerate(decoded_quats, start=1):
        pose_quat = tuple(float(v) for v in decoded_quat)
        pose_pos = (
            float(xs[frame_no - 1]),
            float(ys[frame_no - 1]),
            float(zs[frame_no - 1]),
        )
        pose_rotation_by_frame[int(frame_no)][int(target_ix)] = pose_quat
        pose_translation_by_frame[int(frame_no)][int(target_ix)] = pose_pos
        _store_frame_override(pose_rotation_overrides_by_frame, frame_no, target_ix, pose_quat)
        _store_frame_override(pose_translation_overrides_by_frame, frame_no, target_ix, pose_pos)
    return True


def _decode_helper_pose_storage(
    anim,
    skel_data,
    blob,
    frame_count,
    pose_translation_by_frame,
    pose_rotation_by_frame,
    pose_translation_overrides_by_frame,
    pose_rotation_overrides_by_frame,
    warnings,
 ):
    active_components = set(int(v) for v in anim.get("generic_active_component_indices", []))
    shared_scales = list(anim.get("generic_shared_scalar_floats", []))
    helper_cursor = int(anim.get("generic_body_control_end_off", 0))
    shared_scale_ix = len(list(anim.get("generic_body_control_blocks", [])))

    decoded_families = set()
    applied_families = set()
    helper_targets = set()
    metadata_only_families = set()
    floor_offset_tracks = []
    usmevent_tracks = []
    base_bone_po_applied = False
    helper_root_applied = False

    po_families = sorted(
        _generic_playback_families(skel_data, ("nal_entropypositionorientation",)),
        key=lambda family: int(family.get("component_index_base", 0)),
    )
    for family in po_families:
        active_entries = _generic_active_entries(family, active_components)
        if not active_entries:
            continue

        block_shared_scale = 1.0
        if shared_scale_ix < len(shared_scales):
            block_shared_scale = float(shared_scales[shared_scale_ix])
        shared_scale_ix += 1

        comp_base = int(family.get("component_index_base", -1))
        try:
            helper_cursor, control_entries = _walk_generic_position_orientation_control(blob, helper_cursor, len(active_entries))
        except Exception as exc:
            warnings.append(f"generic_po_walk_failed:{comp_base}:{exc}")
            continue

        if len(control_entries) != len(active_entries):
            warnings.append(f"generic_po_length_mismatch:{comp_base}:{len(control_entries)}")
            continue

        family_applied = False
        decoded_families.add("nal_entropypositionorientation")
        for entry, control in zip(active_entries, control_entries):
            comp_ix = int(entry.get("component_index", -1))
            scalar_values = list(entry.get("scalar_values", []))
            if len(scalar_values) < 2:
                warnings.append(f"generic_po_component_oob:{comp_ix}")
                continue

            pos_scale = float(scalar_values[0]) * block_shared_scale
            quat_scale = float(scalar_values[1]) * block_shared_scale
            if _apply_po_family_to_pose(
                entry,
                control,
                pos_scale,
                quat_scale,
                "generic_po",
                blob,
                frame_count,
                pose_translation_by_frame,
                pose_rotation_by_frame,
                pose_translation_overrides_by_frame,
                pose_rotation_overrides_by_frame,
                warnings,
            ):
                family_applied = True
                if bool(entry.get("target_is_helper", False)):
                    helper_targets.add(str(entry.get("target_name", "")))

        if family_applied:
            applied_families.add("nal_entropypositionorientation")
            base_bone_po_applied = True

    trajectory_families = sorted(
        _generic_playback_families(skel_data, ("nal_entropytrajectorypositionorientation",)),
        key=lambda family: int(family.get("component_index_base", 0)),
    )
    for family in trajectory_families:
        active_entries = _generic_active_entries(family, active_components)
        if not active_entries:
            continue

        comp_base = int(family.get("component_index_base", -1))
        try:
            helper_cursor, control_entries = _walk_generic_position_orientation_control(blob, helper_cursor, len(active_entries))
        except Exception as exc:
            warnings.append(f"generic_trajectory_walk_failed:{comp_base}:{exc}")
            continue

        if len(control_entries) != len(active_entries):
            warnings.append(f"generic_trajectory_length_mismatch:{comp_base}:{len(control_entries)}")
            continue

        family_applied = False
        decoded_families.add("nal_entropytrajectorypositionorientation")
        for entry, control in zip(active_entries, control_entries):
            scalar_values = list(entry.get("scalar_values", []))
            if len(scalar_values) >= 2:
                pos_scale = float(scalar_values[0])
                quat_scale = float(scalar_values[1])
            else:
                pos_scale = GENERIC_TRAJECTORY_FIXED_SCALE
                quat_scale = GENERIC_TRAJECTORY_FIXED_SCALE
            if _apply_po_family_to_pose(
                entry,
                control,
                pos_scale,
                quat_scale,
                "generic_trajectory",
                blob,
                frame_count,
                pose_translation_by_frame,
                pose_rotation_by_frame,
                pose_translation_overrides_by_frame,
                pose_rotation_overrides_by_frame,
                warnings,
            ):
                family_applied = True
                if bool(entry.get("target_is_helper", False)):
                    helper_targets.add(str(entry.get("target_name", "")))

        if family_applied:
            applied_families.add("nal_entropytrajectorypositionorientation")
            helper_root_applied = True

    float1_families = sorted(
        _generic_playback_families(skel_data, ("nal_entropyfloat1",)),
        key=lambda family: int(family.get("component_index_base", 0)),
    )
    for family in float1_families:
        active_entries = _generic_active_entries(family, active_components)
        if not active_entries:
            continue

        metadata_only_families.add("nal_entropyfloat1")
        for entry in active_entries:
            comp_ix = int(entry.get("component_index", -1))
            default_value = entry.get("default_value")
            if default_value is None:
                warnings.append(f"generic_float1_component_oob:{comp_ix}")
                continue
            floor_offset_tracks.append({
                "target_index": int(entry.get("target_index", -1)),
                "target_name": str(entry.get("target_name", f"Bone_{int(entry.get('target_index', -1))}")),
                "component_index": comp_ix,
                "default_value": float(default_value),
                "min_value": float(default_value),
                "max_value": float(default_value),
                "frame_count": int(frame_count),
                "note": "default_pose_only",
            })
            if bool(entry.get("target_is_helper", False)):
                helper_targets.add(str(entry.get("target_name", "")))

    usmevent_families = sorted(
        _generic_playback_families(skel_data, ("usmevent",)),
        key=lambda family: int(family.get("component_index_base", 0)),
    )
    for family in usmevent_families:
        active_entries = _generic_active_entries(family, active_components)
        if not active_entries:
            continue

        metadata_only_families.add("usmevent")
        for entry in active_entries:
            usmevent_tracks.append({
                "target_index": int(entry.get("target_index", -1)),
                "target_name": str(entry.get("target_name", f"Bone_{int(entry.get('target_index', -1))}")),
                "component_index": int(entry.get("component_index", -1)),
                "note": "active_component_present_decode_pending",
            })
            if bool(entry.get("target_is_helper", False)):
                helper_targets.add(str(entry.get("target_name", "")))

    return {
        "decoded_families": decoded_families,
        "applied_families": applied_families,
        "helper_targets": {name for name in helper_targets if str(name).strip()},
        "metadata_only_families": metadata_only_families,
        "floor_offset_tracks": floor_offset_tracks,
        "usmevent_tracks": usmevent_tracks,
        "base_bone_po_applied": bool(base_bone_po_applied),
        "helper_root_applied": bool(helper_root_applied),
    }


def _resolve_storage_value(source_name, pose_value, default_value):
    if str(source_name) == "default":
        return default_value
    if str(source_name) == "pose":
        return pose_value
    return pose_value


def _build_local_matrices_for_frame(target_ids, mode_by_target, default_translation, default_rotation, pose_translation, pose_rotation):
    local_mats = {}
    for target_ix in target_ids:
        mode = mode_by_target.get(int(target_ix), {})
        translation = _resolve_storage_value(
            mode.get("translation_source", "none"),
            pose_translation.get(int(target_ix), default_translation.get(int(target_ix), (0.0, 0.0, 0.0))),
            default_translation.get(int(target_ix), (0.0, 0.0, 0.0)),
        )
        rotation = _resolve_storage_value(
            mode.get("rotation_source", "none"),
            pose_rotation.get(int(target_ix), default_rotation.get(int(target_ix), (1.0, 0.0, 0.0, 0.0))),
            default_rotation.get(int(target_ix), (1.0, 0.0, 0.0, 0.0)),
        )
        local_mats[int(target_ix)] = _mat_from_quat_pos(rotation, translation)
    return local_mats

def _read_const_translation(const_bytes, cursor):
    values = struct.unpack_from("<3f", const_bytes, int(cursor))
    return (float(values[0]), float(values[1]), float(values[2])), int(cursor) + 12


def _read_const_rotation(const_bytes, cursor):
    values = struct.unpack_from("<4f", const_bytes, int(cursor))
    return _quat_wxyz_from_xyzw(values), int(cursor) + 16


def _read_const_transform(const_bytes, cursor):
    quat_vals = struct.unpack_from("<4f", const_bytes, int(cursor))
    pos_vals = struct.unpack_from("<3f", const_bytes, int(cursor) + 16)
    return (
        _quat_wxyz_from_xyzw(quat_vals),
        (float(pos_vals[0]), float(pos_vals[1]), float(pos_vals[2])),
        int(cursor) + 32,
    )


def _build_local_matrices_from_lookup(
    target_ids,
    lookup_ops,
    const_bytes,
    default_translation,
    default_rotation,
    pose_translation,
    pose_rotation,
    warnings,
 ):
    translation_by_target = {int(target_ix): tuple(default_translation.get(int(target_ix), (0.0, 0.0, 0.0))) for target_ix in target_ids}
    rotation_by_target = {int(target_ix): tuple(default_rotation.get(int(target_ix), (1.0, 0.0, 0.0, 0.0))) for target_ix in target_ids}
    const_cursor = 0

    for op in list(lookup_ops or ()):
        op_name = str(op.get("op_name", ""))
        source = str(op.get("source", "pose"))
        args = [int(v) for v in list(op.get("args", ()))]
        if op_name not in ("copy_translation", "copy_rotation", "copy_transform"):
            continue
        if not args:
            continue
        target_ix = int(args[0])
        if target_ix not in translation_by_target:
            continue

        if source == "pose":
            if op_name in ("copy_translation", "copy_transform"):
                translation_by_target[target_ix] = tuple(
                    float(v) for v in pose_translation.get(target_ix, translation_by_target[target_ix])
                )
            if op_name in ("copy_rotation", "copy_transform"):
                rotation_by_target[target_ix] = tuple(
                    float(v) for v in pose_rotation.get(target_ix, rotation_by_target[target_ix])
                )
            continue

        try:
            if op_name == "copy_translation":
                translation, const_cursor = _read_const_translation(const_bytes, const_cursor)
                translation_by_target[target_ix] = translation
            elif op_name == "copy_rotation":
                rotation, const_cursor = _read_const_rotation(const_bytes, const_cursor)
                rotation_by_target[target_ix] = rotation
            else:
                rotation, translation, const_cursor = _read_const_transform(const_bytes, const_cursor)
                rotation_by_target[target_ix] = rotation
                translation_by_target[target_ix] = translation
        except Exception as exc:
            warnings.append(f"generic_lookup_const_fallback:{op_name}:{target_ix}:{exc}")
            break

    return {
        int(target_ix): _mat_from_quat_pos(rotation_by_target[int(target_ix)], translation_by_target[int(target_ix)])
        for target_ix in target_ids
    }


def _build_eval_order(target_ids, parent_by_target):
    ordered = []
    visiting = set()
    visited = set()

    def visit(target_ix):
        target_ix = int(target_ix)
        if target_ix in visited:
            return
        if target_ix in visiting:
            return
        visiting.add(target_ix)
        parent_ix = int(parent_by_target.get(target_ix, -1))
        if parent_ix >= 0:
            visit(parent_ix)
        visiting.discard(target_ix)
        visited.add(target_ix)
        ordered.append(target_ix)

    for target_ix in target_ids:
        visit(target_ix)
    return ordered


def _compose_world_mats(eval_order, parent_by_target, local_mats):
    world_mats = {}
    for target_ix in eval_order:
        local_m = local_mats.get(int(target_ix))
        if local_m is None:
            continue
        parent_ix = int(parent_by_target.get(int(target_ix), -1))
        if parent_ix >= 0 and parent_ix in world_mats:
            world_mats[int(target_ix)] = _mat_local_to_world(local_m, world_mats[parent_ix])
        else:
            world_mats[int(target_ix)] = local_m
    return world_mats


def evaluate_generic_animation(anim, skel_data, blob):
    frame_count = int(anim.get("frame_count", 0))
    warnings = []
    if frame_count <= 0:
        return {
            "bone_tracks": {},
            "decode_warnings": ["generic_frame_count_invalid"],
            "generic_partial_playback_note": "generic_no_frames",
            "runtime_frame_world_engine": {},
            "runtime_default_world_engine": {},
            "runtime_parent_by_bone": {},
        }

    target_ids = _build_target_ids(skel_data)
    parent_by_target = _build_parent_by_target(skel_data, target_ids)
    mode_by_target = _build_target_mode_by_target(skel_data)
    default_translation, default_rotation = _build_default_storage(skel_data, target_ids)
    pose_translation_by_frame, pose_rotation_by_frame = _build_pose_storage(default_translation, default_rotation, frame_count)
    pose_translation_overrides_by_frame = {}
    pose_rotation_overrides_by_frame = {}

    playback_families = _generic_playback_families(skel_data, _GENERIC_SUPPORTED_ENCODINGS)
    active_components = set(int(v) for v in anim.get("generic_active_component_indices", []))
    generic_active_families = {
        str(family.get("encoding_name", "Unknown"))
        for family in playback_families
        if _generic_active_entries(family, active_components)
    }

    decoded_families, applied_families, float3_targets, float3_skipped_targets, had_body_blocks = _decode_body_pose_storage(
        anim,
        skel_data,
        blob,
        frame_count,
        pose_translation_by_frame,
        pose_rotation_by_frame,
        pose_translation_overrides_by_frame,
        pose_rotation_overrides_by_frame,
        warnings,
    )
    helper_info = _decode_helper_pose_storage(
        anim,
        skel_data,
        blob,
        frame_count,
        pose_translation_by_frame,
        pose_rotation_by_frame,
        pose_translation_overrides_by_frame,
        pose_rotation_overrides_by_frame,
        warnings,
    )
    decoded_families.update(helper_info["decoded_families"])
    applied_families.update(helper_info["applied_families"])
    metadata_only_families = set(helper_info["metadata_only_families"])

    generic_lookup_a_supported = bool((skel_data or {}).get("generic_lookup_a_supported", False))
    if not generic_lookup_a_supported:
        warnings.append("generic_matrix_program_unsupported")

    lookup_ops = list((skel_data or {}).get("generic_lookup_a_ops", ()))
    const_bytes = bytes((skel_data or {}).get("generic_lookup_b_bytes", b""))
    eval_order = _build_eval_order(target_ids, parent_by_target)
    default_local_mats = _build_local_matrices_from_lookup(
        target_ids,
        lookup_ops,
        const_bytes,
        default_translation,
        default_rotation,
        default_translation,
        default_rotation,
        warnings,
    )
    default_world_mats = _compose_world_mats(eval_order, parent_by_target, default_local_mats)

    runtime_frame_world_engine = {}
    if generic_lookup_a_supported:
        for frame_no in range(1, frame_count + 1):
            local_mats = _build_local_matrices_from_lookup(
                target_ids,
                lookup_ops,
                const_bytes,
                default_translation,
                default_rotation,
                pose_translation_by_frame[int(frame_no)],
                pose_rotation_by_frame[int(frame_no)],
                warnings,
            )
            world_mats = _compose_world_mats(eval_order, parent_by_target, local_mats)
            runtime_frame_world_engine[int(frame_no)] = {
                int(target_ix): _mat_to_rows(world_m)
                for target_ix, world_m in world_mats.items()
            }

    if "nal_entropyfloat3" in decoded_families and not float3_targets:
        metadata_only_families.add("nal_entropyfloat3")

    runtime_default_world_engine = {
        int(target_ix): _mat_to_rows(world_m)
        for target_ix, world_m in default_world_mats.items()
    }
    runtime_parent_by_bone = {
        int(target_ix): int(parent_by_target.get(int(target_ix), -1))
        for target_ix in target_ids
    }

    partial_note = ""
    if warnings and not runtime_frame_world_engine:
        partial_note = "generic_matrix_evaluation_missing"
    elif generic_lookup_a_supported and runtime_frame_world_engine:
        partial_note = "generic_runtime_matrix_lookup_a_subset"
    elif helper_info["helper_root_applied"]:
        partial_note = "generic_body_rotation_plus_helper_root"
    elif helper_info["base_bone_po_applied"]:
        partial_note = "generic_body_rotation_plus_base_bone_po"
    elif had_body_blocks:
        partial_note = "generic_body_rotation_only"

    return {
        "bone_tracks": {},
        "decode_warnings": warnings,
        "generic_partial_playback_note": partial_note,
        "generic_active_families": sorted(generic_active_families),
        "generic_decoded_families": sorted(decoded_families),
        "generic_applied_families": sorted(applied_families),
        "generic_metadata_only_families": sorted(metadata_only_families),
        "generic_helper_targets": sorted(helper_info["helper_targets"]),
        "generic_lookup_a_supported": bool(generic_lookup_a_supported),
        "generic_float3_applied_targets": sorted(
            str(target.get("name", f"Bone_{int(target.get('node_index', -1))}"))
            for target in list((skel_data or {}).get("generic_targets", ()))
            if int(target.get("node_index", -1)) in float3_targets
        ),
        "generic_float3_skipped_targets": sorted(
            str(target.get("name", f"Bone_{int(target.get('node_index', -1))}"))
            for target in list((skel_data or {}).get("generic_targets", ()))
            if int(target.get("node_index", -1)) in float3_skipped_targets
        ),
        "generic_floor_offset_tracks": helper_info["floor_offset_tracks"],
        "generic_usmevent_tracks": helper_info["usmevent_tracks"],
        "generic_pose_translation_engine": {
            int(frame_no): {int(bone_id): tuple(value) for bone_id, value in bone_map.items()}
            for frame_no, bone_map in pose_translation_overrides_by_frame.items()
        },
        "generic_pose_rotation_engine": {
            int(frame_no): {int(bone_id): tuple(value) for bone_id, value in bone_map.items()}
            for frame_no, bone_map in pose_rotation_overrides_by_frame.items()
        },
        "runtime_frame_world_engine": runtime_frame_world_engine,
        "runtime_default_world_engine": runtime_default_world_engine,
        "runtime_parent_by_bone": runtime_parent_by_bone,
    }
