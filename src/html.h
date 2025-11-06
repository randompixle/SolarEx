#pragma once
#include "re_sdl.h"
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RE_MAX_ELEMENTS 512
#define RE_URL_MAX 1024

typedef enum { RE_E_TEXT, RE_E_IMG } ReElementType;

typedef struct {
  int h1, bold, italic;
  SDL_Color color;
} ReStyle;

typedef struct {
  ReElementType type;
  char text[1024];
  ReStyle style;
  char src[RE_URL_MAX];
  int img_w, img_h;
  SDL_Texture* tex;
} ReElement;

typedef struct {
  ReElement elems[RE_MAX_ELEMENTS];
  size_t count;
} ReDocument;

void re_parse_html(const char* html, ReDocument* out);

#ifdef __cplusplus
}
#endif
