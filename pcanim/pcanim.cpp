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

#define u32 uint32_t
#define s32 int32_t

#define u16 uint16_t
#define s16 int16_t

#define u8 uint8_t
#define s8 int8_t


enum CompDataFlags
{
    HAS_TRACK_DATA = 0x1,
    HAS_PER_ANIM_DATA = 0x2,
    HAS_PER_SKEL_DATA = 0x4,
};



struct nalSkeletonEntry {
    s32 p[2];
    s32 hash;
    char name[20];
};

struct nalAnimationFileHeader {
    u32 Version;
    u32 Flags;
    s32 SizeStringTable;
    s32 num_skeletons;
    tlFixedString Name;
    s32 NumAnims;
    u32 FirstAnim;
    s32 FileBuf;
    s32 RefCount;
};


struct nalAnimHeader {
    s32 vtbl;                       // runtime resolved
    s32 NextAnim;                   // rel. ptr into anim (can be used as size)
    tlFixedString name;             // anim name
    s32 unk_field;                  // runtime
    s32 version;                    // anim format version
    float animDuration;             // full anim len
    s32   flags;                    // &1 == loop
    float T_scale;                  // quant scale time
};

struct nalCharAnimData {
    nalAnimHeader header;

    s32 instanceCount;      // runtime
    s32 compList_offs;      // 40        
    s32 animUserData_offs;  // 44
    s32 trackData_offs;     // 48
    s32 internaloffs;       // 
    s32 frameCount;
    float currentTime;
    s32 m_pCompList[10];
    s32 animTrackCount;
    s32 m_pAnimUserData[8];
};

class nalCharAnim {
public:
    nalCharAnimData data;

    bool looping() {
        return data.header.flags & 1;
    }

    nalCharAnim(std::ifstream& ifs, nalSkeletonFile* skel = nullptr) {
        auto base = (int)ifs.tellg();
        ifs.read(reinterpret_cast<char*>(&data), sizeof nalCharAnimData);
        auto b = (int)ifs.tellg();

        int compListAbs = base + data.compList_offs;
        int animListAbs = base + data.animUserData_offs;
        int trackListAbs = base + data.trackData_offs;

        constexpr const int testSkelComponents = 6;
        const int numComponents = skel ? skel->components.size() : testSkelComponents;

        int animUserDataIx = 0;
        int trackIx = 0;

        for (int compIx = 0; compIx < numComponents; ++compIx) {
            int flags = 0;
            ifs.seekg(compListAbs + compIx * 4, std::ios::beg);
            ifs.read(reinterpret_cast<char*>(&flags), 4);
            if ((flags & 1) == 0)
                continue;

            if (flags & HAS_PER_ANIM_DATA) {
                int tableEntryOffset = animListAbs + (animUserDataIx + 1) * 4;
                int elemOffset = 0;
                ifs.seekg(tableEntryOffset, std::ios::beg);
                ifs.read(reinterpret_cast<char*>(&elemOffset), 4);

                int absPtr = animListAbs + elemOffset;
                printf("[%d] [0x%X] @ 0x%X\n", compIx, elemOffset, absPtr);
                ++animUserDataIx;
            }

            if (flags & HAS_TRACK_DATA) {
                ifs.seekg(trackListAbs, std::ios::beg);
                int mask = -1;
                ifs.read(reinterpret_cast<char*>(&mask), 4);


                int num_quats = __popcnt(mask & 0x1F);
                bool hasExtra = (mask & 0x20) != 0;
                int num_tracks = 3 * num_quats + (hasExtra ? 6 : 0);
                printf("[%d] q=%d t=%d [extras=%s]\n", compIx, num_quats, num_tracks, hasExtra ? "true" : "false");
            }
        }


        
        ifs.seekg(b);   // @todo: remove when parser done, doing this to cleanly read all for now
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

                nalCharAnim anim(ifs);
                if (anim.data.header.version == CHAR_ANIM)
                {
                    animations.push_back(anim);

                    while (anim.data.header.NextAnim != 0) {
                        ifs.seekg(((int)ifs.tellg()) + anim.data.header.NextAnim - sizeof nalCharAnimData, std::ios::beg);
                        
                        anim = nalCharAnim(ifs, skelIx != -1 ? skel : nullptr);
                        if (anim.data.header.version == CHAR_ANIM)
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
                                    << " T_scale=" << std::setw(7) << std::fixed << a.header.T_scale
                                    << " T=" << std::setw(7) << std::fixed << a.currentTime
                                    << " loop=" << std::setw(5) << std::boolalpha << anim.animations[i].looping()
                                    << " frames=" << std::setw(5) << a.frameCount
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