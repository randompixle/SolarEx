#!/bin/sh
set -e

maybe_install_dependencies() {
  [ -n "$REEXPLORE_SKIP_INSTALL" ] && return

  PM=""
  BASE_PACKAGES=""
  SDL_PACKAGES=""
  CURL_PACKAGES=""

  if command -v apt-get >/dev/null 2>&1; then
    PM="apt"
    BASE_PACKAGES="build-essential cmake pkg-config"
    SDL_PACKAGES="libsdl2-dev"
    CURL_PACKAGES="libcurl4-openssl-dev"
  elif command -v dnf >/dev/null 2>&1; then
    PM="dnf"
    BASE_PACKAGES="cmake pkg-config"
    SDL_PACKAGES="SDL2-devel"
    CURL_PACKAGES="libcurl-devel"
  elif command -v pacman >/dev/null 2>&1; then
    PM="pacman"
    BASE_PACKAGES="base-devel cmake pkgconf"
    SDL_PACKAGES="sdl2"
    CURL_PACKAGES="curl"
  else
    echo "No supported package manager found for automatic dependency installation." >&2
    PM=""
  fi

  [ -z "$PM" ] && return

  NEED_BASE=0
  NEED_SDL=0
  NEED_CURL=0

  if command -v pkg-config >/dev/null 2>&1; then
    if ! pkg-config --exists sdl2 >/dev/null 2>&1; then
      NEED_SDL=1
    fi
    if ! pkg-config --exists libcurl >/dev/null 2>&1; then
      NEED_CURL=1
    fi
  else
    NEED_BASE=1
    NEED_SDL=1
    NEED_CURL=1
  fi

  if [ $NEED_SDL -eq 1 ] || [ $NEED_CURL -eq 1 ]; then
    NEED_BASE=1
  fi

  if [ $NEED_BASE -eq 0 ] && [ $NEED_SDL -eq 0 ] && [ $NEED_CURL -eq 0 ]; then
    return
  fi

  echo "Attempting to install build dependencies using $PM..."

  case "$PM" in
    apt)
      CMD="apt-get update && apt-get install -y"
      [ $NEED_BASE -eq 1 ] && CMD="$CMD $BASE_PACKAGES"
      [ $NEED_SDL -eq 1 ] && CMD="$CMD $SDL_PACKAGES"
      [ $NEED_CURL -eq 1 ] && CMD="$CMD $CURL_PACKAGES"
      ;;
    dnf)
      CMD="dnf install -y"
      [ $NEED_BASE -eq 1 ] && CMD="$CMD $BASE_PACKAGES"
      [ $NEED_SDL -eq 1 ] && CMD="$CMD $SDL_PACKAGES"
      [ $NEED_CURL -eq 1 ] && CMD="$CMD $CURL_PACKAGES"
      ;;
    pacman)
      CMD="pacman -Sy --noconfirm"
      [ $NEED_BASE -eq 1 ] && CMD="$CMD $BASE_PACKAGES"
      [ $NEED_SDL -eq 1 ] && CMD="$CMD $SDL_PACKAGES"
      [ $NEED_CURL -eq 1 ] && CMD="$CMD $CURL_PACKAGES"
      ;;
  esac

  if [ -z "$CMD" ]; then
    return
  fi

  if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
      CMD="sudo sh -c '$CMD'"
    else
      echo "Administrator privileges are required to install packages." >&2
      return
    fi
  fi

  set +e
  sh -c "$CMD"
  STATUS=$?
  set -e
  if [ $STATUS -ne 0 ]; then
    echo "Warning: automatic dependency installation failed (exit code $STATUS). Please install packages manually if necessary." >&2
  fi
}

maybe_install_dependencies

BUILD_DIR="build"
rm -rf "$BUILD_DIR"
mkdir "$BUILD_DIR"
cd "$BUILD_DIR"
cmake ..
cmake --build .
