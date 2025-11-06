#include "font.h"

#include <stdlib.h>
#include <string.h>

static int glyph_width(const ReFont* f) {
  int base = f && f->pixel_size > 0 ? f->pixel_size : 16;
  int w = (base * 3) / 5;
  if (w < 3) w = 3;
  return w;
}

static int line_height(const ReFont* f) {
  int base = f && f->pixel_size > 0 ? f->pixel_size : 16;
  return base + base / 4;
}

int re_font_load(ReFont* f, const char* ttf_path, int pixel_size) {
  if (!f) return -1;
  memset(f, 0, sizeof(*f));
  f->pixel_size = pixel_size > 0 ? pixel_size : 16;
  f->scale = 1.0f;
  f->ascent = f->pixel_size;
  f->descent = f->pixel_size / 4;
  f->line_gap = f->pixel_size / 6;
  f->loaded = 1;
  (void)ttf_path;
  return 0;
}

void re_font_free(ReFont* f) {
  if (!f) return;
  memset(f, 0, sizeof(*f));
}

void re_font_measure(ReFont* f, const char* text, int* out_w, int* out_h) {
  int width = 0;
  int max_width = 0;
  int height = line_height(f);
  if (!f || !f->loaded || !text || !*text) {
    if (out_w) *out_w = 0;
    if (out_h) *out_h = 0;
    return;
  }

  int gw = glyph_width(f) + 1;
  const unsigned char* p = (const unsigned char*)text;
  while (*p) {
    if (*p == '\n') {
      if (width > max_width) max_width = width;
      width = 0;
      height += line_height(f);
      ++p;
      continue;
    }
    width += gw;
    ++p;
  }
  if (width > max_width) max_width = width;
  if (max_width <= 0) max_width = glyph_width(f);
  if (height <= 0) height = line_height(f);
  if (out_w) *out_w = max_width;
  if (out_h) *out_h = height;
}

SDL_Texture* re_font_render(SDL_Renderer* renderer, ReFont* f, const char* text, SDL_Color color) {
  if (!renderer || !f || !f->loaded || !text || !*text) return NULL;
  int width = 0, height = 0;
  re_font_measure(f, text, &width, &height);
  if (width <= 0 || height <= 0) return NULL;

  int gw = glyph_width(f);
  int gh = f->pixel_size > 0 ? f->pixel_size : 16;
  int lh = line_height(f);
  int pitch = width * 4;
  size_t buf_size = (size_t)pitch * (size_t)height;
  unsigned char* pixels = (unsigned char*)calloc(1, buf_size);
  if (!pixels) return NULL;

  int pen_x = 0;
  int pen_y = 0;
  const unsigned char* p = (const unsigned char*)text;
  while (*p) {
    if (*p == '\n') {
      pen_x = 0;
      pen_y += lh;
      ++p;
      continue;
    }
    if (*p != ' ') {
      for (int row = 0; row < gh && pen_y + row < height; ++row) {
        for (int col = 0; col < gw && pen_x + col < width; ++col) {
          size_t idx = (size_t)(pen_y + row) * (size_t)pitch + (size_t)(pen_x + col) * 4u;
          pixels[idx + 0] = color.r;
          pixels[idx + 1] = color.g;
          pixels[idx + 2] = color.b;
          pixels[idx + 3] = color.a;
        }
      }
    }
    pen_x += gw + 1;
    if (pen_x + gw >= width) {
      pen_x = 0;
      pen_y += lh;
    }
    ++p;
  }

  SDL_Surface* surface = SDL_CreateRGBSurfaceFrom(pixels, width, height, 32, pitch,
                                                  0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000);
  if (!surface) {
    free(pixels);
    return NULL;
  }
  SDL_Texture* tex = SDL_CreateTextureFromSurface(renderer, surface);
  SDL_FreeSurface(surface);
  free(pixels);
  return tex;
}
