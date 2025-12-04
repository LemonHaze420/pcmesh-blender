// uncomment for tool
#ifndef PCANIM_STANDALONE			
#define PCSKEL_STANDALONE			
#endif

#include <vector>
#include <variant>
#include <span>
#include <iostream>
#include <fstream>
#include <ostream>
#include <filesystem>
#include "../common.h"
#include <magic_enum.hpp>


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

class nalSkeletonFile {
public:
	nalSkeletonFileHeader header;
	std::vector<nalComponentInfo> components;

	std::vector<ComponentPose> poses;	// not in runtime

	inline int GetPoseIndexForCompIndex(int compIndex) {
		if (components[compIndex].flags & HAS_TRACK_DATA)
			return -1;

		int poseIx = -1;
		for (int i = 0; i <= compIndex; ++i) {
			if ((components[i].flags & HAS_TRACK_DATA) == 0)
				++poseIx;
		}
		return poseIx;
	}

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
			poses.resize(num);
			if (header.components_offs > 0)
				skel.seekg(header.components_offs, std::ios::beg);
			else
				return;

			for (int i = 0; i < num; ++i) {
				nalComponentInfo comp;
				skel.read(reinterpret_cast<char*>(&comp), sizeof nalComponentInfo);
				components.push_back(comp);

				poses[i].compIndex = i;
				poses[i].type = comp.type;
				poses[i].pose = std::monostate{};
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
					if (components[i].flags & HAS_PER_SKEL_DATA)
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

							for (int i = 0; i < 5; ++i) {
								printf("offsets[%d] %f %f %f\n", i, torso.offsetLocs[i].v[0], torso.offsetLocs[i].v[1], torso.offsetLocs[i].v[2] );
							}
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

				if (header.defaultPoseOffsets_offs > 0) {
					skel.seekg(header.defaultPoseOffsets_offs, std::ios::beg);

					int32_t numPoseBlocks = 0;
					skel.read(reinterpret_cast<char*>(&numPoseBlocks), sizeof numPoseBlocks);

					std::vector<uint32_t> poseOffsets(numPoseBlocks);
					skel.read(reinterpret_cast<char*>(poseOffsets.data()), numPoseBlocks * sizeof(uint32_t));
					
					uint32_t totalPoseBytes = poseOffsets.back();
					std::vector<uint8_t> poseBlob(totalPoseBytes);

					skel.seekg(header.defaultPoseOffsets_offs, std::ios::beg);
					skel.read(reinterpret_cast<char*>(poseBlob.data()), totalPoseBytes);

					auto getPoseFloats = [&](int poseIx) -> std::span<const float> {
						uint32_t start = poseOffsets[poseIx];
						uint32_t end = (poseIx + 1 < numPoseBlocks) ? poseOffsets[poseIx + 1] : totalPoseBytes;
						auto* base = reinterpret_cast<const float*>(poseBlob.data() + start);
						size_t count = (end - start) / 4;
						return { base, count };
					};

					for (int i = 0; i < header.numComponents; ++i) {
						auto& comp = components[i];
						int pIx = GetPoseIndexForCompIndex(i);
						if (pIx < 0) continue;

						auto floats = getPoseFloats(pIx);

						auto& cp = poses[i];
						cp.compIndex = i;
						cp.type      = comp.type;
						switch (comp.type) {
							case nalComponentType::TorsoHead_OneNeck_Compressed:
							case nalComponentType::TorsoHead_TwoNeck_Compressed:
							{
								TorsoHeadPose pose{};
								std::memcpy(&pose, floats.data(), sizeof(TorsoHeadPose));
								cp.pose = pose;
								break;
							}

							case nalComponentType::LegsFeet_Compressed:
							{
								LegsPose p{};
								std::memcpy(&p, floats.data(), sizeof(LegsPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::LegsFeet_IK_Compressed:
							{
								LegsIKPose p{};
								std::memcpy(&p, floats.data(), sizeof(LegsIKPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::ArmsHands_Compressed:
							{
								ArmsPose p{};
								std::memcpy(&p, floats.data(), sizeof(ArmsPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::ArmsHands_IK_Compressed:
							{
								ArmStdPose p{};
								std::memcpy(&p, floats.data(), sizeof(ArmStdPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::FiveFinger_Top2KnuckleCurl:
							{
								Fing5KnuckCurlPose p{};
								std::memcpy(&p, floats.data(), sizeof(Fing5KnuckCurlPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::FiveFinger_ReducedAngular:
							{
								Fing5ReducedPose p{};
								std::memcpy(&p, floats.data(), sizeof(Fing5ReducedPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::FiveFinger_FullRotational:
							{
								Fing5StdPose p{};
								std::memcpy(&p, floats.data(), sizeof(Fing5StdPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::FiveFinger_IndividualCurl:
							{
								Fing5CurlPose p{};
								std::memcpy(&p, floats.data(), sizeof(Fing5CurlPose));
								cp.pose = p;
								break;
							}

							case nalComponentType::FakerootEntropyCompressed:
							{
								FakerootPose p{};
								std::memcpy(&p, floats.data(), sizeof(FakerootPose));
								cp.pose = p;
								break;
							}

							default:
							{
								if (floats.size_bytes() > 0)
									printf("len (unhandled) = %zu\n", floats.size_bytes());
								break;
							}
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