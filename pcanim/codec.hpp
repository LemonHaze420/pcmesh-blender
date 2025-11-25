#pragma once
#include "../common.h"

float m_total_delta = 0.25;
int g_iInitialValuesBitTable[4] = { 2, 4, 7, 20 };
int g_iSceneAnimInitialValuesBitTable[4] = { 4, 7, 12, 30 };


namespace CharEntropyDecoder {
    struct CharChannelDecoder
    {
        uint8_t* ptr;
        uint8_t bitpos;
        uint8_t decoder;
        uint8_t zeroes[2];
    };
    struct EncTrackData {
        float    fWholeValue;
        float    fDeltaValue;
        float    fSecDeltaValue;
        uint32_t iNumZerosInTrack;
    };

    bool IsZeroEncType(u8 i) {
        return i == 0;
    }


}