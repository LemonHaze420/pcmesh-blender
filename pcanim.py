import io
import math
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

    if base + 164 <= len(blob):
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


def _get_default_component_quat(skel_data, comp_ix, role_ix):
    comps = skel_data.get("components", [])
    for c in comps:
        if int(c.get("component_index",-1)) != comp_ix:
            continue

        dp = c.get("default_pose")
        if not dp:
            return None

        quats = dp.get("quats")
        if not quats:
            return None

        if role_ix < 0 or role_ix >= len(quats):
            return None

        # parser already stores WXYZ
        return _quat_normalize_wxyz(quats[role_ix])

    return None
    
def _build_component_order(skel_data):
    if not skel_data:
        return list(DEFAULT_COMP_ORDER)

    meta = skel_data.get("component_meta") or []
    if meta:
        order = []
        for comp in meta:
            ctype = int(comp.get("type", 0))
            order.append(NAL_TO_COMP_ID.get(ctype, COMP_GENERIC))
        if order:
            return order

    components = skel_data.get("components") or []
    if components:
        order = []
        for comp in components:
            ctype = int(comp.get("type_id", 0))
            order.append(NAL_TO_COMP_ID.get(ctype, COMP_GENERIC))
        if order:
            return order

    return list(DEFAULT_COMP_ORDER)


def _decode_anim_components(blob, anim, comp_order):
    components = []
    warnings = []

    base = int(anim.get("offset", 0))
    comp_list_abs = base + int(anim.get("comp_list_offset", 0)) - 8
    anim_list_abs = base + int(anim.get("anim_user_data_offset", 0))
    track_list_abs = base + int(anim.get("track_data_offset", 0))

    if comp_list_abs < 0 or anim_list_abs < 0 or track_list_abs < 0:
        return components, ["Invalid component table offsets"]

    anim_user_data_ix = 0
    track_ix = 0

    frame_count = max(1, int(anim.get("frame_count", 1)))
    current_time = float(anim.get("current_time", 0.0))
    is_scene_anim = bool(int(anim.get("flags", 0)) & FLAG_SCENE_ANIM)

    for comp_ix in comp_order:
        flag_off = comp_list_abs + int(comp_ix) * 4
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
                f"Anim '{anim.get('name', '')}' comp {comp_ix}: codec table out of bounds"
            )
            track_ix += 1
            continue

        codec_ixs = list(blob[codec_ixs_abs : codec_ixs_abs + ntracks])

        track_entry_offset = track_list_abs + (track_ix + 1) * 4
        if track_entry_offset < 0 or track_entry_offset + 4 > len(blob):
            warnings.append(
                f"Anim '{anim.get('name', '')}' comp {comp_ix}: track table entry out of bounds"
            )
            track_ix += 1
            continue

        track_offset = struct.unpack_from("<i", blob, track_entry_offset)[0]
        track_data_abs = track_list_abs + int(track_offset)

        encoded_size = _get_num_bytes_for_comp(comp_ix, mask)
        if encoded_size <= 0:
            warnings.append(
                f"Anim '{anim.get('name', '')}' comp {comp_ix}: unsupported encoded size formula"
            )
            track_ix += 1
            continue

        if track_data_abs < 0 or track_data_abs + encoded_size > len(blob):
            warnings.append(
                f"Anim '{anim.get('name', '')}' comp {comp_ix}: encoded track data out of bounds"
            )
            track_ix += 1
            continue

        encoded_data = bytes(blob[track_data_abs : track_data_abs + encoded_size])

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
                f"Anim '{anim.get('name', '')}' comp {comp_ix}: {decode_error}"
            )

        components.append(
            {
                "comp_ix": int(comp_ix),
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


def _find_component_by_type(skel_data, type_values):
    comps = skel_data.get("components", []) if skel_data else []
    wanted = set(int(v) for v in type_values)
    for comp in comps:
        ctype = int(comp.get("type_id", 0))
        if ctype in wanted:
            return comp
    return None


def _quat_normalize_wxyz(q):
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    n2 = w * w + x * x + y * y + z * z
    if n2 <= 1e-20:
        return (1.0, 0.0, 0.0, 0.0)
    inv = 1.0 / math.sqrt(n2)
    return (w * inv, x * inv, y * inv, z * inv)


def _quat_inverse_wxyz(q):
    w, x, y, z = _quat_normalize_wxyz(q)
    return (w, -x, -y, -z)


def _quat_mul_wxyz(a, b):
    aw, ax, ay, az = _quat_normalize_wxyz(a)
    bw, bx, by, bz = _quat_normalize_wxyz(b)
    return _quat_normalize_wxyz((
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ))


_BASIS_M_ENGINE_TO_BLENDER = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, -1.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]
_BASIS_M_BLENDER_TO_ENGINE = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, -1.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def _engine_to_blender_quat_wxyz(q):
    qn = _quat_normalize_wxyz(q)
    rot_eng = _mat_from_quat_pos(qn, (0.0, 0.0, 0.0))
    rot_bl = _mat_local_to_world(
        _mat_local_to_world(_BASIS_M_ENGINE_TO_BLENDER, rot_eng),
        _BASIS_M_BLENDER_TO_ENGINE,
    )
    return _quat_from_matrix_wxyz(rot_bl)


def _quat_from_xyz(x, y, z):
    w = math.sqrt(abs(1.0 - (x * x + y * y + z * z)))
    n2 = w * w + x * x + y * y + z * z
    if n2 <= 0.0:
        return (1.0, 0.0, 0.0, 0.0)
    inv = 1.0 / math.sqrt(n2)
    return (w * inv, x * inv, y * inv, z * inv)


def _safe_bone_idx(indices, role_idx):
    if not indices:
        return None
    if role_idx < 0 or role_idx >= len(indices):
        return None
    bid = int(indices[role_idx])
    if bid < 0:
        return None
    return bid


def _assign_rot(bone_tracks, bone_id, frame_no, quat_wxyz):
    if bone_id is None:
        return
    entry = bone_tracks.setdefault(int(bone_id), {"rotation": {}, "location": {}})
    entry["rotation"][int(frame_no)] = tuple(float(v) for v in quat_wxyz)


def _assign_loc(bone_tracks, bone_id, frame_no, vec_xyz):
    if bone_id is None:
        return
    entry = bone_tracks.setdefault(int(bone_id), {"rotation": {}, "location": {}})
    entry["location"][int(frame_no)] = tuple(float(v) for v in vec_xyz)


def _consume_xyz(values, cursor):
    if cursor + 3 > len(values):
        return None, cursor
    return (float(values[cursor]), float(values[cursor + 1]), float(values[cursor + 2])), cursor + 3


def _vec_dot(a, b):
    return float(a[0] * b[0] + a[1] * b[1] + a[2] * b[2])


def _vec_cross(a, b):
    return (
        float(a[1] * b[2] - a[2] * b[1]),
        float(a[2] * b[0] - a[0] * b[2]),
        float(a[0] * b[1] - a[1] * b[0]),
    )


def _vec_len(v):
    return math.sqrt(max(0.0, _vec_dot(v, v)))


def _vec_norm(v):
    l = _vec_len(v)
    if l <= 1e-12:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / l
    return (v[0] * inv, v[1] * inv, v[2] * inv)


def _mat_identity():
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_compose_from_basis(x_axis, y_axis, z_axis, pos):
    return [
        [float(x_axis[0]), float(x_axis[1]), float(x_axis[2]), 0.0],
        [float(y_axis[0]), float(y_axis[1]), float(y_axis[2]), 0.0],
        [float(z_axis[0]), float(z_axis[1]), float(z_axis[2]), 0.0],
        [float(pos[0]), float(pos[1]), float(pos[2]), 1.0],
    ]


def _mat_from_quat_pos(q_wxyz, pos_xyz):
    w, x, y, z = _quat_normalize_wxyz(q_wxyz)

    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    x_axis = (1.0 - 2.0 * (yy + zz), 2.0 * (xy + wz), 2.0 * (xz - wy))
    y_axis = (2.0 * (xy - wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz + wx))
    z_axis = (2.0 * (xz + wy), 2.0 * (yz - wx), 1.0 - 2.0 * (xx + yy))

    return _mat_compose_from_basis(x_axis, y_axis, z_axis, pos_xyz)


def _mat_local_to_world(local_m, parent_m):
    out = [[0.0, 0.0, 0.0, 0.0] for _ in range(4)]
    for r in range(4):
        for c in range(4):
            out[r][c] = (
                local_m[r][0] * parent_m[0][c]
                + local_m[r][1] * parent_m[1][c]
                + local_m[r][2] * parent_m[2][c]
                + local_m[r][3] * parent_m[3][c]
            )
    return out


def _mat_copy(m):
    return [list(m[0]), list(m[1]), list(m[2]), list(m[3])]


def _mat_rigid_inverse(m):
    r00, r01, r02 = float(m[0][0]), float(m[0][1]), float(m[0][2])
    r10, r11, r12 = float(m[1][0]), float(m[1][1]), float(m[1][2])
    r20, r21, r22 = float(m[2][0]), float(m[2][1]), float(m[2][2])
    tx, ty, tz = float(m[3][0]), float(m[3][1]), float(m[3][2])

    out = _mat_identity()
    out[0][0], out[0][1], out[0][2] = r00, r10, r20
    out[1][0], out[1][1], out[1][2] = r01, r11, r21
    out[2][0], out[2][1], out[2][2] = r02, r12, r22
    out[3][0] = -(tx * r00 + ty * r01 + tz * r02)
    out[3][1] = -(tx * r10 + ty * r11 + tz * r12)
    out[3][2] = -(tx * r20 + ty * r21 + tz * r22)
    return out


def _build_twist_line_xform(pos_xyz, angle):
    s = math.sin(float(angle))
    c = math.cos(float(angle))
    m = _mat_identity()
    m[2][1] = -c
    m[1][1] = s
    m[2][2] = s
    m[1][2] = c
    m[3][0] = float(pos_xyz[0])
    m[3][1] = float(pos_xyz[1])
    m[3][2] = float(pos_xyz[2])
    return m


def _cache_component_world_write_once(frame_xforms, component_world):
    if not component_world:
        return

    wrote = set()
    for bid, world_m in component_world.items():
        if bid is None or world_m is None:
            continue
        ibid = int(bid)
        if ibid in wrote:
            continue
        wrote.add(ibid)
        frame_xforms[ibid] = _mat_copy(world_m)


def _assign_rot_from_runtime_parent_world(
    bone_tracks,
    bone_id,
    frame_no,
    frame_xforms,
    parent_id,
    default_quat=None,
):
    if bone_id is None:
        return
    ibid = int(bone_id)
    if ibid not in frame_xforms:
        return

    local_xform = frame_xforms[ibid]
    if parent_id is not None:
        ipid = int(parent_id)
        if ipid >= 0 and ipid in frame_xforms:
            parent_inv = _mat_rigid_inverse(frame_xforms[ipid])
            local_xform = _mat_local_to_world(local_xform, parent_inv)

    q_local = _quat_from_matrix_wxyz(local_xform)
    if default_quat is not None:
        q_local = _quat_mul_wxyz(_quat_inverse_wxyz(default_quat), _quat_normalize_wxyz(q_local))
    _assign_rot(bone_tracks, ibid, frame_no, _engine_to_blender_quat_wxyz(q_local))


def _quat_from_matrix_wxyz(m):
    m00, m01, m02 = float(m[0][0]), float(m[0][1]), float(m[0][2])
    m10, m11, m12 = float(m[1][0]), float(m[1][1]), float(m[1][2])
    m20, m21, m22 = float(m[2][0]), float(m[2][1]), float(m[2][2])

    trace = m00 + m11 + m22
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m12 - m21) / s
        y = (m20 - m02) / s
        z = (m01 - m10) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(max(1e-20, 1.0 + m00 - m11 - m22)) * 2.0
        w = (m12 - m21) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m20 + m02) / s
    elif m11 > m22:
        s = math.sqrt(max(1e-20, 1.0 + m11 - m00 - m22)) * 2.0
        w = (m20 - m02) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = math.sqrt(max(1e-20, 1.0 + m22 - m00 - m11)) * 2.0
        w = (m01 - m10) / s
        x = (m20 + m02) / s
        y = (m12 + m21) / s
        z = 0.25 * s

    q = _quat_normalize_wxyz((w, x, y, z))
    if q[0] < 0.0:
        return (-q[0], -q[1], -q[2], -q[3])
    return q


def _project_point_onto_line_xform(point_xyz, xform):
    px, py, pz = float(point_xyz[0]), float(point_xyz[1]), float(point_xyz[2])
    return (
        xform[3][0] + px * xform[0][0] + py * xform[1][0] + pz * xform[2][0],
        xform[3][1] + px * xform[0][1] + py * xform[1][1] + pz * xform[2][1],
        xform[3][2] + px * xform[0][2] + py * xform[1][2] + pz * xform[2][2],
    )


def _nal_ik_solve_2d(hinge_xform, base_joint_xyz, target_xyz, ik_data):
    model_base_joint = _project_point_onto_line_xform(base_joint_xyz, hinge_xform)
    target_dir = (
        float(target_xyz[0] - model_base_joint[0]),
        float(target_xyz[1] - model_base_joint[1]),
        float(target_xyz[2] - model_base_joint[2]),
    )

    dist = _vec_len(target_dir)
    if dist <= 1e-12:
        dist = 1e-12
    target_dir = (target_dir[0] / dist, target_dir[1] / dist, target_dir[2] / dist)

    upper_c = float(ik_data.get("fUpperIKc", 0.0))
    upper_invc = float(ik_data.get("fUpperIKInvc", 0.0))
    lower_c = float(ik_data.get("fLowerIKc", 0.0))
    lower_invc = float(ik_data.get("fLowerIKInvc", 0.0))

    cos_upper = (dist * upper_c) + ((1.0 / dist) * upper_invc)
    cos_lower = (dist * lower_c) + ((1.0 / dist) * lower_invc)
    cos_upper = max(-1.0, min(1.0, cos_upper))
    cos_lower = max(-1.0, min(1.0, cos_lower))

    sin_upper = math.sqrt(max(0.0, 1.0 - cos_upper * cos_upper))
    sin_lower = math.sqrt(max(0.0, 1.0 - cos_lower * cos_lower))

    return {
        "model_base_joint": model_base_joint,
        "target_dir": target_dir,
        "sin_upper": sin_upper,
        "cos_upper": cos_upper,
        "sin_lower": sin_lower,
        "cos_lower": cos_lower,
    }


def _leg_heuristic(target_model_matrix, axis_xyz):
    row1 = (
        float(target_model_matrix[1][0]),
        float(target_model_matrix[1][1]),
        float(target_model_matrix[1][2]),
    )
    return _vec_cross(axis_xyz, row1)


def _nal_ik_map_2d_to_3d(
    upper_limb_length,
    sin_upper,
    cos_upper,
    sin_lower,
    cos_lower,
    model_base_joint,
    model_target_dir,
    model_mid_joint_dir,
    sin_twist,
    cos_twist,
):
    z_axis = _vec_norm(_vec_cross(model_target_dir, model_mid_joint_dir))
    y_axis = _vec_cross(z_axis, model_target_dir)
    x_axis = model_target_dir

    basis = _mat_compose_from_basis(x_axis, y_axis, z_axis, model_base_joint)

    upper_local = _mat_compose_from_basis(
        (cos_upper, sin_upper * cos_twist, sin_upper * sin_twist),
        (-sin_upper, cos_upper * cos_twist, cos_upper * sin_twist),
        (0.0, -sin_twist, cos_twist),
        (0.0, 0.0, 0.0),
    )
    upper_model = _mat_local_to_world(upper_local, basis)

    lower_local = _mat_compose_from_basis(
        (cos_lower, -(sin_lower * cos_twist), -(sin_lower * sin_twist)),
        (sin_lower, cos_lower * cos_twist, cos_lower * sin_twist),
        (0.0, -sin_twist, cos_twist),
        (
            upper_limb_length * cos_upper,
            cos_twist * (upper_limb_length * sin_upper),
            sin_twist * (upper_limb_length * sin_upper),
        ),
    )
    lower_model = _mat_local_to_world(lower_local, basis)

    return upper_model, lower_model


def _decompose_ik_spin(base_model_matrix, base_joint_xyz, target_model_matrix, ik_data, heuristic_fn, spin_angle):
    target_pos = (
        float(target_model_matrix[3][0]),
        float(target_model_matrix[3][1]),
        float(target_model_matrix[3][2]),
    )

    solved = _nal_ik_solve_2d(base_model_matrix, base_joint_xyz, target_pos, ik_data)
    model_target_dir = solved["target_dir"]
    model_mid_joint_dir = heuristic_fn(target_model_matrix, model_target_dir)

    sin_twist = math.sin(float(spin_angle))
    cos_twist = math.cos(float(spin_angle))

    upper_model, lower_model = _nal_ik_map_2d_to_3d(
        upper_limb_length=float(ik_data.get("fUpperArmLength", 0.0)),
        sin_upper=solved["sin_upper"],
        cos_upper=solved["cos_upper"],
        sin_lower=solved["sin_lower"],
        cos_lower=solved["cos_lower"],
        model_base_joint=solved["model_base_joint"],
        model_target_dir=model_target_dir,
        model_mid_joint_dir=model_mid_joint_dir,
        sin_twist=sin_twist,
        cos_twist=cos_twist,
    )

    def _remap_rows(m):
        r0 = list(m[0])
        r1 = list(m[1])
        r2 = list(m[2])
        m[0] = [-r0[0], -r0[1], -r0[2], -r0[3]]
        m[1] = [-r2[0], -r2[1], -r2[2], -r2[3]]
        m[2] = [-r1[0], -r1[1], -r1[2], -r1[3]]

    _remap_rows(upper_model)
    _remap_rows(lower_model)
    return upper_model, lower_model


def _components_to_bone_tracks(
    decoded_components,
    skel_data,
    apply_root_motion=False,
    solve_ik=False,
    use_full_arm_tracks=True,
):
    if not skel_data or not decoded_components:
        return {}

    bone_tracks = {}

    frame_xforms = {}

    def _frame_map(frame_no):
        key = int(frame_no)
        fm = frame_xforms.get(key)
        if fm is None:
            fm = {}
            frame_xforms[key] = fm
        return fm

    def _id_quat():
        return (1.0, 0.0, 0.0, 0.0)

    torso_comp = _find_component_by_type(skel_data, (NAL_TORSO_ONE_NECK, NAL_TORSO_TWO_NECK))
    legs_std_comp = _find_component_by_type(skel_data, (NAL_LEGS,))
    legs_ik_comp = _find_component_by_type(skel_data, (NAL_LEGS_IK,))
    arms_comp = _find_component_by_type(skel_data, (NAL_ARMS,))
    arms_ik_comp = _find_component_by_type(skel_data, (NAL_ARMS_IK,))

    torso_bones = list(torso_comp.get("bone_indices", ())) if torso_comp else []
    torso_type_id = int(torso_comp.get("type_id", 0)) if torso_comp else 0
    torso_has_empty_neck = torso_type_id == int(NAL_TORSO_TWO_NECK)
    torso_offsets = list(torso_comp.get("offset_locs", ())) if torso_comp else []
    torso_other = list(torso_comp.get("other_matrix_indices", ())) if torso_comp else []
    empty_neck_orient_xyzw = tuple(torso_comp.get("empty_neck_orient", (0.0, 0.0, 0.0, 1.0))) if torso_comp else (0.0, 0.0, 0.0, 1.0)
    empty_neck_orient = (
        float(empty_neck_orient_xyzw[3]),
        float(empty_neck_orient_xyzw[0]),
        float(empty_neck_orient_xyzw[1]),
        float(empty_neck_orient_xyzw[2]),
    ) if len(empty_neck_orient_xyzw) == 4 else _id_quat()
    empty_neck_pos = tuple(torso_comp.get("empty_neck_pos", (0.0, 0.0, 0.0))) if torso_comp else (0.0, 0.0, 0.0)
    torso_default = (torso_comp or {}).get("default_pose", {})
    torso_default_quats = list(torso_default.get("quats", ()))
    torso_state_quats = [
        _quat_normalize_wxyz(torso_default_quats[i]) if i < len(torso_default_quats) else _id_quat()
        for i in range(6)
    ]
    torso_state_pelvis_pos = tuple(float(v) for v in torso_default.get("pelvis_pos", (0.0, 0.0, 0.0)))

    def _default_quat_or_none(quats, idx):
        if idx < 0 or idx >= len(quats):
            return None
        q = quats[idx]
        if not q or len(q) != 4:
            return None
        return _quat_normalize_wxyz(q)

    def _assign_runtime_local_rot(bone_id, frame_no, quat_wxyz, default_quat=None):
        if bone_id is None:
            return
        q_local = _quat_normalize_wxyz(quat_wxyz)
        if default_quat is not None:
            q_local = _quat_mul_wxyz(_quat_inverse_wxyz(default_quat), q_local)
        _assign_rot(
            bone_tracks,
            bone_id,
            frame_no,
            _engine_to_blender_quat_wxyz(q_local),
        )

    legs_std_bones = list(legs_std_comp.get("bone_indices", ())) if legs_std_comp else []
    legs_std_offsets = list(legs_std_comp.get("offset_locs", ())) if legs_std_comp else []
    legs_std_other = list(legs_std_comp.get("other_matrix_indices", ())) if legs_std_comp else []
    legs_std_default = (legs_std_comp or {}).get("default_pose", {})
    legs_std_default_quats = list(legs_std_default.get("quats", ()))
    legs_std_state_quats = [
        _quat_normalize_wxyz(legs_std_default_quats[i]) if i < len(legs_std_default_quats) else _id_quat()
        for i in range(8)
    ]

    legs_ik_bones = list(legs_ik_comp.get("bone_indices", ())) if legs_ik_comp else []
    legs_offsets = list(legs_ik_comp.get("offset_locs", ())) if legs_ik_comp else []
    legs_ik_data = list(legs_ik_comp.get("ik_data", ())) if legs_ik_comp else []
    legs_ik_other = list(legs_ik_comp.get("other_matrix_indices", ())) if legs_ik_comp else []
    legs_ik_default = (legs_ik_comp or {}).get("default_pose", {})
    legs_ik_default_quats = list(legs_ik_default.get("quats", ()))
    legs_ik_state_toe_quats = [
        _quat_normalize_wxyz(legs_ik_default_quats[i]) if i < len(legs_ik_default_quats) else _id_quat()
        for i in range(2)
    ]
    legs_ik_state_foot_quats = [
        _quat_normalize_wxyz(legs_ik_default_quats[i + 2]) if (i + 2) < len(legs_ik_default_quats) else _id_quat()
        for i in range(2)
    ]
    legs_ik_default_pos = list(legs_ik_default.get("foot_pos", ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))))
    while len(legs_ik_default_pos) < 2:
        legs_ik_default_pos.append((0.0, 0.0, 0.0))
    legs_ik_state_foot_pos = [
        (float(legs_ik_default_pos[0][0]), float(legs_ik_default_pos[0][1]), float(legs_ik_default_pos[0][2])),
        (float(legs_ik_default_pos[1][0]), float(legs_ik_default_pos[1][1]), float(legs_ik_default_pos[1][2])),
    ]
    legs_ik_default_spin = list(legs_ik_default.get("knee_spin", (0.0, 0.0)))
    while len(legs_ik_default_spin) < 2:
        legs_ik_default_spin.append(0.0)
    legs_ik_state_knee_spin = [float(legs_ik_default_spin[0]), float(legs_ik_default_spin[1])]

    arms_bones = list(arms_comp.get("bone_indices", ())) if arms_comp else []
    arms_offsets = list(arms_comp.get("offset_locs", ())) if arms_comp else []
    arms_other = list(arms_comp.get("other_matrix_indices", ())) if arms_comp else []
    arms_fore_twist = list(arms_comp.get("fore_twist_locs", ())) if arms_comp else []
    arms_default = (arms_comp or {}).get("default_pose", {})
    arms_default_quats = list(arms_default.get("quats", ()))
    arms_state_quats = [
        _quat_normalize_wxyz(arms_default_quats[i]) if i < len(arms_default_quats) else _id_quat()
        for i in range(8)
    ]
    arms_ik_bones = list(arms_ik_comp.get("bone_indices", ())) if arms_ik_comp else []
    arms_ik_default = (arms_ik_comp or {}).get("default_pose", {})
    arms_ik_default_track_quats = list(arms_ik_default.get("track_quats", ()))
    arms_ik_default_hand_quats = list(arms_ik_default.get("hand_quats", ()))

    # TorsoHeadBones
    TORSO_PELVIS = 0
    TORSO_SPINE = 1
    TORSO_SPINE1 = 2
    TORSO_SPINE2 = 3
    TORSO_NECK = 4
    TORSO_HEAD = 5

    # LegsBones
    LEGS_L_TOE = 0
    LEGS_R_TOE = 1
    LEGS_L_FOOT = 2
    LEGS_R_FOOT = 3

    # ArmHandsCompressedBones
    ARMS_L_CLAV = 0
    ARMS_L_UPPER = 1
    ARMS_L_FORE = 2
    ARMS_R_CLAV = 4
    ARMS_R_UPPER = 5
    ARMS_R_FORE = 6
    ARMS_L_HAND = 3
    ARMS_R_HAND = 7

    # ArmsHandsIKBones
    ARMSIK_L_CLAV = 0
    ARMSIK_R_CLAV = 1
    ARMSIK_L_HAND = 2
    ARMSIK_R_HAND = 3

    comp_eval_order = _build_component_order(skel_data)
    comp_rank = {int(cid): idx for idx, cid in enumerate(comp_eval_order)}
    comps_sorted = sorted(
        decoded_components,
        key=lambda c: comp_rank.get(int(c.get("comp_ix", -1)), 10_000),
    )

    for comp in comps_sorted:
        comp_ix = int(comp.get("comp_ix", -1))
        mask = int(comp.get("mask", 0))
        frames = comp.get("frames", [])
        if not frames:
            continue

        for frame_idx, values in enumerate(frames):
            frame_no = frame_idx + 1
            cursor = 0

            if comp_ix in (COMP_TORSO_HEAD, COMP_TORSO_HEAD_STD):
                frame_mats = _frame_map(frame_no)
                comp_world = {}

                for bit in range(5):
                    if (mask & (1 << bit)) == 0:
                        continue
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is None:
                        break
                    torso_state_quats[bit] = _quat_from_xyz(*xyz)

                if mask & 0x20:
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is not None:
                        torso_state_quats[5] = _quat_from_xyz(*xyz)

                    loc, cursor = _consume_xyz(values, cursor)
                    if loc is not None:
                        torso_state_pelvis_pos = (float(loc[0]), float(loc[1]), float(loc[2]))
                        if apply_root_motion:
                            pelvis_id = _safe_bone_idx(torso_bones, TORSO_PELVIS)
                            _assign_loc(bone_tracks, pelvis_id, frame_no, torso_state_pelvis_pos)

                # component-local
                if len(torso_bones) >= 6 and len(torso_offsets) >= 5:
                    pelvis_id = _safe_bone_idx(torso_bones, TORSO_PELVIS)
                    if pelvis_id is not None:
                        comp_world[pelvis_id] = _mat_from_quat_pos(torso_state_quats[5], torso_state_pelvis_pos)

                    for i in range(5):
                        bid = _safe_bone_idx(torso_bones, i + 1)
                        if bid is None:
                            continue
                        comp_world[bid] = _mat_from_quat_pos(torso_state_quats[i], torso_offsets[i])

                    for i in range(1, 6):
                        child = _safe_bone_idx(torso_bones, i)
                        parent = _safe_bone_idx(torso_bones, i - 1)
                        if child is None or parent is None:
                            continue
                        if child in comp_world and parent in comp_world:
                            comp_world[child] = _mat_local_to_world(comp_world[child], comp_world[parent])

                    if torso_has_empty_neck and len(torso_other) >= 1:
                        other0 = int(torso_other[0])
                        if other0 >= 0:
                            comp_world[other0] = _mat_from_quat_pos(empty_neck_orient, empty_neck_pos)
                            spine2_id = _safe_bone_idx(torso_bones, TORSO_SPINE2)
                            if spine2_id is not None and spine2_id in comp_world:
                                comp_world[other0] = _mat_local_to_world(comp_world[other0], comp_world[spine2_id])
                    _cache_component_world_write_once(frame_mats, comp_world)

                    if pelvis_id is not None:
                        _assign_runtime_local_rot(
                            pelvis_id,
                            frame_no,
                            torso_state_quats[5],
                            default_quat=_default_quat_or_none(torso_default_quats, 5),
                        )

                    for i in range(5):
                        bid = _safe_bone_idx(torso_bones, i + 1)
                        if bid is None:
                            continue
                        _assign_runtime_local_rot(
                            bid,
                            frame_no,
                            torso_state_quats[i],
                            default_quat=_default_quat_or_none(torso_default_quats, i),
                        )

                    if torso_has_empty_neck and len(torso_other) >= 1:
                        other0 = int(torso_other[0])
                        if other0 >= 0 and other0 in frame_mats:
                            _assign_runtime_local_rot(
                                other0,
                                frame_no,
                                empty_neck_orient,
                                default_quat=empty_neck_orient,
                            )

            elif comp_ix == COMP_LEGS_IK:
                frame_mats = _frame_map(frame_no)

                for bit in range(2):
                    if (mask & (1 << bit)) == 0:
                        continue
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is None:
                        break
                    legs_ik_state_toe_quats[bit] = _quat_from_xyz(*xyz)

                for bit in range(2, 4):
                    if (mask & (1 << bit)) == 0:
                        continue

                    qxyz, cursor = _consume_xyz(values, cursor)
                    if qxyz is None:
                        break
                    legs_ik_state_foot_quats[bit - 2] = _quat_from_xyz(*qxyz)

                    pos_xyz, cursor = _consume_xyz(values, cursor)
                    if pos_xyz is not None:
                        legs_ik_state_foot_pos[bit - 2] = (
                            float(pos_xyz[0]),
                            float(pos_xyz[1]),
                            float(pos_xyz[2]),
                        )

                    if cursor < len(values):
                        legs_ik_state_knee_spin[bit - 2] = float(values[cursor])
                        cursor += 1

                can_build_legs_ik = (
                    len(legs_ik_bones) >= 8
                    and len(legs_offsets) >= 8
                    and len(legs_ik_data) >= 2
                    and len(legs_ik_other) >= 1
                )

                if can_build_legs_ik:
                    comp_world = {}

                    l_foot_id = _safe_bone_idx(legs_ik_bones, 2)
                    r_foot_id = _safe_bone_idx(legs_ik_bones, 3)
                    l_thigh_id = _safe_bone_idx(legs_ik_bones, 4)
                    l_calf_id = _safe_bone_idx(legs_ik_bones, 5)
                    r_thigh_id = _safe_bone_idx(legs_ik_bones, 6)
                    r_calf_id = _safe_bone_idx(legs_ik_bones, 7)

                    if l_foot_id is not None:
                        comp_world[l_foot_id] = _mat_from_quat_pos(legs_ik_state_foot_quats[0], legs_ik_state_foot_pos[0])
                    if r_foot_id is not None:
                        comp_world[r_foot_id] = _mat_from_quat_pos(legs_ik_state_foot_quats[1], legs_ik_state_foot_pos[1])

                    if solve_ik and l_foot_id is not None and l_foot_id in comp_world and l_thigh_id is not None and l_calf_id is not None:
                        l_upper, l_lower = _decompose_ik_spin(
                            base_model_matrix=_mat_identity(),
                            base_joint_xyz=legs_offsets[4],
                            target_model_matrix=comp_world[l_foot_id],
                            ik_data=legs_ik_data[0],
                            heuristic_fn=_leg_heuristic,
                            spin_angle=legs_ik_state_knee_spin[0],
                        )
                        comp_world[l_thigh_id] = l_upper
                        comp_world[l_calf_id] = l_lower

                    if solve_ik and r_foot_id is not None and r_foot_id in comp_world and r_thigh_id is not None and r_calf_id is not None:
                        r_upper, r_lower = _decompose_ik_spin(
                            base_model_matrix=_mat_identity(),
                            base_joint_xyz=legs_offsets[6],
                            target_model_matrix=comp_world[r_foot_id],
                            ik_data=legs_ik_data[1],
                            heuristic_fn=_leg_heuristic,
                            spin_angle=legs_ik_state_knee_spin[1],
                        )
                        comp_world[r_thigh_id] = r_upper
                        comp_world[r_calf_id] = r_lower

                    anchor_id = int(legs_ik_other[0])
                    anchor_world = frame_mats.get(anchor_id, _mat_identity()) if anchor_id >= 0 else _mat_identity()

                    for role in (2, 3, 4, 5, 6, 7):
                        bid = _safe_bone_idx(legs_ik_bones, role)
                        if bid is None or bid not in comp_world:
                            continue
                        comp_world[bid] = _mat_local_to_world(comp_world[bid], anchor_world)

                    for side in (0, 1):
                        toe_id = _safe_bone_idx(legs_ik_bones, side)
                        foot_id = _safe_bone_idx(legs_ik_bones, side + 2)
                        if toe_id is None:
                            continue

                        toe_off = legs_offsets[side] if side < len(legs_offsets) else (0.0, 0.0, 0.0)
                        toe_local = _mat_from_quat_pos(legs_ik_state_toe_quats[side], toe_off)
                        if foot_id is not None and foot_id in comp_world:
                            comp_world[toe_id] = _mat_local_to_world(toe_local, comp_world[foot_id])
                        else:
                            comp_world[toe_id] = toe_local

                    _cache_component_world_write_once(frame_mats, comp_world)

                l_toe_id = _safe_bone_idx(legs_ik_bones, 0)
                r_toe_id = _safe_bone_idx(legs_ik_bones, 1)
                l_foot_id = _safe_bone_idx(legs_ik_bones, 2)
                r_foot_id = _safe_bone_idx(legs_ik_bones, 3)
                l_thigh_id = _safe_bone_idx(legs_ik_bones, 4)
                l_calf_id = _safe_bone_idx(legs_ik_bones, 5)
                r_thigh_id = _safe_bone_idx(legs_ik_bones, 6)
                r_calf_id = _safe_bone_idx(legs_ik_bones, 7)
                _assign_runtime_local_rot(
                    l_toe_id,
                    frame_no,
                    legs_ik_state_toe_quats[0],
                    default_quat=_default_quat_or_none(legs_ik_default_quats, 0),
                )
                _assign_runtime_local_rot(
                    r_toe_id,
                    frame_no,
                    legs_ik_state_toe_quats[1],
                    default_quat=_default_quat_or_none(legs_ik_default_quats, 1),
                )
                _assign_runtime_local_rot(
                    l_foot_id,
                    frame_no,
                    legs_ik_state_foot_quats[0],
                    default_quat=_default_quat_or_none(legs_ik_default_quats, 2),
                )
                _assign_runtime_local_rot(
                    r_foot_id,
                    frame_no,
                    legs_ik_state_foot_quats[1],
                    default_quat=_default_quat_or_none(legs_ik_default_quats, 3),
                )

                if can_build_legs_ik and solve_ik:
                    anchor_id = int(legs_ik_other[0]) if len(legs_ik_other) >= 1 else -1
                    _assign_rot_from_runtime_parent_world(
                        bone_tracks,
                        l_thigh_id,
                        frame_no,
                        frame_mats,
                        anchor_id,
                        default_quat=_default_quat_or_none(legs_std_default_quats, 4),
                    )
                    _assign_rot_from_runtime_parent_world(
                        bone_tracks,
                        l_calf_id,
                        frame_no,
                        frame_mats,
                        l_thigh_id,
                        default_quat=_default_quat_or_none(legs_std_default_quats, 5),
                    )
                    _assign_rot_from_runtime_parent_world(
                        bone_tracks,
                        r_thigh_id,
                        frame_no,
                        frame_mats,
                        anchor_id,
                        default_quat=_default_quat_or_none(legs_std_default_quats, 6),
                    )
                    _assign_rot_from_runtime_parent_world(
                        bone_tracks,
                        r_calf_id,
                        frame_no,
                        frame_mats,
                        r_thigh_id,
                        default_quat=_default_quat_or_none(legs_std_default_quats, 7),
                    )

            elif comp_ix == COMP_LEGS:
                frame_mats = _frame_map(frame_no)

                for bit in range(8):
                    if (mask & (1 << bit)) == 0:
                        continue
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is None:
                        break
                    legs_std_state_quats[bit] = _quat_from_xyz(*xyz)

                can_build_std_legs = (
                    len(legs_std_bones) >= 8 and len(legs_std_offsets) >= 8 and len(legs_std_other) >= 1
                )

                if can_build_std_legs:
                    comp_world = {}
                    for i in range(8):
                        bid = _safe_bone_idx(legs_std_bones, i)
                        if bid is None:
                            continue
                        comp_world[bid] = _mat_from_quat_pos(legs_std_state_quats[i], legs_std_offsets[i])

                    anchor_id = int(legs_std_other[0])
                    anchor_world = frame_mats.get(anchor_id, _mat_identity()) if anchor_id >= 0 else _mat_identity()

                    for i in range(8):
                        bid = _safe_bone_idx(legs_std_bones, i)
                        if bid is None or bid not in comp_world:
                            continue
                        if i == 0 or i == 4:
                            comp_world[bid] = _mat_local_to_world(comp_world[bid], anchor_world)
                        else:
                            prev_bid = _safe_bone_idx(legs_std_bones, i - 1)
                            if prev_bid is not None and prev_bid in comp_world:
                                comp_world[bid] = _mat_local_to_world(comp_world[bid], comp_world[prev_bid])

                    _cache_component_world_write_once(frame_mats, comp_world)
                    for i in range(8):
                        bid = _safe_bone_idx(legs_std_bones, i)
                        if bid is None:
                            continue
                        _assign_runtime_local_rot(
                            bid,
                            frame_no,
                            legs_std_state_quats[i],
                            default_quat=_default_quat_or_none(legs_std_default_quats, i),
                        )
                else:
                    bit_to_role = {
                        0: LEGS_L_TOE,
                        1: LEGS_R_TOE,
                        2: LEGS_L_FOOT,
                        3: LEGS_R_FOOT,
                        4: 4,
                        5: 5,
                        6: 6,
                        7: 7,
                    }

                    for bit, role in bit_to_role.items():
                        if (mask & (1 << bit)) == 0:
                            continue
                        bone_id = _safe_bone_idx(legs_std_bones, role)
                        _assign_runtime_local_rot(
                            bone_id,
                            frame_no,
                            legs_std_state_quats[bit],
                            default_quat=_default_quat_or_none(legs_std_default_quats, bit),
                        )

            elif comp_ix == COMP_ARMS:
                use_ik = not arms_bones and bool(arms_ik_bones)
                bit_to_role = (
                    {
                        0: ARMSIK_L_CLAV,
                        1: 4,
                        2: 6,
                        3: ARMSIK_L_HAND,
                        4: ARMSIK_R_CLAV,
                        5: 5,
                        6: 7,
                        7: ARMSIK_R_HAND,
                    }
                    if use_ik
                    else {
                        0: ARMS_L_CLAV,
                        1: ARMS_L_UPPER,
                        2: ARMS_L_FORE,
                        3: ARMS_L_HAND,
                        4: ARMS_R_CLAV,
                        5: ARMS_R_UPPER,
                        6: ARMS_R_FORE,
                        7: ARMS_R_HAND,
                    }
                )
                arm_indices = arms_ik_bones if use_ik else arms_bones

                frame_mats = _frame_map(frame_no)
                pending = {}

                for bit in range(8):
                    if (mask & (1 << bit)) == 0:
                        continue
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is None:
                        break
                    pending[bit] = _quat_from_xyz(*xyz)

                can_reconstruct_arms_std = (
                    (not use_ik)
                    and len(arms_bones) >= 8
                    and len(arms_offsets) >= 8
                    and len(arms_other) >= 5
                )

                if can_reconstruct_arms_std:
                    comp_world = {}
                    for bit, q in pending.items():
                        if 0 <= bit < 8:
                            arms_state_quats[bit] = q

                    for i in range(8):
                        bid = _safe_bone_idx(arms_bones, i)
                        if bid is None:
                            continue
                        comp_world[bid] = _mat_from_quat_pos(arms_state_quats[i], arms_offsets[i])

                    anchor_id = int(arms_other[4])
                    anchor_world = frame_mats.get(anchor_id, _mat_identity()) if anchor_id >= 0 else _mat_identity()

                    for i in range(8):
                        bid = _safe_bone_idx(arms_bones, i)
                        if bid is None or bid not in comp_world:
                            continue
                        if i == 0 or i == 4:
                            comp_world[bid] = _mat_local_to_world(comp_world[bid], anchor_world)
                        else:
                            prev_bid = _safe_bone_idx(arms_bones, i - 1)
                            if prev_bid is not None and prev_bid in comp_world:
                                comp_world[bid] = _mat_local_to_world(comp_world[bid], comp_world[prev_bid])

                    for i in range(4):
                        if i >= len(arms_other):
                            continue
                        oid = int(arms_other[i])
                        if oid < 0:
                            continue
                        pos = arms_fore_twist[i] if i < len(arms_fore_twist) else (0.0, 0.0, 0.0)
                        comp_world[oid] = _build_twist_line_xform(pos, 0.0)

                    for i in range(4):
                        if i >= len(arms_other):
                            continue
                        oid = int(arms_other[i])
                        if oid < 0 or oid not in comp_world:
                            continue

                        if i == 0:
                            parent_id = _safe_bone_idx(arms_bones, ARMS_L_FORE)
                        elif i == 2:
                            parent_id = _safe_bone_idx(arms_bones, ARMS_R_FORE)
                        elif i == 1:
                            parent_id = int(arm_indices[8]) if len(arm_indices) > 8 else int(arms_other[0])
                        else:
                            parent_id = int(arm_indices[10]) if len(arm_indices) > 10 else int(arms_other[2])

                        if parent_id in comp_world:
                            comp_world[oid] = _mat_local_to_world(comp_world[oid], comp_world[parent_id])

                    _cache_component_world_write_once(frame_mats, comp_world)

                    if use_full_arm_tracks:
                        roles = (ARMS_L_CLAV, ARMS_L_UPPER, ARMS_L_FORE, ARMS_L_HAND, ARMS_R_CLAV, ARMS_R_UPPER, ARMS_R_FORE, ARMS_R_HAND)
                    else:
                        roles = (ARMS_L_CLAV, ARMS_L_HAND, ARMS_R_CLAV, ARMS_R_HAND)

                    for role in roles:
                        bid = _safe_bone_idx(arms_bones, role)
                        if bid is None:
                            continue
                        _assign_runtime_local_rot(
                            bid,
                            frame_no,
                            arms_state_quats[role],
                            default_quat=_default_quat_or_none(arms_default_quats, role),
                        )

                    for i in range(4):
                        if i >= len(arms_other):
                            continue
                        oid = int(arms_other[i])
                        if oid < 0:
                            continue
                        if i == 0:
                            parent_id = _safe_bone_idx(arms_bones, ARMS_L_FORE)
                        elif i == 2:
                            parent_id = _safe_bone_idx(arms_bones, ARMS_R_FORE)
                        elif i == 1:
                            parent_id = int(arm_indices[8]) if len(arm_indices) > 8 else int(arms_other[0])
                        else:
                            parent_id = int(arm_indices[10]) if len(arm_indices) > 10 else int(arms_other[2])
                        _assign_rot_from_runtime_parent_world(
                            bone_tracks, oid, frame_no, frame_mats, parent_id
                        )
                else:
                    for bit in range(8):
                        if bit not in pending:
                            continue
                        role = bit_to_role.get(bit)
                        if role is None:
                            continue
                        if not use_full_arm_tracks:
                            if use_ik:
                                if role not in (ARMSIK_L_CLAV, ARMSIK_R_CLAV, ARMSIK_L_HAND, ARMSIK_R_HAND):
                                    continue
                            else:
                                if role not in (ARMS_L_CLAV, ARMS_R_CLAV, ARMS_L_HAND, ARMS_R_HAND):
                                    continue
                        bone_id = _safe_bone_idx(arm_indices, int(role))
                        default_q = None
                        if use_ik:
                            if role == ARMSIK_L_CLAV:
                                default_q = _default_quat_or_none(arms_ik_default_track_quats, 0)
                            elif role == ARMSIK_R_CLAV:
                                default_q = _default_quat_or_none(arms_ik_default_track_quats, 1)
                            elif role == ARMSIK_L_HAND:
                                default_q = _default_quat_or_none(arms_ik_default_hand_quats, 0)
                            elif role == ARMSIK_R_HAND:
                                default_q = _default_quat_or_none(arms_ik_default_hand_quats, 1)
                        else:
                            default_q = _default_quat_or_none(arms_default_quats, int(role))
                        _assign_runtime_local_rot(bone_id, frame_no, pending[bit], default_quat=default_q)

            elif comp_ix == COMP_ARMS_IK:
                for bit in range(2):
                    if (mask & (1 << bit)) == 0:
                        continue
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is None:
                        break
                    role = ARMSIK_L_CLAV if bit == 0 else ARMSIK_R_CLAV
                    bone_id = _safe_bone_idx(arms_ik_bones, role)
                    q = _quat_from_xyz(*xyz)
                    default_q = _default_quat_or_none(arms_ik_default_track_quats, 0 if bit == 0 else 1)
                    _assign_runtime_local_rot(bone_id, frame_no, q, default_quat=default_q)

                for bit in range(2, 4):
                    if (mask & (1 << bit)) == 0:
                        continue
                    qxyz, cursor = _consume_xyz(values, cursor)
                    if qxyz is None:
                        break

                    # hand target position + elbow spin retained
                    _, cursor = _consume_xyz(values, cursor)
                    if cursor < len(values):
                        cursor += 1

                    role = ARMSIK_L_HAND if bit == 2 else ARMSIK_R_HAND
                    bone_id = _safe_bone_idx(arms_ik_bones, role)
                    q = _quat_from_xyz(*qxyz)
                    default_q = _default_quat_or_none(arms_ik_default_hand_quats, 0 if bit == 2 else 1)
                    _assign_runtime_local_rot(bone_id, frame_no, q, default_quat=default_q)

    return bone_tracks


def open_pcanim(
    filepath,
    skel_data=None,
    decode_tracks=True,
    apply_root_motion=False,
    solve_ik=False,
    use_full_arm_tracks=True,
):
    with io.open(filepath, "rb") as f:
        blob = f.read()

    if len(blob) < 64:
        raise PCANIMParseError("File is too small for a PCANIM header")

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

    comp_order = _build_component_order(skel_data)

    all_warnings = []
    for anim in out["animations"]:
        if int(anim.get("version", 0)) != CHAR_ANIM:
            anim["decoded_components"] = []
            anim["bone_tracks"] = {}
            anim["decode_warnings"] = [
                f"Anim '{anim.get('name', '')}' has unsupported version 0x{int(anim.get('version', 0)) & 0xFFFFFFFF:08X}"
            ]
            all_warnings.extend(anim["decode_warnings"])
            continue

        components, warnings = _decode_anim_components(blob, anim, comp_order)
        anim["decoded_components"] = components
        anim["decode_warnings"] = warnings
        if warnings:
            all_warnings.extend(warnings)

        if skel_data:
            anim["bone_tracks"] = _components_to_bone_tracks(
                components,
                skel_data,
                apply_root_motion=bool(apply_root_motion),
                solve_ik=bool(solve_ik),
                use_full_arm_tracks=bool(use_full_arm_tracks),
            )
        else:
            anim["bone_tracks"] = {}

    out["decode_warnings"] = all_warnings
    return out
