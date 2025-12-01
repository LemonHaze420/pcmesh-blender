// LemonHaze - 2025
// uncomment for tool
#define PCANIM_STANDALONE
#include <filesystem>
#include <iostream>
#include <fstream>
#include <istream>
#include <vector>
#include "../common.h"
#include "../pcskel/pcskel.cpp"
#include "codec.hpp"

#define ANIM_CONTAINER  65793
#define CHAR_ANIM       65539
#define GEN_ANIM        66048

struct nalSkeletonEntry {
    s32 p[2];
    s32 hash;
    char name[20];
};

struct nalAnimationFileHeader {
    u32 Version;                    // 
    u32 Flags;                      // 
    s32 SizeStringTable;            // 
    s32 num_skeletons;              // 
    tlFixedString Name;             // 
    s32 NumAnims;                   //
    u32 FirstAnim;                  // rel. offs into first anim
    s32 FileBuf;                    // runtime
    s32 RefCount;                   // runtime - current refs
};

struct nalAnimHeader {
    s32 vtbl;                       // runtime resolved
    s32 NextAnim;                   // rel. ptr into anim (can be used as size)
    tlFixedString name;             // anim name
    s32 skelIx;                     // runtime
    s32 version;                    // anim format version
    float animDuration;             // full anim len
    nalAnimFlags   flags;           // &1 == loop, &0x20000 == scene anim
    float T_scale;                  // quant scale time
};

struct nalCharAnimData {
    nalAnimHeader header;

    s32 instanceCount;      // runtime - current instance count
    s32 compList_offs;      //         
    s32 animUserData_offs;  // 44
    s32 trackData_offs;     // 48
    s32 internaloffs;       // 
    s32 frameCount;         // total frm count
    float currentTime;      // time2dequant
    s32 m_pCompList[10];    // 
    s32 animTrackCount;     // 
    s32 m_pAnimUserData[8]; // 
};

class nalCharAnim {
public:
    nalCharAnimData data;

    bool scene_anim() {
        return data.header.flags & IS_SCENE_ANIM;
    }

    bool looping() {
        return data.header.flags & LOOPING;
    }

    bool validate_version()
    {
        return data.header.version == CHAR_ANIM;
    }

    nalCharAnim(std::ifstream& ifs, nalSkeletonFile* skel = nullptr) {
        auto base = (int)ifs.tellg();
        ifs.read(reinterpret_cast<char*>(&data), sizeof nalCharAnimData);
        auto b = (int)ifs.tellg();

        int compListAbs = base + data.compList_offs;
        int animListAbs = base + data.animUserData_offs;
        int trackListAbs = base + data.trackData_offs;

        constexpr const int testSkelComponents = 7;
        const int numComponents = skel ? skel->components.size() : testSkelComponents;

        int animUserDataIx = 0;
        int trackIx = 0;

        std::vector<int> compTracks;

        for (int compIx = 0; compIx < numComponents; ++compIx) {
            int perAnimDataOffs = animListAbs;
            int flags = 0;
            ifs.seekg(compListAbs + compIx * 4, std::ios::beg);
            ifs.read(reinterpret_cast<char*>(&flags), 4);
            if ((flags & HAS_TRACK_DATA) == 0)
                continue;

            int poseIx = compIx;
            if (flags & HAS_PER_ANIM_DATA) {
                int tableEntryOffset = animListAbs + (animUserDataIx + 1) * 4;
                int elemOffset = 0;
                ifs.seekg(tableEntryOffset, std::ios::beg);
                ifs.read(reinterpret_cast<char*>(&elemOffset), 4);

                perAnimDataOffs += elemOffset;
                printf("[A][C%02d][0x%X] 0x%X\n", compIx, elemOffset, perAnimDataOffs);
                ++animUserDataIx;
            }

            if (has_track(flags)) {
                ifs.seekg(perAnimDataOffs, std::ios::beg);              

                int mask = -1;
                ifs.read(reinterpret_cast<char*>(&mask), 4);

                const int codecIxsAbs = static_cast<int>(ifs.tellg());
                
                int trackEntryOffset = trackListAbs + (trackIx + 1) * 4;
                ifs.seekg(trackEntryOffset, std::ios::beg);

                int trackOffset = 0;
                ifs.read(reinterpret_cast<char*>(&trackOffset), 4);
                int trackDataAbs = trackListAbs + trackOffset;

                auto ntracks = get_num_tracks(mask), len = -1;
                auto nquats = get_num_quats(mask);
                switch ((iComponentID)compIx) {
                    case iComponentID::iTorsoHeadStdPose:
                    case iComponentID::iTorsoHeadEnt:
                    {
                        len = getNumBytes_TorsoHeadEnt(mask);
                        printf("[T][C%02d] q=%d t=%d [extras=%s] @ 0x%X\n", compIx, nquats, ntracks, get_has_extras(mask) ? "true" : "false", trackDataAbs);
                        printf("ntracks=%d\n", ntracks);
                        printf("len=%d\n", len);
                        if (len)
                            printf("decoded len=%d\n", 16 * (ntracks + 15));
                        break;
                    }
                    case iComponentID::iLegsEnt:
                    {
                        len = getNumBytes_StandardLegsFeet(mask);
                        printf("[T][C%02d] q=%d t=%d [extras=%s] @ 0x%X\n", compIx, get_num_quats(mask), ntracks, get_has_extras(mask) ? "true" : "false", trackDataAbs);
                        break;
                    }
                    default:
                    {
                        printf("[T][C%02d] q=%d t=%d [extras=%s] @ 0x%X\n", compIx, get_num_quats(mask), ntracks, get_has_extras(mask) ? "true" : "false", trackDataAbs);
                        continue;
                    }
                }

                if (len != -1 && nquats > 0)
                {
                    std::vector<uint8_t> codecBytes(ntracks);
                    {
                        auto savedPos = ifs.tellg();
                        ifs.seekg(codecIxsAbs, std::ios::beg);
                        ifs.read(reinterpret_cast<char*>(codecBytes.data()), ntracks);
                        ifs.seekg(savedPos, std::ios::beg);
                    }
                    std::vector<uint8_t> encoded_data(len);
                    {
                        auto savedPos = ifs.tellg();
                        ifs.seekg(trackDataAbs, std::ios::beg);
                        ifs.read(reinterpret_cast<char*>(encoded_data.data()), len);
                        ifs.seekg(savedPos, std::ios::beg);
                    }

                    std::vector<CharEntropyDecoder::EncTrackData> tracks(ntracks);
                    CharEntropyDecoder::CharChannelDecoder decoder(encoded_data.data(), tracks);

                    for (uint32_t frame = 0; frame < data.frameCount; ++frame) {
                        debug_evaluate(frame);

                        IntegrateForFrame(tracks, codecBytes.data(), mask, frame, decoder, ntracks, data.currentTime, scene_anim());
                        
                        CharEntropyDecoder::TrackData track;
                        DecomposeTrack(track, tracks, compIx, frame, ntracks);
                        decoded_tracks.push_back(track);

                        #if _DEBUG
                        for (int q = 0; q < nquats; ++q) {
                            int base = 3 * q;
                            printf("[%s] x=%f y=%f z=%f\n", compIx != iLegsEnt ? magic_enum::enum_name(magic_enum::enum_cast<TorsoHeadTracks>(q).value()).data() : magic_enum::enum_name(magic_enum::enum_cast<LegsTracks>(q).value()).data(),
                                                            tracks[base].fWholeValue,
                                                            tracks[base + 1].fWholeValue,
                                                            tracks[base + 2].fWholeValue);
                        }
                        if (get_has_extras(mask)) {
                            int base = 3 * nquats;
                            for (int e = 0; e < 6; ++e) {
                                printf("[C%02d][E%d] v=%f\n", compIx, e, tracks[base + e].fWholeValue);
                            }
                        }
                        #endif
                    }
                }
                trackIx++;          // @todo: just for now same as below, only increment if we match this component & apply
            }
        }
        ifs.seekg(b);               // doing this to cleanly read all for now
    }

private:
    std::vector<CharEntropyDecoder::TrackData> decoded_tracks;

    char debug_evaluate(uint32_t frame)
    {
        // probably not gonna need this
#if _DEBUG
        float currFrameIndex;
        if (data.frameCount <= 1) {
            currFrameIndex = 0.0f;
        }
        else if (looping()) {
            currFrameIndex = static_cast<float>(frame) / static_cast<float>(data.frameCount);
        }
        else {
            currFrameIndex = static_cast<float>(frame) / static_cast<float>(data.frameCount - 1);
        }

        float outT, outBlendT;
        unsigned int next, curr;
        char loop_count = evaluate_lerp_params(data.header.flags, data.header.T_scale, data.frameCount, &outT,
            &next,
            &curr,
            &outBlendT,
            currFrameIndex);
        return loop_count;
#else
        return 0;
#endif
    }
};

class nalAnimFile {
public:
    nalAnimationFileHeader header{};
    std::vector<nalSkeletonEntry> skeletons;
    std::vector<nalCharAnim> animations;

    nalAnimFile(std::ifstream& ifs, nalSkeletonFile* skel = nullptr) {
        u32 version_test = -1;
        ifs.seekg(0, std::ios::beg);
        ifs.read(reinterpret_cast<char*>(&version_test), 4);
        ifs.seekg(0, std::ios::beg);
        
        if (version_test == ANIM_CONTAINER) {
            ifs.read(reinterpret_cast<char*>(&header), sizeof nalAnimationFileHeader);
            header.Flags &= ~4u;   // mark opened

            auto p = ifs.tellg();
            ifs.seekg(0, std::ios::end);
            auto end = ifs.tellg();
            ifs.seekg(p, std::ios::beg);

            int skelIx = -1;
            for (int i = 0; i < header.num_skeletons; ++i) {
                nalSkeletonEntry skel_entry;
                ifs.read(reinterpret_cast<char*>(&skel_entry), sizeof nalSkeletonEntry);
                if (skel) {
                    if (strstr(skel_entry.name, skel->header.Name.string))
                        skelIx = i;
                }
                skeletons.push_back(skel_entry);
            }

            if (header.FirstAnim > 0) {
                ifs.seekg(header.FirstAnim, std::ios::beg);

                nalCharAnim anim(ifs, skel);
                if (anim.validate_version())
                {
                    animations.push_back(anim);

                    while (anim.data.header.NextAnim != 0) {
                        ifs.seekg(((int)ifs.tellg()) + anim.data.header.NextAnim - sizeof nalCharAnimData, std::ios::beg);
                        
                        anim = nalCharAnim(ifs, skel);
                        if (anim.validate_version())
                            animations.push_back(anim);
                    }
                }
            }
            
            header.Flags |= 8u;
        }
    }
};

#if defined(PCANIM_STANDALONE)
    int main(int argc, char ** argp)
    {
        std::filesystem::path path = argp[1];
        auto read = [](auto path) {
            std::ifstream ifs(path, std::ios::binary);
            if (ifs.good()) {
                nalAnimFile anim(ifs);
                if (anim.animations.size()) {
                    std::cout << "name=" << anim.header.Name.string << "\n";
                    for (const auto& skel : anim.skeletons)
                        std::cout << "skel=" << skel.name << "\n";

                    for (size_t i = 0; i < anim.animations.size(); ++i) {
                        auto& a = anim.animations[i].data;

                        std::cout
                            << " [" << std::setw(3) << i << "] "
                            << std::left << std::setw(36) << a.header.name.string
                            << std::right
                                    << " T_scale="      << std::setw(7) << std::fixed << a.header.T_scale
                                    << " T="            << std::setw(7) << std::fixed << a.currentTime
                                    << " loop="         << std::setw(5) << std::boolalpha << anim.animations[i].looping()
                                    << " scene_anim="   << std::setw(5) << std::boolalpha << anim.animations[i].scene_anim()
                                    << " frames="       << std::setw(4) << a.frameCount
                                    << " skel="         << std::setw(5) << anim.skeletons[a.header.skelIx].name
                            << '\n';
                    }
                }
                ifs.close();

            }
        };
        if (!std::filesystem::is_directory(path))
            read(path);
        else
        {
            for (auto& p : std::filesystem::recursive_directory_iterator(path))
                if (p.is_regular_file())
                    read(p.path());
        }
        return 0;
    }
#endif