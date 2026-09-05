import math

try:
    from .pcanim_transforms import (
        _engine_to_blender_quat_wxyz,
        _quat_mul_wxyz,
        _quat_normalize_wxyz,
    )
except Exception:
    from pcanim_transforms import (  # type: ignore
        _engine_to_blender_quat_wxyz,
        _quat_mul_wxyz,
        _quat_normalize_wxyz,
    )
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

FLAG_SCENE_ANIM = 0x00020000
HAS_TRACK_DATA = 0x1
HAS_PER_ANIM_DATA = 0x2

GENERIC_TRAJECTORY_FIXED_SCALE = 0.001

def _walk_generic_entropy_float3_control(blob, offset, active_count):
    cursor = int(offset)
    entries = []
    for _ in range(max(0, int(active_count))):
        len_x = int(blob[cursor])
        x_data_off = cursor + 1
        cursor = x_data_off + len_x
        len_y = int(blob[cursor])
        y_data_off = cursor + 1
        cursor = y_data_off + len_y
        len_z = int(blob[cursor])
        z_data_off = cursor + 1
        cursor = z_data_off + len_z
        entries.append({
            "len_x": len_x,
            "len_y": len_y,
            "len_z": len_z,
            "x_data_off": int(x_data_off),
            "y_data_off": int(y_data_off),
            "z_data_off": int(z_data_off),
        })
    return cursor, entries


def _walk_generic_packed16_quat_control(blob, offset, active_count):
    cursor = int(offset)
    entries = []
    for _ in range(max(0, int(active_count))):
        data_len = int(blob[cursor])
        data_off = cursor + 1
        cursor = data_off + data_len
        entries.append({
            "len": data_len,
            "data_off": int(data_off),
        })
    return cursor, entries



def _walk_generic_position_orientation_control(blob, offset, active_count):
    cursor = int(offset)
    entries = []
    for _ in range(max(0, int(active_count))):
        len_x = int(blob[cursor])
        x_data_off = cursor + 1
        cursor = x_data_off + len_x
        len_y = int(blob[cursor])
        y_data_off = cursor + 1
        cursor = y_data_off + len_y
        len_z = int(blob[cursor])
        z_data_off = cursor + 1
        cursor = z_data_off + len_z
        quat_len = int(blob[cursor])
        quat_data_off = cursor + 1
        cursor = quat_data_off + quat_len
        entries.append({
            "len_x": len_x,
            "len_y": len_y,
            "len_z": len_z,
            "len_q": quat_len,
            "x_data_off": int(x_data_off),
            "y_data_off": int(y_data_off),
            "z_data_off": int(z_data_off),
            "q_data_off": int(quat_data_off),
        })
    return cursor, entries


def _generic_playback_families(skel_data, encodings=None):
    families = list((skel_data or {}).get("generic_playback_families", ()))
    if encodings is None:
        return families
    wanted = {str(name) for name in encodings}
    return [
        family
        for family in families
        if str(family.get("encoding_name", "")) in wanted
    ]

def _generic_active_entries(family, active_components):
    return [
        entry
        for entry in list((family or {}).get("entries", ()))
        if int(entry.get("component_index", -1)) in active_components
    ]

def _inspect_generic_body_control(blob, anim, skel_data):
    common_off = int(anim.get("generic_common_header_off", 0))
    if common_off <= 0 or common_off + 56 > len(blob):
        return {}

    active_components = set(int(v) for v in anim.get("generic_active_component_indices", []))
    families = sorted(
        _generic_playback_families(
            skel_data,
            ("nal_entropyfloat3", "nal_packed16entropyquaternion"),
        ),
        key=lambda family: int(family.get("component_index_base", 0)),
    )
    if not families:
        return {}

    cursor = common_off + 56
    blocks = []
    scalar_cursor = 0
    try:
        for family in families:
            active_entries = _generic_active_entries(family, active_components)
            encoding_name = str(family.get("encoding_name", "Unknown"))
            block = {
                "encoding_name": encoding_name,
                "component_index_base": int(family.get("component_index_base", 0)),
                "component_count": int(family.get("component_count", 0)),
                "active_component_indices": [int(entry.get("component_index", -1)) for entry in active_entries],
                "active_component_count": int(len(active_entries)),
                "control_start_off": int(cursor),
                "scalar_tail_start": int(scalar_cursor),
            }
            if encoding_name == "nal_entropyfloat3":
                cursor, entries = _walk_generic_entropy_float3_control(blob, cursor, len(active_entries))
                block["control_entries"] = entries
            else:
                cursor, entries = _walk_generic_packed16_quat_control(blob, cursor, len(active_entries))
                block["control_entries"] = entries
            scalar_cursor += int(family.get("component_count", 0))
            block["scalar_tail_end"] = int(scalar_cursor)
            block["control_end_off"] = int(cursor)
            blocks.append(block)
    except Exception as exc:
        return {
            "generic_body_control_start_off": int(common_off + 56),
            "generic_body_control_error": str(exc),
            "generic_body_control_blocks": blocks,
        }

    return {
        "generic_body_control_start_off": int(common_off + 56),
        "generic_body_control_end_off": int(cursor),
        "generic_body_control_blocks": blocks,
    }


GENERIC_ENTROPY_MAGNITUDE_BIT_WIDTH = (3, 5, 8, 21)


class _GenericScalarState:
    __slots__ = ("stream", "codec", "runlen", "whole_int", "delta_int")

    def __init__(self, data):
        self.stream = _BitStream(data)
        self.codec = -1
        self.runlen = 0
        self.whole_int = 0
        self.delta_int = 0


def _generic_read_s32(stream):
    raw = stream.read_bits(32)
    if raw & 0x80000000:
        raw -= 0x100000000
    return int(raw)


def _generic_read_i16_bias(stream):
    return int(stream.read_bits(16)) - 0x8000


def _generic_decode_small_delta(code):
    if (code & 0x1F) != 0:
        if code & 1:
            shift = ((code >> 1) & 0xF) + 1
            group = (code >> 5) & 0x7
            if (group & 0x4) == 0:
                group -= 7
            return int(group << shift)
        return int(((code >> 1) & 0xF) - 8)
    shift = ((code >> 5) & 0xF) + 17
    group = code >> 9
    if (group & 0x4) == 0:
        group -= 7
    return int(group << shift)


def _generic_expand_entropy_runs(state, sample_count):
    out = []
    remaining = int(sample_count)
    while remaining > 0:
        if state.runlen > 0:
            zeros = min(remaining, int(state.runlen))
            out.extend([0] * zeros)
            state.runlen -= zeros
            remaining -= zeros
            continue

        decoder_fn = DECODER_TABLE.get(int(state.codec) & 0x3F)
        if decoder_fn is None:
            raise PCANIMCodecError(f"Unsupported Generic entropy decoder index {int(state.codec) & 0x3F}")
        runlen, decoded = decoder_fn(state.stream)
        out.append(int(decoded))
        remaining -= 1
        zero_fill = min(remaining, max(0, int(runlen) - 1))
        if zero_fill > 0:
            out.extend([0] * zero_fill)
            remaining -= zero_fill
        state.runlen = max(0, int(runlen) - 1 - zero_fill)
    return out


def _decode_generic_entropy_scalar_stream(data, sample_count, scale):
    sample_count = int(sample_count)
    if sample_count <= 0:
        return []

    state = _GenericScalarState(data)
    signed_scale = float(scale) < 0.0
    scale_abs = abs(float(scale))
    codec = int(state.stream.read_bits(5))
    if signed_scale:
        codec += 0x20
    state.codec = codec

    if state.stream.read_bits(1):
        whole_int = _generic_read_s32(state.stream)
    else:
        whole_int = _generic_read_i16_bias(state.stream)
    state.whole_int = int(whole_int)

    if state.codec & 0x20:
        if state.stream.read_bits(1):
            delta_int = _generic_read_s32(state.stream)
        else:
            delta_int = _generic_read_i16_bias(state.stream)
    else:
        delta_int = _generic_decode_small_delta(int(state.stream.read_bits(12)))
    state.delta_int = int(delta_int)

    # Decomp seeds the predictor with the first absolute sample and the second
    # absolute sample (`whole + delta`), not the raw delta residual itself.
    second_int = int(state.whole_int) + int(state.delta_int)
    out = [float(state.whole_int) * scale_abs]
    if sample_count == 1:
        return out
    out.append(float(second_int) * scale_abs)
    if sample_count == 2:
        return out

    encoded = _generic_expand_entropy_runs(state, sample_count - 2)
    prev2 = int(state.whole_int)
    prev1 = int(second_int)
    for raw in encoded:
        curr = int(raw) + 2 * prev1 - prev2
        out.append(float(curr) * scale_abs)
        prev2, prev1 = prev1, curr
    return out


class _GenericQuatChannelState:
    __slots__ = ("bitpos", "codec", "runlen")

    def __init__(self, bitpos=0, codec=-1, runlen=0):
        self.bitpos = int(bitpos)
        self.codec = int(codec)
        self.runlen = int(runlen)

    def clone(self):
        return _GenericQuatChannelState(self.bitpos, self.codec, self.runlen)


def _generic_decode_quat_signed_lsb(raw):
    value = int(raw)
    return -(value >> 1) if (value & 1) else (value >> 1)


def _generic_decode_packed_quat_small_delta(code):
    value = int(code)
    if (value & 0x1F) != 0:
        if value & 1:
            shift = ((value >> 1) & 0x7) + 1
            group = (value >> 4) & 0x7
            if (group & 0x4) == 0:
                group -= 7
            return int(group << shift)
        return int(((value >> 1) & 0xF) - 8)
    shift = ((value >> 5) & 0xF) + 9
    group = value >> 9
    if (group & 0x4) == 0:
        group -= 7
    return int(group << shift)


def _generic_decode_packed_quat_next_channel(data, channel, sample_count):
    next_channel = channel.clone()
    next_channel.runlen = 0
    if int(sample_count) > 2:
        stream = _BitStream(data)
        stream.bitpos = int(next_channel.bitpos)
        temp_state = _GenericScalarState(b"")
        temp_state.stream = stream
        temp_state.codec = int(next_channel.codec)
        temp_state.runlen = 0
        _generic_expand_entropy_runs(temp_state, int(sample_count) - 2)
        next_channel.bitpos = int(temp_state.stream.bitpos)
        next_channel.runlen = int(temp_state.runlen)
    return next_channel


def _decode_generic_packed16_quat_state(data, sample_count, scale):
    sample_count = int(sample_count)
    if sample_count <= 0:
        return None

    scale_abs = abs(float(scale))
    signed_scale = float(scale) < 0.0
    states = [_GenericQuatChannelState(), _GenericQuatChannelState(), _GenericQuatChannelState()]
    seed_components = []
    delta_components = []

    for comp_ix in range(3):
        channel = states[comp_ix]
        stream = _BitStream(data)
        stream.bitpos = int(channel.bitpos)

        next_channel_skip = 0
        if comp_ix < 2:
            if stream.read_bits(1):
                next_channel_skip = int(stream.read_bits(11)) + 256

        codec = int(stream.read_bits(5))
        if signed_scale:
            codec += 0x20
        channel.codec = codec

        magnitude_ix = int(stream.read_bits(2))
        magnitude_bits = int(GENERIC_ENTROPY_MAGNITUDE_BIT_WIDTH[magnitude_ix])
        seed_int = _generic_decode_quat_signed_lsb(stream.read_bits(magnitude_bits))
        seed_components.append(float(seed_int) * scale_abs * 0.25)

        if signed_scale:
            delta_mag_ix = int(stream.read_bits(2))
            delta_mag_bits = int(GENERIC_ENTROPY_MAGNITUDE_BIT_WIDTH[delta_mag_ix])
            delta_int = _generic_decode_quat_signed_lsb(stream.read_bits(delta_mag_bits))
        else:
            delta_int = _generic_decode_packed_quat_small_delta(stream.read_bits(12))
        delta_components.append(int(delta_int))

        channel.bitpos = int(stream.bitpos)
        channel.runlen = 0

        if comp_ix >= 2:
            continue

        if next_channel_skip > 0:
            next_channel = _GenericQuatChannelState(
                bitpos=int(stream.bitpos) + int(next_channel_skip),
                codec=-1,
                runlen=0,
            )
        else:
            next_channel = _generic_decode_packed_quat_next_channel(data, channel, sample_count)
            next_channel.codec = -1
            next_channel.runlen = 0
        states[comp_ix + 1] = next_channel

    seed_x, seed_y, seed_z = seed_components
    seed_w = math.sqrt(abs(1.0 - (seed_x * seed_x + seed_y * seed_y + seed_z * seed_z)))
    seed_quat = _quat_normalize_wxyz((seed_w, seed_x, seed_y, seed_z))

    return {
        "quat": seed_quat,
        "channels": states,
        "delta_components": delta_components,
        "scale_abs": scale_abs,
        "flags": 0x80,
    }


def _decode_generic_packed16_quat_stream(data, sample_count, scale):
    sample_count = int(sample_count)
    if sample_count <= 0:
        return []

    state = _decode_generic_packed16_quat_state(data, sample_count, scale)
    if state is None:
        return []

    current_quat = state["quat"]
    channels = state["channels"]
    delta_components = [int(v) for v in state["delta_components"]]
    scale_abs = float(state["scale_abs"])
    flags = int(state["flags"])
    out = []
    remaining = sample_count

    while remaining > 0 and (flags & 0xC0):
        if flags & 0x40:
            dx, dy, dz = (float(delta_components[0]) * scale_abs, float(delta_components[1]) * scale_abs, float(delta_components[2]) * scale_abs)
            dw = math.sqrt(abs(1.0 - (dx * dx + dy * dy + dz * dz)))
            delta_quat = _quat_normalize_wxyz((dw, dx, dy, dz))
            current_quat = _quat_normalize_wxyz(_quat_mul_wxyz(delta_quat, current_quat))
        out.append(current_quat)
        remaining -= 1
        flags = (int(channels[0].codec) & 0x3F) | max(0, flags - 0x40)

    if remaining <= 0:
        return out

    streams = []
    for channel in channels:
        stream = _BitStream(data)
        stream.bitpos = int(channel.bitpos)
        temp_state = _GenericScalarState(b"")
        temp_state.stream = stream
        temp_state.codec = int(channel.codec)
        temp_state.runlen = int(channel.runlen)
        streams.append(_generic_expand_entropy_runs(temp_state, remaining))

    x_accum, y_accum, z_accum = delta_components
    for idx in range(remaining):
        x_accum += int(streams[0][idx])
        y_accum += int(streams[1][idx])
        z_accum += int(streams[2][idx])
        dx = float(x_accum) * scale_abs
        dy = float(y_accum) * scale_abs
        dz = float(z_accum) * scale_abs
        dw = math.sqrt(abs(1.0 - (dx * dx + dy * dy + dz * dz)))
        delta_quat = _quat_normalize_wxyz((dw, dx, dy, dz))
        current_quat = _quat_normalize_wxyz(_quat_mul_wxyz(delta_quat, current_quat))
        out.append(current_quat)

    return out


def _decode_generic_tracks(anim, skel_data, blob):
    body_blocks = list(anim.get("generic_body_control_blocks", []))
    if not body_blocks:
        return {}, ["generic_body_control_missing"], "", {}

    playback_families = _generic_playback_families(
        skel_data,
        (
            "nal_entropyfloat3",
            "nal_packed16entropyquaternion",
            "nal_entropypositionorientation",
            "nal_entropytrajectorypositionorientation",
            "nal_entropyfloat1",
            "usmevent",
        ),
    )
    family_by_base = {
        int(family.get("component_index_base", -1)): family
        for family in playback_families
    }
    active_components = set(int(v) for v in anim.get("generic_active_component_indices", []))
    frame_count = int(anim.get("frame_count", 0))
    shared_scales = list(anim.get("generic_shared_scalar_floats", []))
    shared_scale_ix = 0
    bone_tracks = {}
    warnings = []
    partial_note = "generic_body_rotation_only"

    generic_active_families = {
        str(family.get("encoding_name", "Unknown"))
        for family in playback_families
        if _generic_active_entries(family, active_components)
    }

    decoded_families = set()
    applied_families = set()
    metadata_only_families = set()
    helper_targets = set()
    floor_offset_tracks = []
    usmevent_tracks = []
    base_bone_po_applied = False
    helper_root_applied = False
    generic_lookup_a_supported = bool((skel_data or {}).get("generic_lookup_a_supported", False))
    float3_applied = False
    float3_applied_targets = set()
    float3_skipped_targets = set()
    if not generic_lookup_a_supported and "nal_entropyfloat3" in generic_active_families:
        warnings.append("generic_float3_matrix_program_unsupported")

    def _record_named_target(collection, entry):
        target_name = str(entry.get("target_name", "")).strip()
        if target_name:
            collection.add(target_name)

    def _record_helper_target(entry):
        if not bool(entry.get("target_is_helper", False)):
            return
        _record_named_target(helper_targets, entry)
    def _apply_po_track(entry, control, pos_scale, quat_scale, warning_prefix):
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

        default_quat_xyzw = tuple(float(v) for v in default_value[:4])
        default_quat = _quat_normalize_wxyz((
            default_quat_xyzw[3],
            default_quat_xyzw[0],
            default_quat_xyzw[1],
            default_quat_xyzw[2],
        ))
        default_pos = tuple(float(v) for v in default_value[4:7])

        track = bone_tracks.setdefault(int(target_ix), {"rotation": {}, "location": {}})
        rot_track = track.setdefault("rotation", {})
        loc_track = track.setdefault("location", {})
        for frame_no, decoded_quat in enumerate(decoded_quats, start=1):
            final_quat = _quat_mul_wxyz(decoded_quat, default_quat)
            rot_track[int(frame_no)] = _engine_to_blender_quat_wxyz(final_quat)
            loc_track[int(frame_no)] = (
                float(default_pos[0] + xs[frame_no - 1]),
                float(default_pos[1] + ys[frame_no - 1]),
                float(default_pos[2] + zs[frame_no - 1]),
            )
        return True

    for block in body_blocks:
        encoding_name = str(block.get("encoding_name", ""))
        if encoding_name not in ("nal_entropyfloat3", "nal_packed16entropyquaternion"):
            continue

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

            if encoding_name == "nal_entropyfloat3":
                matrix_translation_source = str(entry.get("matrix_translation_source", "unknown"))
                matrix_translation_op = str(entry.get("matrix_translation_op", "unknown"))
                if (
                    not generic_lookup_a_supported
                    or matrix_translation_source != "pose"
                    or matrix_translation_op not in ("copy_translation", "copy_transform")
                ):
                    _record_named_target(float3_skipped_targets, entry)
                    continue

                default_value = tuple(float(v) for v in list(entry.get("default_value") or ()))
                if len(default_value) < 3 or len(scalar_values) < 1:
                    warnings.append(f"generic_component_oob:{encoding_name}:{comp_ix}")
                    continue
                scalar_scale = float(scalar_values[0]) * block_shared_scale

                x_data_off = int(control.get("x_data_off", 0))
                y_data_off = int(control.get("y_data_off", 0))
                z_data_off = int(control.get("z_data_off", 0))
                x_data = blob[x_data_off : x_data_off + int(control.get("len_x", 0))]
                y_data = blob[y_data_off : y_data_off + int(control.get("len_y", 0))]
                z_data = blob[z_data_off : z_data_off + int(control.get("len_z", 0))]
                try:
                    xs = _decode_generic_entropy_scalar_stream(x_data, frame_count, scalar_scale)
                    ys = _decode_generic_entropy_scalar_stream(y_data, frame_count, scalar_scale)
                    zs = _decode_generic_entropy_scalar_stream(z_data, frame_count, scalar_scale)
                except Exception as exc:
                    warnings.append(f"generic_float3_decode_failed:{comp_ix}:{exc}")
                    continue

                track = bone_tracks.setdefault(int(target_ix), {"rotation": {}, "location": {}})
                loc_track = track.setdefault("location", {})
                for frame_no in range(frame_count):
                    loc_track[int(frame_no) + 1] = (
                        float(default_value[0] + xs[frame_no]),
                        float(default_value[1] + ys[frame_no]),
                        float(default_value[2] + zs[frame_no]),
                    )
                family_applied = True
                float3_applied = True
                _record_named_target(float3_applied_targets, entry)
                continue

            default_quat = tuple(float(v) for v in list(entry.get("default_value") or ()))
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

            track = bone_tracks.setdefault(int(target_ix), {"rotation": {}, "location": {}})
            rot_track = track.setdefault("rotation", {})
            default_quat = _quat_normalize_wxyz(default_quat)
            for frame_no, decoded_quat in enumerate(decoded_quats, start=1):
                final_quat = _quat_mul_wxyz(decoded_quat, default_quat)
                rot_track[int(frame_no)] = _engine_to_blender_quat_wxyz(final_quat)
            family_applied = True

        if family_applied:
            applied_families.add(encoding_name)

    helper_cursor = int(anim.get("generic_body_control_end_off", 0))

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
            if _apply_po_track(entry, control, pos_scale, quat_scale, "generic_po"):
                family_applied = True
                _record_helper_target(entry)

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
            if _apply_po_track(
                entry,
                control,
                GENERIC_TRAJECTORY_FIXED_SCALE,
                GENERIC_TRAJECTORY_FIXED_SCALE,
                "generic_trajectory",
            ):
                family_applied = True
                _record_helper_target(entry)

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
            _record_helper_target(entry)

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
            _record_helper_target(entry)

    if "nal_entropyfloat3" in decoded_families and not float3_applied:
        metadata_only_families.add("nal_entropyfloat3")

    if float3_applied:
        if helper_root_applied:
            partial_note = "generic_body_translation_plus_rotation_plus_helper_root"
        elif base_bone_po_applied:
            partial_note = "generic_body_translation_plus_rotation_plus_base_bone_po"
        else:
            partial_note = "generic_body_translation_plus_rotation"
    elif helper_root_applied:
        partial_note = "generic_body_rotation_plus_helper_root"
    elif base_bone_po_applied:
        partial_note = "generic_body_rotation_plus_base_bone_po"

    extras = {
        "generic_active_families": sorted(generic_active_families),
        "generic_decoded_families": sorted(decoded_families),
        "generic_applied_families": sorted(applied_families),
        "generic_metadata_only_families": sorted(metadata_only_families),
        "generic_helper_targets": sorted(helper_targets),
        "generic_lookup_a_supported": bool(generic_lookup_a_supported),
        "generic_float3_applied_targets": sorted(float3_applied_targets),
        "generic_float3_skipped_targets": sorted(float3_skipped_targets),
        "generic_floor_offset_tracks": floor_offset_tracks,
        "generic_usmevent_tracks": usmevent_tracks,
    }
    return bone_tracks, warnings, partial_note, extras


class PCANIMCodecError(Exception):
    pass

def _popcount(v):
    return int(v & 0xFFFFFFFF).bit_count()


def _count(mask, filt, weight=1):
    return weight * _popcount(mask & filt)


def _to_bytes(tracks, header_size=0):
    return (tracks * 16) + header_size


def _get_num_quats(mask):
    return _popcount(mask & 0x1F)


def _get_has_extras(mask):
    return (mask & 0x20) != 0


def _get_num_tracks(mask):
    return 3 * _get_num_quats(mask) + (6 if _get_has_extras(mask) else 0)


def _get_arbitrary_quat_bit_count(track_meta=None):
    if not isinstance(track_meta, dict):
        return 12
    try:
        count = int(track_meta.get("quat_track_count", 12))
    except Exception:
        return 12
    return max(0, count)


def _get_arbitrary_total_slot_count(track_meta=None):
    if not isinstance(track_meta, dict):
        return 16
    try:
        quat_count = int(track_meta.get("quat_track_count", 12))
    except Exception:
        quat_count = 12
    try:
        vector_count = int(track_meta.get("vector_track_count", max(0, 16 - quat_count)))
    except Exception:
        vector_count = max(0, 16 - quat_count)
    total = max(0, quat_count) + max(0, vector_count)
    return total if total > 0 else 16


def _coerce_mask_words(mask, total_slots):
    words_needed = max(1, (max(0, int(total_slots)) + 31) // 32)
    if isinstance(mask, (list, tuple)):
        words = [int(v) & 0xFFFFFFFF for v in mask[:words_needed]]
    else:
        words = [int(mask) & 0xFFFFFFFF]
    if len(words) < words_needed:
        words.extend([0] * (words_needed - len(words)))
    return words


def _count_mask_bits(mask, total_slots):
    words = _coerce_mask_words(mask, total_slots)
    total_slots = max(0, int(total_slots))
    count = 0
    full_words, rem = divmod(total_slots, 32)
    for word_ix in range(full_words):
        count += _popcount(words[word_ix])
    if rem:
        count += _popcount(words[full_words] & ((1 << rem) - 1))
    return count


def _iter_mask_bits(mask, total_slots):
    words = _coerce_mask_words(mask, total_slots)
    for bit in range(max(0, int(total_slots))):
        if words[bit >> 5] & (1 << (bit & 31)):
            yield bit


def _get_num_tracks_for_comp(comp_ix, mask, track_meta=None):
    if comp_ix == COMP_ARBITRARY_PO:
        return 3 * _count_mask_bits(mask, _get_arbitrary_total_slot_count(track_meta))
    if comp_ix == COMP_GENERIC:
        return 0
    if comp_ix == COMP_FAKEROOT_STD:
        tracks = 9
        if mask & 0x1:
            tracks += 6
        if mask & 0x2:
            tracks += 1
        return tracks

    if comp_ix in (COMP_TORSO_HEAD, COMP_TORSO_HEAD_STD):
        return _count(mask, 0x1F, 3) + _count(mask, 0x20, 6)

    if comp_ix in (COMP_LEGS, COMP_ARMS):
        return _count(mask, 0xFF, 3)

    if comp_ix in (COMP_LEGS_IK, COMP_ARMS_IK):
        tracks = 0
        if mask & 0x1:
            tracks += 3
        if mask & 0x2:
            tracks += 3
        if mask & 0x4:
            tracks += 7
        if mask & 0x8:
            tracks += 7
        return tracks

    if comp_ix == COMP_TENTACLE:
        return _popcount(mask & 0x7FFF)

    if comp_ix in (COMP_FING52, COMP_FING5_REDUCED):
        return _popcount(mask & 0x3FFFFFFF) + _popcount(mask & 0x3FF) + _popcount(mask & 0x3)

    if comp_ix == COMP_FING5_CURL:
        return 15 + _count(mask, 0x3FF, 2) + _count(mask, 0x3, 2)

    if comp_ix == COMP_FING5:
        return 61 + _count(mask, 0x3FFFFFFF, 3)

    return _get_num_tracks(mask)


def _get_num_bytes_for_comp(comp_ix, mask, track_meta=None):
    if comp_ix == COMP_ARBITRARY_PO:
        return _to_bytes(_get_num_tracks_for_comp(comp_ix, mask, track_meta), 0x3C)
    if comp_ix == COMP_GENERIC:
        return 0
    if comp_ix == COMP_FAKEROOT_STD:
        tracks = 9 + _count(mask, 0x1, 6) + _count(mask, 0x2, 1)
        return _to_bytes(tracks)

    if comp_ix in (COMP_TORSO_HEAD, COMP_TORSO_HEAD_STD):
        tracks = _count(mask, 0x1F, 3) + _count(mask, 0x20, 6)
        return _to_bytes(tracks)

    if comp_ix in (COMP_LEGS, COMP_ARMS):
        tracks = 17 + _count(mask, 0xFF, 3)
        return _to_bytes(tracks)

    if comp_ix in (COMP_LEGS_IK, COMP_ARMS_IK):
        tracks = _count(mask, 0xF, 3) + _count(mask, 0xC, 4)
        return _to_bytes(tracks)

    if comp_ix == COMP_TENTACLE:
        tracks = _popcount(mask & 0x7FFF)
        return _to_bytes(tracks, 136)

    if comp_ix == COMP_FING52:
        tracks = _popcount(mask & 0x3FFFFFFF) + _popcount(mask & 0x3FF) + _popcount(mask & 0x3)
        return _to_bytes(tracks)

    if comp_ix == COMP_FING5_CURL:
        tracks = 15 + _count(mask, 0x3FF, 2) + _count(mask, 0x3, 2)
        return _to_bytes(tracks)

    if comp_ix == COMP_FING5_REDUCED:
        tracks = _popcount(mask & 0x3FFFFFFF) + _popcount(mask & 0x3FF) + _popcount(mask & 0x3)
        return _to_bytes(tracks)

    if comp_ix == COMP_FING5:
        tracks = 61 + _count(mask, 0x3FFFFFFF, 3)
        return _to_bytes(tracks)

    return -1


def _has_track(flags):
    return (flags & (HAS_TRACK_DATA | HAS_PER_ANIM_DATA)) == (HAS_TRACK_DATA | HAS_PER_ANIM_DATA)


class _BitStream:
    __slots__ = ("_data", "bitpos")

    def __init__(self, data):
        self._data = data
        self.bitpos = 0

    def _get_bit(self, bit_index):
        if bit_index < 0:
            return 0
        byte_index = bit_index >> 3
        if byte_index >= len(self._data):
            return 0
        return (self._data[byte_index] >> (bit_index & 7)) & 1

    def peek_bits(self, n):
        out = 0
        base = self.bitpos
        for i in range(n):
            out |= self._get_bit(base + i) << i
        return out

    def read_bits(self, n):
        out = self.peek_bits(n)
        self.bitpos += n
        return out

    def consume(self, n):
        self.bitpos += n

    def read_signed_bits(self, n):
        raw = self.read_bits(1 + n)
        neg = (raw & 1) != 0
        value = raw >> 1
        return -value if neg else value


def _dec_0(bs):
    del bs
    return 0, 0


def _dec_1a(bs):
    code = bs.peek_bits(2)
    if code & 1:
        bs.consume(2)
        return 1, code - 2
    bs.consume(1)
    return 1, 0


def _dec_1b(bs):
    code = bs.peek_bits(4)
    if code & 1:
        if code & 2:
            if code & 4:
                bs.consume(4)
                return 1, (code >> 2) - 2
            bs.consume(3)
            return 1, 0
        bs.consume(2)
        return 2, 0
    bs.consume(1)
    return 7, 0


def _dec_1c(bs):
    code = bs.peek_bits(3)
    if code & 1:
        if code & 2:
            bs.consume(3)
            return 1, (code >> 1) - 2
        bs.consume(2)
        return 1, 0
    bs.consume(1)
    return 3, 0


def _dec_1d(bs):
    code = bs.peek_bits(4)
    if code & 1:
        if code & 2:
            if code & 4:
                bs.consume(4)
                return 1, (code >> 2) - 2
            bs.consume(3)
            return 1, 0
        bs.consume(2)
        return 2, 0
    bs.consume(1)
    return 4, 0


def _dec_1e(bs):
    code = bs.read_bits(2)
    if code != 0:
        return 1, code - 2
    return 6, 0


def _dec_2a(bs):
    code = bs.peek_bits(3)
    if code & 1:
        bs.consume(3)
        return 1, (code >> 2) + (code >> 1) - 2
    bs.consume(1)
    return 1, 0


def _dec_2b(bs):
    code = bs.peek_bits(3)
    if (code & 3) != 0:
        code &= 3
        bs.consume(2)
    else:
        bs.consume(3)
    return 1, code - 2


def _dec_2c(bs):
    code = bs.peek_bits(5)
    result = 1
    if code & 1:
        if code & 2:
            if code & 4:
                bs.consume(5)
                return result, (code >> 4) + (code >> 3) - 2
            bs.consume(3)
            return result, 0
        bs.consume(2)
        return 2, 0
    bs.consume(1)
    return 4, 0


def _dec_3a(bs):
    code = bs.peek_bits(4)
    if (code & 3) != 0:
        bs.consume(2)
        return 1, (code & 3) - 2
    tmp = code >> 2
    if (tmp & 2) == 0:
        tmp -= 3
    bs.consume(4)
    return 1, tmp


def _dec_3b(bs):
    code = bs.read_bits(3)
    if code != 0:
        return 1, code - 4
    return 3, 0


def _dec_5a(bs):
    code = bs.peek_bits(5)
    if (code & 3) != 0:
        bs.consume(2)
        return 1, (code & 3) - 2
    tmp = code >> 2
    if (tmp & 4) != 0:
        tmp -= 2
    else:
        tmp -= 5
    bs.consume(5)
    return 1, tmp


def _dec_7a(bs):
    code = bs.read_bits(4)
    if code != 0:
        return 1, code - 8
    return 4, 0


def _dec_7b(bs):
    code = bs.peek_bits(5)
    low3 = code & 7
    if low3 < 3:
        if low3 == 2:
            value = 3 if (code & 8) != 0 else -3
            bs.consume(4)
            return 1, value
        if (code & 1) != 0:
            value = -4 - (code >> 3)
        else:
            value = (code >> 3) + 4
        bs.consume(5)
        return 1, value

    bs.consume(3)
    return 1, low3 - 5


def _dec_7c(bs):
    code = bs.peek_bits(6)
    if (code & 3) != 0:
        bs.consume(2)
        return 1, (code & 3) - 2

    if (code & 4) != 0:
        tmp = code >> 3
        if (tmp & 4) == 0:
            tmp -= 7
        bs.consume(6)
        return 1, tmp

    tmp = (code >> 3) & 3
    if (tmp & 2) == 0:
        tmp -= 3
    bs.consume(5)
    return 1, tmp


def _dec_f15a(bs):
    code = bs.peek_bits(5)
    if code & 1:
        half = code >> 1
        quarter = code >> 2
        lf = half & 1
        if (quarter & 4) == 0:
            quarter -= 7
        bs.consume(5)
        return 1, quarter << lf

    low4 = code & 0xF
    bs.consume(4)
    if low4 != 0:
        return 1, (low4 >> 1) - 4
    return 4, 0


def _dec_f15b(bs):
    code = bs.peek_bits(7)
    if (code & 3) != 0:
        bs.consume(2)
        return 1, (code & 3) - 2

    if (code & 4) != 0:
        half = code >> 3
        high = code >> 4
        lf = half & 1
        if (high & 4) == 0:
            high -= 7
        bs.consume(7)
        return 1, high << lf

    tmp = (code >> 3) & 3
    if (tmp & 2) == 0:
        tmp -= 3
    bs.consume(5)
    return 1, tmp


def _dec_f15c(bs):
    code = bs.peek_bits(7)
    if code & 1:
        if code & 2:
            if code & 4:
                half = code >> 3
                high = code >> 4
                lf = half & 1
                if (high & 4) == 0:
                    high -= 7
                bs.consume(7)
                return 1, high << lf

            tmp = (code >> 3) & 3
            if (tmp & 2) == 0:
                tmp -= 3
            bs.consume(5)
            return 1, tmp

        bs.consume(3)
        return 1, ((code >> 1) & 2) - 1

    bs.consume(2)
    if (code & 2) == 0:
        return 8, 0
    return 1, 0


def _dec_f31a(bs):
    code = bs.read_bits(5)
    if code == 0:
        return 5, 0

    low2 = code & 3
    high = code >> 2
    if low2 != 0:
        shift = low2 - 1
        if (high & 4) == 0:
            high -= 7
        return 1, high << shift

    return 1, high - 4


def _dec_f31b(bs):
    code = bs.peek_bits(6)
    result = 1

    if code & 1:
        if code & 2:
            shift = ((code >> 2) & 1) + 1
            high = code >> 3
            bs.consume(6)
        else:
            shift = 0
            high = (code >> 2) & 7
            bs.consume(5)

        if (high & 4) == 0:
            high -= 7
        return result, high << shift

    low4 = code & 0xF
    bs.consume(4)
    if low4 != 0:
        return result, (low4 >> 1) - 4
    return 4, 0


def _dec_f31c(bs):
    code = bs.peek_bits(7)
    low3 = code & 7

    if low3 < 3:
        if (code & 7) != 0:
            if low3 == 1:
                shift = 0
                high = (code >> 3) & 7
                bs.consume(6)
            else:
                shift = ((code >> 3) & 1) + 1
                high = code >> 4
                bs.consume(7)

            if (high & 4) == 0:
                high -= 7
            return 1, high << shift

        value = 3 if (code & 8) != 0 else -3
        bs.consume(4)
        return 1, value

    bs.consume(3)
    return 1, low3 - 5


def _dec_f31d(bs):
    code = bs.peek_bits(7)
    result = 1

    if code & 1:
        if code & 2:
            if code & 0xC:
                shift = ((code >> 2) & 3) - 1
                high = code >> 4
                if (high & 4) == 0:
                    high -= 7
                bs.consume(7)
                return result, high << shift

            high = (code >> 4) & 3
            if (high & 2) == 0:
                high -= 3
            bs.consume(6)
            return result, high

        bs.consume(3)
        return result, ((code >> 1) & 2) - 1

    bs.consume(2)
    if (code & 2) == 0:
        return 8, 0
    return result, 0


def _dec_f63a(bs):
    code = bs.peek_bits(6)
    result = 1

    if code & 1:
        half = code >> 1
        high = code >> 3
        shift = half & 3
        if (high & 4) == 0:
            high -= 7
        bs.consume(6)
        return result, high << shift

    low4 = code & 0xF
    bs.consume(4)
    if low4 != 0:
        return result, (low4 >> 1) - 4
    return 4, 0


def _dec_f63b(bs):
    code = bs.peek_bits(6)
    result = 1

    if code & 1:
        if code & 2:
            shift = ((code >> 2) & 1) + 2
            high = code >> 3
            bs.consume(6)
        else:
            high = (code >> 2) & 7
            shift = 1
            bs.consume(5)

        if (high & 4) == 0:
            high -= 7
        return result, high << shift

    low5 = code & 0x1F
    bs.consume(5)
    if low5 != 0:
        return result, (low5 >> 1) - 8
    return 5, 0


def _dec_f127(bs):
    code = bs.peek_bits(6)
    result = 1

    if code & 1:
        low2 = (code >> 1) & 3
        high = code >> 3
        shift = low2 + 1
        if (high & 4) == 0:
            high -= 7
        bs.consume(6)
        return result, high << shift

    low5 = code & 0x1F
    bs.consume(5)
    if low5 != 0:
        return result, (low5 >> 1) - 8
    return 5, 0


def _dec_f255(bs):
    code = bs.peek_bits(6)
    result = 1
    low3 = code & 7

    if low3 >= 2:
        high = code >> 3
        shift = low3 - 2
        if (high & 4) == 0:
            high -= 7
        bs.consume(6)
        return result, high << shift

    low5 = code & 0x1F
    bs.consume(5)
    if low5 != 0:
        if low5 & 1:
            return result, low5 >> 3
        return result, -(low5 >> 3)
    return 5, 0


def _dec_f2047(bs):
    code = bs.peek_bits(7)
    result = 1

    if code & 1:
        low3 = (code >> 1) & 7
        high = code >> 4
        shift = low3 + 1
        if (high & 4) == 0:
            high -= 7
        bs.consume(7)
        return result, high << shift

    low5 = code & 0x1F
    bs.consume(5)
    if low5 != 0:
        return result, (low5 >> 1) - 8
    return 5, 0


def _dec_f15bit(bs):
    code = bs.peek_bits(9)
    low3 = code & 7

    if low3 >= 2:
        if low3 == 7:
            low3 = ((code >> 3) & 7) + 5
            high = code >> 6
            bs.consume(9)
        else:
            high = (code >> 3) & 7
            low3 -= 2
            bs.consume(6)

        if (high & 4) == 0:
            high -= 7
        return 1, high << low3

    bs.consume(5)
    low5 = code & 0x1F
    if low5 != 0:
        return 1, (low5 >> 3) if (low5 & 1) else -(low5 >> 3)
    return 5, 0


def _dec_f23bit(bs):
    code = bs.peek_bits(10)
    low3 = code & 7

    if low3 >= 2:
        if low3 == 7:
            low3 = ((code >> 3) & 0xF) + 5
            high = code >> 7
            bs.consume(10)
        else:
            high = (code >> 3) & 7
            low3 -= 2
            bs.consume(6)

        if (high & 4) == 0:
            high -= 7
        return 1, high << low3

    bs.consume(5)
    low5 = code & 0x1F
    if low5 != 0:
        return 1, (low5 >> 3) if (low5 & 1) else -(low5 >> 3)
    return 5, 0


def _dec_f31bit(bs):
    code = bs.peek_bits(8)
    low5 = code & 0x1F

    if low5 == 2:
        bs.consume(5)
        return 1, 0

    if low5 >= 2:
        high = code >> 5
        shift = low5 - 3
        if (high & 4) == 0:
            high -= 7
        bs.consume(8)
        return 1, high << shift

    if code & 1:
        value = ((code >> 5) & 3) + 1
    else:
        value = -1 - ((code >> 5) & 3)
    bs.consume(7)
    return 1, value


def _dec_15(bs):
    code = bs.read_bits(5)
    if code != 0:
        return 1, code - 16
    return 5, 0


def _dec_0_16(bs):
    code = bs.peek_bits(7)
    if code & 1:
        if code & 2:
            bs.consume(7)
            return 1, (code >> 6) + (code >> 2) - 16
        bs.consume(2)
        return 1, 0

    bs.consume(1)
    return 4, 0


def _dec_0_1_17(bs):
    code = bs.peek_bits(7)
    if code & 1:
        if code & 2:
            tmp = code >> 2
            value = tmp - 14 if (tmp & 0x10) else tmp - 17
            bs.consume(7)
            return 1, value
        bs.consume(3)
        return 1, ((code >> 1) & 2) - 1

    bs.consume(2)
    if code & 2:
        return 1, 0
    return 8, 0


def _dec_1_17(bs):
    code = bs.peek_bits(7)
    if (code & 3) != 0:
        bs.consume(2)
        return 1, (code & 3) - 2

    bs.consume(7)
    tmp = code >> 2
    value = tmp - 14 if (tmp & 0x10) else tmp - 17
    return 1, value


def _dec_31(bs):
    code = bs.read_bits(6)
    if code != 0:
        return 1, code - 32
    return 6, 0


def _dec_0_1_33(bs):
    code = bs.peek_bits(8)
    if code & 1:
        if code & 2:
            tmp = code >> 2
            value = tmp - 30 if (tmp & 0x20) else tmp - 33
            bs.consume(8)
            return 1, value
        bs.consume(3)
        return 1, ((code >> 1) & 2) - 1

    bs.consume(2)
    if code & 2:
        return 1, 0
    return 8, 0


def _dec_3_35(bs):
    code = bs.peek_bits(8)
    low3 = code & 7
    if low3 < 3:
        if code & 2:
            bs.consume(4)
            return 1, 3 if (code & 8) else -3

        if code & 1:
            value = (code >> 3) + 4
        else:
            value = -4 - (code >> 3)
        bs.consume(8)
        return 1, value

    bs.consume(3)
    return 1, low3 - 5


def _dec_63(bs):
    code = bs.read_bits(7)
    if code != 0:
        return 1, code - 64
    return 7, 0


def _dec_127(bs):
    code = bs.read_bits(8)
    if code != 0:
        return 1, code - 128
    return 8, 0


def _dec_255(bs):
    code = bs.read_bits(9)
    if code != 0:
        return 1, code - 256
    return 8, 0


def _dec_511(bs):
    code = bs.read_bits(10)
    if code != 0:
        return 1, code - 512
    return 8, 0


def _dec_1023(bs):
    code = bs.read_bits(11)
    if code != 0:
        return 1, code - 1024
    return 8, 0


def _dec_15bit(bs):
    code = bs.read_bits(16)
    if code != 0:
        return 1, code - 0x8000
    return 8, 0


def _dec_23bit(bs):
    code = bs.read_bits(24)
    if code != 0:
        return 1, code - 0x800000
    return 8, 0


def _dec_31bit(bs):
    code = bs.read_bits(32)
    if code == 0x80000000:
        return 8, 0
    if code & 0x80000000:
        code -= 0x100000000
    return 1, code


def _dec_err(bs):
    del bs
    return 0, 0


DECODER_TABLE = {
    0: _dec_0,
    1: _dec_1a,
    2: _dec_1b,
    3: _dec_1c,
    4: _dec_1d,
    5: _dec_1e,
    6: _dec_2a,
    7: _dec_2b,
    8: _dec_2c,
    9: _dec_3a,
    10: _dec_3b,
    11: _dec_5a,
    12: _dec_7a,
    13: _dec_7b,
    14: _dec_7c,
    15: _dec_f15a,
    16: _dec_f15b,
    17: _dec_f15c,
    18: _dec_f31a,
    19: _dec_f31b,
    20: _dec_f31c,
    21: _dec_f31d,
    22: _dec_f63a,
    23: _dec_f63b,
    24: _dec_f127,
    25: _dec_f255,
    26: _dec_f2047,
    27: _dec_f15bit,
    28: _dec_f23bit,
    29: _dec_f31bit,
    30: _dec_err,
    31: _dec_err,
    32: _dec_0,
    33: _dec_1a,
    34: _dec_1b,
    35: _dec_1c,
    36: _dec_1d,
    37: _dec_1e,
    38: _dec_2a,
    39: _dec_2b,
    40: _dec_2c,
    41: _dec_3a,
    42: _dec_3b,
    43: _dec_5a,
    44: _dec_7a,
    45: _dec_7b,
    46: _dec_7c,
    47: _dec_15,
    48: _dec_0_16,
    49: _dec_0_1_17,
    50: _dec_1_17,
    51: _dec_31,
    52: _dec_0_1_33,
    53: _dec_3_35,
    54: _dec_63,
    55: _dec_127,
    56: _dec_255,
    57: _dec_511,
    58: _dec_1023,
    59: _dec_15bit,
    60: _dec_23bit,
    61: _dec_31bit,
    62: _dec_err,
    63: _dec_err,
}


class _TrackState:
    __slots__ = ("whole", "delta", "sec_delta", "zeros")

    def __init__(self):
        self.whole = 0.0
        self.delta = 0.0
        self.sec_delta = 0.0
        self.zeros = 0


ENTROPY_BASE_QUANT_STEP = 0.25
DEQUANT_SCALE = 0.0009765625
INITIAL_VALUES_BIT_TABLE = (2, 4, 7, 20)
SCENE_INITIAL_VALUES_BIT_TABLE = (4, 7, 12, 30)


def _quat_compose_xyz(x, y, z):
    w = math.sqrt(abs(1.0 - (x * x + y * y + z * z)))
    return (x, y, z, w)


def _quat_norm(q):
    x, y, z, w = q
    length2 = x * x + y * y + z * z + w * w
    if length2 <= 0.0:
        return (0.0, 0.0, 0.0, 1.0)
    inv = 1.0 / math.sqrt(length2)
    return (x * inv, y * inv, z * inv, w * inv)



def _quat_mul(q_delta, q_base):
    ax, ay, az, aw = q_delta
    bx, by, bz, bw = q_base
    out_x = bw * ax + ay * bz - az * by + bx * aw
    out_y = ay * bw + aw * by - bz * ax + bx * az
    out_z = ax * by - ay * bx + bw * az + bz * aw
    out_w = bw * aw - (ay * by + ax * bx + bz * az)
    return (out_x, out_y, out_z, out_w)

def _apply_quat_delta_to_tracks(tracks, idx):
    tx = tracks[idx]
    ty = tracks[idx + 1]
    tz = tracks[idx + 2]

    q_base = _quat_compose_xyz(tx.whole, ty.whole, tz.whole)
    q_delta = _quat_norm(_quat_compose_xyz(tx.delta, ty.delta, tz.delta))
    out_x, out_y, out_z, out_w = _quat_mul(q_delta, q_base)
    if out_w < 0.0:
        out_x = -out_x
        out_y = -out_y
        out_z = -out_z

    tx.whole = out_x
    ty.whole = out_y
    tz.whole = out_z


def _reconstruct_quat_initial(tracks, idx):
    _apply_quat_delta_to_tracks(tracks, idx)


def _apply_quat_delta_accum(tracks, idx):
    tx = tracks[idx]
    ty = tracks[idx + 1]
    tz = tracks[idx + 2]
    tx.delta += tx.sec_delta
    ty.delta += ty.sec_delta
    tz.delta += tz.sec_delta
    _apply_quat_delta_to_tracks(tracks, idx)


def _dequant_tracks(tracks, codec_ixs, dec, frame, scaled_quant, is_scene_anim):
    for t, track in enumerate(tracks):
        codec_byte = codec_ixs[t]
        mask_idx = codec_byte >> 6
        num = codec_byte & 0x3F

        if frame == 0:
            bits = SCENE_INITIAL_VALUES_BIT_TABLE[3] if is_scene_anim else INITIAL_VALUES_BIT_TABLE[3]
            base = dec.read_signed_bits(bits)
            track.zeros = 0
            track.whole = float(base) * (scaled_quant * ENTROPY_BASE_QUANT_STEP)
            continue

        if frame == 1:
            bits = SCENE_INITIAL_VALUES_BIT_TABLE[mask_idx] if is_scene_anim else INITIAL_VALUES_BIT_TABLE[mask_idx]
            d0 = dec.read_signed_bits(bits)
            track.delta = float(d0) * scaled_quant
            continue

        if num == 0:
            track.sec_delta = 0.0
            continue

        if track.zeros == 0:
            decoder_fn = DECODER_TABLE.get(num)
            if decoder_fn is None:
                raise PCANIMCodecError(f"Unsupported entropy decoder index {num}")
            runlen, decoded = decoder_fn(dec)
            track.zeros = int(runlen) - 1
            track.sec_delta = float(decoded) * scaled_quant
        else:
            track.zeros -= 1
            track.sec_delta = 0.0


def _integrate_for_frame_torso(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    scaled_quant = DEQUANT_SCALE * float(time_scale)
    _dequant_tracks(tracks, codec_ixs, dec, frame, scaled_quant, is_scene_anim)

    if frame == 0:
        return

    if frame == 1:
        decoded_tracks = 0
        for i in range(5):
            if mask & (1 << i):
                _reconstruct_quat_initial(tracks, decoded_tracks)
                decoded_tracks += 3

        if mask & 0x20:
            _reconstruct_quat_initial(tracks, decoded_tracks)
            track_ix = decoded_tracks + 3
            t0 = tracks[track_ix]
            track_ix += 1
            t1 = tracks[track_ix]
            t2 = tracks[track_ix + 1]
            t0.whole += t0.delta
            t1.whole += t1.delta
            t2.whole += t2.delta
        return

    track_ix = 0
    for i in range(5):
        if mask & (1 << i):
            _apply_quat_delta_accum(tracks, track_ix)
            track_ix += 3

    if mask & 0x20:
        _apply_quat_delta_accum(tracks, track_ix)

        tmp_ix = track_ix + 3
        for extra in range(3):
            te = tracks[tmp_ix + extra]
            d = te.sec_delta + te.delta
            te.delta = d
            te.whole += d


def _integrate_for_frame_quat_masked(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim, bit_count=8):
    scaled_quant = DEQUANT_SCALE * float(time_scale)
    _dequant_tracks(tracks, codec_ixs, dec, frame, scaled_quant, is_scene_anim)

    if frame == 0:
        return

    track_ix = 0
    for bit in range(bit_count):
        if (mask & (1 << bit)) == 0:
            continue
        if frame == 1:
            _reconstruct_quat_initial(tracks, track_ix)
        else:
            _apply_quat_delta_accum(tracks, track_ix)
        track_ix += 3


def _integrate_for_frame_fakeroot(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    scaled_quant = DEQUANT_SCALE * float(time_scale)
    _dequant_tracks(tracks, codec_ixs, dec, frame, scaled_quant, is_scene_anim)

    if frame == 0:
        return

    track_ix = 0
    if mask & 0x1:
        if frame == 1:
            _reconstruct_quat_initial(tracks, track_ix)
            for j in range(3, 6):
                t = tracks[track_ix + j]
                t.whole += t.delta
        else:
            _apply_quat_delta_accum(tracks, track_ix)
            for j in range(3, 6):
                t = tracks[track_ix + j]
                d = t.sec_delta + t.delta
                t.delta = d
                t.whole += d
        track_ix = 6

    if (mask & 0x2) and track_ix < len(tracks):
        t = tracks[track_ix]
        if frame == 1:
            t.whole += t.delta
        else:
            d = t.sec_delta + t.delta
            t.delta = d
            t.whole += d


def _integrate_for_frame_ik(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    scaled_quant = DEQUANT_SCALE * float(time_scale)
    _dequant_tracks(tracks, codec_ixs, dec, frame, scaled_quant, is_scene_anim)

    if frame == 0:
        return

    track_ix = 0

    for bit in range(2):
        if (mask & (1 << bit)) == 0:
            continue
        if frame == 1:
            _reconstruct_quat_initial(tracks, track_ix)
        else:
            _apply_quat_delta_accum(tracks, track_ix)
        track_ix += 3

    for bit in range(2, 4):
        if (mask & (1 << bit)) == 0:
            continue

        if frame == 1:
            _reconstruct_quat_initial(tracks, track_ix)
            for j in range(3, 7):
                t = tracks[track_ix + j]
                t.whole += t.delta
        else:
            _apply_quat_delta_accum(tracks, track_ix)
            for j in range(3, 7):
                t = tracks[track_ix + j]
                d = t.sec_delta + t.delta
                t.delta = d
                t.whole += d

        track_ix += 7


def _integrate_for_frame_linear(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    del mask
    scaled_quant = DEQUANT_SCALE * float(time_scale)
    _dequant_tracks(tracks, codec_ixs, dec, frame, scaled_quant, is_scene_anim)

    if frame == 0:
        return

    for t in tracks:
        if frame == 1:
            t.whole += t.delta
        else:
            d = t.sec_delta + t.delta
            t.delta = d
            t.whole += d


def _integrate_for_frame_arbitrary(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim, track_meta=None):
    scaled_quant = DEQUANT_SCALE * float(time_scale)
    _dequant_tracks(tracks, codec_ixs, dec, frame, scaled_quant, is_scene_anim)

    if frame == 0:
        return

    quat_bit_count = _get_arbitrary_quat_bit_count(track_meta)
    total_slot_count = _get_arbitrary_total_slot_count(track_meta)
    track_ix = 0
    for bit in _iter_mask_bits(mask, total_slot_count):
        if bit < quat_bit_count:
            if frame == 1:
                _reconstruct_quat_initial(tracks, track_ix)
            else:
                _apply_quat_delta_accum(tracks, track_ix)
        else:
            for j in range(3):
                t = tracks[track_ix + j]
                if frame == 1:
                    t.whole += t.delta
                else:
                    d = t.sec_delta + t.delta
                    t.delta = d
                    t.whole += d
        track_ix += 3

def _integrate_for_frame_noop(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    del tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim


def _integrate_for_frame_torso_head(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_torso(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_torso_head_std(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_torso(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_legs(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_quat_masked(
        tracks,
        codec_ixs,
        mask,
        frame,
        dec,
        time_scale,
        is_scene_anim,
        bit_count=8,
    )


def _integrate_for_frame_arms(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_quat_masked(
        tracks,
        codec_ixs,
        mask,
        frame,
        dec,
        time_scale,
        is_scene_anim,
        bit_count=8,
    )


def _integrate_for_frame_legs_ik(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_ik(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_arms_ik(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_ik(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_tentacle(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_linear(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_fing52(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_linear(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_fing5_curl(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_linear(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_fing5_reduced(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_linear(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


def _integrate_for_frame_fing5(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim):
    _integrate_for_frame_linear(tracks, codec_ixs, mask, frame, dec, time_scale, is_scene_anim)


_INTEGRATOR_BY_COMPONENT = {
    COMP_ARBITRARY_PO: _integrate_for_frame_arbitrary,
    COMP_GENERIC: _integrate_for_frame_noop,
    COMP_FAKEROOT_STD: _integrate_for_frame_fakeroot,
    COMP_TORSO_HEAD: _integrate_for_frame_torso_head,
    COMP_TORSO_HEAD_STD: _integrate_for_frame_torso_head_std,
    COMP_LEGS: _integrate_for_frame_legs,
    COMP_LEGS_IK: _integrate_for_frame_legs_ik,
    COMP_ARMS: _integrate_for_frame_arms,
    COMP_ARMS_IK: _integrate_for_frame_arms_ik,
    COMP_TENTACLE: _integrate_for_frame_tentacle,
    COMP_FING52: _integrate_for_frame_fing52,
    COMP_FING5_CURL: _integrate_for_frame_fing5_curl,
    COMP_FING5_REDUCED: _integrate_for_frame_fing5_reduced,
    COMP_FING5: _integrate_for_frame_fing5,
}


def _decode_component_frames(comp_ix, codec_ixs, encoded_data, mask, frame_count, current_time, is_scene_anim, track_meta=None):
    if frame_count <= 0:
        return []

    integrator = _INTEGRATOR_BY_COMPONENT.get(int(comp_ix))
    if integrator is None:
        raise PCANIMCodecError(f"No integrator for component {int(comp_ix)}")

    if not codec_ixs:
        return [[] for _ in range(frame_count)]

    tracks = [_TrackState() for _ in range(len(codec_ixs))]
    dec = _BitStream(encoded_data)

    out = []
    for frame in range(frame_count):
        if int(comp_ix) == COMP_ARBITRARY_PO:
            integrator(tracks, codec_ixs, mask, frame, dec, current_time, is_scene_anim, track_meta=track_meta)
        else:
            integrator(tracks, codec_ixs, mask, frame, dec, current_time, is_scene_anim)
        out.append([float(t.whole) for t in tracks])
    return out
