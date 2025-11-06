cmake_minimum_required(VERSION 3.10)
project(ReExploreXP C)
set(CMAKE_C_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include_directories(${CMAKE_SOURCE_DIR}/src)
include_directories(${CMAKE_SOURCE_DIR}/third_party)

find_package(PkgConfig QUIET)
if (PkgConfig_FOUND)
  pkg_check_modules(SDL2 QUIET sdl2)
  pkg_check_modules(CURL QUIET libcurl)
endif()

if (SDL2_FOUND)
  include_directories(${SDL2_INCLUDE_DIRS})
  link_directories(${SDL2_LIBRARY_DIRS})
else()
  message(WARNING "pkg-config SDL2 not found; using stub implementation")
endif()

if (CURL_FOUND)
  include_directories(${CURL_INCLUDE_DIRS})
  link_directories(${CURL_LIBRARY_DIRS})
else()
  message(WARNING "pkg-config curl not found; using fallback")
endif()

add_executable(ReExploreXP
        src/main.c
        src/render.c
        src/html.c
        src/net.c
        src/font.c
)

if (NOT SDL2_FOUND)
  target_sources(ReExploreXP PRIVATE src/sdl_stub.c)
endif()

if (SDL2_FOUND)
  target_link_libraries(ReExploreXP ${SDL2_LIBRARIES})
endif()

if (CURL_FOUND)
  target_link_libraries(ReExploreXP ${CURL_LIBRARIES})
  target_compile_definitions(ReExploreXP PRIVATE RE_HAVE_CURL=1)
endif()
