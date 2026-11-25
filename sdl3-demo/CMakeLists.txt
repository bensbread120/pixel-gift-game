# CMake project for the game executable.
#
# SDL3, SDL3_image and glm are made available by the top-level CMakeLists.txt.

add_executable (sdl3-demo "sdl3-demo.cpp" "story.h" "world.h" "ui.h" "input.h" "art_gen.h" "engine/sdl_app.h" "engine/texture_cache.h")

set_target_properties(sdl3-demo PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
)

target_link_libraries(sdl3-demo PRIVATE SDL3::SDL3 SDL3_image::SDL3_image glm::glm)

if (EMSCRIPTEN)
  # Produces index.html + index.js + index.wasm + index.data in the build dir,
  # ready to serve as a static site.
  set(SHELL_FILE ${PROJECT_SOURCE_DIR}/web/shell.html)
  set_target_properties(sdl3-demo PROPERTIES
    OUTPUT_NAME "index"
    SUFFIX ".html"
    # relink when the shell or any asset changes, not just the code
    LINK_DEPENDS "${SHELL_FILE}"
  )
  target_link_options(sdl3-demo PRIVATE
    # assets/ lands at /assets in the virtual filesystem. SDL_GetBasePath()
    # is "/" there, so TextureCache's "<base>assets/x.png" resolves the same
    # way it does natively. The .aseprite source art isn't needed at runtime.
    "--preload-file=${PROJECT_SOURCE_DIR}/assets@/assets"
    "--exclude-file=*.aseprite"
    "--shell-file=${SHELL_FILE}"
    "-sALLOW_MEMORY_GROWTH=1"
  )
  # --preload-file doesn't track the files it packs; re-link when any change
  file(GLOB_RECURSE ASSET_FILES CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/assets/*)
  set_property(TARGET sdl3-demo APPEND PROPERTY LINK_DEPENDS ${ASSET_FILES})
  return()
endif()

# Windows has no rpath, so an exe only finds DLLs that sit next to it (or on
# PATH). Copy every DLL the exe links against into its output folder.
if (WIN32)
  add_custom_command(TARGET sdl3-demo POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different $<TARGET_RUNTIME_DLLS:sdl3-demo> $<TARGET_FILE_DIR:sdl3-demo>
    COMMAND_EXPAND_LISTS
  )
endif()

# The game loads textures from an assets/ folder next to the exe. This is a
# separate target, rather than a post-build step, so it reruns on every build
# and picks up asset changes even when no code has changed.
add_custom_target(copy-assets
  COMMAND ${CMAKE_COMMAND} -E copy_directory ${PROJECT_SOURCE_DIR}/assets $<TARGET_FILE_DIR:sdl3-demo>/assets
)
add_dependencies(sdl3-demo copy-assets)
