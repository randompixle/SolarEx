#include "sdl_stub.h"

#include <stdlib.h>
#include <string.h>

int SDL_Init(Uint32 flags) {
  (void)flags;
  return 0;
}

SDL_Window* SDL_CreateWindow(const char* title, int x, int y, int w, int h, Uint32 flags) {
  (void)title;
  (void)x;
  (void)y;
  (void)flags;
  SDL_Window* win = (SDL_Window*)calloc(1, sizeof(SDL_Window));
  if (!win) return NULL;
  win->width = w > 0 ? w : 800;
  win->height = h > 0 ? h : 600;
  return win;
}

SDL_Renderer* SDL_CreateRenderer(SDL_Window* window, int index, Uint32 flags) {
  (void)index;
  (void)flags;
  SDL_Renderer* ren = (SDL_Renderer*)calloc(1, sizeof(SDL_Renderer));
  if (!ren) return NULL;
  ren->window = window;
  ren->width = window ? window->width : 800;
  ren->height = window ? window->height : 600;
  ren->draw_r = ren->draw_g = ren->draw_b = ren->draw_a = 0;
  return ren;
}

void SDL_DestroyRenderer(SDL_Renderer* renderer) {
  free(renderer);
}

void SDL_DestroyWindow(SDL_Window* window) {
  free(window);
}

void SDL_StartTextInput(void) {}

void SDL_Quit(void) {}

int SDL_PollEvent(SDL_Event* event) {
  static int emitted = 0;
  if (!event) return 0;
  if (!emitted) {
    emitted = 1;
    memset(event, 0, sizeof(*event));
    event->type = SDL_QUIT;
    return 1;
  }
  return 0;
}

int SDL_SetRenderDrawColor(SDL_Renderer* renderer, Uint8 r, Uint8 g, Uint8 b, Uint8 a) {
  if (!renderer) return -1;
  renderer->draw_r = r;
  renderer->draw_g = g;
  renderer->draw_b = b;
  renderer->draw_a = a;
  return 0;
}

int SDL_RenderFillRect(SDL_Renderer* renderer, const SDL_Rect* rect) {
  (void)renderer;
  (void)rect;
  return 0;
}

int SDL_RenderCopy(SDL_Renderer* renderer, SDL_Texture* texture, const SDL_Rect* src, const SDL_Rect* dst) {
  (void)renderer;
  (void)texture;
  (void)src;
  (void)dst;
  return 0;
}

int SDL_RenderSetClipRect(SDL_Renderer* renderer, const SDL_Rect* rect) {
  (void)renderer;
  (void)rect;
  return 0;
}

int SDL_RenderClear(SDL_Renderer* renderer) {
  (void)renderer;
  return 0;
}

void SDL_RenderPresent(SDL_Renderer* renderer) {
  (void)renderer;
}

SDL_Surface* SDL_CreateRGBSurfaceFrom(void* pixels, int width, int height, int depth, int pitch,
                                      Uint32 rmask, Uint32 gmask, Uint32 bmask, Uint32 amask) {
  (void)depth;
  (void)rmask;
  (void)gmask;
  (void)bmask;
  (void)amask;
  SDL_Surface* surf = (SDL_Surface*)calloc(1, sizeof(SDL_Surface));
  if (!surf) return NULL;
  surf->pixels = pixels;
  surf->width = width;
  surf->height = height;
  surf->pitch = pitch;
  return surf;
}

void SDL_FreeSurface(SDL_Surface* surface) {
  free(surface);
}

SDL_Texture* SDL_CreateTextureFromSurface(SDL_Renderer* renderer, SDL_Surface* surface) {
  (void)renderer;
  if (!surface) return NULL;
  SDL_Texture* tex = (SDL_Texture*)calloc(1, sizeof(SDL_Texture));
  if (!tex) return NULL;
  tex->width = surface->width;
  tex->height = surface->height;
  size_t size = 0;
  if (surface->height > 0 && surface->pitch > 0) {
    size = (size_t)surface->height * (size_t)surface->pitch;
  }
  if (size > 0 && surface->pixels) {
    tex->pixels = (Uint8*)malloc(size);
    if (tex->pixels) {
      memcpy(tex->pixels, surface->pixels, size);
    }
  }
  return tex;
}

void SDL_DestroyTexture(SDL_Texture* texture) {
  if (!texture) return;
  free(texture->pixels);
  free(texture);
}

int SDL_GetRendererOutputSize(SDL_Renderer* renderer, int* w, int* h) {
  if (!renderer) return -1;
  if (w) *w = renderer->width > 0 ? renderer->width : 800;
  if (h) *h = renderer->height > 0 ? renderer->height : 600;
  return 0;
}
