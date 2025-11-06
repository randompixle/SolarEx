#pragma once

#include "re_sdl.h"

typedef struct {
  void* tt_data;
  int pixel_size;
  int tt_size;
  float scale;
  int ascent;
  int descent;
  int line_gap;
  int loaded;
} ReFont;

int re_font_load(ReFont* f, const char* ttf_path, int pixel_size);
void re_font_free(ReFont* f);
void re_font_measure(ReFont* f, const char* text, int* out_w, int* out_h);
SDL_Texture* re_font_render(SDL_Renderer* renderer, ReFont* f, const char* text, SDL_Color color);
