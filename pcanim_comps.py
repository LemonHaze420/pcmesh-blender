import math

try:
    from .pcanim import (
        COMP_ARBITRARY_PO,
        COMP_ARMS,
        COMP_ARMS_IK,
        COMP_FAKEROOT_STD,
        COMP_FING5,
        COMP_FING5_CURL,
        COMP_FING5_REDUCED,
        COMP_FING52,
        COMP_GENERIC,
        COMP_LEGS,
        COMP_LEGS_IK,
        COMP_TENTACLE,
        COMP_TORSO_HEAD,
        COMP_TORSO_HEAD_STD,
        NAL_ARBITRARY_PO,
        NAL_ARMS,
        NAL_ARMS_IK,
        NAL_FAKEROOT,
        NAL_FING5,
        NAL_FING5_CURL,
        NAL_FING5_REDUCED,
        NAL_FING52,
        NAL_GENERIC,
        NAL_LEGS,
        NAL_LEGS_IK,
        NAL_TENTACLES,
        NAL_TORSO_ONE_NECK,
        NAL_TORSO_TWO_NECK,
        ROOT_BONE_TRACK_ID,
    )
except Exception:
    from pcanim import (  # type: ignore
        COMP_ARBITRARY_PO,
        COMP_ARMS,
        COMP_ARMS_IK,
        COMP_FAKEROOT_STD,
        COMP_FING5,
        COMP_FING5_CURL,
        COMP_FING5_REDUCED,
        COMP_FING52,
        COMP_GENERIC,
        COMP_LEGS,
        COMP_LEGS_IK,
        COMP_TENTACLE,
        COMP_TORSO_HEAD,
        COMP_TORSO_HEAD_STD,
        NAL_ARBITRARY_PO,
        NAL_ARMS,
        NAL_ARMS_IK,
        NAL_FAKEROOT,
        NAL_FING5,
        NAL_FING5_CURL,
        NAL_FING5_REDUCED,
        NAL_FING52,
        NAL_GENERIC,
        NAL_LEGS,
        NAL_LEGS_IK,
        NAL_TENTACLES,
        NAL_TORSO_ONE_NECK,
        NAL_TORSO_TWO_NECK,
        ROOT_BONE_TRACK_ID,
    )


try:
    from .pcanim_transforms import (
        _apply_default_local_delta,
        _apply_default_local_delta_post,
        _arm_heuristic,
        _build_twist_line_xform,
        _consume_xyz,
        _decompose_ik_spin,
        _delta_from_default_local,
        _delta_space_correction_from_default,
        _engine_to_blender_quat_wxyz,
        _fing52_hinge_local_matrix,
        _fing52_tip_hinge_angle,
        _left_arm_heuristic,
        _leg_heuristic,
        _mat_compose_from_basis,
        _mat_copy,
        _mat_from_quat_pos,
        _mat_identity,
        _mat_local_to_world,
        _mat_rigid_inverse,
        _mat_to_rows,
        _nal_ik_map_2d_to_3d,
        _nal_ik_solve_2d,
        _project_point_onto_line_xform,
        _quat_axis_angle_wxyz,
        _quat_from_matrix_wxyz,
        _quat_from_xyz,
        _quat_from_yz_angles_wxyz,
        _quat_inverse_wxyz,
        _quat_is_near_identity,
        _quat_mul_wxyz,
        _quat_normalize_wxyz,
        _quat_twist_about_axis_wxyz,
        _right_arm_heuristic,
        _vec_cross,
        _vec_dot,
        _vec_len,
        _vec_norm,
    )
except Exception:
    from pcanim_transforms import (  # type: ignore
        _apply_default_local_delta,
        _apply_default_local_delta_post,
        _arm_heuristic,
        _build_twist_line_xform,
        _consume_xyz,
        _decompose_ik_spin,
        _delta_from_default_local,
        _delta_space_correction_from_default,
        _engine_to_blender_quat_wxyz,
        _fing52_hinge_local_matrix,
        _fing52_tip_hinge_angle,
        _left_arm_heuristic,
        _leg_heuristic,
        _mat_compose_from_basis,
        _mat_copy,
        _mat_from_quat_pos,
        _mat_identity,
        _mat_local_to_world,
        _mat_rigid_inverse,
        _mat_to_rows,
        _nal_ik_map_2d_to_3d,
        _nal_ik_solve_2d,
        _project_point_onto_line_xform,
        _quat_axis_angle_wxyz,
        _quat_from_matrix_wxyz,
        _quat_from_xyz,
        _quat_from_yz_angles_wxyz,
        _quat_inverse_wxyz,
        _quat_is_near_identity,
        _quat_mul_wxyz,
        _quat_normalize_wxyz,
        _quat_twist_about_axis_wxyz,
        _right_arm_heuristic,
        _vec_cross,
        _vec_dot,
        _vec_len,
        _vec_norm,
    )


def _find_component_by_type(skel_data, type_values):
    comps = skel_data.get("components", []) if skel_data else []
    wanted = set(int(v) for v in type_values)
    for comp in comps:
        ctype = int(comp.get("type_id", 0))
        if ctype in wanted:
            return comp
    return None




def get_bone(indices, role_idx):
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


def _assign_parent_space_rot(
    bone_tracks,
    bone_id,
    frame_no,
    frame_xforms,
    parent_id,
    default_quat=None,
    default_delta_order="pre",
    local_correction_quat=None,
    local_correction_order="post",
    local_correction_space="engine",
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
    if default_delta_order == "post":
        q_local = _apply_default_local_delta_post(q_local, default_quat)
    else:
        q_local = _apply_default_local_delta(q_local, default_quat)
    if local_correction_quat is not None and local_correction_space != "blender":
        if local_correction_order == "pre":
            q_local = _quat_mul_wxyz(local_correction_quat, q_local)
        else:
            q_local = _quat_mul_wxyz(q_local, local_correction_quat)

    q_out = _engine_to_blender_quat_wxyz(q_local)

    if local_correction_quat is not None and local_correction_space == "blender":
        if local_correction_order == "pre":
            q_out = _quat_mul_wxyz(local_correction_quat, q_out)
        else:
            q_out = _quat_mul_wxyz(q_out, local_correction_quat)

    _assign_rot(bone_tracks, ibid, frame_no, q_out)




def _components_to_bone_tracks(
    decoded_components,
    skel_data,
    apply_root_motion=False,
    solve_ik=False,
    use_full_arm_tracks=True,
    rest_local_quats_by_bone=None,
    debug_capture=None,
    runtime_capture=None,
 ):
    if not skel_data or not decoded_components:
        return {}

    bone_tracks = {}

    frame_xforms = {}

    debug_frame_set = set()
    debug_records = None
    if isinstance(debug_capture, dict):
        for frame_no in debug_capture.get("frames", ()):  # type: ignore[arg-type]
            try:
                fno = int(frame_no)
            except Exception:
                continue
            if fno > 0:
                debug_frame_set.add(fno)
        debug_capture["frames"] = sorted(debug_frame_set)
        debug_records = debug_capture.setdefault("records", {})

    def _debug_frame_bucket(frame_no):
        if debug_records is None:
            return None
        fno = int(frame_no)
        if fno not in debug_frame_set:
            return None
        key = str(fno)
        bucket = debug_records.get(key)
        if bucket is None:
            bucket = {}
            debug_records[key] = bucket
        return bucket

    def _frame_map(frame_no):
        key = int(frame_no)
        fm = frame_xforms.get(key)
        if fm is None:
            fm = {}
            frame_xforms[key] = fm
        return fm

    def _id_quat():
        return (1.0, 0.0, 0.0, 0.0)

    arbitrary_comp = _find_component_by_type(skel_data, (NAL_ARBITRARY_PO,))
    generic_comp = _find_component_by_type(skel_data, (NAL_GENERIC,))
    torso_comp = _find_component_by_type(skel_data, (NAL_TORSO_ONE_NECK, NAL_TORSO_TWO_NECK))
    legs_std_comp = _find_component_by_type(skel_data, (NAL_LEGS,))
    legs_ik_comp = _find_component_by_type(skel_data, (NAL_LEGS_IK,))
    arms_comp = _find_component_by_type(skel_data, (NAL_ARMS,))
    arms_ik_comp = _find_component_by_type(skel_data, (NAL_ARMS_IK,))
    fakeroot_comp = _find_component_by_type(skel_data, (NAL_FAKEROOT,))
    tentacle_comp = _find_component_by_type(skel_data, (NAL_TENTACLES,))
    fing52_comp = _find_component_by_type(skel_data, (NAL_FING52,))
    fing5_curl_comp = _find_component_by_type(skel_data, (NAL_FING5_CURL,))
    fing5_reduced_comp = _find_component_by_type(skel_data, (NAL_FING5_REDUCED,))
    fing5_full_comp = _find_component_by_type(skel_data, (NAL_FING5,))

    legs_solve_ik = bool(
        solve_ik
        or (
            legs_ik_comp is not None
            and legs_std_comp is None
        )
    )
    arms_solve_ik = bool(
        solve_ik
        or (
            arms_ik_comp is not None
            and arms_comp is None
        )
    )

    arbitrary_nodes = list(arbitrary_comp.get("nodes", ())) if arbitrary_comp else []

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

    rest_local_quat_map = {}
    if isinstance(rest_local_quats_by_bone, dict):
        for key, value in rest_local_quats_by_bone.items():
            try:
                bid = int(key)
            except Exception:
                continue
            if bid < 0:
                continue
            if not value or len(value) != 4:
                continue
            rest_local_quat_map[bid] = _quat_normalize_wxyz(tuple(float(v) for v in value))

    def _default_quat_for_bone(bone_id, fallback_quat=None):
        if bone_id is not None:
            bid = int(bone_id)
            if bid in rest_local_quat_map:
                return rest_local_quat_map[bid]
        if fallback_quat is None:
            return None
        return _quat_normalize_wxyz(fallback_quat)

    def _has_rest_default_for_bone(bone_id):
        if bone_id is None:
            return False
        return int(bone_id) in rest_local_quat_map

    raw_parent_map = skel_data.get("parent_map", {}) if isinstance(skel_data, dict) else {}
    skel_parent_map = {}
    if isinstance(raw_parent_map, dict):
        for key, value in raw_parent_map.items():
            try:
                k = int(key)
                v = int(value)
            except Exception:
                continue
            skel_parent_map[k] = v

    def _local_parent_for_bone(bone_id, fallback_parent=None):
        if bone_id is None:
            return None if fallback_parent is None else int(fallback_parent)

        bid = int(bone_id)
        if skel_parent_map and bid in skel_parent_map:
            pid = skel_parent_map.get(bid)
            if pid is None or int(pid) < 0 or int(pid) == bid:
                return None
            return int(pid)

        if fallback_parent is None:
            return None
        return int(fallback_parent)

    def _assign_runtime_local_rot(
        bone_id,
        frame_no,
        quat_wxyz,
        default_quat=None,
    ):
        if bone_id is None:
            return            
        q_local = _apply_default_local_delta(quat_wxyz, default_quat)
        _assign_rot(
            bone_tracks,
            bone_id,
            frame_no,
            _engine_to_blender_quat_wxyz(q_local),
        )

    torso_default_world = {}
    if len(torso_bones) >= 6 and len(torso_offsets) >= 5:
        d_pelvis_id = get_bone(torso_bones, 0)
        if d_pelvis_id is not None:
            torso_default_world[d_pelvis_id] = _mat_from_quat_pos(torso_state_quats[5], torso_state_pelvis_pos)

        for i in range(5):
            bid = get_bone(torso_bones, i + 1)
            if bid is None:
                continue
            torso_default_world[bid] = _mat_from_quat_pos(torso_state_quats[i], torso_offsets[i])

        for i in range(1, 6):
            child = get_bone(torso_bones, i)
            parent = get_bone(torso_bones, i - 1)
            if child is None or parent is None:
                continue
            if child in torso_default_world and parent in torso_default_world:
                torso_default_world[child] = _mat_local_to_world(torso_default_world[child], torso_default_world[parent])

        if torso_has_empty_neck and len(torso_other) >= 1:
            other0 = int(torso_other[0])
            if other0 >= 0:
                torso_default_world[other0] = _mat_from_quat_pos(empty_neck_orient, empty_neck_pos)
                spine2_id = get_bone(torso_bones, 3)
                if spine2_id is not None and spine2_id in torso_default_world:
                    torso_default_world[other0] = _mat_local_to_world(torso_default_world[other0], torso_default_world[spine2_id])

    runtime_default_world = dict(torso_default_world)

    legs_std_bones = list(legs_std_comp.get("bone_indices", ())) if legs_std_comp else []
    legs_std_offsets = list(legs_std_comp.get("offset_locs", ())) if legs_std_comp else []
    legs_std_other = list(legs_std_comp.get("other_matrix_indices", ())) if legs_std_comp else []
    legs_std_default = (legs_std_comp or {}).get("default_pose", {})
    legs_std_default_quats = list(legs_std_default.get("quats", ()))
    legs_std_state_quats = [
        _quat_normalize_wxyz(legs_std_default_quats[i]) if i < len(legs_std_default_quats) else _id_quat()
        for i in range(8)
    ]

    if len(legs_std_bones) >= 8 and len(legs_std_offsets) >= 8 and len(legs_std_other) >= 1:
        legs_std_default_world = {}
        anchor_id = int(legs_std_other[0])
        anchor_world = runtime_default_world.get(anchor_id, _mat_identity()) if anchor_id >= 0 else _mat_identity()

        parent_role = {
            4: None,
            5: 4,
            2: 5,
            0: 2,
            6: None,
            7: 6,
            3: 7,
            1: 3,
        }
        eval_order = (4, 5, 2, 0, 6, 7, 3, 1)

        for role in eval_order:
            bid = get_bone(legs_std_bones, role)
            if bid is None:
                continue

            local = _mat_from_quat_pos(legs_std_state_quats[role], legs_std_offsets[role])
            prole = parent_role.get(role)
            if prole is None:
                legs_std_default_world[bid] = _mat_local_to_world(local, anchor_world)
                continue

            parent_bid = get_bone(legs_std_bones, prole)
            if parent_bid is not None and parent_bid in legs_std_default_world:
                legs_std_default_world[bid] = _mat_local_to_world(local, legs_std_default_world[parent_bid])
            else:
                legs_std_default_world[bid] = _mat_local_to_world(local, anchor_world)

        runtime_default_world.update(legs_std_default_world)

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

    legs_ik_default_local_quat = {}
    if len(legs_ik_bones) >= 8 and len(legs_offsets) >= 8 and len(legs_ik_data) >= 2:
        default_world = {}

        dl_toe_id = get_bone(legs_ik_bones, 0)
        dr_toe_id = get_bone(legs_ik_bones, 1)
        dl_foot_id = get_bone(legs_ik_bones, 2)
        dr_foot_id = get_bone(legs_ik_bones, 3)
        dl_thigh_id = get_bone(legs_ik_bones, 4)
        dl_calf_id = get_bone(legs_ik_bones, 5)
        dr_thigh_id = get_bone(legs_ik_bones, 6)
        dr_calf_id = get_bone(legs_ik_bones, 7)

        if dl_foot_id is not None:
            default_world[dl_foot_id] = _mat_from_quat_pos(legs_ik_state_foot_quats[0], legs_ik_state_foot_pos[0])
        if dr_foot_id is not None:
            default_world[dr_foot_id] = _mat_from_quat_pos(legs_ik_state_foot_quats[1], legs_ik_state_foot_pos[1])

        if dl_foot_id is not None and dl_foot_id in default_world and dl_thigh_id is not None and dl_calf_id is not None:
            dl_upper, dl_lower = _decompose_ik_spin(
                base_model_matrix=_mat_identity(),
                base_joint_xyz=legs_offsets[4],
                target_model_matrix=default_world[dl_foot_id],
                ik_data=legs_ik_data[0],
                heuristic_fn=_leg_heuristic,
                spin_angle=legs_ik_state_knee_spin[0],
            )
            default_world[dl_thigh_id] = dl_upper
            default_world[dl_calf_id] = dl_lower

        if dr_foot_id is not None and dr_foot_id in default_world and dr_thigh_id is not None and dr_calf_id is not None:
            dr_upper, dr_lower = _decompose_ik_spin(
                base_model_matrix=_mat_identity(),
                base_joint_xyz=legs_offsets[6],
                target_model_matrix=default_world[dr_foot_id],
                ik_data=legs_ik_data[1],
                heuristic_fn=_leg_heuristic,
                spin_angle=legs_ik_state_knee_spin[1],
            )
            default_world[dr_thigh_id] = dr_upper
            default_world[dr_calf_id] = dr_lower

        anchor_id = int(legs_ik_other[0]) if len(legs_ik_other) >= 1 else -1
        if anchor_id >= 0 and anchor_id in torso_default_world:
            anchor_world = torso_default_world[anchor_id]
        else:
            d_pelvis_id = get_bone(torso_bones, 0)
            if d_pelvis_id is not None and d_pelvis_id in torso_default_world:
                anchor_world = torso_default_world[d_pelvis_id]
            else:
                anchor_world = _mat_identity()

        for role in (2, 3, 4, 5, 6, 7):
            bid = get_bone(legs_ik_bones, role)
            if bid is None or bid not in default_world:
                continue
            default_world[bid] = _mat_local_to_world(default_world[bid], anchor_world)

        for side in (0, 1):
            toe_id = get_bone(legs_ik_bones, side)
            foot_id = get_bone(legs_ik_bones, side + 2)
            if toe_id is None:
                continue

            toe_off = legs_offsets[side] if side < len(legs_offsets) else (0.0, 0.0, 0.0)
            toe_local = _mat_from_quat_pos(legs_ik_state_toe_quats[side], toe_off)
            if foot_id is not None and foot_id in default_world:
                default_world[toe_id] = _mat_local_to_world(toe_local, default_world[foot_id])
            else:
                default_world[toe_id] = toe_local

        default_frame_mats = dict(torso_default_world)
        default_frame_mats.update(default_world)
        runtime_default_world.update(default_frame_mats)

        d_pelvis_id = get_bone(torso_bones, 0)
        thigh_parent_fallback = d_pelvis_id if d_pelvis_id is not None else anchor_id
        if thigh_parent_fallback is not None and int(thigh_parent_fallback) not in default_frame_mats:
            thigh_parent_fallback = anchor_id if anchor_id in default_frame_mats else None

        for bid, fallback_parent in (
            (dl_thigh_id, thigh_parent_fallback),
            (dl_calf_id, dl_thigh_id),
            (dl_foot_id, dl_calf_id),
            (dl_toe_id, dl_foot_id),
            (dr_thigh_id, thigh_parent_fallback),
            (dr_calf_id, dr_thigh_id),
            (dr_foot_id, dr_calf_id),
            (dr_toe_id, dr_foot_id),
        ):
            if bid is None or bid not in default_frame_mats:
                continue
            local_xform = default_frame_mats[bid]
            parent_id = _local_parent_for_bone(bid, fallback_parent)
            if parent_id is not None and int(parent_id) in default_frame_mats:
                parent_inv = _mat_rigid_inverse(default_frame_mats[int(parent_id)])
                local_xform = _mat_local_to_world(local_xform, parent_inv)
            legs_ik_default_local_quat[bid] = _quat_from_matrix_wxyz(local_xform)

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
    arms_ik_offsets = list(arms_ik_comp.get("offset_locs", ())) if arms_ik_comp else []
    arms_ik_data = list(arms_ik_comp.get("ik_data", ())) if arms_ik_comp else []
    arms_ik_other = list(arms_ik_comp.get("other_matrix_indices", ())) if arms_ik_comp else []
    arms_ik_default = (arms_ik_comp or {}).get("default_pose", {})
    arms_ik_default_track_quats = list(arms_ik_default.get("track_quats", ()))
    arms_ik_default_hand_quats = list(arms_ik_default.get("hand_quats", ()))
    arms_ik_default_hand_pos = list(arms_ik_default.get("hand_pos", ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))))
    while len(arms_ik_default_hand_pos) < 2:
        arms_ik_default_hand_pos.append((0.0, 0.0, 0.0))
    arms_ik_state_track_quats = [
        _quat_normalize_wxyz(arms_ik_default_track_quats[i]) if i < len(arms_ik_default_track_quats) else _id_quat()
        for i in range(2)
    ]
    arms_ik_state_hand_quats = [
        _quat_normalize_wxyz(arms_ik_default_hand_quats[i]) if i < len(arms_ik_default_hand_quats) else _id_quat()
        for i in range(2)
    ]
    arms_ik_state_hand_pos = [
        (
            float(arms_ik_default_hand_pos[0][0]),
            float(arms_ik_default_hand_pos[0][1]),
            float(arms_ik_default_hand_pos[0][2]),
        ),
        (
            float(arms_ik_default_hand_pos[1][0]),
            float(arms_ik_default_hand_pos[1][1]),
            float(arms_ik_default_hand_pos[1][2]),
        ),
    ]
    arms_ik_default_elbow_spin = list(arms_ik_default.get("elbow_spin", (0.0, 0.0)))
    while len(arms_ik_default_elbow_spin) < 2:
        arms_ik_default_elbow_spin.append(0.0)
    arms_ik_state_elbow_spin = [float(arms_ik_default_elbow_spin[0]), float(arms_ik_default_elbow_spin[1])]

    fakeroot_default = (fakeroot_comp or {}).get("default_pose", {})
    fakeroot_state_quat = _quat_normalize_wxyz(fakeroot_default.get("quat", _id_quat()))
    fakeroot_state_pos = tuple(float(v) for v in fakeroot_default.get("pos", (0.0, 0.0, 0.0)))
    fakeroot_state_floor = float(fakeroot_default.get("floor_offset", 0.0))
    fakeroot_base_twist = None
    fakeroot_base_pos = None

    tentacle_default = (tentacle_comp or {}).get("default_pose", {})
    tentacle_state_values = [float(v) for v in tentacle_default.get("values", ())]
    while len(tentacle_state_values) < 15:
        tentacle_state_values.append(0.0)
    tentacle_state_values = tentacle_state_values[:15]
    tentacle_group_names = ("uplefttent", "uprighttent", "lowlefttent", "lowrighttent", "tongue")

    def _tentacle_controls_from_state(state_vals):
        controls = {}
        for group_ix, group_name in enumerate(tentacle_group_names):
            base = group_ix * 3
            controls[group_name] = {
                "diameter": float(state_vals[base]),
                "activity": float(state_vals[base + 1]),
                "pull": float(state_vals[base + 2]),
            }
        return controls

    fing52_bones = list(fing52_comp.get("bone_indices", ())) if fing52_comp else []
    fing52_offsets = list(fing52_comp.get("offset_locs", ())) if fing52_comp else []
    fing52_other = list(fing52_comp.get("other_matrix_indices", ())) if fing52_comp else []
    fing52_default = (fing52_comp or {}).get("default_pose", {})
    fing52_default_thumb_quats = list(fing52_default.get("thumb_quats", ()))
    fing52_default_base_y = [float(v) for v in fing52_default.get("base_y_tracks", ())]
    fing52_default_base_z = [float(v) for v in fing52_default.get("base_z_tracks", ())]
    fing52_default_hinge = [float(v) for v in fing52_default.get("hinge_tracks", ())]
    fing52_default_other = [float(v) for v in fing52_default.get("other_tracks", ())]
    while len(fing52_default_base_y) < 8:
        fing52_default_base_y.append(0.0)
    while len(fing52_default_base_z) < 8:
        fing52_default_base_z.append(0.0)
    while len(fing52_default_hinge) < 10:
        fing52_default_hinge.append(0.0)
    while len(fing52_default_other) < 10:
        fing52_default_other.append(0.0)
    if not any(abs(v) > 1e-8 for v in fing52_default_hinge[:10]):
        fing52_default_hinge = [float(v) for v in fing52_default_other[:10]]
    fing52_state_thumb_quats = [
        _quat_normalize_wxyz(fing52_default_thumb_quats[i]) if i < len(fing52_default_thumb_quats) else _id_quat()
        for i in range(2)
    ]
    fing52_state_base_yz = [
        (
            fing52_default_base_y[i] if i < len(fing52_default_base_y) else 0.0,
            fing52_default_base_z[i] if i < len(fing52_default_base_z) else 0.0,
        )
        for i in range(8)
    ]
    fing52_state_hinge = [float(v) for v in fing52_default_hinge[:10]]
    fing52_can_runtime_build = (
        len(fing52_bones) >= 30
        and len(fing52_offsets) >= 30
        and len(fing52_other) >= 2
    )

    def _fing52_anchor_slot(chain_ix):
        idx = int(chain_ix)
        return 1 if idx == 1 or idx >= 6 else 0

    def _fing52_anchor_id(chain_ix):
        slot = _fing52_anchor_slot(chain_ix)
        if slot >= len(fing52_other):
            return None
        try:
            anchor_id = int(fing52_other[slot])
        except Exception:
            return None
        return anchor_id if anchor_id >= 0 else None

    def _fing52_base_local_quat(base_ix, thumb_quats, base_yz):
        if base_ix < 2:
            if base_ix < len(thumb_quats):
                return _quat_normalize_wxyz(thumb_quats[base_ix])
            return _id_quat()
        yz_ix = base_ix - 2
        if yz_ix < len(base_yz):
            y_ang, z_ang = base_yz[yz_ix]
        else:
            y_ang, z_ang = 0.0, 0.0
        return _quat_from_yz_angles_wxyz(y_ang, z_ang)

    def _build_fing52_component_world(frame_mats, thumb_quats, base_yz, hinge_angles):
        if not fing52_can_runtime_build:
            return {}
        comp_world = {}
        base_world_by_chain = {}

        for base_ix in range(10):
            bid = get_bone(fing52_bones, base_ix)
            local_xform = _mat_from_quat_pos(
                _fing52_base_local_quat(base_ix, thumb_quats, base_yz),
                fing52_offsets[base_ix],
            )

            anchor_world = _mat_identity()
            anchor_id = _fing52_anchor_id(base_ix)
            if anchor_id is not None:
                if anchor_id in frame_mats:
                    anchor_world = frame_mats[anchor_id]
                elif anchor_id in runtime_default_world:
                    anchor_world = runtime_default_world[anchor_id]

            world_xform = _mat_local_to_world(local_xform, anchor_world)
            base_world_by_chain[base_ix] = world_xform
            if bid is not None:
                comp_world[bid] = world_xform

        for chain_ix in range(10):
            base_world = base_world_by_chain.get(chain_ix)
            if base_world is None:
                continue

            ang = float(hinge_angles[chain_ix]) if chain_ix < len(hinge_angles) else 0.0
            mid_local = _fing52_hinge_local_matrix(
                ang,
                fing52_offsets[10 + chain_ix],
            )
            tip_local = _fing52_hinge_local_matrix(
                _fing52_tip_hinge_angle(ang, is_thumb=(chain_ix < 2)),
                fing52_offsets[20 + chain_ix],
            )

            mid_world = _mat_local_to_world(mid_local, base_world)
            tip_world = _mat_local_to_world(tip_local, mid_world)

            mid_bid = get_bone(fing52_bones, 10 + chain_ix)
            tip_bid = get_bone(fing52_bones, 20 + chain_ix)
            if mid_bid is not None:
                comp_world[mid_bid] = mid_world
            if tip_bid is not None:
                comp_world[tip_bid] = tip_world

        return comp_world

    def _apply_fing52_pose(frame_no, thumb_quats, base_yz, hinge_angles):
        if not fing52_can_runtime_build:
            return False
        frame_mats = _frame_map(frame_no)
        comp_world = _build_fing52_component_world(frame_mats, thumb_quats, base_yz, hinge_angles)
        if not comp_world:
            return False

        for chain_ix in range(10):
            anchor_id = _fing52_anchor_id(chain_ix)
            if anchor_id is None or anchor_id in frame_mats or anchor_id not in runtime_default_world:
                continue
            frame_mats[anchor_id] = _mat_copy(runtime_default_world[anchor_id])

        _cache_component_world_write_once(frame_mats, comp_world)
        frame_applied = False

        for base_ix in range(10):
            bid = get_bone(fing52_bones, base_ix)
            if bid is None:
                continue

            if base_ix < 2:
                default_q = _default_quat_or_none(fing52_default_thumb_quats, base_ix)
            else:
                default_q = _quat_from_yz_angles_wxyz(
                    fing52_default_base_y[base_ix - 2],
                    fing52_default_base_z[base_ix - 2],
                )

            _assign_parent_space_rot(
                bone_tracks,
                bid,
                frame_no,
                frame_mats,
                _local_parent_for_bone(bid, _fing52_anchor_id(base_ix)),
                default_quat=_default_quat_for_bone(bid, default_q),
                local_correction_quat=fing52_local_correction_by_role.get(base_ix),
                local_correction_order="pre",
                local_correction_space="engine",
            )
            frame_applied = True

        for chain_ix in range(10):
            base_bid = get_bone(fing52_bones, chain_ix)
            mid_bid = get_bone(fing52_bones, 10 + chain_ix)
            tip_bid = get_bone(fing52_bones, 20 + chain_ix)
            default_ang = float(fing52_default_hinge[chain_ix])
            default_q_mid = _quat_axis_angle_wxyz((1.0, 0.0, 0.0), default_ang)
            default_q_tip = _quat_axis_angle_wxyz(
                (1.0, 0.0, 0.0),
                _fing52_tip_hinge_angle(default_ang, is_thumb=(chain_ix < 2)),
            )

            _assign_parent_space_rot(
                bone_tracks,
                mid_bid,
                frame_no,
                frame_mats,
                _local_parent_for_bone(mid_bid, base_bid),
                default_quat=_default_quat_for_bone(mid_bid, default_q_mid),
                local_correction_quat=fing52_local_correction_by_role.get(10 + chain_ix),
                local_correction_order="pre",
                local_correction_space="engine",
            )
            _assign_parent_space_rot(
                bone_tracks,
                tip_bid,
                frame_no,
                frame_mats,
                _local_parent_for_bone(tip_bid, mid_bid if mid_bid is not None else base_bid),
                default_quat=_default_quat_for_bone(tip_bid, default_q_tip),
                local_correction_quat=fing52_local_correction_by_role.get(20 + chain_ix),
                local_correction_order="pre",
                local_correction_space="engine",
            )
            if mid_bid is not None or tip_bid is not None:
                frame_applied = True

        if debug_frame_set and int(frame_no) in debug_frame_set:
            bucket = _debug_frame_bucket(frame_no)
            if bucket is not None:
                fing52_state = bucket.setdefault("fing52_state", {})
                fing52_state["thumb_quats_wxyz"] = [
                    [float(q[0]), float(q[1]), float(q[2]), float(q[3])]
                    for q in thumb_quats[:2]
                ]
                fing52_state["base_yz"] = [
                    [float(v[0]), float(v[1])]
                    for v in base_yz[:8]
                ]
                fing52_state["hinge"] = [float(v) for v in hinge_angles[:10]]
                fing52_world = {}
                for bid, world_m in comp_world.items():
                    if bid is None or world_m is None:
                        continue
                    fing52_world[str(int(bid))] = _mat_to_rows(world_m)
                fing52_state["component_world"] = fing52_world

        return frame_applied


    fing52_local_correction_by_role = {}
    if fing52_can_runtime_build:
        fing52_default_world = _build_fing52_component_world(
            dict(runtime_default_world),
            fing52_state_thumb_quats,
            fing52_state_base_yz,
            fing52_state_hinge,
        )
        if fing52_default_world:
            fing52_default_frame_mats = dict(runtime_default_world)
            fing52_default_frame_mats.update(fing52_default_world)
            for role in range(30):
                bid = get_bone(fing52_bones, role)
                if bid is None or bid not in fing52_default_frame_mats:
                    continue

                if role < 10:
                    parent_fallback = _fing52_anchor_id(role)
                    if role < 2:
                        default_q_ref = _default_quat_for_bone(
                            bid,
                            _default_quat_or_none(fing52_default_thumb_quats, role),
                        )
                    else:
                        default_q_ref = _default_quat_for_bone(
                            bid,
                            _quat_from_yz_angles_wxyz(
                                fing52_default_base_y[role - 2],
                                fing52_default_base_z[role - 2],
                            ),
                        )
                elif role < 20:
                    parent_fallback = get_bone(fing52_bones, role - 10)
                    default_ang = float(fing52_default_hinge[role - 10])
                    default_q_ref = _default_quat_for_bone(
                            bid,
                            _quat_axis_angle_wxyz((1.0, 0.0, 0.0), default_ang),
                        )
                else:
                    parent_fallback = get_bone(fing52_bones, role - 10)
                    default_ang = float(fing52_default_hinge[role - 20])
                    default_q_ref = _default_quat_for_bone(
                            bid,
                            _quat_axis_angle_wxyz(
                                (1.0, 0.0, 0.0),
                                _fing52_tip_hinge_angle(default_ang, is_thumb=((role - 20) < 2)),
                            ),
                        )

                if default_q_ref is None:
                    continue


                local_xform = fing52_default_frame_mats[bid]
                parent_id = _local_parent_for_bone(bid, parent_fallback)
                if parent_id is not None and int(parent_id) in fing52_default_frame_mats:
                    parent_inv = _mat_rigid_inverse(fing52_default_frame_mats[int(parent_id)])
                    local_xform = _mat_local_to_world(local_xform, parent_inv)

                q_default_local = _quat_from_matrix_wxyz(local_xform)
                q_corr = _delta_space_correction_from_default(q_default_local, default_q_ref, order="pre")
                if not _quat_is_near_identity(q_corr):
                    fing52_local_correction_by_role[role] = q_corr
            runtime_default_world.update(fing52_default_world)


    fing5_curl_bones = list(fing5_curl_comp.get("bone_indices", ())) if fing5_curl_comp else []
    fing5_curl_default = (fing5_curl_comp or {}).get("default_pose", {})
    fing5_curl_default_quats = list(fing5_curl_default.get("quats", ()))
    fing5_curl_default_curl = [float(v) for v in fing5_curl_default.get("finger_curl", ())]
    while len(fing5_curl_default_curl) < 10:
        fing5_curl_default_curl.append(0.0)
    fing5_curl_state_thumb_quats = [
        _quat_normalize_wxyz(fing5_curl_default_quats[i]) if i < len(fing5_curl_default_quats) else _id_quat()
        for i in range(2)
    ]
    fing5_curl_state_base_z = [0.0 for _ in range(8)]
    fing5_curl_state_hinge = [float(v) for v in fing5_curl_default_curl[:10]]

    fing5_reduced_bones = list(fing5_reduced_comp.get("bone_indices", ())) if fing5_reduced_comp else []
    fing5_reduced_default = (fing5_reduced_comp or {}).get("default_pose", {})
    fing5_reduced_default_quats = list(fing5_reduced_default.get("quats", ()))
    fing5_reduced_state_thumb_quats = [
        _quat_normalize_wxyz(fing5_reduced_default_quats[i]) if i < len(fing5_reduced_default_quats) else _id_quat()
        for i in range(2)
    ]
    fing5_reduced_state_base_yz = [(0.0, 0.0) for _ in range(8)]
    fing5_reduced_state_mid_hinge = [0.0 for _ in range(10)]
    fing5_reduced_state_tip_hinge = [0.0 for _ in range(10)]

    fing5_full_bones = list(fing5_full_comp.get("bone_indices", ())) if fing5_full_comp else []
    fing5_full_default = (fing5_full_comp or {}).get("default_pose", {})
    fing5_full_default_quats = list(fing5_full_default.get("quats", ()))
    fing5_full_state_quats = [
        _quat_normalize_wxyz(fing5_full_default_quats[i]) if i < len(fing5_full_default_quats) else _id_quat()
        for i in range(30)
    ]

    TORSO_PELVIS = 0
    TORSO_SPINE = 1
    TORSO_SPINE1 = 2
    TORSO_SPINE2 = 3
    TORSO_NECK = 4
    TORSO_HEAD = 5

    LEGS_L_TOE = 0
    LEGS_R_TOE = 1
    LEGS_L_FOOT = 2
    LEGS_R_FOOT = 3

    ARMS_L_CLAV = 0
    ARMS_L_UPPER = 1
    ARMS_L_FORE = 2
    ARMS_R_CLAV = 4
    ARMS_R_UPPER = 5
    ARMS_R_FORE = 6
    ARMS_L_HAND = 3
    ARMS_R_HAND = 7

    ARMSIK_L_CLAV = 0
    ARMSIK_R_CLAV = 1
    ARMSIK_L_HAND = 2
    ARMSIK_R_HAND = 3

    arms_parent_role_map = {
        ARMS_L_CLAV: None,
        ARMS_L_UPPER: ARMS_L_CLAV,
        ARMS_L_FORE: ARMS_L_UPPER,
        ARMS_L_HAND: ARMS_L_FORE,
        ARMS_R_CLAV: None,
        ARMS_R_UPPER: ARMS_R_CLAV,
        ARMS_R_FORE: ARMS_R_UPPER,
        ARMS_R_HAND: ARMS_R_FORE,
    }
    arms_default_delta_order_by_role = {
        ARMS_L_CLAV: "pre",
        ARMS_L_UPPER: "post",
        ARMS_L_FORE: "post",
        ARMS_L_HAND: "pre",
        ARMS_R_CLAV: "pre",
        ARMS_R_UPPER: "post",
        ARMS_R_FORE: "post",
        ARMS_R_HAND: "pre",
    }

    arms_local_correction_by_role = {}
    if len(arms_bones) >= 8 and len(arms_offsets) >= 8 and len(arms_other) >= 5:
        arms_default_world = {}
        for i in range(8):
            bid = get_bone(arms_bones, i)
            if bid is None:
                continue
            arms_default_world[bid] = _mat_from_quat_pos(arms_state_quats[i], arms_offsets[i])

        anchor_id = int(arms_other[4])
        if anchor_id >= 0 and anchor_id in torso_default_world:
            anchor_world = torso_default_world[anchor_id]
        else:
            d_spine2_id = get_bone(torso_bones, TORSO_SPINE2)
            if d_spine2_id is not None and d_spine2_id in torso_default_world:
                anchor_world = torso_default_world[d_spine2_id]
            else:
                anchor_world = _mat_identity()

        for i in range(8):
            bid = get_bone(arms_bones, i)
            if bid is None or bid not in arms_default_world:
                continue
            if i == ARMS_L_CLAV or i == ARMS_R_CLAV:
                arms_default_world[bid] = _mat_local_to_world(arms_default_world[bid], anchor_world)
            else:
                prev_bid = get_bone(arms_bones, i - 1)
                if prev_bid is not None and prev_bid in arms_default_world:
                    arms_default_world[bid] = _mat_local_to_world(arms_default_world[bid], arms_default_world[prev_bid])

        for i in range(4):
            if i >= len(arms_other):
                continue
            oid = int(arms_other[i])
            if oid < 0:
                continue
            pos = arms_fore_twist[i] if i < len(arms_fore_twist) else (0.0, 0.0, 0.0)
            arms_default_world[oid] = _build_twist_line_xform(pos, 0.0)

        for i in range(4):
            if i >= len(arms_other):
                continue
            oid = int(arms_other[i])
            if oid < 0 or oid not in arms_default_world:
                continue

            if i == 0:
                parent_id = get_bone(arms_bones, ARMS_L_FORE)
            elif i == 2:
                parent_id = get_bone(arms_bones, ARMS_R_FORE)
            elif i == 1:
                parent_id = int(arms_bones[8]) if len(arms_bones) > 8 else int(arms_other[0])
            else:
                parent_id = int(arms_bones[10]) if len(arms_bones) > 10 else int(arms_other[2])

            if parent_id in arms_default_world:
                arms_default_world[oid] = _mat_local_to_world(arms_default_world[oid], arms_default_world[parent_id])

        arms_default_frame_mats = dict(torso_default_world)
        arms_default_frame_mats.update(arms_default_world)
        runtime_default_world.update(arms_default_frame_mats)

        anchor_parent_id = anchor_id if anchor_id >= 0 else get_bone(torso_bones, TORSO_SPINE2)
        for role in (ARMS_L_CLAV, ARMS_L_UPPER, ARMS_L_FORE, ARMS_L_HAND, ARMS_R_CLAV, ARMS_R_UPPER, ARMS_R_FORE, ARMS_R_HAND):
            bid = get_bone(arms_bones, role)
            if bid is None or bid not in arms_default_frame_mats:
                continue
            if _has_rest_default_for_bone(bid):
                continue

            parent_role = arms_parent_role_map.get(role)
            if parent_role is None:
                parent_fallback = anchor_parent_id
            else:
                parent_fallback = get_bone(arms_bones, parent_role)

            local_xform = arms_default_frame_mats[bid]
            parent_id = _local_parent_for_bone(bid, parent_fallback)
            if parent_id is not None and int(parent_id) in arms_default_frame_mats:
                parent_inv = _mat_rigid_inverse(arms_default_frame_mats[int(parent_id)])
                local_xform = _mat_local_to_world(local_xform, parent_inv)

            q_default_local = _quat_from_matrix_wxyz(local_xform)
            q_default_ref = _default_quat_for_bone(bid, _default_quat_or_none(arms_default_quats, role))
            if q_default_ref is None:
                continue
            delta_order = arms_default_delta_order_by_role.get(role, "pre")
            q_corr = _delta_space_correction_from_default(q_default_local, q_default_ref, order=delta_order)
            if not _quat_is_near_identity(q_corr):
                arms_local_correction_by_role[role] = q_corr

    if len(arms_ik_bones) >= 8 and len(arms_ik_offsets) >= 8 and len(arms_ik_data) >= 2 and len(arms_ik_other) >= 5:
        arms_ik_default_world = {}

        anchor_id = int(arms_ik_other[4])
        if anchor_id >= 0 and anchor_id in runtime_default_world:
            anchor_world = runtime_default_world[anchor_id]
        else:
            spine2_id = get_bone(torso_bones, TORSO_SPINE2)
            if spine2_id is not None and spine2_id in runtime_default_world:
                anchor_world = runtime_default_world[spine2_id]
            else:
                anchor_world = _mat_identity()
        hand_anchor_id = int(arms_ik_other[5]) if len(arms_ik_other) >= 6 else anchor_id
        if hand_anchor_id >= 0 and hand_anchor_id in runtime_default_world:
            hand_anchor_world = runtime_default_world[hand_anchor_id]
        else:
            hand_anchor_world = anchor_world

        l_clav_id = get_bone(arms_ik_bones, ARMSIK_L_CLAV)
        r_clav_id = get_bone(arms_ik_bones, ARMSIK_R_CLAV)
        l_hand_id = get_bone(arms_ik_bones, ARMSIK_L_HAND)
        r_hand_id = get_bone(arms_ik_bones, ARMSIK_R_HAND)
        l_upper_id = get_bone(arms_ik_bones, 4)
        r_upper_id = get_bone(arms_ik_bones, 5)
        l_fore_id = get_bone(arms_ik_bones, 6)
        r_fore_id = get_bone(arms_ik_bones, 7)

        if l_clav_id is not None:
            l_clav_local = _mat_from_quat_pos(arms_ik_state_track_quats[0], arms_ik_offsets[0])
            arms_ik_default_world[l_clav_id] = _mat_local_to_world(l_clav_local, anchor_world)
        if r_clav_id is not None:
            r_clav_local = _mat_from_quat_pos(arms_ik_state_track_quats[1], arms_ik_offsets[1])
            arms_ik_default_world[r_clav_id] = _mat_local_to_world(r_clav_local, anchor_world)

        if l_hand_id is not None:
            l_hand_local = _mat_from_quat_pos(arms_ik_state_hand_quats[0], arms_ik_state_hand_pos[0])
            arms_ik_default_world[l_hand_id] = _mat_local_to_world(l_hand_local, hand_anchor_world)
        if r_hand_id is not None:
            r_hand_local = _mat_from_quat_pos(arms_ik_state_hand_quats[1], arms_ik_state_hand_pos[1])
            arms_ik_default_world[r_hand_id] = _mat_local_to_world(r_hand_local, hand_anchor_world)

        if arms_solve_ik and l_upper_id is not None and l_fore_id is not None and l_hand_id is not None and l_hand_id in arms_ik_default_world:
            l_base = arms_ik_default_world.get(l_clav_id, anchor_world)
            l_upper, l_lower = _decompose_ik_spin(
                base_model_matrix=l_base,
                base_joint_xyz=arms_ik_offsets[4],
                target_model_matrix=arms_ik_default_world[l_hand_id],
                ik_data=arms_ik_data[0],
                heuristic_fn=_left_arm_heuristic,
                spin_angle=arms_ik_state_elbow_spin[0],
            )
            arms_ik_default_world[l_upper_id] = l_upper
            arms_ik_default_world[l_fore_id] = l_lower

        if arms_solve_ik and r_upper_id is not None and r_fore_id is not None and r_hand_id is not None and r_hand_id in arms_ik_default_world:
            r_base = arms_ik_default_world.get(r_clav_id, anchor_world)
            r_upper, r_lower = _decompose_ik_spin(
                base_model_matrix=r_base,
                base_joint_xyz=arms_ik_offsets[5],
                target_model_matrix=arms_ik_default_world[r_hand_id],
                ik_data=arms_ik_data[1],
                heuristic_fn=_right_arm_heuristic,
                spin_angle=arms_ik_state_elbow_spin[1],
            )
            arms_ik_default_world[r_upper_id] = r_upper
            arms_ik_default_world[r_fore_id] = r_lower

        runtime_default_world.update(arms_ik_default_world)

    if isinstance(debug_capture, dict):
        debug_capture["arms_local_correction_by_role"] = {
            str(int(role)): [float(q[0]), float(q[1]), float(q[2]), float(q[3])]
            for role, q in arms_local_correction_by_role.items()
        }

    pose_parent_by_bone = {}
    pose_default_quat = {}
    pose_delta_order = {}
    pose_delta_correction = {}

    def _register_pose_target(
        bone_id,
        parent_id=None,
        default_quat=None,
        default_delta_order="pre",
    ):
        if bone_id is None:
            return
        bid = int(bone_id)
        if bid < 0:
            return
        pose_parent_by_bone[bid] = None if parent_id is None else int(parent_id)
        pose_delta_order[bid] = str(default_delta_order)
        if default_quat is not None:
            pose_default_quat[bid] = _quat_normalize_wxyz(default_quat)

    torso_pelvis_id = get_bone(torso_bones, TORSO_PELVIS)
    torso_spine_id = get_bone(torso_bones, TORSO_SPINE)
    torso_spine1_id = get_bone(torso_bones, TORSO_SPINE1)
    torso_spine2_id = get_bone(torso_bones, TORSO_SPINE2)
    torso_neck_id = get_bone(torso_bones, TORSO_NECK)
    torso_head_id = get_bone(torso_bones, TORSO_HEAD)

    if isinstance(debug_capture, dict):
        debug_capture["torso_bones"] = {
            "pelvis": None if torso_pelvis_id is None else int(torso_pelvis_id),
            "spine": None if torso_spine_id is None else int(torso_spine_id),
            "spine1": None if torso_spine1_id is None else int(torso_spine1_id),
            "spine2": None if torso_spine2_id is None else int(torso_spine2_id),
            "neck": None if torso_neck_id is None else int(torso_neck_id),
            "head": None if torso_head_id is None else int(torso_head_id),
        }
        debug_capture["legs_ik_bones"] = {
            "l_toe": get_bone(legs_ik_bones, 0),
            "r_toe": get_bone(legs_ik_bones, 1),
            "l_foot": get_bone(legs_ik_bones, 2),
            "r_foot": get_bone(legs_ik_bones, 3),
            "l_thigh": get_bone(legs_ik_bones, 4),
            "l_calf": get_bone(legs_ik_bones, 5),
            "r_thigh": get_bone(legs_ik_bones, 6),
            "r_calf": get_bone(legs_ik_bones, 7),
        }
        debug_capture["arms_bones"] = {
            "l_clav": get_bone(arms_bones, ARMS_L_CLAV),
            "l_upper": get_bone(arms_bones, ARMS_L_UPPER),
            "l_fore": get_bone(arms_bones, ARMS_L_FORE),
            "l_hand": get_bone(arms_bones, ARMS_L_HAND),
            "r_clav": get_bone(arms_bones, ARMS_R_CLAV),
            "r_upper": get_bone(arms_bones, ARMS_R_UPPER),
            "r_fore": get_bone(arms_bones, ARMS_R_FORE),
            "r_hand": get_bone(arms_bones, ARMS_R_HAND),
        }
    _register_pose_target(
        torso_pelvis_id,
        None,
        _default_quat_for_bone(torso_pelvis_id, _default_quat_or_none(torso_default_quats, 5)),
        default_delta_order="post",
    )
    _register_pose_target(
        torso_spine_id,
        torso_pelvis_id,
        _default_quat_for_bone(torso_spine_id, _default_quat_or_none(torso_default_quats, 0)),
    )
    _register_pose_target(
        torso_spine1_id,
        torso_spine_id,
        _default_quat_for_bone(torso_spine1_id, _default_quat_or_none(torso_default_quats, 1)),
    )
    _register_pose_target(
        torso_spine2_id,
        torso_spine1_id,
        _default_quat_for_bone(torso_spine2_id, _default_quat_or_none(torso_default_quats, 2)),
    )
    _register_pose_target(
        torso_neck_id,
        torso_spine2_id,
        _default_quat_for_bone(torso_neck_id, _default_quat_or_none(torso_default_quats, 3)),
    )
    _register_pose_target(
        torso_head_id,
        torso_neck_id,
        _default_quat_for_bone(torso_head_id, _default_quat_or_none(torso_default_quats, 4)),
    )
    if torso_has_empty_neck and len(torso_other) >= 1:
        empty_neck_id = int(torso_other[0])
        _register_pose_target(empty_neck_id, torso_spine2_id, empty_neck_orient)

    for bone_id in sorted(pose_parent_by_bone.keys()):
        if bone_id not in torso_default_world:
            continue

        local_xform = torso_default_world[bone_id]
        parent_id = pose_parent_by_bone.get(bone_id)
        if parent_id is not None and parent_id in torso_default_world:
            parent_inv = _mat_rigid_inverse(torso_default_world[parent_id])
            local_xform = _mat_local_to_world(local_xform, parent_inv)

        q_default_local = _quat_from_matrix_wxyz(local_xform)
        q_default_ref = pose_default_quat.get(bone_id)
        if q_default_ref is None:
            continue
        delta_order = pose_delta_order.get(bone_id, "pre")
        q_corr = _delta_space_correction_from_default(q_default_local, q_default_ref, order=delta_order)
        if not _quat_is_near_identity(q_corr):
            pose_delta_correction[bone_id] = q_corr

    comps_sorted = sorted(
        decoded_components,
        key=lambda c: (int(c.get("slot_ix", 1 << 30)), int(c.get("comp_ix", -1))),
    )

    for comp in comps_sorted:
        comp_ix = int(comp.get("comp_ix", -1))
        mask = int(comp.get("mask", 0))
        frames = comp.get("frames", [])
        if not frames:
            comp["apply_mode"] = "noop"
            continue

        comp_applied = False

        for frame_idx, values in enumerate(frames):
            frame_no = frame_idx + 1
            cursor = 0

            # runtime-verified
            if comp_ix in (COMP_TORSO_HEAD, COMP_TORSO_HEAD_STD):
                comp_applied = True
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
                        pelvis_id = get_bone(torso_bones, TORSO_PELVIS)
                        _assign_loc(bone_tracks, pelvis_id, frame_no, torso_state_pelvis_pos)

                if len(torso_bones) >= 6 and len(torso_offsets) >= 5:
                    pelvis_id = get_bone(torso_bones, TORSO_PELVIS)
                    if pelvis_id is not None:
                        comp_world[pelvis_id] = _mat_from_quat_pos(torso_state_quats[5], torso_state_pelvis_pos)

                    for i in range(5):
                        bid = get_bone(torso_bones, i + 1)
                        if bid is None:
                            continue
                        comp_world[bid] = _mat_from_quat_pos(torso_state_quats[i], torso_offsets[i])

                    for i in range(1, 6):
                        child = get_bone(torso_bones, i)
                        parent = get_bone(torso_bones, i - 1)
                        if child is None or parent is None:
                            continue
                        if child in comp_world and parent in comp_world:
                            comp_world[child] = _mat_local_to_world(comp_world[child], comp_world[parent])

                    if torso_has_empty_neck and len(torso_other) >= 1:
                        other0 = int(torso_other[0])
                        if other0 >= 0:
                            comp_world[other0] = _mat_from_quat_pos(empty_neck_orient, empty_neck_pos)
                            spine2_id = get_bone(torso_bones, TORSO_SPINE2)
                            if spine2_id is not None and spine2_id in comp_world:
                                comp_world[other0] = _mat_local_to_world(comp_world[other0], comp_world[spine2_id])
                    _cache_component_world_write_once(frame_mats, comp_world)

                    if debug_frame_set and int(frame_no) in debug_frame_set:
                        bucket = _debug_frame_bucket(frame_no)
                        if bucket is not None:
                            torso_state = bucket.setdefault("torso_state", {})
                            torso_state["mask"] = int(mask)
                            torso_state["pelvis_pos"] = [
                                float(torso_state_pelvis_pos[0]),
                                float(torso_state_pelvis_pos[1]),
                                float(torso_state_pelvis_pos[2]),
                            ]
                            torso_state["quats_wxyz"] = [
                                [float(q[0]), float(q[1]), float(q[2]), float(q[3])]
                                for q in torso_state_quats
                            ]
                            torso_world = {}
                            for bid, world_m in comp_world.items():
                                if bid is None or world_m is None:
                                    continue
                                torso_world[str(int(bid))] = _mat_to_rows(world_m)
                            torso_state["component_world"] = torso_world

                    if pelvis_id is not None:
                        _assign_runtime_local_rot(
                            pelvis_id,
                            frame_no,
                            torso_state_quats[5],
                            default_quat=_default_quat_for_bone(pelvis_id, _default_quat_or_none(torso_default_quats, 5)),
                        )

                    for i in range(5):
                        bid = get_bone(torso_bones, i + 1)
                        if bid is None:
                            continue
                        _assign_runtime_local_rot(
                            bid,
                            frame_no,
                            torso_state_quats[i],
                            default_quat=_default_quat_for_bone(bid, _default_quat_or_none(torso_default_quats, i)),
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

            # runtime-verified
            elif comp_ix == COMP_LEGS_IK:
                comp_applied = True
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

                    l_foot_id = get_bone(legs_ik_bones, 2)
                    r_foot_id = get_bone(legs_ik_bones, 3)
                    l_thigh_id = get_bone(legs_ik_bones, 4)
                    l_calf_id = get_bone(legs_ik_bones, 5)
                    r_thigh_id = get_bone(legs_ik_bones, 6)
                    r_calf_id = get_bone(legs_ik_bones, 7)

                    if l_foot_id is not None:
                        comp_world[l_foot_id] = _mat_from_quat_pos(legs_ik_state_foot_quats[0], legs_ik_state_foot_pos[0])
                    if r_foot_id is not None:
                        comp_world[r_foot_id] = _mat_from_quat_pos(legs_ik_state_foot_quats[1], legs_ik_state_foot_pos[1])

                    if legs_solve_ik and l_foot_id is not None and l_foot_id in comp_world and l_thigh_id is not None and l_calf_id is not None:
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

                    if legs_solve_ik and r_foot_id is not None and r_foot_id in comp_world and r_thigh_id is not None and r_calf_id is not None:
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
                    if anchor_id >= 0 and anchor_id in frame_mats:
                        anchor_world = frame_mats[anchor_id]
                    else:
                        pelvis_id = get_bone(torso_bones, TORSO_PELVIS)
                        anchor_world = frame_mats.get(pelvis_id, _mat_identity()) if pelvis_id is not None else _mat_identity()

                    for role in (2, 3, 4, 5, 6, 7):
                        bid = get_bone(legs_ik_bones, role)
                        if bid is None or bid not in comp_world:
                            continue
                        comp_world[bid] = _mat_local_to_world(comp_world[bid], anchor_world)

                    for side in (0, 1):
                        toe_id = get_bone(legs_ik_bones, side)
                        foot_id = get_bone(legs_ik_bones, side + 2)
                        if toe_id is None:
                            continue

                        toe_off = legs_offsets[side] if side < len(legs_offsets) else (0.0, 0.0, 0.0)
                        toe_local = _mat_from_quat_pos(legs_ik_state_toe_quats[side], toe_off)
                        if foot_id is not None and foot_id in comp_world:
                            comp_world[toe_id] = _mat_local_to_world(toe_local, comp_world[foot_id])
                        else:
                            comp_world[toe_id] = toe_local

                    _cache_component_world_write_once(frame_mats, comp_world)

                    if debug_frame_set and int(frame_no) in debug_frame_set:
                        bucket = _debug_frame_bucket(frame_no)
                        if bucket is not None:
                            legs_ik_state = bucket.setdefault("legs_ik_state", {})
                            legs_ik_state["mask"] = int(mask)
                            legs_ik_state["knee_spin"] = [
                                float(legs_ik_state_knee_spin[0]),
                                float(legs_ik_state_knee_spin[1]),
                            ]
                            legs_ik_state["toe_quats_wxyz"] = [
                                [float(q[0]), float(q[1]), float(q[2]), float(q[3])]
                                for q in legs_ik_state_toe_quats
                            ]
                            legs_ik_state["foot_quats_wxyz"] = [
                                [float(q[0]), float(q[1]), float(q[2]), float(q[3])]
                                for q in legs_ik_state_foot_quats
                            ]
                            legs_ik_state["foot_pos"] = [
                                [
                                    float(legs_ik_state_foot_pos[0][0]),
                                    float(legs_ik_state_foot_pos[0][1]),
                                    float(legs_ik_state_foot_pos[0][2]),
                                ],
                                [
                                    float(legs_ik_state_foot_pos[1][0]),
                                    float(legs_ik_state_foot_pos[1][1]),
                                    float(legs_ik_state_foot_pos[1][2]),
                                ],
                            ]
                            legs_world = {}
                            for bid, world_m in comp_world.items():
                                if bid is None or world_m is None:
                                    continue
                                legs_world[str(int(bid))] = _mat_to_rows(world_m)
                            legs_ik_state["component_world"] = legs_world

                l_toe_id = get_bone(legs_ik_bones, 0)
                r_toe_id = get_bone(legs_ik_bones, 1)
                l_foot_id = get_bone(legs_ik_bones, 2)
                r_foot_id = get_bone(legs_ik_bones, 3)
                l_thigh_id = get_bone(legs_ik_bones, 4)
                l_calf_id = get_bone(legs_ik_bones, 5)
                r_thigh_id = get_bone(legs_ik_bones, 6)
                r_calf_id = get_bone(legs_ik_bones, 7)
                if can_build_legs_ik and legs_solve_ik:
                    anchor_id = int(legs_ik_other[0]) if len(legs_ik_other) >= 1 else -1
                    pelvis_id = get_bone(torso_bones, TORSO_PELVIS)
                    thigh_parent_fallback = pelvis_id if pelvis_id is not None else anchor_id
                    if thigh_parent_fallback is not None and int(thigh_parent_fallback) not in frame_mats:
                        thigh_parent_fallback = anchor_id if anchor_id in frame_mats else None

                    l_thigh_default = legs_ik_default_local_quat.get(l_thigh_id) if l_thigh_id is not None else None
                    if l_thigh_default is None:
                        l_thigh_default = _default_quat_or_none(legs_std_default_quats, 4)

                    l_calf_default = legs_ik_default_local_quat.get(l_calf_id) if l_calf_id is not None else None
                    if l_calf_default is None:
                        l_calf_default = _default_quat_or_none(legs_std_default_quats, 5)

                    r_thigh_default = legs_ik_default_local_quat.get(r_thigh_id) if r_thigh_id is not None else None
                    if r_thigh_default is None:
                        r_thigh_default = _default_quat_or_none(legs_std_default_quats, 6)

                    r_calf_default = legs_ik_default_local_quat.get(r_calf_id) if r_calf_id is not None else None
                    if r_calf_default is None:
                        r_calf_default = _default_quat_or_none(legs_std_default_quats, 7)

                    l_foot_default = legs_ik_default_local_quat.get(l_foot_id) if l_foot_id is not None else None
                    if l_foot_default is None:
                        l_foot_default = _default_quat_or_none(legs_ik_default_quats, 2)
                    r_foot_default = legs_ik_default_local_quat.get(r_foot_id) if r_foot_id is not None else None
                    if r_foot_default is None:
                        r_foot_default = _default_quat_or_none(legs_ik_default_quats, 3)
                    l_toe_default = legs_ik_default_local_quat.get(l_toe_id) if l_toe_id is not None else None
                    if l_toe_default is None:
                        l_toe_default = _default_quat_or_none(legs_ik_default_quats, 0)
                    r_toe_default = legs_ik_default_local_quat.get(r_toe_id) if r_toe_id is not None else None
                    if r_toe_default is None:
                        r_toe_default = _default_quat_or_none(legs_ik_default_quats, 1)

                    _assign_parent_space_rot(
                        bone_tracks,
                        l_thigh_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(l_thigh_id, thigh_parent_fallback),
                        default_quat=l_thigh_default,
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        l_calf_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(l_calf_id, l_thigh_id),
                        default_quat=l_calf_default,
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        r_thigh_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(r_thigh_id, thigh_parent_fallback),
                        default_quat=r_thigh_default,
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        r_calf_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(r_calf_id, r_thigh_id),
                        default_quat=r_calf_default,
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        l_foot_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(l_foot_id, l_calf_id),
                        default_quat=l_foot_default,
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        r_foot_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(r_foot_id, r_calf_id),
                        default_quat=r_foot_default,
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        l_toe_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(l_toe_id, l_foot_id),
                        default_quat=l_toe_default,
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        r_toe_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(r_toe_id, r_foot_id),
                        default_quat=r_toe_default,
                    )
                else:
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

            elif comp_ix == COMP_LEGS:
                comp_applied = True
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
                    anchor_id = int(legs_std_other[0])
                    anchor_world = frame_mats.get(anchor_id, _mat_identity()) if anchor_id >= 0 else _mat_identity()

                    parent_role = {
                        4: None,
                        5: 4,
                        2: 5,
                        0: 2,
                        6: None,
                        7: 6,
                        3: 7,
                        1: 3,
                    }
                    eval_order = (4, 5, 2, 0, 6, 7, 3, 1)

                    for role in eval_order:
                        bid = get_bone(legs_std_bones, role)
                        if bid is None:
                            continue

                        local = _mat_from_quat_pos(legs_std_state_quats[role], legs_std_offsets[role])
                        prole = parent_role.get(role)
                        if prole is None:
                            comp_world[bid] = _mat_local_to_world(local, anchor_world)
                            continue

                        parent_bid = get_bone(legs_std_bones, prole)
                        if parent_bid is not None and parent_bid in comp_world:
                            comp_world[bid] = _mat_local_to_world(local, comp_world[parent_bid])
                        else:
                            comp_world[bid] = _mat_local_to_world(local, anchor_world)

                    _cache_component_world_write_once(frame_mats, comp_world)
                    for i in range(8):
                        bid = get_bone(legs_std_bones, i)
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
                        bone_id = get_bone(legs_std_bones, role)
                        _assign_runtime_local_rot(
                            bone_id,
                            frame_no,
                            legs_std_state_quats[bit],
                            default_quat=_default_quat_or_none(legs_std_default_quats, bit),
                        )

            # runtime-verified
            elif comp_ix == COMP_ARMS:
                comp_applied = True
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
                        bid = get_bone(arms_bones, i)
                        if bid is None:
                            continue
                        comp_world[bid] = _mat_from_quat_pos(arms_state_quats[i], arms_offsets[i])

                    left_twist_line_angle = 0.5 * math.pi
                    right_twist_line_angle = 0.5 * math.pi
                    left_smoothed_twist = left_twist_line_angle / 0.33000001
                    right_smoothed_twist = right_twist_line_angle / 0.33000001

                    anchor_id = int(arms_other[4])
                    if anchor_id >= 0 and anchor_id in frame_mats:
                        anchor_world = frame_mats[anchor_id]
                    else:
                        spine2_id = get_bone(torso_bones, TORSO_SPINE2)
                        anchor_world = frame_mats.get(spine2_id, _mat_identity()) if spine2_id is not None else _mat_identity()

                    for i in range(8):
                        bid = get_bone(arms_bones, i)
                        if bid is None or bid not in comp_world:
                            continue
                        if i == 0 or i == 4:
                            comp_world[bid] = _mat_local_to_world(comp_world[bid], anchor_world)
                        else:
                            prev_bid = get_bone(arms_bones, i - 1)
                            if prev_bid is not None and prev_bid in comp_world:
                                comp_world[bid] = _mat_local_to_world(comp_world[bid], comp_world[prev_bid])

                    for i in range(4):
                        if i >= len(arms_other):
                            continue
                        oid = int(arms_other[i])
                        if oid < 0:
                            continue
                        pos = arms_fore_twist[i] if i < len(arms_fore_twist) else (0.0, 0.0, 0.0)
                        angle = left_twist_line_angle if i < 2 else right_twist_line_angle
                        comp_world[oid] = _build_twist_line_xform(pos, angle)

                    for i in range(4):
                        if i >= len(arms_other):
                            continue
                        oid = int(arms_other[i])
                        if oid < 0 or oid not in comp_world:
                            continue

                        if i == 0:
                            parent_id = get_bone(arms_bones, ARMS_L_FORE)
                        elif i == 2:
                            parent_id = get_bone(arms_bones, ARMS_R_FORE)
                        elif i == 1:
                            parent_id = int(arm_indices[8]) if len(arm_indices) > 8 else int(arms_other[0])
                        else:
                            parent_id = int(arm_indices[10]) if len(arm_indices) > 10 else int(arms_other[2])

                        if parent_id in comp_world:
                            comp_world[oid] = _mat_local_to_world(comp_world[oid], comp_world[parent_id])

                    _cache_component_world_write_once(frame_mats, comp_world)

                    if debug_frame_set and int(frame_no) in debug_frame_set:
                        bucket = _debug_frame_bucket(frame_no)
                        if bucket is not None:
                            arms_state = bucket.setdefault("arms_state", {})
                            arms_state["mask"] = int(mask)
                            arms_state["quats_wxyz"] = [
                                [float(q[0]), float(q[1]), float(q[2]), float(q[3])]
                                for q in arms_state_quats
                            ]
                            arms_state["smoothed_twist"] = [
                                float(left_smoothed_twist),
                                float(right_smoothed_twist),
                            ]
                            arms_state["twist_line_angle"] = [
                                float(left_twist_line_angle),
                                float(right_twist_line_angle),
                            ]
                            arms_world = {}
                            for bid, world_m in comp_world.items():
                                if bid is None or world_m is None:
                                    continue
                                arms_world[str(int(bid))] = _mat_to_rows(world_m)
                            arms_state["component_world"] = arms_world

                    if use_full_arm_tracks:
                        roles = (ARMS_L_CLAV, ARMS_L_UPPER, ARMS_L_FORE, ARMS_L_HAND, ARMS_R_CLAV, ARMS_R_UPPER, ARMS_R_FORE, ARMS_R_HAND)
                    else:
                        roles = (ARMS_L_CLAV, ARMS_L_HAND, ARMS_R_CLAV, ARMS_R_HAND)

                    spine2_id = get_bone(torso_bones, TORSO_SPINE2)
                    anchor_parent_id = anchor_id if anchor_id >= 0 else spine2_id

                    for role in roles:
                        bid = get_bone(arms_bones, role)
                        if bid is None:
                            continue

                        parent_role = arms_parent_role_map.get(role)
                        if parent_role is None:
                            parent_fallback = anchor_parent_id
                        else:
                            parent_fallback = get_bone(arms_bones, parent_role)

                        delta_order = arms_default_delta_order_by_role.get(role, "pre")

                        arm_correction_q = arms_local_correction_by_role.get(role)
                        arm_correction_space = "engine"
                        arm_correction_order = delta_order

                        _assign_parent_space_rot(
                            bone_tracks,
                            bid,
                            frame_no,
                            frame_mats,
                            _local_parent_for_bone(bid, parent_fallback),
                            default_quat=_default_quat_for_bone(bid, _default_quat_or_none(arms_default_quats, role)),
                            default_delta_order=delta_order,
                            local_correction_quat=arm_correction_q,
                            local_correction_order=arm_correction_order,
                            local_correction_space=arm_correction_space,
                        )

                    for i in range(4):
                        if i >= len(arms_other):
                            continue
                        oid = int(arms_other[i])
                        if oid < 0:
                            continue
                        if i == 0:
                            parent_id = get_bone(arms_bones, ARMS_L_FORE)
                        elif i == 2:
                            parent_id = get_bone(arms_bones, ARMS_R_FORE)
                        elif i == 1:
                            parent_id = int(arm_indices[8]) if len(arm_indices) > 8 else int(arms_other[0])
                        else:
                            parent_id = int(arm_indices[10]) if len(arm_indices) > 10 else int(arms_other[2])
                        _assign_parent_space_rot(
                            bone_tracks,
                            oid,
                            frame_no,
                            frame_mats,
                            _local_parent_for_bone(oid, parent_id),
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
                        bone_id = get_bone(arm_indices, int(role))
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
                        _assign_runtime_local_rot(
                            bone_id,
                            frame_no,
                            pending[bit],
                            default_quat=_default_quat_for_bone(bone_id, default_q),
                        )

            elif comp_ix == COMP_ARMS_IK:
                comp_applied = True
                frame_mats = _frame_map(frame_no)

                for bit in range(2):
                    if (mask & (1 << bit)) == 0:
                        continue
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is None:
                        break
                    arms_ik_state_track_quats[bit] = _quat_from_xyz(*xyz)

                for bit in range(2, 4):
                    if (mask & (1 << bit)) == 0:
                        continue
                    qxyz, cursor = _consume_xyz(values, cursor)
                    if qxyz is None:
                        break
                    hand_side = bit - 2
                    arms_ik_state_hand_quats[hand_side] = _quat_from_xyz(*qxyz)

                    pos_xyz, cursor = _consume_xyz(values, cursor)
                    if pos_xyz is not None:
                        arms_ik_state_hand_pos[hand_side] = (
                            float(pos_xyz[0]),
                            float(pos_xyz[1]),
                            float(pos_xyz[2]),
                        )

                    if cursor < len(values):
                        arms_ik_state_elbow_spin[hand_side] = float(values[cursor])
                        cursor += 1

                can_build_arms_ik = (
                    len(arms_ik_bones) >= 8
                    and len(arms_ik_offsets) >= 8
                    and len(arms_ik_data) >= 2
                    and len(arms_ik_other) >= 5
                )

                if can_build_arms_ik:
                    comp_world = {}

                    l_clav_id = get_bone(arms_ik_bones, ARMSIK_L_CLAV)
                    r_clav_id = get_bone(arms_ik_bones, ARMSIK_R_CLAV)
                    l_hand_id = get_bone(arms_ik_bones, ARMSIK_L_HAND)
                    r_hand_id = get_bone(arms_ik_bones, ARMSIK_R_HAND)
                    l_upper_id = get_bone(arms_ik_bones, 4)
                    r_upper_id = get_bone(arms_ik_bones, 5)
                    l_fore_id = get_bone(arms_ik_bones, 6)
                    r_fore_id = get_bone(arms_ik_bones, 7)

                    anchor_id = int(arms_ik_other[4])
                    if anchor_id >= 0 and anchor_id in frame_mats:
                        anchor_world = frame_mats[anchor_id]
                    else:
                        spine2_id = get_bone(torso_bones, TORSO_SPINE2)
                        anchor_world = frame_mats.get(spine2_id, _mat_identity()) if spine2_id is not None else _mat_identity()
                    hand_anchor_id = int(arms_ik_other[5]) if len(arms_ik_other) >= 6 else anchor_id
                    if hand_anchor_id >= 0 and hand_anchor_id in frame_mats:
                        hand_anchor_world = frame_mats[hand_anchor_id]
                    else:
                        hand_anchor_world = anchor_world

                    if l_clav_id is not None:
                        l_clav_local = _mat_from_quat_pos(arms_ik_state_track_quats[0], arms_ik_offsets[0])
                        comp_world[l_clav_id] = _mat_local_to_world(l_clav_local, anchor_world)
                    if r_clav_id is not None:
                        r_clav_local = _mat_from_quat_pos(arms_ik_state_track_quats[1], arms_ik_offsets[1])
                        comp_world[r_clav_id] = _mat_local_to_world(r_clav_local, anchor_world)

                    if l_hand_id is not None:
                        l_hand_local = _mat_from_quat_pos(arms_ik_state_hand_quats[0], arms_ik_state_hand_pos[0])
                        comp_world[l_hand_id] = _mat_local_to_world(l_hand_local, hand_anchor_world)
                    if r_hand_id is not None:
                        r_hand_local = _mat_from_quat_pos(arms_ik_state_hand_quats[1], arms_ik_state_hand_pos[1])
                        comp_world[r_hand_id] = _mat_local_to_world(r_hand_local, hand_anchor_world)

                    if arms_solve_ik and l_upper_id is not None and l_fore_id is not None and l_hand_id is not None and l_hand_id in comp_world:
                        l_base = comp_world.get(l_clav_id, anchor_world)
                        l_upper, l_lower = _decompose_ik_spin(
                            base_model_matrix=l_base,
                            base_joint_xyz=arms_ik_offsets[4],
                            target_model_matrix=comp_world[l_hand_id],
                            ik_data=arms_ik_data[0],
                            heuristic_fn=_left_arm_heuristic,
                            spin_angle=arms_ik_state_elbow_spin[0],
                        )
                        comp_world[l_upper_id] = l_upper
                        comp_world[l_fore_id] = l_lower

                    if arms_solve_ik and r_upper_id is not None and r_fore_id is not None and r_hand_id is not None and r_hand_id in comp_world:
                        r_base = comp_world.get(r_clav_id, anchor_world)
                        r_upper, r_lower = _decompose_ik_spin(
                            base_model_matrix=r_base,
                            base_joint_xyz=arms_ik_offsets[5],
                            target_model_matrix=comp_world[r_hand_id],
                            ik_data=arms_ik_data[1],
                            heuristic_fn=_right_arm_heuristic,
                            spin_angle=arms_ik_state_elbow_spin[1],
                        )
                        comp_world[r_upper_id] = r_upper
                        comp_world[r_fore_id] = r_lower

                    _cache_component_world_write_once(frame_mats, comp_world)

                l_clav_id = get_bone(arms_ik_bones, ARMSIK_L_CLAV)
                r_clav_id = get_bone(arms_ik_bones, ARMSIK_R_CLAV)
                l_hand_id = get_bone(arms_ik_bones, ARMSIK_L_HAND)
                r_hand_id = get_bone(arms_ik_bones, ARMSIK_R_HAND)
                _assign_runtime_local_rot(
                    l_clav_id,
                    frame_no,
                    arms_ik_state_track_quats[0],
                    default_quat=_default_quat_for_bone(l_clav_id, _default_quat_or_none(arms_ik_default_track_quats, 0)),
                )
                _assign_runtime_local_rot(
                    r_clav_id,
                    frame_no,
                    arms_ik_state_track_quats[1],
                    default_quat=_default_quat_for_bone(r_clav_id, _default_quat_or_none(arms_ik_default_track_quats, 1)),
                )
                _assign_runtime_local_rot(
                    l_hand_id,
                    frame_no,
                    arms_ik_state_hand_quats[0],
                    default_quat=_default_quat_for_bone(l_hand_id, _default_quat_or_none(arms_ik_default_hand_quats, 0)),
                )
                _assign_runtime_local_rot(
                    r_hand_id,
                    frame_no,
                    arms_ik_state_hand_quats[1],
                    default_quat=_default_quat_for_bone(r_hand_id, _default_quat_or_none(arms_ik_default_hand_quats, 1)),
                )

                if can_build_arms_ik and arms_solve_ik:
                    l_upper_id = get_bone(arms_ik_bones, 4)
                    r_upper_id = get_bone(arms_ik_bones, 5)
                    l_fore_id = get_bone(arms_ik_bones, 6)
                    r_fore_id = get_bone(arms_ik_bones, 7)
                    _assign_parent_space_rot(
                        bone_tracks,
                        l_upper_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(l_upper_id, l_clav_id),
                        default_quat=_default_quat_for_bone(l_upper_id),
                        default_delta_order=arms_default_delta_order_by_role.get(ARMS_L_UPPER, "pre"),
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        l_fore_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(l_fore_id, l_upper_id),
                        default_quat=_default_quat_for_bone(l_fore_id),
                        default_delta_order=arms_default_delta_order_by_role.get(ARMS_L_FORE, "pre"),
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        r_upper_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(r_upper_id, r_clav_id),
                        default_quat=_default_quat_for_bone(r_upper_id),
                        default_delta_order=arms_default_delta_order_by_role.get(ARMS_R_UPPER, "pre"),
                    )
                    _assign_parent_space_rot(
                        bone_tracks,
                        r_fore_id,
                        frame_no,
                        frame_mats,
                        _local_parent_for_bone(r_fore_id, r_upper_id),
                        default_quat=_default_quat_for_bone(r_fore_id),
                        default_delta_order=arms_default_delta_order_by_role.get(ARMS_R_FORE, "pre"),
                    )

            elif comp_ix == COMP_FAKEROOT_STD:
                comp_applied = True
                if mask & 0x1:
                    qxyz, cursor = _consume_xyz(values, cursor)
                    if qxyz is not None:
                        fakeroot_state_quat = _quat_from_xyz(*qxyz)

                    pos, cursor = _consume_xyz(values, cursor)
                    if pos is not None:
                        fakeroot_state_pos = (float(pos[0]), float(pos[1]), float(pos[2]))

                if (mask & 0x2) and cursor < len(values):
                    fakeroot_state_floor = float(values[cursor])
                    cursor += 1

                root_q_bl = _engine_to_blender_quat_wxyz(fakeroot_state_quat)
                root_q_bl = _quat_twist_about_axis_wxyz(root_q_bl, (0.0, 0.0, 1.0))
                if fakeroot_base_twist is None:
                    fakeroot_base_twist = root_q_bl
                if fakeroot_base_pos is None:
                    fakeroot_base_pos = tuple(float(v) for v in fakeroot_state_pos)
                root_q_rel = _quat_mul_wxyz(_quat_inverse_wxyz(fakeroot_base_twist), root_q_bl)
                root_pos_rel = (
                    float(fakeroot_state_pos[0] - fakeroot_base_pos[0]),
                    float(fakeroot_state_pos[1] - fakeroot_base_pos[1]),
                    float(fakeroot_state_pos[2] - fakeroot_base_pos[2]),
                )
                if apply_root_motion:
                    _assign_rot(bone_tracks, ROOT_BONE_TRACK_ID, frame_no, root_q_rel)
                    _assign_loc(bone_tracks, ROOT_BONE_TRACK_ID, frame_no, root_pos_rel)

                _ = fakeroot_state_floor

            elif comp_ix == COMP_FING52:
                for bit in range(20):
                    if (mask & (1 << bit)) == 0:
                        continue

                    if bit < 2:
                        xyz, cursor = _consume_xyz(values, cursor)
                        if xyz is None:
                            break
                        fing52_state_thumb_quats[bit] = _quat_from_xyz(*xyz)
                        continue

                    if bit < 10:
                        if cursor + 2 > len(values):
                            break
                        y_ang = float(values[cursor])
                        z_ang = float(values[cursor + 1])
                        cursor += 2
                        fing52_state_base_yz[bit - 2] = (y_ang, z_ang)
                        continue

                    if cursor >= len(values):
                        break
                    fing52_state_hinge[bit - 10] = float(values[cursor])
                    cursor += 1

                if _apply_fing52_pose(
                    frame_no,
                    fing52_state_thumb_quats,
                    fing52_state_base_yz,
                    fing52_state_hinge,
                ):
                    comp_applied = True


            elif comp_ix == COMP_FING5_CURL:
                frame_applied = False

                for bit in range(10):
                    if (mask & (1 << bit)) == 0:
                        continue

                    if bit < 2:
                        xyz, cursor = _consume_xyz(values, cursor)
                        if xyz is None:
                            break
                        fing5_curl_state_thumb_quats[bit] = _quat_from_xyz(*xyz)
                        if cursor < len(values):
                            fing5_curl_state_hinge[bit] = float(values[cursor])
                            cursor += 1
                        continue

                    if cursor + 2 > len(values):
                        break
                    z_ang = float(values[cursor])
                    y_ang = float(values[cursor + 1])
                    cursor += 2
                    fing5_curl_state_base_z[bit - 2] = z_ang
                    fing5_curl_state_hinge[bit] = y_ang

                if len(fing5_curl_bones) >= 30:
                    for base_ix in range(10):
                        bid = get_bone(fing5_curl_bones, base_ix)
                        if bid is None:
                            continue

                        if base_ix < 2:
                            q = fing5_curl_state_thumb_quats[base_ix]
                            default_q = _default_quat_or_none(fing5_curl_default_quats, base_ix)
                        else:
                            q = _quat_from_yz_angles_wxyz(
                                fing5_curl_state_hinge[base_ix],
                                fing5_curl_state_base_z[base_ix - 2],
                            )
                            default_q = None

                        _assign_runtime_local_rot(bid, frame_no, q, default_quat=default_q)
                        frame_applied = True

                    for chain_ix in range(10):
                        mid_bid = get_bone(fing5_curl_bones, 10 + chain_ix)
                        tip_bid = get_bone(fing5_curl_bones, 20 + chain_ix)
                        base_ang = float(fing5_curl_state_hinge[chain_ix])
                        q_mid = _quat_axis_angle_wxyz((1.0, 0.0, 0.0), base_ang)
                        q_tip = _quat_axis_angle_wxyz(
                            (1.0, 0.0, 0.0),
                            _fing52_tip_hinge_angle(base_ang, is_thumb=(chain_ix < 2)),
                        )
                        if chain_ix >= 2:
                            q_tip = _quat_axis_angle_wxyz((1.0, 0.0, 0.0), base_ang)
                        _assign_runtime_local_rot(mid_bid, frame_no, q_mid)
                        _assign_runtime_local_rot(tip_bid, frame_no, q_tip)
                        frame_applied = True

                if frame_applied:
                    comp_applied = True

            elif comp_ix == COMP_FING5_REDUCED:
                frame_applied = False

                for bit in range(30):
                    if (mask & (1 << bit)) == 0:
                        continue

                    if bit < 2:
                        xyz, cursor = _consume_xyz(values, cursor)
                        if xyz is None:
                            break
                        fing5_reduced_state_thumb_quats[bit] = _quat_from_xyz(*xyz)
                        continue

                    if bit < 10:
                        if cursor + 2 > len(values):
                            break
                        z_ang = float(values[cursor])
                        y_ang = float(values[cursor + 1])
                        cursor += 2
                        fing5_reduced_state_base_yz[bit - 2] = (y_ang, z_ang)
                        continue

                    if bit < 20:
                        if cursor >= len(values):
                            break
                        fing5_reduced_state_mid_hinge[bit - 10] = float(values[cursor])
                        cursor += 1
                        continue

                    if cursor >= len(values):
                        break
                    fing5_reduced_state_tip_hinge[bit - 20] = float(values[cursor])
                    cursor += 1

                if len(fing5_reduced_bones) >= 30:
                    for base_ix in range(10):
                        bid = get_bone(fing5_reduced_bones, base_ix)
                        if bid is None:
                            continue

                        if base_ix < 2:
                            q = fing5_reduced_state_thumb_quats[base_ix]
                            default_q = _default_quat_or_none(fing5_reduced_default_quats, base_ix)
                        else:
                            y_ang, z_ang = fing5_reduced_state_base_yz[base_ix - 2]
                            q = _quat_from_yz_angles_wxyz(y_ang, z_ang)
                            default_q = None

                        _assign_runtime_local_rot(bid, frame_no, q, default_quat=default_q)
                        frame_applied = True

                    for chain_ix in range(10):
                        mid_bid = get_bone(fing5_reduced_bones, 10 + chain_ix)
                        tip_bid = get_bone(fing5_reduced_bones, 20 + chain_ix)
                        q_mid = _quat_axis_angle_wxyz((1.0, 0.0, 0.0), fing5_reduced_state_mid_hinge[chain_ix])
                        q_tip = _quat_axis_angle_wxyz((1.0, 0.0, 0.0), fing5_reduced_state_tip_hinge[chain_ix])
                        _assign_runtime_local_rot(mid_bid, frame_no, q_mid)
                        _assign_runtime_local_rot(tip_bid, frame_no, q_tip)
                        frame_applied = True

                if frame_applied:
                    comp_applied = True

            elif comp_ix == COMP_FING5:
                frame_applied = False

                for bit in range(30):
                    if (mask & (1 << bit)) == 0:
                        continue
                    xyz, cursor = _consume_xyz(values, cursor)
                    if xyz is None:
                        break
                    fing5_full_state_quats[bit] = _quat_from_xyz(*xyz)

                if len(fing5_full_bones) >= 30:
                    for bit in range(30):
                        bid = get_bone(fing5_full_bones, bit)
                        if bid is None:
                            continue
                        _assign_runtime_local_rot(
                            bid,
                            frame_no,
                            fing5_full_state_quats[bit],
                            default_quat=_default_quat_or_none(fing5_full_default_quats, bit),
                        )
                        frame_applied = True

                if frame_applied:
                    comp_applied = True

            elif comp_ix == COMP_ARBITRARY_PO:
                comp_applied = True
                notes = comp.setdefault("apply_notes", [])
                if "arbitrary_po_metadata_only" not in notes:
                    notes.append("arbitrary_po_metadata_only")
                if arbitrary_nodes and "arbitrary_node_count" not in comp:
                    comp["arbitrary_node_count"] = int(len(arbitrary_nodes))
                continue

            elif comp_ix == COMP_GENERIC:
                comp_applied = True
                notes = comp.setdefault("apply_notes", [])
                if "generic_metadata_only" not in notes:
                    notes.append("generic_metadata_only")
                continue

            elif comp_ix == COMP_TENTACLE:
                frame_applied = False
                for bit in range(15):
                    if (mask & (1 << bit)) == 0:
                        continue
                    if cursor >= len(values):
                        break
                    tentacle_state_values[bit] = float(values[cursor])
                    cursor += 1
                    frame_applied = True

                controls_by_frame = comp.setdefault("tentacle_controls", {})
                controls_by_frame[int(frame_no)] = _tentacle_controls_from_state(tentacle_state_values)
                if frame_applied or controls_by_frame:
                    comp_applied = True
                continue

        comp["apply_mode"] = "applied" if comp_applied else "noop"

    total_frames = max(
        (len(comp.get("frames", ())) for comp in decoded_components if isinstance(comp.get("frames"), list)),
        default=0,
    )
    if total_frames > 0 and fing52_can_runtime_build:
        finger_bone_ids = {
            int(bid)
            for bid in fing52_bones[:30]
            if bid is not None and int(bid) >= 0
        }
        if finger_bone_ids and not any(bid in bone_tracks for bid in finger_bone_ids):
            for frame_no in range(1, total_frames + 1):
                _apply_fing52_pose(
                    frame_no,
                    fing52_state_thumb_quats,
                    fing52_state_base_yz,
                    fing52_state_hinge,
                )


    blended_pose_tracks = bone_tracks
    blended_frame_xforms = frame_xforms

    for frame_no in sorted(blended_frame_xforms.keys(), key=lambda x: int(x)):
        frame_mats = blended_frame_xforms.get(int(frame_no), {})
        if not frame_mats:
            continue

        for bone_id in sorted(pose_parent_by_bone.keys()):
            if bone_id not in frame_mats:
                continue

            local_xform = frame_mats[bone_id]
            parent_id = pose_parent_by_bone.get(bone_id)
            if parent_id is not None and parent_id in frame_mats:
                parent_inv = _mat_rigid_inverse(frame_mats[parent_id])
                local_xform = _mat_local_to_world(local_xform, parent_inv)

            q_local_from_matrix = _quat_from_matrix_wxyz(local_xform)
            default_q = pose_default_quat.get(bone_id)
            delta_order = pose_delta_order.get(bone_id, "pre")
            q_local = _delta_from_default_local(q_local_from_matrix, default_q, order=delta_order)
            q_correction = pose_delta_correction.get(bone_id)
            if q_correction is not None:
                if str(delta_order).lower() == "post":
                    q_local = _quat_mul_wxyz(q_local, q_correction)
                else:
                    q_local = _quat_mul_wxyz(q_correction, q_local)
            q_local_bl = _engine_to_blender_quat_wxyz(q_local)
            _assign_rot(blended_pose_tracks, bone_id, int(frame_no), q_local_bl)

            if debug_frame_set and int(frame_no) in debug_frame_set:
                bucket = _debug_frame_bucket(frame_no)
                if bucket is not None:
                    finalize_debug = bucket.setdefault("finalize", {})
                    finalize_debug[str(int(bone_id))] = {
                        "parent_bone_id": None if parent_id is None else int(parent_id),
                        "world_matrix": _mat_to_rows(frame_mats[bone_id]),
                        "local_matrix": _mat_to_rows(local_xform),
                        "quat_from_matrix_wxyz": [
                            float(q_local_from_matrix[0]),
                            float(q_local_from_matrix[1]),
                            float(q_local_from_matrix[2]),
                            float(q_local_from_matrix[3]),
                        ],
                        "default_quat_wxyz": None if default_q is None else [
                            float(default_q[0]),
                            float(default_q[1]),
                            float(default_q[2]),
                            float(default_q[3]),
                        ],
                        "default_delta_order": str(delta_order),
                        "default_delta_correction_wxyz": None if q_correction is None else [
                            float(q_correction[0]),
                            float(q_correction[1]),
                            float(q_correction[2]),
                            float(q_correction[3]),
                        ],
                        "final_engine_quat_wxyz": [
                            float(q_local[0]),
                            float(q_local[1]),
                            float(q_local[2]),
                            float(q_local[3]),
                        ],
                        "final_blender_quat_wxyz": [
                            float(q_local_bl[0]),
                            float(q_local_bl[1]),
                            float(q_local_bl[2]),
                            float(q_local_bl[3]),
                        ],
                    }


    if isinstance(runtime_capture, dict):
        runtime_capture["default_world_engine"] = {
            int(bid): _mat_to_rows(world_m)
            for bid, world_m in runtime_default_world.items()
            if bid is not None and int(bid) >= 0 and world_m is not None
        }
        runtime_capture["frame_world_engine"] = {
            int(frame_no): {
                int(bid): _mat_to_rows(world_m)
                for bid, world_m in frame_mats.items()
                if bid is not None and int(bid) >= 0 and world_m is not None
            }
            for frame_no, frame_mats in blended_frame_xforms.items()
            if isinstance(frame_mats, dict) and frame_mats
        }

        runtime_bone_ids = set(runtime_capture["default_world_engine"].keys())
        for frame_mats in runtime_capture["frame_world_engine"].values():
            runtime_bone_ids.update(int(bid) for bid in frame_mats.keys())

        parent_by_bone = {}

        def _set_runtime_parent(child_id, parent_id):
            if child_id is None:
                return
            bid = int(child_id)
            if bid < 0:
                return
            pid = -1 if parent_id is None else int(parent_id)
            if pid == bid:
                pid = -1
            parent_by_bone[bid] = pid if pid >= 0 else -1

        _set_runtime_parent(torso_pelvis_id, None)
        _set_runtime_parent(torso_spine_id, torso_pelvis_id)
        _set_runtime_parent(torso_spine1_id, torso_spine_id)
        _set_runtime_parent(torso_spine2_id, torso_spine1_id)
        if torso_has_empty_neck and len(torso_other) >= 1:
            empty_neck_id = int(torso_other[0])
            _set_runtime_parent(empty_neck_id, torso_spine2_id)
            _set_runtime_parent(torso_neck_id, empty_neck_id)
        else:
            _set_runtime_parent(torso_neck_id, torso_spine2_id)
        _set_runtime_parent(torso_head_id, torso_neck_id)

        def _set_leg_chain(leg_bones, thigh_parent_id):
            if len(leg_bones) < 8:
                return
            l_toe = get_bone(leg_bones, 0)
            r_toe = get_bone(leg_bones, 1)
            l_foot = get_bone(leg_bones, 2)
            r_foot = get_bone(leg_bones, 3)
            l_thigh = get_bone(leg_bones, 4)
            l_calf = get_bone(leg_bones, 5)
            r_thigh = get_bone(leg_bones, 6)
            r_calf = get_bone(leg_bones, 7)

            _set_runtime_parent(l_thigh, thigh_parent_id)
            _set_runtime_parent(l_calf, l_thigh)
            _set_runtime_parent(l_foot, l_calf)
            _set_runtime_parent(l_toe, l_foot)
            _set_runtime_parent(r_thigh, thigh_parent_id)
            _set_runtime_parent(r_calf, r_thigh)
            _set_runtime_parent(r_foot, r_calf)
            _set_runtime_parent(r_toe, r_foot)

        _set_leg_chain(legs_std_bones, torso_pelvis_id)
        _set_leg_chain(legs_ik_bones, torso_pelvis_id)

        def _set_arm_chain(arm_bones, arm_other, clav_parent_id, is_ik=False):
            if is_ik:
                if len(arm_bones) < 8:
                    return
                l_clav = get_bone(arm_bones, 0)
                r_clav = get_bone(arm_bones, 1)
                l_hand = get_bone(arm_bones, 2)
                r_hand = get_bone(arm_bones, 3)
                l_upper = get_bone(arm_bones, 4)
                r_upper = get_bone(arm_bones, 5)
                l_fore = get_bone(arm_bones, 6)
                r_fore = get_bone(arm_bones, 7)
            else:
                if len(arm_bones) < 8:
                    return
                l_clav = get_bone(arm_bones, ARMS_L_CLAV)
                l_upper = get_bone(arm_bones, ARMS_L_UPPER)
                l_fore = get_bone(arm_bones, ARMS_L_FORE)
                l_hand = get_bone(arm_bones, ARMS_L_HAND)
                r_clav = get_bone(arm_bones, ARMS_R_CLAV)
                r_upper = get_bone(arm_bones, ARMS_R_UPPER)
                r_fore = get_bone(arm_bones, ARMS_R_FORE)
                r_hand = get_bone(arm_bones, ARMS_R_HAND)

            _set_runtime_parent(l_clav, clav_parent_id)
            _set_runtime_parent(l_upper, l_clav)
            _set_runtime_parent(l_fore, l_upper)
            _set_runtime_parent(l_hand, l_fore)
            _set_runtime_parent(r_clav, clav_parent_id)
            _set_runtime_parent(r_upper, r_clav)
            _set_runtime_parent(r_fore, r_upper)
            _set_runtime_parent(r_hand, r_fore)

            if len(arm_other) >= 4:
                l_twist0 = int(arm_other[0])
                l_twist1 = int(arm_other[1])
                r_twist0 = int(arm_other[2])
                r_twist1 = int(arm_other[3])
                _set_runtime_parent(l_twist0, l_fore)
                _set_runtime_parent(l_twist1, l_twist0)
                _set_runtime_parent(r_twist0, r_fore)
                _set_runtime_parent(r_twist1, r_twist0)

        arms_anchor_parent = int(arms_other[4]) if len(arms_other) >= 5 and int(arms_other[4]) >= 0 else torso_spine2_id
        arms_ik_anchor_parent = int(arms_ik_other[4]) if len(arms_ik_other) >= 5 and int(arms_ik_other[4]) >= 0 else torso_spine2_id
        _set_arm_chain(arms_bones, arms_other, arms_anchor_parent, is_ik=False)
        _set_arm_chain(arms_ik_bones, arms_ik_other, arms_ik_anchor_parent, is_ik=True)

        def _set_finger_chain(finger_bones, finger_other):
            if len(finger_bones) < 30 or len(finger_other) < 2:
                return
            for chain_ix in range(10):
                base_id = get_bone(finger_bones, chain_ix)
                mid_id = get_bone(finger_bones, 10 + chain_ix)
                tip_id = get_bone(finger_bones, 20 + chain_ix)
                anchor_slot = _fing52_anchor_slot(chain_ix)
                anchor_id = None
                if anchor_slot < len(finger_other):
                    anchor_raw = int(finger_other[anchor_slot])
                    if anchor_raw >= 0:
                        anchor_id = anchor_raw
                _set_runtime_parent(base_id, anchor_id)
                _set_runtime_parent(mid_id, base_id)
                _set_runtime_parent(tip_id, mid_id)

        _set_finger_chain(fing52_bones, fing52_other)


        for bid in sorted(runtime_bone_ids):
            if bid in parent_by_bone:
                continue
            pid = skel_parent_map.get(int(bid))
            if pid is None:
                pid = pose_parent_by_bone.get(int(bid))
            if pid is None or int(pid) < 0 or int(pid) == int(bid):
                parent_by_bone[int(bid)] = -1
            else:
                parent_by_bone[int(bid)] = int(pid)

        runtime_capture["parent_by_bone"] = parent_by_bone

    return blended_pose_tracks


