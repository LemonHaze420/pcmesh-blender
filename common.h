#pragma once

#define u32 uint32_t
#define s32 int32_t

#define u16 uint16_t
#define s16 int16_t

#define u8 uint8_t
#define s8 int8_t

struct tlFixedString {
	uint32_t  hash;
	char string[28];
};
struct vector4 {
	float v[4];
};
struct vector3 {
	float v[3];
};
struct matrix4x4 {
	vector4 m[4];
};


// General

char evaluate_lerp_params(
    uint32_t flags,
    float T_scale,
    uint32_t frm_count,
    float* outT,
    unsigned int* out_next_idx, unsigned int* out_curr_idx,
    float* outBlendT,
    float index)
{
    bool should_loop = (flags & 1);
    *outT = index * T_scale;
    if (index == 1.0f && T_scale == 0.0f) {
        *out_next_idx = 0;
        *out_curr_idx = 0;
        *outBlendT = 0.0f;
        *outT = 0.0f;
        return 0;
    }

    float total_frames = (float)frm_count;
    float effective_frames = should_loop ? total_frames : (total_frames - 1.0f);
    if (effective_frames < 0.0f) effective_frames = 0.0f;

    float raw_pos = index * effective_frames;
    float pos_floor = std::floor(raw_pos);
    float pos_ceil = std::ceil(raw_pos);

    unsigned int next_idx = (unsigned int)pos_ceil;
    *outBlendT = raw_pos - pos_floor;

    if (pos_ceil == raw_pos) {
        next_idx++;
        *outBlendT = 0.0f;
    }

    char loop_count = 0;
    if (should_loop) {
        if (frm_count > 0) {
            loop_count = (char)(next_idx / frm_count);
            next_idx %= frm_count;
        }
    }
    else {
        unsigned int last_frame = (frm_count > 0) ? (frm_count - 1) : 0;

        if (index >= 1.0f) {
            *outBlendT = 1.0f;
            next_idx = last_frame;
        }
        else if (next_idx > last_frame) {
            next_idx = last_frame;
        }
    }

    if (next_idx > 0) {
        *out_curr_idx = next_idx - 1;
    }
    else {
        if (should_loop && frm_count > 0)
            *out_curr_idx = frm_count - 1;
        else
            *out_curr_idx = 0;
    }

    *out_next_idx = next_idx;
    return loop_count;
}

// Components

enum CompDataFlags
{
	HAS_TRACK_DATA = 0x1,
	HAS_PER_ANIM_DATA = 0x2,
	HAS_PER_SKEL_DATA = 0x4,
};


constexpr bool get_has_extras(uint32_t mask)
{
    return (mask & 0x20) != 0;
}

int get_num_quats(uint32_t mask)
{
    return __popcnt(mask & 0x1F);
}

int get_num_tracks(uint32_t mask)
{
    return 3 * get_num_quats(mask) + (get_has_extras(mask)  ? 6 : 0);
}

constexpr int count(uint32_t mask, uint32_t filter, int weight = 1) {
    return weight * std::popcount(mask & filter);
}

constexpr int to_bytes(int tracks, int header_size = 0) {
    return (tracks * 16) + header_size;
}


// TorsoHeadEnt/StdPose

inline int getNumTracks_TorsoHeadEnt(uint32_t mask) {
    return count(mask, 0x1Fu, 3) + count(mask, 0x20u, 6);
}

inline int getNumBytes_TorsoHeadEnt(uint32_t mask) {
    return to_bytes(getNumTracks_TorsoHeadEnt(mask));
}

inline int getNumBytes_TorsoHeadStdPose(uint32_t mask) {
    return to_bytes(getNumTracks_TorsoHeadEnt(mask) + 15);
}

// LegsIK

inline int getNumTracks_LegsIK(uint32_t mask) {
    return count(mask, 0xFu, 3) + count(mask, 0xCu, 4);
}

inline int getNumBytes_LegsIK(uint32_t mask) {
    return to_bytes(getNumTracks_LegsIK(mask));
}

// Arms & Standard Legs

inline int getNumTracks_Limbs(uint32_t mask, int base_tracks) {
    return base_tracks + count(mask, 0xFFu, 3);
}

inline int getNumBytes_ArmsEntChar(uint32_t mask) {
    return to_bytes(getNumTracks_Limbs(mask, 17));
}

inline int getNumBytes_StandardLegsFeet(uint32_t mask) {
    return to_bytes(getNumTracks_Limbs(mask, 17));
}

// Tentacles

inline int getNumBytes_Tentacles(uint32_t mask) {
    int tracks = std::popcount(mask & 0x7FFFu);
    return to_bytes(tracks, 136);
}

// Fingers (Standard, Reduced, 52Knuck)

inline int getNumBytes_StandardFingers5(uint32_t mask) {
    int tracks = 61 + count(mask, 0x3FFFFFFFu, 3);
    return to_bytes(tracks);
}

inline int getNumTracks_ReducedFingersLogic(uint32_t mask) {
    return std::popcount(mask & 0x3FFFFFFFu)
        + std::popcount(mask & 0x3FFu)
        + std::popcount(mask & 0x3u);
}

inline int getNumBytes_ReducedFingers5(uint32_t mask) {
    return to_bytes(getNumTracks_ReducedFingersLogic(mask));
}

inline int getNumBytes_Fing52KnuckEnt(uint32_t mask) {
    return to_bytes(getNumTracks_ReducedFingersLogic(mask));
}

// CurlFingers5

inline int getNumBytes_CurlFingers5(uint32_t mask) {
    int tracks = 15 + count(mask, 0x3FFu, 2) + count(mask, 0x3u, 2);
    return to_bytes(tracks);
}

// FakerootStdEnt

inline int getNumBytes_FakerootStdEnt(uint32_t mask) {
    int tracks = 9 + count(mask, 0x1u, 6) + count(mask, 0x2u, 1);
    return to_bytes(tracks);
}


// ArbitraryPOCharComp

inline int getNumBytes_ArbitraryPOCharComp(const uint32_t* bitfield, uint32_t totalSlots) {
    int total_tracks = 0;
    uint32_t full_ints = totalSlots / 32;

    for (uint32_t i = 0; i < full_ints; ++i) {
        total_tracks += 3 * std::popcount(bitfield[i]);
    }

    uint32_t rem = totalSlots % 32;
    if (rem) {
        uint32_t mask = (1u << rem) - 1;
        total_tracks += 3 * std::popcount(bitfield[full_ints] & mask);
    }

    return to_bytes(total_tracks, 0x3C); // 0x3C header
}
