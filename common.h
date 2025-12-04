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
struct quat {
    union {
        vector4 v4;
        float v[4];
    };

    void compose(vector3* xyz) {
        float x, y, z;
        x = v4.v[0] = xyz->v[0];
        y = v4.v[1] = xyz->v[1];
        z = v4.v[2] = xyz->v[2];
        v4.v[3] = std::sqrt((float)std::fabs(1.0 - (y * y + z * z + x * x)));
    }

    void norm() {
        float x = v[0], y = v[1], z = v[2], w = v[3];
        float len2 = x * x + y * y + z * z + w * w;
        if (len2 > 0.0f) {
            float invLen = 1.0f / std::sqrt(len2);
            v[0] = x * invLen;
            v[1] = y * invLen;
            v[2] = z * invLen;
            v[3] = w * invLen;
        }
    }
    static quat mul(const quat& q_delta, const quat& q_base) {
        quat q_out;

        const float ax = q_delta.v[0];
        const float ay = q_delta.v[1];
        const float az = q_delta.v[2];
        const float aw = q_delta.v[3];

        const float bx = q_base.v[0];
        const float by = q_base.v[1];
        const float bz = q_base.v[2];
        const float bw = q_base.v[3];

        q_out.v[0] = bw * ax + ay * bz - az * by + bx * aw;
        q_out.v[1] = ay * bw + aw * by - bz * ax + bx * az;
        q_out.v[2] = ax * by - ay * bx + bw * az + bz * aw;
        q_out.v[3] = bw * aw - (ay * by + ax * bx + bz * az);
        return q_out;
    }
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


	printf("loops=%d  T=%f  blend=%f  next=%u  curr=%u\n", loop_count, outT, outBlendT, next_idx, *out_curr_idx);

    return loop_count;
}

// Components

enum iComponentID {
    iArbitraryPO,
    igeneric,
    iFakerootStdEnt,
    iTorsoHeadEnt,
    iTorsoHeadStdPose,
    iLegsEnt			= 5,
    iLegsIKEnt,
    iArmsEnt,
    iArmIKEnt,
    iTentacleEnt,
    iFing52KnuckEnt,
    iFing5CurlEnt,
    iFing5RedEnt,
    iFing5Ent
};

enum CompDataFlags
{
	HAS_TRACK_DATA = 0x1,
	HAS_PER_ANIM_DATA = 0x2,
	HAS_PER_SKEL_DATA = 0x4,
};

constexpr bool has_track(uint32_t flags) {
    return (flags & (HAS_PER_ANIM_DATA | HAS_TRACK_DATA)) == (HAS_PER_ANIM_DATA | HAS_TRACK_DATA);
}

constexpr bool get_has_extras(uint32_t mask)
{
    return (mask & 0x20) != 0;
}

int get_num_quats(uint32_t mask)
{
    return std::popcount(mask & 0x1F);
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


// TorsoHeadEnt/StdPose - D:8

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

static inline int get_numBytes_for_comp(iComponentID compIx, int mask) {
    int len = -1;

    switch (compIx) {
        case iArbitraryPO:
        case igeneric: {
            break;
        }
        case iFakerootStdEnt: {
            len = getNumBytes_FakerootStdEnt(mask);
            break;
        }
        case iTorsoHeadStdPose:
        case iTorsoHeadEnt: {
            len = getNumBytes_TorsoHeadEnt(mask);
            break;
        }
        case iLegsEnt: {
            len = getNumBytes_StandardLegsFeet(mask);
            break;
        }
        case iLegsIKEnt: {
            len = getNumBytes_LegsIK(mask);
            break;
        }
        case iArmsEnt: {
            len = getNumBytes_ArmsEntChar(mask);
            break;
        }
        case iArmIKEnt: {
            break;
        }
        case iTentacleEnt: {
            len = getNumBytes_Tentacles(mask);
            break;
        }
        case iFing52KnuckEnt: {
            len = getNumBytes_Fing52KnuckEnt(mask);
            break;
        }
        case iFing5CurlEnt: {
            len = getNumBytes_CurlFingers5(mask);
            break;
        }
        case iFing5RedEnt: {
            len = getNumBytes_ReducedFingers5(mask);
            break;
        }
        case iFing5Ent: {
            len = getNumBytes_StandardFingers5(mask);
            break;
        }
        default:
            break;
    }
    return len;
}


// Animation

enum nalAnimFlags : int32_t {
    IS_SCENE_ANIM = 0x20000,
    LOOPING = 1
};


enum class nalComponentType : uint32_t
{
    ArbitraryPO = 0xC5E45DCF,
    Generic = 0xEC4755BD,
    FakerootEntropyCompressed = 0xB916E121,
    TorsoHead_TwoNeck_Compressed = 0x7E916D6A,  // done
    TorsoHead_OneNeck_Compressed = 0x70EA5DF2,  // done
    LegsFeet_Compressed = 0x47CBEBDB,
    LegsFeet_IK_Compressed = 0xA556994F,  // done
    ArmsHands_Compressed = 0xE01F4F4D,  // done
    ArmsHands_IK_Compressed = 0xF0AD5C8E,  // untested
    Tentacles_Compressed = 0x464A04D8,
    FiveFinger_Top2KnuckleCurl = 0xE7D9A8D3,
    FiveFinger_IndividualCurl = 0xE7A8F925,
    FiveFinger_ReducedAngular = 0xE78254B9,
    FiveFinger_FullRotational = 0xAFEB6A28
};
constexpr std::string_view component_to_string(nalComponentType e) {
    switch (e) {
    case nalComponentType::ArbitraryPO:                 return "ArbitraryPO";
    case nalComponentType::Generic:                     return "Generic";
    case nalComponentType::FakerootEntropyCompressed:   return "Fakeroot Entropy Compressed";
    case nalComponentType::TorsoHead_TwoNeck_Compressed:return "TorsoHead TwoNeck Entropy Compressed";
    case nalComponentType::TorsoHead_OneNeck_Compressed:return "TorsoHead OneNeck Entropy Compressed";
    case nalComponentType::LegsFeet_Compressed:         return "Legs&Feet Entropy Compressed";
    case nalComponentType::LegsFeet_IK_Compressed:      return "Legs&Feet IK Entropy Compressed";
    case nalComponentType::ArmsHands_Compressed:        return "Arms&Hands Entropy Compressed";
    case nalComponentType::ArmsHands_IK_Compressed:     return "Arms&Hands IK Entropy Compressed";
    case nalComponentType::Tentacles_Compressed:        return "Tentacles Compressed";
    case nalComponentType::FiveFinger_Top2KnuckleCurl:  return "Five Finger Top 2 Knuckle Curl Entropy Compressed";
    case nalComponentType::FiveFinger_IndividualCurl:   return "Five Finger Individual Finger Curl Entropy Compressed";
    case nalComponentType::FiveFinger_ReducedAngular:   return "Five Finger Reduced-size Angular Entropy Compressed";
    case nalComponentType::FiveFinger_FullRotational:   return "Five Finger Full-Rotational Entropy Compressed";
    default:                                  return "Unknown type";
    }
}

struct TorsoHeadPose {
    quat spine;
    quat spine1;
    quat spine2;
    quat neck;
    quat head;
    quat pelvisOrient;
    vector3 pelvisPos;
    uint32_t pad;
};
struct LegsPose {
    quat l_toe;
    quat r_toe;
    quat l_foot;
    quat r_foot;
};
struct LegsIKPose {
    quat leftFootQuatTrack;
    quat rightFootQuatTrack;
    quat leftFootTrack;
    quat rightFootTrack;
    vector3 leftFootPos;
    vector3 rightFootPos;
    float f_LKneeSpin;
    float f_RKneeSpin;
};

struct ArmStdPose {
    quat tracks[2];
    quat hands[2];
    vector3 handpos[2];
    float fElbowSpin[2];
};
struct ArmsPose {
    quat l_clav;
    quat l_upperarm;
    quat l_forearm;
    quat l_hand;

    quat r_clav;
    quat r_upperarm;
    quat r_forearm;
    quat r_hand;

};
struct Fing5ReducedPose {
    quat tracks[2];
    quat fingerBaseKnuckYRot[2];
    quat fingerBaseKnuckZRot[2];
    quat otherKnuckTracks[5];
};
struct Fing5StdPose {
    quat tracks[30];
};
struct Fing5CurlPose {
    quat tracks[2];
    quat fingerBaseKnuckZRot[2];
    float fingerCurl[10];
    uint32_t pad[2];
};
struct Fing5KnuckCurlPose {
    quat quatTracks[2];
    quat fingerBaseKnuckYRot[2];
    quat fingerBaseKnuckZRot[2];
    quat unk[3];
    float otherKnuckTracks[10];
    u32 availableTracks;
    unsigned int iPadding[1];
};

struct FakerootPose {
    quat fakerootOrient;
    vector3 pos;
    float floorOffset;
    u32 signalStart;
    u32 numSignals;
    u32 pad[2];
};


using PoseVariant = std::variant<
    std::monostate,
    TorsoHeadPose,
    LegsPose,
    LegsIKPose,
    ArmsPose,
    ArmStdPose,
    Fing5KnuckCurlPose,
    Fing5ReducedPose,
    Fing5StdPose,
    Fing5CurlPose,
    FakerootPose
>;

// not in runtime
struct ComponentPose {
    int compIndex;
    nalComponentType type;
    PoseVariant pose;
};


// Tracks etc


struct IKSkelData {
    float fUpperIKc;
    float fUpperIKInvc;
    float fLowerIKc;
    float fLowerIKInvc;
    float fUpperArmLength;
    float fLowerArmLength;
};


struct ArmsHandsIKBlock {
    vector3 offsetLocs[8];
    vector3 foreTwistLocs[4];
    IKSkelData theIKData[2];
    uint32_t boneIxs[8];
    uint32_t otherMatrixIxs[6];
    uint32_t iPadding[3];
};

enum TorsoHeadTracks : uint32_t {
    TRACK_SPINE_QUAT = 0,
    TRACK_SPINE1_QUAT = 1,
    TRACK_SPINE2_QUAT = 2,
    TRACK_NECK_QUAT = 3,
    TRACK_HEAD_QUAT = 4,
    TRACK_PELVIS_QUAT = 5,
    NUM_QUAT_TRACKS = 5,
};


enum TorsoHeadBones : uint32_t {
    TORSO_BONE_PELVIS = 0,
    TORSO_BONE_SPINE = 1,
    TORSO_BONE_SPINE1 = 2,
    TORSO_BONE_SPINE2 = 3,
    TORSO_BONE_NECK = 4,
    TORSO_BONE_HEAD = 5,
    TORSO_BONE_NECK_AUX = 6,

    TORSO_NUM_BONE_MATRICES = 6,
    TORSO_NUM_TOTAL_MATRICES = 7,
    TORSO_NUM_EXTRA_MATRICES = 1
};
struct TorsoHeadBlock {
    vector4 emptyNeckOrient;
    vector3 emptyNeckPos;
    vector3 offsetLocs[5];
    uint32_t boneIxs[6];         // TorsoHeadBones
    uint32_t otherMatrixIxs[1];
};




enum LegsTracks : uint32_t {
    TRACK_L_TOE_QUAT = 0,
    TRACK_R_TOE_QUAT = 1,
    TRACK_L_FOOT = 2,
    TRACK_R_FOOT = 3,
    NUM_TOTAL_TRACKS = 4,
    NUM_LEG_TRACKS = 2
};


enum LegsBones : uint32_t {
    LEGS_BONE_L_TOE = 0,
    LEGS_BONE_R_TOE = 1,
    LEGS_BONE_L_FOOT = 2,
    LEGS_BONE_R_FOOT = 3,
    LEGS_BONE_L_THIGH = 4,
    LEGS_BONE_L_CALF = 5,
    LEGS_BONE_R_THIGH = 6,
    LEGS_BONE_R_CALF = 7,
    LEGS_NUM_BONE_MATRICES = 8,
    LEGS_BONE_PELVIS = 8,
    LEGS_NUM_TOTAL_MATRICES = 9,
    LEGS_NUM_EXTRA_MATRICES = 1
};
struct LegsIKBlock {
    vector3 offsetLocs[8];
    IKSkelData theIKData[2];
    uint32_t boneIxs[8];   // LegsBones
    uint32_t otherMatrixIxs[1];
    uint32_t iPadding[3];
};

enum ArmHandsCompressedBones : uint32_t {
    ARMS_BONE_L_CLAVICLE = 0,
    ARMS_BONE_L_UPPERARM = 1,
    ARMS_BONE_L_FOREARM = 2,
    ARMS_BONE_L_HAND = 3,
    ARMS_BONE_R_CLAVICLE = 4,
    ARMS_BONE_R_UPPERARM = 5,
    ARMS_BONE_R_FOREARM = 6,
    ARMS_BONE_R_HAND = 7,
    ARMS_NUM_BONE_MATRICES = 8,
    ARMS_BONE_L_FORE_TWIST_0 = 8,
    ARMS_BONE_L_FORE_TWIST_1 = 9,
    ARMS_BONE_R_FORE_TWIST_0 = 10,
    ARMS_BONE_R_FORE_TWIST_1 = 11,
    ARMS_BONE_NECK_PARENT = 12,
    ARMS_NUM_TOTAL_MATRICES = 13,
    ARMS_NUM_EXTRA_MATRICES = 5,
    ARMS_NUM_FORE_TWIST_MATS = 4
};
enum ArmsQuatTracks : uint32_t {
    TRACK_L_CLAVICLE_QUAT = 0,
    TRACK_L_UPPERARM_QUAT = 1,
    TRACK_L_FOREARM_QUAT = 2,
    TRACK_L_HAND_QUAT = 3,
    TRACK_R_CLAVICLE_QUAT = 4,
    TRACK_R_UPPERARM_QUAT = 5,
    TRACK_R_FOREARM_QUAT = 6,
    TRACK_R_HAND_QUAT = 7,
    NUM_ARM_QUAT_TRACKS = 8
};

struct ArmsHandsCompressedBlock {
    vector3 offsetLocs[8];
    vector3 foreTwistLocs[4];
    uint32_t boneIxs[8]; // ArmBones
    uint32_t otherMatrixIxs[5];
};


enum ArmsHandsIKBones : uint32_t {
    ARMSIK_BONE_L_CLAVICLE = 0,
    ARMSIK_BONE_R_CLAVICLE = 1,
    ARMSIK_BONE_L_HAND = 2,
    ARMSIK_BONE_R_HAND = 3,
    ARMSIK_BONE_L_UPPERARM = 4,
    ARMSIK_BONE_R_UPPERARM = 5,
    ARMSIK_BONE_L_FOREARM = 6,
    ARMSIK_BONE_R_FOREARM = 7,
    ARMSIK_NUM_BONE_MATRICES = 8,
    ARMSIK_BONE_L_FORE_TWIST_0 = 8,
    ARMSIK_BONE_L_FORE_TWIST_1 = 9,
    ARMSIK_BONE_R_FORE_TWIST_0 = 10,
    ARMSIK_BONE_R_FORE_TWIST_1 = 11,
    ARMSIK_BONE_NECK_PARENT = 12,
    ARMSIK_BONE_PELVIS = 13,
    ARMSIK_NUM_TOTAL_MATRICES = 14,
    ARMSIK_NUM_EXTRA_MATRICES = 6,
    ARMSIK_NUM_FORE_TWIST_MATS = 4
};



struct Fing5ReducedPose_PerSkelData {
    vector3 offsetLocs[30];
    int32_t boneIxs[30];
    uint32_t otherMatrixIxs[2];
};

// perSkelData block offsets
enum FingerBones {
    FINGERS_BONE_L_FINGER_0 = 0,
    FINGERS_BONE_R_FINGER_0 = 1,
    FINGERS_BONE_L_FINGER_1 = 2,
    FINGERS_BONE_L_FINGER_2 = 3,
    FINGERS_BONE_L_FINGER_3 = 4,
    FINGERS_BONE_L_FINGER_4 = 5,
    FINGERS_BONE_R_FINGER_1 = 6,
    FINGERS_BONE_R_FINGER_2 = 7,
    FINGERS_BONE_R_FINGER_3 = 8,
    FINGERS_BONE_R_FINGER_4 = 9,
    FINGERS_BONE_L_FINGER_01 = 10,
    FINGERS_BONE_R_FINGER_01 = 11,
    FINGERS_BONE_L_FINGER_11 = 12,
    FINGERS_BONE_L_FINGER_21 = 13,
    FINGERS_BONE_L_FINGER_31 = 14,
    FINGERS_BONE_L_FINGER_41 = 15,
    FINGERS_BONE_R_FINGER_11 = 16,
    FINGERS_BONE_R_FINGER_21 = 17,
    FINGERS_BONE_R_FINGER_31 = 18,
    FINGERS_BONE_R_FINGER_41 = 19,
    FINGERS_BONE_L_FINGER_02 = 20,
    FINGERS_BONE_R_FINGER_02 = 21,
    FINGERS_BONE_L_FINGER_12 = 22,
    FINGERS_BONE_L_FINGER_22 = 23,
    FINGERS_BONE_L_FINGER_32 = 24,
    FINGERS_BONE_L_FINGER_42 = 25,
    FINGERS_BONE_R_FINGER_12 = 26,
    FINGERS_BONE_R_FINGER_22 = 27,
    FINGERS_BONE_R_FINGER_32 = 28,
    FINGERS_BONE_R_FINGER_42 = 29,
    FINGERS_NUM_BONE_MATRICES = 30,
    FINGERS_BONE_L_HAND_PARENT = 30,
    FINGERS_BONE_R_HAND_PARENT = 31,
    FINGERS_NUM_TOTAL_MATRICES = 32,
    FINGERS_NUM_EXTRA_MATRICES = 2
};

struct IKLegsCompressed {
    vector4 v[9];
    uint32_t boneidx[9];
};
struct ArmsHandsCompressed {
    vector4 v[9];
    uint32_t boneidx[16];
};
struct FiveFinger_Top2KnuckleCurl {
    vector4 v[22];
    float aa[2];
    uint32_t boneidx[32];

};


