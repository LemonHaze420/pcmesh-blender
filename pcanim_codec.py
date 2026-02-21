import math

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


def _get_num_tracks_for_comp(comp_ix, mask):
    if comp_ix in (COMP_ARBITRARY_PO, COMP_GENERIC):
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


def _get_num_bytes_for_comp(comp_ix, mask):
    if comp_ix in (COMP_ARBITRARY_PO, COMP_GENERIC):
        return -1

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


def _decode_component_frames(comp_ix, codec_ixs, encoded_data, mask, frame_count, current_time, is_scene_anim):
    if frame_count <= 0:
        return []
    if not codec_ixs:
        return [[] for _ in range(frame_count)]

    tracks = [_TrackState() for _ in range(len(codec_ixs))]
    dec = _BitStream(encoded_data)

    out = []
    for frame in range(frame_count):
        if comp_ix in (COMP_LEGS_IK, COMP_ARMS_IK):
            _integrate_for_frame_ik(tracks, codec_ixs, mask, frame, dec, current_time, is_scene_anim)
        elif comp_ix in (COMP_LEGS, COMP_ARMS):
            _integrate_for_frame_quat_masked(
                tracks,
                codec_ixs,
                mask,
                frame,
                dec,
                current_time,
                is_scene_anim,
                bit_count=8,
            )
        elif comp_ix == COMP_FAKEROOT_STD:
            _integrate_for_frame_fakeroot(tracks, codec_ixs, mask, frame, dec, current_time, is_scene_anim)
        else:
            _integrate_for_frame_torso(tracks, codec_ixs, mask, frame, dec, current_time, is_scene_anim)
        out.append([float(t.whole) for t in tracks])
    return out

