#pragma once

#include <stdint.h>
#include <stddef.h>

typedef uint32_t Uint32;
typedef uint8_t Uint8;
typedef int32_t Sint32;

typedef struct SDL_Window {
  int width;
  int height;
} SDL_Window;

typedef struct SDL_Renderer {
  SDL_Window* window;
  int width;
  int height;
  Uint8 draw_r, draw_g, draw_b, draw_a;
} SDL_Renderer;

typedef struct SDL_Texture {
  int width;
  int height;
  Uint8* pixels;
} SDL_Texture;

typedef struct SDL_Surface {
  void* pixels;
  int width;
  int height;
  int pitch;
} SDL_Surface;

typedef struct SDL_Color {
  Uint8 r, g, b, a;
} SDL_Color;

typedef struct SDL_Rect {
  int x, y, w, h;
} SDL_Rect;

typedef int SDL_Keycode;

typedef struct SDL_Keysym {
  SDL_Keycode sym;
} SDL_Keysym;

typedef struct SDL_MouseWheelEvent {
  int y;
} SDL_MouseWheelEvent;

typedef struct SDL_TextInputEvent {
  char text[32];
} SDL_TextInputEvent;

typedef struct SDL_KeyboardEvent {
  SDL_Keysym keysym;
} SDL_KeyboardEvent;

typedef struct SDL_Event {
  Uint32 type;
  union {
    SDL_MouseWheelEvent wheel;
    SDL_TextInputEvent text;
    SDL_KeyboardEvent key;
  };
} SDL_Event;

#define SDL_INIT_VIDEO 0x00000020u
#define SDL_WINDOWPOS_CENTERED 0
#define SDL_WINDOW_SHOWN 0x00000004u
#define SDL_RENDERER_ACCELERATED 0x00000002u
#define SDL_RENDERER_PRESENTVSYNC 0x00000004u

#define SDL_QUIT 0x100
#define SDL_MOUSEWHEEL 0x207
#define SDL_TEXTINPUT 0x302
#define SDL_KEYDOWN 0x300

#define SDLK_BACKSPACE 8
#define SDLK_RETURN 13

int SDL_Init(Uint32 flags);
SDL_Window* SDL_CreateWindow(const char* title, int x, int y, int w, int h, Uint32 flags);
SDL_Renderer* SDL_CreateRenderer(SDL_Window* window, int index, Uint32 flags);
void SDL_DestroyRenderer(SDL_Renderer* renderer);
void SDL_DestroyWindow(SDL_Window* window);
void SDL_StartTextInput(void);
void SDL_Quit(void);
int SDL_PollEvent(SDL_Event* event);
int SDL_SetRenderDrawColor(SDL_Renderer* renderer, Uint8 r, Uint8 g, Uint8 b, Uint8 a);
int SDL_RenderFillRect(SDL_Renderer* renderer, const SDL_Rect* rect);
int SDL_RenderCopy(SDL_Renderer* renderer, SDL_Texture* texture, const SDL_Rect* src, const SDL_Rect* dst);
int SDL_RenderSetClipRect(SDL_Renderer* renderer, const SDL_Rect* rect);
int SDL_RenderClear(SDL_Renderer* renderer);
void SDL_RenderPresent(SDL_Renderer* renderer);
SDL_Surface* SDL_CreateRGBSurfaceFrom(void* pixels, int width, int height, int depth, int pitch,
                                      Uint32 rmask, Uint32 gmask, Uint32 bmask, Uint32 amask);
void SDL_FreeSurface(SDL_Surface* surface);
SDL_Texture* SDL_CreateTextureFromSurface(SDL_Renderer* renderer, SDL_Surface* surface);
void SDL_DestroyTexture(SDL_Texture* texture);
int SDL_GetRendererOutputSize(SDL_Renderer* renderer, int* w, int* h);

