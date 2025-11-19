#pragma author LemonHaze
#pragma description 

#define uint32_t u32
#define int32_t s32

import std.io;
import type.base;

enum entropy : u32
{
    ENTROPY_ArbitraryPO                          = 0xC5E45DCF,
    ENTROPY_Generic                              = 0xEC4755BD,
    ENTROPY_FakerootEntropyCompressed            = 0xB916E121,
    ENTROPY_TorsoHead_TwoNeck_Compressed         = 0x7E916D6A,  // done
    ENTROPY_TorsoHead_OneNeck_Compressed         = 0x70EA5DF2,  // done
    ENTROPY_LegsFeet_Compressed                  = 0x47CBEBDB,
    ENTROPY_LegsFeet_IK_Compressed               = 0xA556994F,  // done
    ENTROPY_ArmsHands_Compressed                 = 0xE01F4F4D,  // done
    ENTROPY_ArmsHands_IK_Compressed              = 0xF0AD5C8E,  // untested
    ENTROPY_Tentacles_Compressed                 = 0x464A04D8,  
    ENTROPY_FiveFinger_Top2KnuckleCurl           = 0xE7D9A8D3,
    ENTROPY_FiveFinger_IndividualCurl            = 0xE7A8F925,
    ENTROPY_FiveFinger_ReducedAngular            = 0xE78254B9,
    ENTROPY_FiveFinger_FullRotational            = 0xAFEB6A28
};

struct tlFixedString {
   u32 hash;
   char name[28];
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

struct Fing5ReducedPose_PerSkelData {
    vector3 offsetLocs[30];
    s32 boneIxs[30];
    u32 otherMatrixIxs[2];
};

// perSkelData block offsets


struct IKLegsCompressed {
    vector4 v[9];
    u32 boneidx[9];
};
struct ArmsHandsCompressed {
    vector4 v[9];
    u32 boneidx[16];
};
struct FiveFinger_Top2KnuckleCurl {
    vector4 v[22];
    float aa[2];
    u32 boneidx[38-4];
};

struct GenericNode {
    tlFixedString name;
    u16 iQuatIx, iPosIx;
    
    s16 iMyMatrixIx,iParentMatrixIx;
    u16 bIsQuatAnim,bIsPosAnim;
    s32 unk2;
};
struct ArbitraryPO {
    u32 boneCount;
    u32 unkCount2,unkCount3,c,d,e,f,poseOffset;
    if (boneCount > 12) {
        vector4 extras[boneCount-12+1];
    }
    GenericNode nodes[boneCount];
};

struct IKSkelData {
	float fUpperIKc;
	float fUpperIKInvc;
	float fLowerIKc;
	float fLowerIKInvc;
	float fUpperArmLength;
	float fLowerArmLength;  
};


enum TorsoHeadBones : u32 {
	BONE_PELVIS = 0,
	BONE_SPINE = 1,
	BONE_SPINE1 = 2,
	BONE_SPINE2 = 3,
	BONE_NECK = 4,
	BONE_HEAD = 5,  
	BONE_NECK_AUX = 6,  
	
	NUM_BONE_MATRICES = 6,
	NUM_TOTAL_MATRICES = 7,
	NUM_EXTRA_MATRICES = 1
};
struct TorsoHeadBlock {
    vector4 emptyNeckOrient;
    vector3 emptyNeckPos;
    vector3 offsetLocs[5];
    u32 boneIxs[6];         // TorsoHeadBones
    u32 otherMatrixIxs[1];
};

enum LegsBones : u32 {
	BONE_L_TOE = 0,
	BONE_R_TOE = 1,
	BONE_L_FOOT = 2,
	BONE_R_FOOT = 3,
	BONE_L_THIGH = 4,
	BONE_L_CALF = 5,
	BONE_R_THIGH = 6,
	BONE_R_CALF = 7,
	NUM_BONE_MATRICES = 8,
	BONE_PELVIS = 8,
	NUM_TOTAL_MATRICES = 9,
	NUM_EXTRA_MATRICES = 1  
};
struct LegsIKBlock {
    vector3 offsetLocs[8];
	IKSkelData theIKData[2];
    u32 boneIxs[8];   // LegsBones
    u32 otherMatrixIxs[1];
    u32 iPadding[3];
};

enum ArmHandsCompressedBones : u32 {
	BONE_L_CLAVICLE = 0,
	BONE_L_UPPERARM = 1,
	BONE_L_FOREARM = 2,
	BONE_L_HAND = 3,
	BONE_R_CLAVICLE = 4,
	BONE_R_UPPERARM = 5,
	BONE_R_FOREARM = 6,
	BONE_R_HAND = 7,
	NUM_BONE_MATRICES = 8,
	BONE_L_FORE_TWIST_0 = 8,
	BONE_L_FORE_TWIST_1 = 9,
	BONE_R_FORE_TWIST_0 = 10,
	BONE_R_FORE_TWIST_1 = 11,
	BONE_NECK_PARENT = 12,
	NUM_TOTAL_MATRICES = 13,
	NUM_EXTRA_MATRICES = 5,
	NUM_FORE_TWIST_MATS = 4
};
struct ArmsHandsCompressedBlock {
    vector3 offsetLocs[8];
	vector3 foreTwistLocs[4];
    u32 boneIxs[8]; // ArmBones
    u32 otherMatrixIxs[5];    
};


enum ArmsHandsIKBones : u32 {
	BONE_L_CLAVICLE = 0,
	BONE_R_CLAVICLE = 1,
	BONE_L_HAND = 2,
	BONE_R_HAND = 3,
	BONE_L_UPPERARM = 4,
	BONE_R_UPPERARM = 5,
	BONE_L_FOREARM = 6,
	BONE_R_FOREARM = 7,
	NUM_BONE_MATRICES = 8,
	BONE_L_FORE_TWIST_0 = 8,
	BONE_L_FORE_TWIST_1 = 9,
	BONE_R_FORE_TWIST_0 = 10,
	BONE_R_FORE_TWIST_1 = 11,
	BONE_NECK_PARENT = 12,
	BONE_PELVIS = 13,
	NUM_TOTAL_MATRICES = 14,
	NUM_EXTRA_MATRICES = 6,
	NUM_FORE_TWIST_MATS = 4
};
struct ArmsHandsIKBlock {
	vector3 offsetLocs[8];
	vector3 foreTwistLocs[4];
	IKSkelData theIKData[2];
	u32 boneIxs[8];
	u32 otherMatrixIxs[6];
    u32 iPadding[3];
};


struct block_header {
    s32 number_blocks;
    s32 blockOffsets[number_blocks];
};

struct component_meta {
   s32 index;
   entropy type;
   s32 flags;
   if (flags & 4) {
//      std::print(std::format("Has Skeleton Data!"));

        match (type) {
            (entropy::ENTROPY_TorsoHead_TwoNeck_Compressed): {
//                TorsoHeadBlock torso @ (file.perSkelDataInt_offs + file.hdr.blockOffsets[i]);
            }        
        }
   }
};


struct skeleton_file {
   u32 Class;
   u32 Version;

   if (Version == 65539) {
       tlFixedString Name, Category;
       s32 numSkelData;
       u8  gap[28-4];

       u32 numComponents;
       s32 poseDataAlign, poseDataSize;
       s32 components_offs;
       s32 perSkelDataInt_offs;
       s32 defaultPoseOffsets_offs;

       if (components_offs > 0) {
           component_meta components[numComponents] @ components_offs;
       }

       if (perSkelDataInt_offs > 0) {
           block_header hdr @ perSkelDataInt_offs;

           /*TorsoHeadBlock torsoHead @ (perSkelDataInt_offs + hdr.blockOffsets[0]);
           LegsIKBlock legsIK    @ (perSkelDataInt_offs + hdr.blockOffsets[1]);
           ArmsHandsCompressedBlock arms      @ (perSkelDataInt_offs + hdr.blockOffsets[2]);
           FiveFinger_Top2KnuckleCurl fingers   @ (perSkelDataInt_offs + hdr.blockOffsets[3]);
           ArbitraryPO arbitrary @ (perSkelDataInt_offs + hdr.blockOffsets[4]);
           GenericNode nodes[arbitrary.boneCount] @ perSkelDataInt_offs + hdr.blockOffsets[4] + sizeof(ArbitraryPO);*/
       }
   }
};


skeleton_file file @ 0x0;
ArbitraryPO arbitrary @ file.perSkelDataInt_offs + 1120;

for(auto i = 0, i < file.numComponents, i = i + 1) {
    if(file.components[i].flags & 4 != 0) {
        std::print(std::format("{:s}",file.components[i].type));
    }
}