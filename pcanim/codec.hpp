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

    int ReadSignedBits(CharChannelDecoder* dec, unsigned int n31)
    {
        uint64_t buffer = 0;
        std::memcpy(&buffer, dec->ptr, sizeof(uint64_t));
        buffer >>= dec->bitpos;
        bool neg = (buffer & 1) != 0;
        unsigned int value = (unsigned int)((buffer >> 1) & ((1ULL << n31) - 1));
        int bits_consumed = 1 + n31;

        dec->bitpos += bits_consumed;
        dec->ptr += (dec->bitpos / 8);      // advance
        dec->bitpos %= 8;                   // keep the remainder
        return neg ? -(int)value : (int)value;
    }

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