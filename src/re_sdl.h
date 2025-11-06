#pragma once

#if defined(__has_include)
#  if __has_include(<SDL2/SDL.h>)
#    include <SDL2/SDL.h>
#    define RE_SDL_HAS_REAL 1
#  endif
#endif

#ifndef RE_SDL_HAS_REAL
#  include "sdl_stub.h"
#endif
