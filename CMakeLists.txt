# Top-level CMake project file: dependencies and global configuration.
#
# 3.24 is the first version where FetchContent supports FIND_PACKAGE_ARGS,
# which the dependency setup below relies on.
cmake_minimum_required (VERSION 3.24)

# Enable Hot Reload for MSVC compilers if supported.
if (POLICY CMP0141)
  cmake_policy(SET CMP0141 NEW)
  set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "$<IF:$<AND:$<C_COMPILER_ID:MSVC>,$<CXX_COMPILER_ID:MSVC>>,$<$<CONFIG:Debug,RelWithDebInfo>:EditAndContinue>,$<$<CONFIG:Debug,RelWithDebInfo>:ProgramDatabase>>")
endif()

project ("sdl3-demo")

# A Debug WebAssembly build is big and slow (the per-frame A* noticeably so),
# so the web build defaults to Release. Single-config generators only.
if (EMSCRIPTEN AND NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# --- Dependencies -----------------------------------------------------------
#
# Each library is declared with FIND_PACKAGE_ARGS, which means:
#   1. CMake first tries find_package() -- so a copy you've installed yourself
#      (pointed at via CMAKE_PREFIX_PATH, or a distro package on Linux) is used
#      as-is. This keeps native rebuilds fast.
#   2. If that fails, the pinned source archive below is downloaded into the
#      build directory and built as part of this project.
#
# The web build always takes path 2, so it never depends on system packages.
# Pass -DFETCHCONTENT_TRY_FIND_PACKAGE_MODE=NEVER to always download natively too.
include(FetchContent)

if (EMSCRIPTEN)
  set(FETCHCONTENT_TRY_FIND_PACKAGE_MODE NEVER CACHE STRING "" FORCE)
  # WebAssembly has no shared libraries: link everything statically.
  set(SDL_SHARED OFF CACHE BOOL "" FORCE)
  set(SDL_STATIC ON CACHE BOOL "" FORCE)
  set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE) # SDL_image reads this
else()
  # Build SDL as shared libraries (SDL3.dll / libSDL3.so), matching the
  # prebuilt packages.
  set(SDL_SHARED ON CACHE BOOL "" FORCE)
  set(SDL_STATIC OFF CACHE BOOL "" FORCE)
endif()
set(SDL_TEST_LIBRARY OFF CACHE BOOL "" FORCE)

# SDL_image can load many formats. Every asset is a PNG, which SDL_image
# decodes with its built-in stb_image backend, so turn everything else off:
# no external libraries, and a smaller wasm.
set(SDLIMAGE_VENDORED OFF CACHE BOOL "" FORCE)
set(SDLIMAGE_BACKEND_STB ON CACHE BOOL "" FORCE)
set(SDLIMAGE_PNG ON CACHE BOOL "" FORCE)
set(SDLIMAGE_PNG_LIBPNG OFF CACHE BOOL "" FORCE)
set(SDLIMAGE_PNG_SAVE OFF CACHE BOOL "" FORCE)
foreach(fmt ANI AVIF BMP GIF JPG JXL LBM PCX PNM QOI SVG TGA TIF WEBP XCF XPM XV)
  set(SDLIMAGE_${fmt} OFF CACHE BOOL "" FORCE)
endforeach()
set(SDLIMAGE_SAMPLES OFF CACHE BOOL "" FORCE)
set(SDLIMAGE_INSTALL OFF CACHE BOOL "" FORCE)

# glm is header-only; skip building its optional compiled library.
set(GLM_BUILD_LIBRARY OFF CACHE BOOL "" FORCE)
set(GLM_BUILD_INSTALL OFF CACHE BOOL "" FORCE)

FetchContent_Declare(SDL3
  URL https://github.com/libsdl-org/SDL/releases/download/release-3.4.14/SDL3-3.4.14.tar.gz
  FIND_PACKAGE_ARGS
)
FetchContent_Declare(SDL3_image
  URL https://github.com/libsdl-org/SDL_image/releases/download/release-3.4.4/SDL3_image-3.4.4.tar.gz
  FIND_PACKAGE_ARGS
)
FetchContent_Declare(glm
  URL https://github.com/g-truc/glm/archive/refs/tags/1.0.3.tar.gz
  FIND_PACKAGE_ARGS
)
# Order matters: SDL3_image needs SDL3 to already be available.
FetchContent_MakeAvailable(SDL3 SDL3_image glm)

# Include sub-projects.
add_subdirectory ("sdl3-demo")
