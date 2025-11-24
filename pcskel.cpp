// uncomment for tool
//#define PCSKEL_STANDALONE			

#include <vector>
#include <iostream>
#include <fstream>
#include <ostream>
#include <filesystem>

#include <magic_enum.hpp>

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
struct ArbitraryPO {
	uint32_t boneCount;
	uint32_t unkCount;
	uint32_t unkCount2;
	uint32_t unkOffset;

	uint32_t startOffset;
	uint32_t startOffset2;
	uint32_t blockStart;
	uint32_t startOffset4;	
};
struct GenericNode {
	tlFixedString name;
	uint16_t iQuatIx, iPosIx;

	int16_t iMyMatrixIx, iParentMatrixIx;
	uint16_t bIsQuatAnim, bIsPosAnim;
	int32_t unk2;
};

struct IKSkelData {
	float fUpperIKc;
	float fUpperIKInvc;
	float fLowerIKc;
	float fLowerIKInvc;
	float fUpperArmLength;
	float fLowerArmLength;
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
struct ArmsHandsIKBlock {
	vector3 offsetLocs[8];
	vector3 foreTwistLocs[4];
	IKSkelData theIKData[2];
	uint32_t boneIxs[8];
	uint32_t otherMatrixIxs[6];
	uint32_t iPadding[3];
};

struct nalComponentInfo {
	int32_t index;
	nalComponentType type;
	int32_t flags;
};

struct nalSkeletonFileHeader {
	uint32_t Class;
	uint32_t Version;
	tlFixedString Name, Category;
	int32_t numSkelData;
	uint8_t  gap[28 - 4];
	uint32_t numComponents;
	int32_t poseDataAlign, poseDataSize;
	int32_t components_offs;
	int32_t perSkelDataInt_offs;
	int32_t defaultPoseOffsets_offs;

};

enum ComponentFlags : int32_t {
	COMP_ENABLED = 1,
	COMP_HAS_SKEL_DATA = 4,
};

class nalSkeletonFile {
public:
	nalSkeletonFileHeader header;
	std::vector<nalComponentInfo> components;


	nalSkeletonFile(std::ifstream& skel) {
		skel.read(reinterpret_cast<char*>(&header), sizeof nalSkeletonFileHeader);
		printf("Name: %s\nType: %s\n", header.Name.string, header.Category.string);
		printf("Version: %d\n", header.Version);

		if (strstr(header.Category.string, "generic")	||
			strstr(header.Category.string, "panel")) {
			return;
		}

		if (header.numComponents) {
			auto num = header.numComponents;
			if (header.components_offs > 0)
				skel.seekg(header.components_offs, std::ios::beg);
			else
				return;
			for (int i = 0; i < num; ++i) {
				nalComponentInfo comp;
				skel.read(reinterpret_cast<char*>(&comp), sizeof nalComponentInfo);
				components.push_back(comp);
			}
		}

		if (header.perSkelDataInt_offs > 0) {
			int32_t num_blocks;
			std::vector<int32_t> block_offsets;

			skel.seekg(header.perSkelDataInt_offs, std::ios::beg);
			skel.read(reinterpret_cast<char*>(&num_blocks), sizeof int32_t);
			for (int i = 0; i < num_blocks; ++i) {
				int32_t offset;
				skel.read(reinterpret_cast<char*>(&offset), sizeof int32_t);
				block_offsets.push_back(offset);
			}

			if (header.numComponents) {
				std::vector<int32_t> indices;
				for (int i = 0; i < header.numComponents; ++i) {
					if (components[i].flags & COMP_HAS_SKEL_DATA)
						indices.push_back(i);
				}

				if (!indices.size())
					return;

				auto blockBase = header.perSkelDataInt_offs;
				for (int blockIndex = 0; blockIndex < block_offsets.size(); ++blockIndex) {
					auto component = components[indices[blockIndex]];
					printf("\nType: %s\n", component_to_string(component.type).data());
					auto compBlockStart = blockBase + block_offsets[blockIndex];
					skel.seekg(compBlockStart, std::ios::beg);

					switch (component.type) {
						case nalComponentType::TorsoHead_TwoNeck_Compressed:
						case nalComponentType::TorsoHead_OneNeck_Compressed:
						{
							TorsoHeadBlock torso;
							skel.read(reinterpret_cast<char*>(&torso), sizeof TorsoHeadBlock);
							for (int i = 0; i < TORSO_NUM_BONE_MATRICES; ++i)
								printf("%s: %d \t%s", magic_enum::enum_name(magic_enum::enum_cast<TorsoHeadBones>(i).value()).data(), torso.boneIxs[i], i % 2 ? "\n" : "");
							printf("\n");
							break;
						}
						case nalComponentType::LegsFeet_IK_Compressed:
						{
							LegsIKBlock legsIK;
							skel.read(reinterpret_cast<char*>(&legsIK), sizeof LegsIKBlock);
							for (int i = 0; i < LEGS_NUM_BONE_MATRICES; ++i)
								printf("%s: %d \t%s", magic_enum::enum_name(magic_enum::enum_cast<LegsBones>(i).value()).data(), legsIK.boneIxs[i], i % 2 ? "\n" : "");
							printf("\n");
							break;
						}
						case nalComponentType::ArmsHands_Compressed: {
							ArmsHandsCompressed arms;
							skel.read(reinterpret_cast<char*>(&arms), sizeof ArmsHandsCompressed);
							for (int i = 0; i < 15; ++i)
								printf("%s: %d  \t%s", magic_enum::enum_name(magic_enum::enum_cast<FingerBones>(i).value()).data(), arms.boneidx[i], i % 2 ? "\n" : "");
							break;
						}
						case nalComponentType::ArmsHands_IK_Compressed: {
							ArmsHandsIKBlock armsIK;
							skel.read(reinterpret_cast<char*>(&armsIK), sizeof ArmsHandsIKBlock);
							for (int i = 0; i < ARMSIK_NUM_BONE_MATRICES; ++i)
								printf("%s: %d  \t%s", magic_enum::enum_name(magic_enum::enum_cast<ArmsHandsIKBones>(i).value()).data(), armsIK.boneIxs[i], i % 2 ? "\n" : "");
							break;
						}
						case nalComponentType::FiveFinger_Top2KnuckleCurl: {
							FiveFinger_Top2KnuckleCurl fingers;
							skel.read(reinterpret_cast<char*>(&fingers), sizeof FiveFinger_Top2KnuckleCurl);
							for (int i = 0; i < FINGERS_NUM_BONE_MATRICES; ++i)
								printf("%s: %d  \t%s", magic_enum::enum_name(magic_enum::enum_cast<FingerBones>(i).value()).data(), fingers.boneidx[i], i % 2 ? "\n" : "");
							break;
						}
						case nalComponentType::ArbitraryPO: {
							ArbitraryPO po;
							skel.read(reinterpret_cast<char*>(&po), sizeof ArbitraryPO);
						
							auto boneCount = po.boneCount;
							std::vector<GenericNode> nodes(boneCount);
							skel.seekg(compBlockStart + po.blockStart, std::ios::beg);
							skel.read(reinterpret_cast<char*>(nodes.data()), sizeof GenericNode * boneCount);

							for (const auto& node : nodes)
								printf("%s \t\t[ID: %d][Parent: %d]\n", node.name.string, node.iMyMatrixIx, node.iParentMatrixIx);
							break;
						}
						default: {
							printf("Unimplemented type (%s)\n", component_to_string(component.type).data());
							break;
						}
					}
				}
			}
		}
		skel.close();
	}
};


#if defined(PCSKEL_STANDALONE)
	int main(int argc, char ** argp)
	{
		auto ifs = std::ifstream(argp[1], std::ios::binary);
		if (ifs.good()) {
			nalSkeletonFile skel (ifs);
		}
		return 0;
	}
#endif