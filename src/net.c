#include "net.h"
#include <stdlib.h>
#include <string.h>

#if defined(RE_HAVE_CURL)
#include <curl/curl.h>

static size_t write_cb(void* ptr, size_t size, size_t nmemb, void* userdata) {
  size_t add = size * nmemb;
  ReBuffer* b = (ReBuffer*)userdata;
  unsigned char* nd = (unsigned char*)realloc(b->data, b->size + add + 1);
  if (!nd) return 0;
  b->data = nd;
  memcpy(b->data + b->size, ptr, add);
  b->size += add;
  b->data[b->size] = 0;
  return add;
}

int re_http_get(const char* url, ReBuffer* out) {
  memset(out, 0, sizeof(*out));
  CURL* c = curl_easy_init();
  if (!c) return -1;
  curl_easy_setopt(c, CURLOPT_URL, url);
  curl_easy_setopt(c, CURLOPT_FOLLOWLOCATION, 1L);
  curl_easy_setopt(c, CURLOPT_USERAGENT, "ReExploreXP/0.5");
  curl_easy_setopt(c, CURLOPT_WRITEFUNCTION, write_cb);
  curl_easy_setopt(c, CURLOPT_WRITEDATA, out);
  curl_easy_setopt(c, CURLOPT_SSL_VERIFYPEER, 0L);
  curl_easy_setopt(c, CURLOPT_SSL_VERIFYHOST, 0L);
  CURLcode rc = curl_easy_perform(c);
  curl_easy_cleanup(c);
  return (rc == CURLE_OK) ? 0 : -2;
}
#else
#include <stdio.h>

int re_http_get(const char* url, ReBuffer* out) {
  (void)url;
  memset(out, 0, sizeof(*out));
  fprintf(stderr, "ReExploreXP built without libcurl; network requests disabled.\n");
  return -1;
}
#endif

void re_buffer_free(ReBuffer* b) { if (b && b->data) free(b->data); if (b) b->data=NULL,b->size=0; }

unsigned char* re_image_decode_rgba(const unsigned char* bytes, int len, int* out_w, int* out_h) {
  (void)bytes;
  (void)len;
  if (out_w) *out_w = 1;
  if (out_h) *out_h = 1;
  unsigned char* px = (unsigned char*)malloc(4);
  if (!px) return NULL;
  px[0] = 200;
  px[1] = 200;
  px[2] = 200;
  px[3] = 255;
  return px;
}
