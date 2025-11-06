#pragma once
#include "re_sdl.h"
#include "html.h"
#include "net.h"
#include "font.h"

typedef struct {
  char url[1024];
  int want_go;
  int scroll;
  int content_w, content_h;
  ReFont font, font_h1;
} ReUI;

void reui_init(ReUI* ui);
void reui_shutdown(ReUI* ui);
int reui_handle_event(ReUI* ui, SDL_Event* e);
void reui_draw(SDL_Renderer* r, ReUI* ui, ReDocument* doc);
