import math


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


def _quat_twist_about_axis_wxyz(q, axis_xyz):
    qn = _quat_normalize_wxyz(q)
    ax, ay, az = float(axis_xyz[0]), float(axis_xyz[1]), float(axis_xyz[2])
    an2 = ax * ax + ay * ay + az * az
    if an2 <= 1e-20:
        return (1.0, 0.0, 0.0, 0.0)
    inv = 1.0 / (an2 ** 0.5)
    ax *= inv
    ay *= inv
    az *= inv

    vdot = qn[1] * ax + qn[2] * ay + qn[3] * az
    twist = _quat_normalize_wxyz((qn[0], ax * vdot, ay * vdot, az * vdot))
    if twist[0] < 0.0:
        return (-twist[0], -twist[1], -twist[2], -twist[3])
    return twist


def _quat_mul_wxyz(a, b):
    aw, ax, ay, az = _quat_normalize_wxyz(a)
    bw, bx, by, bz = _quat_normalize_wxyz(b)
    return _quat_normalize_wxyz((
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ))


def _quat_axis_angle_wxyz(axis_xyz, angle):
    ax, ay, az = float(axis_xyz[0]), float(axis_xyz[1]), float(axis_xyz[2])
    l2 = ax * ax + ay * ay + az * az
    if l2 <= 1e-20:
        return (1.0, 0.0, 0.0, 0.0)
    inv = 1.0 / math.sqrt(l2)
    ax *= inv
    ay *= inv
    az *= inv
    half = 0.5 * float(angle)
    s = math.sin(half)
    c = math.cos(half)
    return _quat_normalize_wxyz((c, ax * s, ay * s, az * s))


def _quat_from_yz_angles_wxyz(y_ang, z_ang):
    qy = _quat_axis_angle_wxyz((0.0, 1.0, 0.0), y_ang)
    qz = _quat_axis_angle_wxyz((0.0, 0.0, 1.0), z_ang)
    return _quat_mul_wxyz(qy, qz)


def _fing52_tip_hinge_angle(base_ang, is_thumb):
    ang = float(base_ang)
    if not is_thumb:
        return ang
    tip = 2.0 * ang
    half_pi = 0.5 * math.pi
    if tip > half_pi:
        return half_pi
    if tip < -half_pi:
        return -half_pi
    return tip


def _fing52_hinge_local_matrix(ang, pos_xyz):
    s = math.sin(float(ang))
    c = math.cos(float(ang))
    m = _mat_identity()
    m[0][0] = float(c)
    m[0][2] = float(s)
    m[2][0] = float(-s)
    m[2][2] = float(c)
    m[3][0] = float(pos_xyz[0])
    m[3][1] = float(pos_xyz[1])
    m[3][2] = float(pos_xyz[2])
    return m


def _engine_to_blender_quat_wxyz(q):
    qn = _quat_normalize_wxyz(q)
    rot_eng = _mat_from_quat_pos(qn, (0.0, 0.0, 0.0))
    rot_bl = _mat_local_to_world(
        _mat_local_to_world(_BASIS_M_BLENDER_TO_ENGINE, rot_eng),
        _BASIS_M_ENGINE_TO_BLENDER,
    )
    return _quat_from_matrix_wxyz(rot_bl)


def _quat_from_xyz(x, y, z):
    w = math.sqrt(abs(1.0 - (x * x + y * y + z * z)))
    n2 = w * w + x * x + y * y + z * z
    if n2 <= 0.0:
        return (1.0, 0.0, 0.0, 0.0)
    inv = 1.0 / math.sqrt(n2)
    return (w * inv, x * inv, y * inv, z * inv)


def _apply_default_local_delta(q_local, default_quat=None):
    qn = _quat_normalize_wxyz(q_local)
    if default_quat is None:
        return qn
    qd_inv = _quat_inverse_wxyz(default_quat)
    return _quat_mul_wxyz(qd_inv, qn)


def _apply_default_local_delta_post(q_local, default_quat=None):
    qn = _quat_normalize_wxyz(q_local)
    if default_quat is None:
        return qn
    qd_inv = _quat_inverse_wxyz(default_quat)
    return _quat_mul_wxyz(qn, qd_inv)


def _delta_from_default_local(q_local, default_quat=None, order="pre"):
    if str(order).lower() == "post":
        return _apply_default_local_delta_post(q_local, default_quat)
    return _apply_default_local_delta(q_local, default_quat)


def _delta_space_correction_from_default(q_local_default, default_quat=None, order="pre"):
    delta_ref = _delta_from_default_local(q_local_default, default_quat, order=order)
    return _quat_inverse_wxyz(delta_ref)


def _quat_is_near_identity(q, eps=1e-4):
    qn = _quat_normalize_wxyz(q)
    return (
        abs(float(qn[0]) - 1.0) <= float(eps)
        and abs(float(qn[1])) <= float(eps)
        and abs(float(qn[2])) <= float(eps)
        and abs(float(qn[3])) <= float(eps)
    )


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

    x = -x
    y = -y
    z = -z

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


def _mat_to_rows(m):
    return [
        [float(m[0][0]), float(m[0][1]), float(m[0][2]), float(m[0][3])],
        [float(m[1][0]), float(m[1][1]), float(m[1][2]), float(m[1][3])],
        [float(m[2][0]), float(m[2][1]), float(m[2][2]), float(m[2][3])],
        [float(m[3][0]), float(m[3][1]), float(m[3][2]), float(m[3][3])],
    ]


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
    q = (q[0], -q[1], -q[2], -q[3])
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


def _leg_heuristic(base_model_matrix, target_model_matrix, axis_xyz):
    row1 = (
        float(target_model_matrix[1][0]),
        float(target_model_matrix[1][1]),
        float(target_model_matrix[1][2]),
    )
    return _vec_cross(axis_xyz, row1)


def _arm_heuristic(base_model_matrix, axis_xyz, mirror_row1=False):
    row0 = (
        float(base_model_matrix[0][0]),
        float(base_model_matrix[0][1]),
        float(base_model_matrix[0][2]),
    )
    row1 = (
        float(base_model_matrix[1][0]),
        float(base_model_matrix[1][1]),
        float(base_model_matrix[1][2]),
    )
    row2 = (
        float(base_model_matrix[2][0]),
        float(base_model_matrix[2][1]),
        float(base_model_matrix[2][2]),
    )

    if mirror_row1:
        row1 = (-row1[0], -row1[1], -row1[2])
        cross = _vec_cross(row1, axis_xyz)
    else:
        cross = _vec_cross(axis_xyz, row1)

    sign = _vec_dot(axis_xyz, row1)
    if sign < 0.0:
        return (
            cross[0] * (sign + 1.0) + (-row0[0] - row2[0]) * (-sign),
            cross[1] * (sign + 1.0) + (-row0[1] - row2[1]) * (-sign),
            cross[2] * (sign + 1.0) + (-row0[2] - row2[2]) * (-sign),
        )

    return (
        cross[0] * (1.0 - sign) + (row2[0] - row0[0]) * sign,
        cross[1] * (1.0 - sign) + (row2[1] - row0[1]) * sign,
        cross[2] * (1.0 - sign) + (row2[2] - row0[2]) * sign,
    )


def _left_arm_heuristic(base_model_matrix, target_model_matrix, axis_xyz):
    return _arm_heuristic(base_model_matrix, axis_xyz, mirror_row1=False)


def _right_arm_heuristic(base_model_matrix, target_model_matrix, axis_xyz):
    return _arm_heuristic(base_model_matrix, axis_xyz, mirror_row1=True)


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
    model_mid_joint_dir = heuristic_fn(base_model_matrix, target_model_matrix, model_target_dir)

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
