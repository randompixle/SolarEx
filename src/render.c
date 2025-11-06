#include "render.h"
#include "re_sdl.h"
#include <string.h>
#include <stdio.h>

static SDL_Color COL_TOOLBAR = {0,120,215,255};
static SDL_Color COL_STATUS  = {235,235,235,255};
static SDL_Color COL_WHITE   = {255,255,255,255};
static SDL_Color COL_TEXT    = {20,20,20,255};

static void rect(SDL_Renderer* r, SDL_Rect rc, SDL_Color c){ SDL_SetRenderDrawColor(r,c.r,c.g,c.b,c.a); SDL_RenderFillRect(r,&rc); }

static void draw_text(SDL_Renderer* r, ReFont* f, const char* s, int x, int y, SDL_Color c) {
  SDL_Texture* tex = re_font_render(r, f, s, c);
  if (!tex) return;
  int w,h; re_font_measure(f, s, &w, &h);
  SDL_Rect dst = {x, y, w, h};
  SDL_RenderCopy(r, tex, NULL, &dst);
  SDL_DestroyTexture(tex);
}

void reui_init(ReUI* ui) {
  memset(ui, 0, sizeof(*ui));
  strncpy(ui->url, "http://neverssl.com/", sizeof(ui->url)-1);
  ui->content_w = 940; ui->content_h = 9999;
  re_font_load(&ui->font, "/usr/share/fonts/dejavu/DejaVuSans.ttf", 18);
  re_font_load(&ui->font_h1, "/usr/share/fonts/dejavu/DejaVuSans.ttf", 28);
}

void reui_shutdown(ReUI* ui) {
  re_font_free(&ui->font);
  re_font_free(&ui->font_h1);
}

int reui_handle_event(ReUI* ui, SDL_Event* e) {
  if (e->type == SDL_MOUSEWHEEL) { ui->scroll -= e->wheel.y * 40; if (ui->scroll<0) ui->scroll=0; return 1; }
  if (e->type == SDL_TEXTINPUT)  { size_t n=strlen(ui->url); if (n+strlen(e->text.text)<sizeof(ui->url)-1){ strcat(ui->url, e->text.text); return 1; } }
  if (e->type == SDL_KEYDOWN) {
    if (e->key.keysym.sym == SDLK_BACKSPACE) { size_t n=strlen(ui->url); if(n) ui->url[n-1]=0; return 1; }
    if (e->key.keysym.sym == SDLK_RETURN) { ui->want_go = 1; return 1; }
  }
  return 0;
}

static void layout(SDL_Renderer* r, ReUI* ui, ReDocument* d, int x, int y, int w) {
  int cy = y - ui->scroll; int cx = x; int lh = 0;
  for (size_t i=0;i<d->count;i++) {
    ReElement* el = &d->elems[i];
    if (el->type == RE_E_TEXT) {
      ReFont* f = el->style.h1 ? &ui->font_h1 : &ui->font;
      char buf[1024]; strncpy(buf, el->text, sizeof(buf)-1);
      char* tok = strtok(buf, " ");
      while (tok) {
        char word[1024]; snprintf(word, sizeof(word), "%s ", tok);
        int tw, th; re_font_measure(f, word, &tw, &th);
        if (cx + tw > x + w) { cx = x; cy += lh ? lh : th; lh = 0; }
        draw_text(r, f, word, cx, cy, COL_TEXT);
        if (th > lh) lh = th; cx += tw;
        tok = strtok(NULL, " ");
      }
      if (strchr(el->text, '\n')) { cx = x; cy += lh ? lh : 20; lh = 0; }
    } else if (el->type == RE_E_IMG && el->tex) {
      int iw = el->img_w, ih = el->img_h;
      if (iw > w) { float s = (float)w/(float)iw; iw = w; ih = (int)(ih*s); }
      if (cx != x) { cx = x; cy += lh ? lh : 20; lh = 0; }
      SDL_Rect dst = {x, cy, iw, ih}; SDL_RenderCopy(r, el->tex, NULL, &dst);
      cy += ih + 8;
    }
  }
}

void reui_draw(SDL_Renderer* r, ReUI* ui, ReDocument* doc) {
  int W,H; SDL_GetRendererOutputSize(r,&W,&H);
  SDL_Rect tb = {0,0,W,40}; rect(r, tb, COL_TOOLBAR);
  SDL_Rect url = {120,6,W-180,28}; rect(r, url, COL_WHITE);
  draw_text(r, &ui->font, "ReExplore XP", 8, 9, (SDL_Color){255,255,255,255});
  draw_text(r, &ui->font, ui->url, url.x+6, url.y+4, (SDL_Color){20,20,20,255});
  SDL_Rect content = {20,50,W-40,H-90}; rect(r, content, COL_WHITE);
  SDL_Rect sb = {0,H-32,W,32}; rect(r, sb, COL_STATUS);
  draw_text(r, &ui->font, "Status: Ready", 8, H-28, (SDL_Color){70,70,70,255});
  SDL_RenderSetClipRect(r, &content);
  layout(r, ui, doc, content.x+10, content.y+10, content.w-20);
  SDL_RenderSetClipRect(r, NULL);
}
