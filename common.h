#pragma once

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