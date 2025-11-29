#pragma once
#include "../common.h"


namespace CharEntropyDecoder {
    float g_fEntropyBaseQuantStep = 0.25;
    float g_fDequantScale = 0.0009765625;
    int g_iInitialValuesBitTable[4] = { 2, 4, 7, 20 };
    int g_iSceneAnimInitialValuesBitTable[4] = { 4, 7, 12, 30 };

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

    static inline std::uint32_t* GetWord(CharChannelDecoder* decoder)
    {
        std::uintptr_t raw = reinterpret_cast<std::uintptr_t>(decoder->ptr);
        raw &= ~static_cast<std::uintptr_t>(3);
        return reinterpret_cast<std::uint32_t*>(raw);
    }

    static inline std::uint32_t GetByteOffset(CharChannelDecoder* decoder)
    {
        return static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(decoder->ptr) & 3u);
    }
    std::uint32_t ChannelDecoder_0(CharChannelDecoder* decoder, std::int32_t* value)
    {
        (void)decoder;
        *value = 0;
        return 0;
    }
    std::uint32_t ChannelDecoder_1a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t shifted = firstWord >> bitOffset;
        std::int32_t code;
        std::int32_t remainingBits;

        if (bitsRemaining < 2u)
            code = (static_cast<std::uint8_t>(shifted) | static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 3;
        else
            code = static_cast<std::int32_t>(shifted & 3u);

        if ((code & 1) != 0)
        {
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                remainingBits = static_cast<std::int32_t>(bitsRemaining) + 30;
            }
            else
            {
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 2;
            }
            *value = code - 2;
        }
        else
        {
            if (bitsRemaining != 0u)
            {
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 1;
            }
            else
            {
                ++wordPtr;
                remainingBits = 31;
            }
            *value = 0;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - static_cast<std::uint32_t>(remainingBits)) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_1b(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t shifted = firstWord >> bitOffset;
        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::int32_t remainingBits;

        if (bitsRemaining < 4u)
            code = (static_cast<std::uint8_t>(shifted) | static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0xF;
        else
            code = static_cast<std::int32_t>(shifted & 0xFu);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                if ((code & 4) != 0)
                {
                    if (bitsRemaining < 4u)
                    {
                        ++wordPtr;
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) + 28;
                    }
                    else
                    {
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) - 4;
                    }
                    *value = (code >> 2) - 2;
                }
                else
                {
                    if (bitsRemaining < 3u)
                    {
                        ++wordPtr;
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) + 29;
                    }
                    else
                    {
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) - 3;
                    }
                    *value = 0;
                }
            }
            else
            {
                if (bitsRemaining < 2u)
                {
                    ++wordPtr;
                    *value = 0;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) + 30;
                }
                else
                {
                    *value = 0;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) - 2;
                }
                resultCode = 2;
            }
        }
        else
        {
            if (bitsRemaining != 0u)
            {
                *value = 0;
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 1;
            }
            else
            {
                ++wordPtr;
                *value = 0;
                remainingBits = 31;
            }
            resultCode = 7;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - static_cast<std::uint32_t>(remainingBits)) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_1c(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t shifted = firstWord >> bitOffset;
        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::int32_t remainingBits;

        if (bitsRemaining < 3u)
            code = (static_cast<std::uint8_t>(shifted) | static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 7;
        else
            code = static_cast<std::int32_t>(shifted & 7u);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                if (bitsRemaining < 3u)
                {
                    ++wordPtr;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) + 29;
                }
                else
                {
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) - 3;
                }
                *value = (code >> 1) - 2;
            }
            else
            {
                if (bitsRemaining < 2u)
                {
                    ++wordPtr;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) + 30;
                }
                else
                {
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) - 2;
                }
                *value = 0;
            }
        }
        else
        {
            if (bitsRemaining != 0u)
            {
                *value = 0;
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 1;
            }
            else
            {
                ++wordPtr;
                *value = 0;
                remainingBits = 31;
            }
            resultCode = 3;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - static_cast<std::uint32_t>(remainingBits)) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_1d(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t shifted = firstWord >> bitOffset;
        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::int32_t remainingBits;

        if (bitsRemaining < 4u)
            code = (static_cast<std::uint8_t>(shifted) | static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0xF;
        else
            code = static_cast<std::int32_t>(shifted & 0xFu);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                if ((code & 4) != 0)
                {
                    if (bitsRemaining < 4u)
                    {
                        ++wordPtr;
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) + 28;
                    }
                    else
                    {
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) - 4;
                    }
                    *value = (code >> 2) - 2;
                }
                else
                {
                    if (bitsRemaining < 3u)
                    {
                        ++wordPtr;
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) + 29;
                    }
                    else
                    {
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) - 3;
                    }
                    *value = 0;
                }
            }
            else
            {
                if (bitsRemaining < 2u)
                {
                    ++wordPtr;
                    *value = 0;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) + 30;
                }
                else
                {
                    *value = 0;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) - 2;
                }
                resultCode = 2;
            }
        }
        else
        {
            if (bitsRemaining != 0u)
            {
                *value = 0;
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 1;
            }
            else
            {
                ++wordPtr;
                *value = 0;
                remainingBits = 31;
            }
            resultCode = 4;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - static_cast<std::uint32_t>(remainingBits)) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_1e(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t remainingBits;

        if (bitsRemaining < 2u)
        {
            ++wordPtr;
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 3;
            remainingBits = bitsRemaining + 30;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 3u);
            remainingBits = bitsRemaining - 2u;
        }

        if (code != 0)
        {
            *value = code - 2;
        }
        else
        {
            *value = 0;
            resultCode = 6;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - remainingBits) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_2a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::int32_t code;
        std::int32_t remainingBits;

        if (bitsRemaining < 3u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 7;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 7u);

        if ((code & 1) != 0)
        {
            if (bitsRemaining < 3u)
            {
                ++wordPtr;
                remainingBits = static_cast<std::int32_t>(bitsRemaining) + 29;
            }
            else
            {
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 3;
            }
            *value = (code >> 2) + (code >> 1) - 2;
        }
        else
        {
            if (bitsRemaining != 0u)
            {
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 1;
            }
            else
            {
                ++wordPtr;
                remainingBits = 31;
            }
            *value = 0;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - static_cast<std::uint32_t>(remainingBits)) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_2b(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = aligned[0];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t shifted = firstWord >> bitOffset;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 3u)
            code = (static_cast<std::uint8_t>(shifted) | static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 7;
        else
            code = static_cast<std::int32_t>(shifted & 7u);

        if ((code & 3) != 0)
        {
            code &= 3;
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
        }
        else if (bitsRemaining < 3u)
        {
            ++wordPtr;
            newBitsRemaining = bitsRemaining + 29u;
        }
        else
        {
            newBitsRemaining = bitsRemaining - 3u;
        }

        *value = code - 2;
        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_2c(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::int32_t remainingBits;

        if (bitsRemaining < 5u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x1F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x1Fu);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                if ((code & 4) != 0)
                {
                    if (bitsRemaining < 5u)
                    {
                        ++wordPtr;
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) + 27;
                    }
                    else
                    {
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) - 5;
                    }
                    *value = (code >> 4) + (code >> 3) - 2;
                }
                else
                {
                    if (bitsRemaining < 3u)
                    {
                        ++wordPtr;
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) + 29;
                    }
                    else
                    {
                        remainingBits = static_cast<std::int32_t>(bitsRemaining) - 3;
                    }
                    *value = 0;
                }
            }
            else
            {
                if (bitsRemaining < 2u)
                {
                    ++wordPtr;
                    *value = 0;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) + 30;
                }
                else
                {
                    *value = 0;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) - 2;
                }
                resultCode = 2;
            }
        }
        else
        {
            if (bitsRemaining != 0u)
            {
                *value = 0;
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 1;
            }
            else
            {
                ++wordPtr;
                *value = 0;
                remainingBits = 31;
            }
            resultCode = 4;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - static_cast<std::uint32_t>(remainingBits)) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_3a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 4u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0xF;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0xFu);

        if ((code & 3) != 0)
        {
            *value = (code & 3) - 2;
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
        }
        else
        {
            std::int32_t tmp = code >> 2;
            if ((tmp & 2) == 0)
                tmp -= 3;
            *value = tmp;

            if (bitsRemaining < 4u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 28u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 4u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_3b(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 3u)
        {
            ++wordPtr;
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 7;
            newBitsRemaining = bitsRemaining + 29u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 7u);
            newBitsRemaining = bitsRemaining - 3u;
        }

        if (code != 0)
        {
            *value = code - 4;
        }
        else
        {
            *value = 0;
            resultCode = 3;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_5a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 5u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x1F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x1Fu);

        if ((code & 3) != 0)
        {
            *value = (code & 3) - 2;
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
        }
        else
        {
            std::int32_t tmp = code >> 2;
            if ((tmp & 4) != 0)
                tmp -= 2;
            else
                tmp -= 5;
            *value = tmp;

            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_7a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 4u)
        {
            ++wordPtr;
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0xF;
            newBitsRemaining = bitsRemaining + 28u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0xFu);
            newBitsRemaining = bitsRemaining - 4u;
        }

        if (code != 0)
        {
            *value = code - 8;
        }
        else
        {
            *value = 0;
            resultCode = 4;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_7b(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::int32_t code;
        std::uint32_t low3;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 5u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x1F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x1Fu);

        low3 = static_cast<std::uint32_t>(code) & 7u;

        if (low3 < 3u)
        {
            if (low3 == 2u)
            {
                *value = (code & 8) != 0 ? 3 : -3;
                if (bitsRemaining < 4u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 28u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 4u;
                }
            }
            else
            {
                if ((code & 1) != 0)
                    *value = -4 - (code >> 3);
                else
                    *value = (code >> 3) + 4;

                if (bitsRemaining < 5u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 27u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 5u;
                }
            }
        }
        else
        {
            *value = static_cast<std::int32_t>(low3) - 5;
            if (bitsRemaining < 3u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 29u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 3u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_7c(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = aligned[0];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t shifted = firstWord >> bitOffset;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 6u)
            code = (static_cast<std::uint8_t>(shifted) | static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x3F;
        else
            code = static_cast<std::int32_t>(shifted & 0x3Fu);

        if ((code & 3) != 0)
        {
            *value = (code & 3) - 2;
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
        }
        else if ((code & 4) != 0)
        {
            std::int32_t tmp = code >> 3;
            if ((tmp & 4) == 0)
                tmp -= 7;
            *value = tmp;
            if (bitsRemaining < 6u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 26u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 6u;
            }
        }
        else
        {
            std::int32_t tmp = (code >> 3) & 3;
            if ((tmp & 2) == 0)
                tmp -= 3;
            *value = tmp;
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_f15a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;
        std::int32_t low4;
        std::int32_t tmp;

        if (bitsRemaining < 5u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x1F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x1Fu);

        if ((code & 1) != 0)
        {
            std::int32_t half = code >> 1;
            std::int32_t quarter = code >> 2;
            std::uint8_t lf = static_cast<std::uint8_t>(half & 1);
            if ((quarter & 4) == 0)
                quarter -= 7;
            *value = quarter << lf;
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }
        }
        else
        {
            if (bitsRemaining < 4u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 28u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 4u;
            }
            low4 = code & 0xF;
            if (low4 != 0)
            {
                *value = (low4 >> 1) - 4;
            }
            else
            {
                *value = 0;
                resultCode = 4;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f15b(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(firstWordShifted) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x7Fu);

        if ((code & 3) != 0)
        {
            *value = (code & 3) - 2;
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
        }
        else if ((code & 4) != 0)
        {
            std::int32_t half = code >> 3;
            std::int32_t high = code >> 4;
            std::uint8_t lf = static_cast<std::uint8_t>(half & 1);
            if ((high & 4) == 0)
                high -= 7;
            *value = high << lf;
            if (bitsRemaining < 7u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 25u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 7u;
            }
        }
        else
        {
            std::int32_t tmp = (code >> 3) & 3;
            if ((tmp & 2) == 0)
                tmp -= 3;
            *value = tmp;
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_f15c(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(firstWordShifted) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x7Fu);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                if ((code & 4) != 0)
                {
                    std::int32_t half = code >> 3;
                    std::int32_t high = code >> 4;
                    std::uint8_t lf = static_cast<std::uint8_t>(half & 1);
                    if ((high & 4) == 0)
                        high -= 7;
                    *value = high << lf;
                    if (bitsRemaining < 7u)
                    {
                        ++wordPtr;
                        newBitsRemaining = bitsRemaining + 25u;
                    }
                    else
                    {
                        newBitsRemaining = bitsRemaining - 7u;
                    }
                }
                else
                {
                    std::int32_t tmp = (code >> 3) & 3;
                    if ((tmp & 2) == 0)
                        tmp -= 3;
                    *value = tmp;
                    if (bitsRemaining < 5u)
                    {
                        ++wordPtr;
                        newBitsRemaining = bitsRemaining + 27u;
                    }
                    else
                    {
                        newBitsRemaining = bitsRemaining - 5u;
                    }
                }
            }
            else
            {
                *value = (((code >> 1) & 2) - 1);
                if (bitsRemaining < 3u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 29u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 3u;
                }
            }
        }
        else
        {
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
            *value = 0;
            if ((code & 2) == 0)
                resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f31a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::int32_t tmp;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 5u)
        {
            ++wordPtr;
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x1F;
            newBitsRemaining = bitsRemaining + 27u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x1Fu);
            newBitsRemaining = bitsRemaining - 5u;
        }

        if (code != 0)
        {
            std::uint8_t low2 = static_cast<std::uint8_t>(code & 3);
            std::int32_t high = code >> 2;
            if (low2 != 0)
            {
                std::uint8_t shift = static_cast<std::uint8_t>(low2 - 1);
                if ((high & 4) == 0)
                    high -= 7;
                tmp = high << shift;
            }
            else
            {
                tmp = high - 4;
            }
            *value = tmp;
        }
        else
        {
            *value = 0;
            resultCode = 5;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f31b(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 6u)
            code = (static_cast<std::uint8_t>(firstWordShifted) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x3F;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x3Fu);

        if ((code & 1) != 0)
        {
            std::int32_t high;
            std::int32_t shift;

            if ((code & 2) != 0)
            {
                shift = ((code >> 2) & 1) + 1;
                high = code >> 3;
                if (bitsRemaining < 6u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 26u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 6u;
                }
            }
            else
            {
                shift = 0;
                high = (code >> 2) & 7;
                if (bitsRemaining < 5u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 27u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 5u;
                }
            }

            if ((high & 4) == 0)
                high -= 7;
            *value = high << shift;
        }
        else
        {
            if (bitsRemaining < 4u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 28u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 4u;
            }

            std::int32_t low4 = code & 0xF;
            if (low4 != 0)
            {
                *value = (low4 >> 1) - 4;
            }
            else
            {
                *value = 0;
                resultCode = 4;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f31c(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::int32_t code;
        std::uint32_t low3;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(firstWordShifted) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x7Fu);

        low3 = static_cast<std::uint32_t>(code) & 7u;

        if (low3 < 3u)
        {
            if ((code & 7) != 0)
            {
                std::int32_t shift;
                std::int32_t high;
                if (low3 == 1u)
                {
                    shift = 0;
                    high = (code >> 3) & 7;
                    if (bitsRemaining < 6u)
                    {
                        ++wordPtr;
                        newBitsRemaining = bitsRemaining + 26u;
                    }
                    else
                    {
                        newBitsRemaining = bitsRemaining - 6u;
                    }
                }
                else
                {
                    shift = ((code >> 3) & 1) + 1;
                    high = code >> 4;
                    if (bitsRemaining < 7u)
                    {
                        ++wordPtr;
                        newBitsRemaining = bitsRemaining + 25u;
                    }
                    else
                    {
                        newBitsRemaining = bitsRemaining - 7u;
                    }
                }

                if ((high & 4) == 0)
                    high -= 7;
                *value = high << shift;
            }
            else
            {
                *value = (code & 8) != 0 ? 3 : -3;
                if (bitsRemaining < 4u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 28u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 4u;
                }
            }
        }
        else
        {
            *value = static_cast<std::int32_t>(low3) - 5;
            if (bitsRemaining < 3u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 29u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 3u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_f31d(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(firstWordShifted) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x7Fu);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                if ((code & 0xC) != 0)
                {
                    std::int32_t shift = ((code >> 2) & 3) - 1;
                    std::int32_t high = code >> 4;
                    if ((high & 4) == 0)
                        high -= 7;
                    *value = high << shift;
                    if (bitsRemaining < 7u)
                    {
                        ++wordPtr;
                        newBitsRemaining = bitsRemaining + 25u;
                    }
                    else
                    {
                        newBitsRemaining = bitsRemaining - 7u;
                    }
                }
                else
                {
                    std::int32_t high = (code >> 4) & 3;
                    if ((high & 2) == 0)
                        high -= 3;
                    *value = high;
                    if (bitsRemaining < 6u)
                    {
                        ++wordPtr;
                        newBitsRemaining = bitsRemaining + 26u;
                    }
                    else
                    {
                        newBitsRemaining = bitsRemaining - 6u;
                    }
                }
            }
            else
            {
                *value = (((code >> 1) & 2) - 1);
                if (bitsRemaining < 3u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 29u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 3u;
                }
            }
        }
        else
        {
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
            *value = 0;
            if ((code & 2) == 0)
                resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f63a(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 6u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x3F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x3Fu);

        if ((code & 1) != 0)
        {
            std::int32_t half = code >> 1;
            std::int32_t high = code >> 3;
            std::uint8_t shift = static_cast<std::uint8_t>(half & 3);
            if ((high & 4) == 0)
                high -= 7;
            *value = high << shift;
            if (bitsRemaining < 6u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 26u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 6u;
            }
        }
        else
        {
            if (bitsRemaining < 4u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 28u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 4u;
            }

            std::int32_t low4 = code & 0xF;
            if (low4 != 0)
            {
                *value = (low4 >> 1) - 4;
            }
            else
            {
                *value = 0;
                resultCode = 4;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f63b(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 6u)
            code = (static_cast<std::uint8_t>(firstWordShifted) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x3F;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x3Fu);

        if ((code & 1) != 0)
        {
            std::int32_t shift;
            std::int32_t high;

            if ((code & 2) != 0)
            {
                shift = ((code >> 2) & 1) + 2;
                high = code >> 3;
                if (bitsRemaining < 6u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 26u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 6u;
                }
            }
            else
            {
                high = (code >> 2) & 7;
                shift = 1;
                if (bitsRemaining < 5u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 27u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 5u;
                }
            }

            if ((high & 4) == 0)
                high -= 7;
            *value = high << shift;
        }
        else
        {
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }

            std::int32_t low5 = code & 0x1F;
            if (low5 != 0)
            {
                *value = (low5 >> 1) - 8;
            }
            else
            {
                *value = 0;
                resultCode = 5;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f127(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 6u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x3F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x3Fu);

        if ((code & 1) != 0)
        {
            std::int32_t low2 = (code >> 1) & 3;
            std::int32_t high = code >> 3;
            std::uint8_t shift = static_cast<std::uint8_t>(low2 + 1);
            if ((high & 4) == 0)
                high -= 7;
            *value = high << shift;
            if (bitsRemaining < 6u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 26u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 6u;
            }
        }
        else
        {
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }

            std::int32_t low5 = code & 0x1F;
            if (low5 != 0)
            {
                *value = (low5 >> 1) - 8;
            }
            else
            {
                *value = 0;
                resultCode = 5;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f255(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 6u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x3F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x3Fu);

        std::uint8_t low3 = static_cast<std::uint8_t>(code & 7);

        if (low3 >= 2u)
        {
            std::int32_t high = code >> 3;
            std::uint8_t shift = static_cast<std::uint8_t>(low3 - 2);
            if ((high & 4) == 0)
                high -= 7;
            *value = high << shift;
            if (bitsRemaining < 6u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 26u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 6u;
            }
        }
        else
        {
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }

            std::int32_t low5 = code & 0x1F;
            if (low5 != 0)
            {
                if ((low5 & 1) != 0)
                    *value = low5 >> 3;
                else
                    *value = -(low5 >> 3);
            }
            else
            {
                *value = 0;
                resultCode = 5;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f2047(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x7Fu);

        if ((code & 1) != 0)
        {
            std::int32_t low3 = (code >> 1) & 7;
            std::int32_t high = code >> 4;
            std::uint8_t shift = static_cast<std::uint8_t>(low3 + 1);
            if ((high & 4) == 0)
                high -= 7;
            *value = high << shift;
            if (bitsRemaining < 7u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 25u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 7u;
            }
        }
        else
        {
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }

            std::int32_t low5 = code & 0x1F;
            if (low5 != 0)
            {
                *value = (low5 >> 1) - 8;
            }
            else
            {
                *value = 0;
                resultCode = 5;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f15bit(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 9u)
            code = (static_cast<std::uint16_t>(firstWordShifted) |
                static_cast<std::uint16_t>(secondWord << bitsRemaining)) & 0x1FF;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x1FFu);

        std::uint32_t low3 = static_cast<std::uint32_t>(code) & 7u;

        if (low3 >= 2u)
        {
            std::int32_t high;
            if (low3 == 7u)
            {
                low3 = ((code >> 3) & 7) + 5;
                high = code >> 6;
                if (bitsRemaining < 9u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 23u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 9u;
                }
            }
            else
            {
                high = (code >> 3) & 7;
                low3 = low3 - 2u;
                if (bitsRemaining < 6u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 26u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 6u;
                }
            }

            if ((high & 4) == 0)
                high -= 7;
            std::int32_t tmp = high << static_cast<std::uint8_t>(low3);
            *value = tmp;
        }
        else
        {
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }

            std::int32_t low5 = code & 0x1F;
            if (low5 != 0)
            {
                std::int32_t tmp = (low5 & 1) != 0 ? (low5 >> 3) : -(low5 >> 3);
                *value = tmp;
            }
            else
            {
                *value = 0;
                resultCode = 5;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f23bit(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 10u)
            code = (static_cast<std::uint16_t>(firstWordShifted) |
                static_cast<std::uint16_t>(secondWord << bitsRemaining)) & 0x3FF;
        else
            code = static_cast<std::int32_t>(firstWordShifted & 0x3FFu);

        std::uint32_t low3 = static_cast<std::uint32_t>(code) & 7u;

        if (low3 >= 2u)
        {
            std::int32_t high;
            if (low3 == 7u)
            {
                low3 = ((code >> 3) & 0xF) + 5;
                high = code >> 7;
                if (bitsRemaining < 10u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 22u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 10u;
                }
            }
            else
            {
                high = (code >> 3) & 7;
                low3 = low3 - 2u;
                if (bitsRemaining < 6u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 26u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 6u;
                }
            }

            if ((high & 4) == 0)
                high -= 7;
            *value = high << static_cast<std::uint8_t>(low3);
        }
        else
        {
            if (bitsRemaining < 5u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }

            std::int32_t low5 = code & 0x1F;
            if (low5 != 0)
            {
                std::int32_t tmp = (low5 & 1) != 0 ? (low5 >> 3) : -(low5 >> 3);
                *value = tmp;
            }
            else
            {
                *value = 0;
                resultCode = 5;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_f31bit(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uintptr_t rawPtr = reinterpret_cast<std::uintptr_t>(decoder->ptr);
        std::uintptr_t alignedRaw = rawPtr & ~static_cast<std::uintptr_t>(3);
        std::uint32_t* aligned = reinterpret_cast<std::uint32_t*>(alignedRaw);

        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitOffset = decoder->bitpos + 8u * static_cast<std::uint32_t>(rawPtr & 3u);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t firstWordShifted = aligned[0] >> bitOffset;
        std::uintptr_t bytePtr = alignedRaw + 8;

        std::uint32_t code;
        std::uint32_t low5 = firstWordShifted & 0x1Fu;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 8u)
            code = static_cast<std::uint8_t>(firstWordShifted | (secondWord << bitsRemaining));
        else
            code = static_cast<std::uint8_t>(firstWordShifted);

        if (low5 == 2u)
        {
            *value = 0;
            if (bitsRemaining < 5u)
            {
                bytePtr += 4;
                newBitsRemaining = bitsRemaining + 27u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 5u;
            }
        }
        else if (low5 >= 2u)
        {
            std::int32_t high = static_cast<std::int32_t>(code >> 5);
            std::uint8_t shift = static_cast<std::uint8_t>((low5 - 3u));
            if ((high & 4) == 0)
                high -= 7;
            *value = high << shift;
            if (bitsRemaining < 8u)
            {
                bytePtr += 4;
                newBitsRemaining = bitsRemaining + 24u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 8u;
            }
        }
        else
        {
            std::int32_t tmp;
            if ((code & 1u) != 0u)
                tmp = static_cast<std::int32_t>(((code >> 5) & 3u) + 1u);
            else
                tmp = -1 - static_cast<std::int32_t>((code >> 5) & 3u);
            *value = tmp;

            if (bitsRemaining < 7u)
            {
                bytePtr += 4;
                newBitsRemaining = bitsRemaining + 25u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 7u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(bytePtr + (((32u - newBitsRemaining) >> 3) - 8u));
        return 1;
    }
    std::uint32_t ChannelDecoder_15(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 5u)
        {
            ++wordPtr;
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x1F;
            newBitsRemaining = bitsRemaining + 27u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x1Fu);
            newBitsRemaining = bitsRemaining - 5u;
        }

        if (code != 0)
        {
            *value = code - 16;
        }
        else
        {
            *value = 0;
            resultCode = 5;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_0_16(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::int32_t remainingBits;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x7Fu);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                if (bitsRemaining < 7u)
                {
                    ++wordPtr;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) + 25;
                }
                else
                {
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) - 7;
                }
                *value = (code >> 6) + (code >> 2) - 16;
            }
            else
            {
                if (bitsRemaining < 2u)
                {
                    ++wordPtr;
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) + 30;
                }
                else
                {
                    remainingBits = static_cast<std::int32_t>(bitsRemaining) - 2;
                }
                *value = 0;
            }
        }
        else
        {
            if (bitsRemaining != 0u)
            {
                *value = 0;
                remainingBits = static_cast<std::int32_t>(bitsRemaining) - 1;
            }
            else
            {
                ++wordPtr;
                *value = 0;
                remainingBits = 31;
            }
            resultCode = 4;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(remainingBits) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - static_cast<std::uint32_t>(remainingBits)) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_0_1_17(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t shifted = aligned[0] >> (decoder->bitpos + 8u * GetByteOffset(decoder));
        std::uint32_t bitsRemaining = 32u - (decoder->bitpos + 8u * GetByteOffset(decoder));
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(shifted) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>(shifted & 0x7Fu);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                std::int32_t tmp = code >> 2;
                std::int32_t val = tmp - 14;
                if ((tmp & 0x10) == 0)
                    val = tmp - 17;
                *value = val;

                if (bitsRemaining < 7u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 25u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 7u;
                }
            }
            else
            {
                *value = (((code >> 1) & 2) - 1);
                if (bitsRemaining < 3u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 29u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 3u;
                }
            }
        }
        else
        {
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
            *value = 0;
            if ((code & 2) == 0)
                resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_1_17(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
        else
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x7Fu);

        if ((code & 3) != 0)
        {
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
            *value = (code & 3) - 2;
        }
        else
        {
            if (bitsRemaining < 7u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 25u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 7u;
            }

            std::int32_t tmp = code >> 2;
            std::int32_t val = ((tmp & 0x10) != 0) ? (tmp - 14) : (tmp - 17);
            *value = val;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_31(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 6u)
        {
            ++wordPtr;
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x3F;
            newBitsRemaining = bitsRemaining + 26u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x3Fu);
            newBitsRemaining = bitsRemaining - 6u;
        }

        if (code != 0)
        {
            *value = code - 32;
        }
        else
        {
            *value = 0;
            resultCode = 6;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_0_1_33(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t shifted = aligned[0] >> (decoder->bitpos + 8u * GetByteOffset(decoder));
        std::uint32_t bitsRemaining = 32u - (decoder->bitpos + 8u * GetByteOffset(decoder));
        std::uint32_t* wordPtr = aligned + 2;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 8u)
            code = static_cast<std::uint8_t>(shifted | (secondWord << bitsRemaining));
        else
            code = static_cast<std::uint8_t>(shifted);

        if ((code & 1) != 0)
        {
            if ((code & 2) != 0)
            {
                std::int32_t tmp = code >> 2;
                std::int32_t val = ((tmp & 0x20) != 0) ? (tmp - 30) : (tmp - 33);
                *value = val;
                if (bitsRemaining < 8u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 24u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 8u;
                }
            }
            else
            {
                *value = (((code >> 1) & 2) - 1);
                if (bitsRemaining < 3u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 29u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 3u;
                }
            }
        }
        else
        {
            if (bitsRemaining < 2u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 30u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 2u;
            }
            *value = 0;
            if ((code & 2) == 0)
                resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_3_35(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = aligned[0];
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t secondWord = aligned[1];
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t shifted = firstWord >> bitOffset;
        std::uint32_t* wordPtr = aligned + 2;

        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 8u)
            code = static_cast<std::uint8_t>(shifted | (secondWord << bitsRemaining));
        else
            code = static_cast<std::uint8_t>(shifted);

        if ((code & 7u) < 3u)
        {
            if ((code & 2) != 0)
            {
                *value = (code & 8) != 0 ? 3 : -3;
                if (bitsRemaining < 4u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 28u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 4u;
                }
            }
            else
            {
                if ((code & 1) != 0)
                    *value = (code >> 3) + 4;
                else
                    *value = -4 - (code >> 3);

                if (bitsRemaining < 8u)
                {
                    ++wordPtr;
                    newBitsRemaining = bitsRemaining + 24u;
                }
                else
                {
                    newBitsRemaining = bitsRemaining - 8u;
                }
            }
        }
        else
        {
            *value = (code & 7) - 5;
            if (bitsRemaining < 3u)
            {
                ++wordPtr;
                newBitsRemaining = bitsRemaining + 29u;
            }
            else
            {
                newBitsRemaining = bitsRemaining - 3u;
            }
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return 1;
    }
    std::uint32_t ChannelDecoder_63(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 7u)
        {
            ++wordPtr;
            code = (static_cast<std::uint8_t>(firstWord >> bitOffset) |
                static_cast<std::uint8_t>(secondWord << bitsRemaining)) & 0x7F;
            newBitsRemaining = bitsRemaining + 25u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x7Fu);
            newBitsRemaining = bitsRemaining - 7u;
        }

        if (code != 0)
        {
            *value = code - 64;
        }
        else
        {
            *value = 0;
            resultCode = 7;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_127(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::uint32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 8u)
        {
            ++wordPtr;
            code = static_cast<std::uint8_t>((firstWord >> bitOffset) | (secondWord << bitsRemaining));
            newBitsRemaining = bitsRemaining + 24u;
        }
        else
        {
            code = static_cast<std::uint8_t>(firstWord >> bitOffset);
            newBitsRemaining = bitsRemaining - 8u;
        }

        if (code != 0)
        {
            *value = static_cast<std::int32_t>(code) - 128;
        }
        else
        {
            *value = 0;
            resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_255(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 9u)
        {
            ++wordPtr;
            code = (static_cast<std::uint16_t>(firstWord >> bitOffset) |
                static_cast<std::uint16_t>(secondWord << bitsRemaining)) & 0x1FF;
            newBitsRemaining = bitsRemaining + 23u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x1FFu);
            newBitsRemaining = bitsRemaining - 9u;
        }

        if (code != 0)
        {
            *value = code - 256;
        }
        else
        {
            *value = 0;
            resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_511(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 10u)
        {
            ++wordPtr;
            code = (static_cast<std::uint16_t>(firstWord >> bitOffset) |
                static_cast<std::uint16_t>(secondWord << bitsRemaining)) & 0x3FF;
            newBitsRemaining = bitsRemaining + 22u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x3FFu);
            newBitsRemaining = bitsRemaining - 10u;
        }

        if (code != 0)
        {
            *value = code - 512;
        }
        else
        {
            *value = 0;
            resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_1023(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 11u)
        {
            ++wordPtr;
            code = (static_cast<std::uint16_t>(firstWord >> bitOffset) |
                static_cast<std::uint16_t>(secondWord << bitsRemaining)) & 0x7FF;
            newBitsRemaining = bitsRemaining + 21u;
        }
        else
        {
            code = static_cast<std::int32_t>((firstWord >> bitOffset) & 0x7FFu);
            newBitsRemaining = bitsRemaining - 11u;
        }

        if (code != 0)
        {
            *value = code - 1024;
        }
        else
        {
            *value = 0;
            resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_15bit(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::uint32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 16u)
        {
            ++wordPtr;
            code = static_cast<std::uint16_t>(firstWord >> bitOffset) |
                static_cast<std::uint16_t>(secondWord << bitsRemaining);
            newBitsRemaining = bitsRemaining + 16u;
        }
        else
        {
            code = static_cast<std::uint16_t>(firstWord >> bitOffset);
            newBitsRemaining = bitsRemaining - 16u;
        }

        if (code != 0u)
        {
            *value = static_cast<std::int32_t>(code) - 0x8000;
        }
        else
        {
            *value = 0;
            resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_23bit(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::uint32_t bitOffset = decoder->bitpos + 8u * GetByteOffset(decoder);
        std::uint32_t bitsRemaining = 32u - bitOffset;
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;
        std::int32_t code;
        std::uint32_t newBitsRemaining;

        if (bitsRemaining < 24u)
        {
            ++wordPtr;
            code = static_cast<std::int32_t>((firstWord | (secondWord << bitsRemaining)) & 0xFFFFFFu);
            newBitsRemaining = bitsRemaining + 8u;
        }
        else
        {
            code = static_cast<std::int32_t>(firstWord & 0xFFFFFFu);
            newBitsRemaining = bitsRemaining - 24u;
        }

        if (code != 0)
        {
            *value = code - 0x800000;
        }
        else
        {
            *value = 0;
            resultCode = 8;
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(newBitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) + ((32u - newBitsRemaining) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_31bit(CharChannelDecoder* decoder, std::int32_t* value)
    {
        std::uint32_t* aligned = GetWord(decoder);
        std::uint32_t firstWord = *aligned++;
        std::uint32_t secondWord = *aligned;
        std::int32_t bitsRemaining = 32 - static_cast<std::int32_t>(decoder->bitpos + 8u * GetByteOffset(decoder));
        std::uint32_t* wordPtr = aligned + 1;

        std::uint32_t resultCode = 1;

        if (bitsRemaining == 32)
        {
            bitsRemaining = 0;
        }
        else
        {
            firstWord |= (secondWord << bitsRemaining);
            ++wordPtr;
        }

        if (firstWord == 0x80000000u)
        {
            *value = 0;
            resultCode = 8;
        }
        else
        {
            *value = static_cast<std::int32_t>(firstWord);
        }

        decoder->bitpos = static_cast<std::uint8_t>(-static_cast<std::int8_t>(bitsRemaining) & 7);
        decoder->ptr = reinterpret_cast<std::uint8_t*>(wordPtr) +
            ((32u - static_cast<std::uint32_t>(bitsRemaining)) >> 3) - 8;
        return resultCode;
    }
    std::uint32_t ChannelDecoder_err(CharChannelDecoder* decoder, std::int32_t* value)
    {
        (void)decoder;
        *value = 0;
        return 0;
    }



    using ChannelDecoderFn = uint32_t(*)(CharChannelDecoder*, int32_t*);
    ChannelDecoderFn DecoderTable[64] =
    {
          ChannelDecoder_0,
          ChannelDecoder_1a,
          ChannelDecoder_1b,
          ChannelDecoder_1c,
          ChannelDecoder_1d,
          ChannelDecoder_1e,
          ChannelDecoder_2a,
          ChannelDecoder_2b,
          ChannelDecoder_2c,
          ChannelDecoder_3a,
          ChannelDecoder_3b,
          ChannelDecoder_5a,
          ChannelDecoder_7a,
          ChannelDecoder_7b,
          ChannelDecoder_7c,
          ChannelDecoder_f15a,
          ChannelDecoder_f15b,
          ChannelDecoder_f15c,
          ChannelDecoder_f31a,
          ChannelDecoder_f31b,
          ChannelDecoder_f31c,
          ChannelDecoder_f31d,
          ChannelDecoder_f63a,
          ChannelDecoder_f63b,
          ChannelDecoder_f127,
          ChannelDecoder_f255,
          ChannelDecoder_f2047,
          ChannelDecoder_f15bit,
          ChannelDecoder_f23bit,
          ChannelDecoder_f31bit,
          ChannelDecoder_err,
          ChannelDecoder_err,
          ChannelDecoder_0,
          ChannelDecoder_1a,
          ChannelDecoder_1b,
          ChannelDecoder_1c,
          ChannelDecoder_1d,
          ChannelDecoder_1e,
          ChannelDecoder_2a,
          ChannelDecoder_2b,
          ChannelDecoder_2c,
          ChannelDecoder_3a,
          ChannelDecoder_3b,
          ChannelDecoder_5a,
          ChannelDecoder_7a,
          ChannelDecoder_7b,
          ChannelDecoder_7c,
          ChannelDecoder_15,
          ChannelDecoder_0_16,
          ChannelDecoder_0_1_17,
          ChannelDecoder_1_17,
          ChannelDecoder_31,
          ChannelDecoder_0_1_33,
          ChannelDecoder_3_35,
          ChannelDecoder_63,
          ChannelDecoder_127,
          ChannelDecoder_255,
          ChannelDecoder_511,
          ChannelDecoder_1023,
          ChannelDecoder_15bit,
          ChannelDecoder_23bit,
          ChannelDecoder_31bit,
          ChannelDecoder_err,
          ChannelDecoder_err
    };


    void DequantTracks(
        EncTrackData* tracks,
        const uint8_t* codecIxs,
        CharChannelDecoder* dec,
        uint32_t            frame,
        uint32_t            startTrack,
        uint32_t            numTracks,
        float               scaledQuant,
        bool                isSceneAnim)
    {
        auto* codec = codecIxs + startTrack;
        auto* track = tracks + startTrack;

        for (uint32_t t = 0; t < numTracks; ++t, ++codec, ++track) {
            uint8_t codecByte = *codec;
            uint8_t maskIdx = codecByte >> 6;
            uint8_t num = codecByte & 0x3F;

            if (frame == 0) {
                uint32_t bits = isSceneAnim
                    ? g_iSceneAnimInitialValuesBitTable[3]
                    : g_iInitialValuesBitTable[3];

                int base = ReadSignedBits(dec, bits);
                track->iNumZerosInTrack = 0;
                track->fWholeValue = base * (scaledQuant * g_fEntropyBaseQuantStep);
                continue;
            }

            if (frame == 1) {
                uint32_t bits = isSceneAnim ? g_iSceneAnimInitialValuesBitTable[maskIdx] : g_iInitialValuesBitTable[maskIdx];

                int d0 = ReadSignedBits(dec, bits);
                track->fDeltaValue = d0 * scaledQuant;
                continue;
            }
            if (num == 0) {
                track->fSecDeltaValue = 0.0f;
                continue;
            }

            if (track->iNumZerosInTrack == 0) {
                int      decoded = 0;
                uint32_t runlen = DecoderTable[num](dec, &decoded);

                track->iNumZerosInTrack = runlen - 1;
                track->fSecDeltaValue = decoded * scaledQuant;
            }
            else {
                --track->iNumZerosInTrack;
                track->fSecDeltaValue = 0.0f;
            }
        }
    }


    static inline int32_t ApplyQuatDeltaToTracks(EncTrackData* tx, EncTrackData* ty, EncTrackData* tz)
    {
        vector3 base_xyz;
        base_xyz.v[0] = tx->fWholeValue;
        base_xyz.v[1] = ty->fWholeValue;
        base_xyz.v[2] = tz->fWholeValue;

        quat q_base;
        q_base.compose(&base_xyz);

        vector3 delta_xyz;
        delta_xyz.v[0] = tx->fDeltaValue;
        delta_xyz.v[1] = ty->fDeltaValue;
        delta_xyz.v[2] = tz->fDeltaValue;

        quat q_delta;
        q_delta.compose(&delta_xyz);
        q_delta.norm();

        quat q_out = quat::mul(q_delta, q_base);
        if (q_out.v[3] < 0.0f) {
            q_out.v[0] = -q_out.v[0];
            q_out.v[1] = -q_out.v[1];
            q_out.v[2] = -q_out.v[2];
            q_out.v[3] = -q_out.v[3];
        }

        tx->fWholeValue = q_out.v[0];
        ty->fWholeValue = q_out.v[1];
        tz->fWholeValue = q_out.v[2];

        return *reinterpret_cast<int32_t*>(&tz->fWholeValue);
    }

    int32_t ReconstructBaseTracks(EncTrackData* tracks, const unsigned char*, unsigned int iFrameIx)
    {
        EncTrackData* tx = &tracks[iFrameIx];
        EncTrackData* ty = &tracks[iFrameIx + 1];
        EncTrackData* tz = &tracks[iFrameIx + 2];

        return ApplyQuatDeltaToTracks(tx, ty, tz);
    }

    int32_t ApplyTrackDeltas(EncTrackData* tracks, const unsigned char*, unsigned int iTrackIx)
    {
        EncTrackData* tx = &tracks[iTrackIx];
        EncTrackData* ty = &tracks[iTrackIx + 1];
        EncTrackData* tz = &tracks[iTrackIx + 2];

        tx->fDeltaValue += tx->fSecDeltaValue;
        ty->fDeltaValue += ty->fSecDeltaValue;
        tz->fDeltaValue += tz->fSecDeltaValue;

        return ApplyQuatDeltaToTracks(tx, ty, tz);
    }

    static void IntegrateForFrame(std::vector<EncTrackData>& tracks, const uint8_t* codecBytes, int mask, unsigned int iFrameIx, CharChannelDecoder& dec, unsigned int ntracks, float scaledQuant, bool isSceneAnim)
    {
        DequantTracks(tracks.data(), codecBytes, &dec, iFrameIx, 0, ntracks, scaledQuant, isSceneAnim);
        if (iFrameIx == 0)
            return;

        if (iFrameIx == 1)
        {
            unsigned decodedTracks = 0;
            for (unsigned i = 0; i < 5; ++i)
            {
                if (mask & (1 << i))
                {
                    ReconstructBaseTracks(tracks.data(), codecBytes, decodedTracks);
                    decodedTracks += 3;
                }
            }

            if (mask & 0x20)
            {
                ReconstructBaseTracks(tracks.data(), codecBytes, decodedTracks);

                unsigned trackIx = decodedTracks + 3;
                auto& t0 = tracks[trackIx++];
                auto& t1 = tracks[trackIx];
                auto& t2 = tracks[trackIx + 1];

                t0.fWholeValue += t0.fDeltaValue;
                t1.fWholeValue += t1.fDeltaValue;
                t2.fWholeValue += t2.fDeltaValue;
            }
            return;
        }


        unsigned iTrackIx = 0;
        for (unsigned j = 0; j < 5; ++j)
        {
            if (mask & (1 << j))
            {
                ApplyTrackDeltas(tracks.data(), codecBytes, iTrackIx);
                iTrackIx += 3;
            }
        }

        // extras
        if (mask & 0x20)
        {
            ApplyTrackDeltas(tracks.data(), codecBytes, iTrackIx);

            unsigned tmpTrackIx = iTrackIx + 3;

            auto& t0 = tracks[tmpTrackIx++];
            float d0 = t0.fSecDeltaValue + t0.fDeltaValue;
            t0.fDeltaValue = d0;
            t0.fWholeValue += d0;

            auto& t1 = tracks[tmpTrackIx++];
            float d1 = t1.fSecDeltaValue + t1.fDeltaValue;
            t1.fDeltaValue = d1;
            t1.fWholeValue += d1;

            auto& t2 = tracks[tmpTrackIx];
            float d2 = t2.fSecDeltaValue + t2.fDeltaValue;
            t2.fDeltaValue = d2;
            t2.fWholeValue += d2;
        }
    }
}