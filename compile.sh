#!/bin/sh
set -e

require_native_toolchain() {
  if ! command -v cmake >/dev/null 2>&1; then
    echo "CMake is required but not found in PATH." >&2
    exit 1
  fi
}

pm_command() {
  PM="$1"
  case "$PM" in
    apt)
      echo "apt-get update && apt-get install -y build-essential cmake pkg-config libsdl2-dev libcurl4-openssl-dev"
      ;;
    dnf)
      echo "dnf install -y gcc gcc-c++ make cmake pkg-config SDL2-devel libcurl-devel"
      ;;
    microdnf)
      echo "microdnf install -y gcc gcc-c++ make cmake pkg-config SDL2-devel libcurl-devel"
      ;;
    yum)
      echo "yum install -y gcc gcc-c++ make cmake pkg-config SDL2-devel libcurl-devel"
      ;;
    pacman)
      echo "pacman -Sy --noconfirm base-devel cmake pkgconf sdl2 curl"
      ;;
    zypper)
      echo "zypper install -y gcc make cmake pkg-config libSDL2-devel libcurl-devel"
      ;;
    xbps-install)
      echo "xbps-install -Sy base-devel cmake pkg-config SDL2-devel libcurl-devel"
      ;;
    apk)
      echo "apk add --no-cache build-base cmake pkgconf sdl2-dev curl-dev"
      ;;
    emerge)
      echo "emerge --ask=n sys-devel/gcc sys-devel/make dev-util/cmake virtual/pkgconfig media-libs/libsdl2 net-misc/curl"
      ;;
    brew)
      echo "brew update && brew install cmake pkg-config sdl2 curl"
      ;;
    *)
      echo ""
      ;;
  esac
}

choose_package_manager() {
  [ -n "$REEXPLORE_SKIP_INSTALL" ] && return
  [ -n "$REEXPLORE_INSTALL_CMD" ] && return

  for PM in rpm-ostree apt-get apt dnf microdnf yum pacman zypper xbps-install apk emerge brew; do
    if command -v "$PM" >/dev/null 2>&1; then
      REEXPLORE_DETECTED_PM="$PM"
      return
    fi
  done

  REEXPLORE_DETECTED_PM=""
}

maybe_install_dependencies() {
  [ -n "$REEXPLORE_SKIP_INSTALL" ] && return

  if [ -n "$REEXPLORE_INSTALL_CMD" ]; then
    INSTALL_CMD="$REEXPLORE_INSTALL_CMD"
  else
    choose_package_manager
    PM="$REEXPLORE_DETECTED_PM"

    case "$PM" in
      rpm-ostree)
        echo "Automatic dependency installation via rpm-ostree is not supported because it requires a host reboot." >&2
        echo "Please install gcc, make, cmake, pkg-config, SDL2 development headers, and libcurl development headers manually." >&2
        return
        ;;
      apt-get)
        PM="apt"
        ;;
    esac

    INSTALL_CMD=$(pm_command "$PM")
    if [ -z "$INSTALL_CMD" ]; then
      echo "No supported package manager detected for automatic dependency installation." >&2
      echo "Please ensure build tools, SDL2 development headers, and libcurl development headers are installed." >&2
      return
    fi
  fi

  if [ -z "$INSTALL_CMD" ]; then
    return
  fi

  if [ "$(id -u)" -ne 0 ] && [ "${INSTALL_CMD#brew}" = "$INSTALL_CMD" ]; then
    if command -v sudo >/dev/null 2>&1; then
      INSTALL_CMD="sudo sh -c '$INSTALL_CMD'"
    else
      echo "Administrator privileges are required to install packages." >&2
      return
    fi
  fi

  echo "Attempting to install build dependencies..."
  set +e
  sh -c "$INSTALL_CMD"
  STATUS=$?
  set -e
  if [ $STATUS -ne 0 ]; then
    echo "Warning: automatic dependency installation failed (exit code $STATUS)." >&2
    echo "Please install build tools, SDL2 development headers, and libcurl development headers manually." >&2
  fi
}

verify_dependencies() {
  if ! command -v pkg-config >/dev/null 2>&1; then
    echo "pkg-config is required to locate SDL2 and libcurl development packages." >&2
    exit 2
  fi

  if ! pkg-config --exists sdl2; then
    echo "SDL2 development files were not found. Please install libsdl2-dev / SDL2-devel." >&2
    exit 2
  fi

  if ! pkg-config --exists libcurl; then
    echo "libcurl development files were not found. Please install libcurl-dev / libcurl-devel." >&2
    exit 2
  fi
}

require_native_toolchain
maybe_install_dependencies

ALLOW_STUB="${REEXPLORE_ALLOW_STUB:-0}"
if [ "$ALLOW_STUB" != "1" ]; then
  verify_dependencies
fi

BUILD_DIR="${REEXPLORE_BUILD_DIR:-build}"
rm -rf "$BUILD_DIR"
if [ "$ALLOW_STUB" = "1" ]; then
  cmake -S . -B "$BUILD_DIR"
else
  cmake -S . -B "$BUILD_DIR" -DRE_REQUIRE_NATIVE=ON
fi
PARALLEL="$(command -v nproc >/dev/null 2>&1 && nproc || sysctl -n hw.ncpu 2>/dev/null || echo 4)"
cmake --build "$BUILD_DIR" --parallel "$PARALLEL"
