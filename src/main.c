#include "re_sdl.h"
#include <string.h>
#include <stdlib.h>
#include "render.h"
#include "html.h"
#include "net.h"

static void hydrate_images(SDL_Renderer* r, ReDocument* d) {
  for (size_t i=0;i<d->count;i++) {
    ReElement* el = &d->elems[i];
    if (el->type != RE_E_IMG) continue;
    ReBuffer b = {0};
    if (re_http_get(el->src, &b) == 0 && b.size > 0) {
      int w=0,h=0; unsigned char* rgba = re_image_decode_rgba(b.data, (int)b.size, &w, &h);
      if (rgba && w>0 && h>0) {
        SDL_Surface* surf = SDL_CreateRGBSurfaceFrom(rgba, w, h, 32, w*4, 0x000000FF,0x0000FF00,0x00FF0000,0xFF000000);
        if (surf) {
          el->tex = SDL_CreateTextureFromSurface(r, surf);
          el->img_w = w; el->img_h = h;
          SDL_FreeSurface(surf);
        }
        free(rgba);
      }
    }
    re_buffer_free(&b);
  }
}

static void load_page(SDL_Renderer* r, const char* url, ReDocument* doc) {
  ReBuffer b = {0};
  int rc = re_http_get(url, &b);
  if (rc == 0 && b.size > 0) {
    re_parse_html((const char*)b.data, doc);
    hydrate_images(r, doc);
  } else {
    memset(doc, 0, sizeof(*doc));
    ReElement* e = &doc->elems[doc->count++];
    e->type = RE_E_TEXT; strcpy(e->text, "Failed to load URL.");
  }
  re_buffer_free(&b);
}

int main(int argc, char** argv) {
  if (SDL_Init(SDL_INIT_VIDEO) < 0) return -1;
  SDL_Window* win = SDL_CreateWindow("ReExplore XP", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, 1100, 780, SDL_WINDOW_SHOWN);
  SDL_Renderer* ren = SDL_CreateRenderer(win, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
  SDL_StartTextInput();

  ReUI ui; reui_init(&ui);
  if (argc > 1) { strncpy(ui.url, argv[1], sizeof(ui.url)-1); }
  ReDocument doc; memset(&doc, 0, sizeof(doc));
  load_page(ren, ui.url, &doc);

  int running=1;
  while (running) {
    SDL_Event e;
    int need=0;
    while (SDL_PollEvent(&e)) {
      if (e.type==SDL_QUIT) running=0;
      need |= reui_handle_event(&ui, &e);
    }
    if (ui.want_go) { ui.want_go=0; load_page(ren, ui.url, &doc); need=1; }
    SDL_SetRenderDrawColor(ren, 0,120,215,255);
    SDL_RenderClear(ren);
    reui_draw(ren, &ui, &doc);
    SDL_RenderPresent(ren);
  }

  reui_shutdown(&ui);
  SDL_DestroyRenderer(ren);
  SDL_DestroyWindow(win);
  SDL_Quit();
  return 0;
}
