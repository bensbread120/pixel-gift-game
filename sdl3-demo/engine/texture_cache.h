#pragma once
#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include <vector>
#include <string>

namespace engine {

// The assets folder, ending in a slash. By default it's assets/ next to the
// executable (the build copies it there), not the current working directory,
// so the game finds its files however it's launched. Set it before loading
// anything to point at another folder (the game's --assets flag).
inline std::string& assetDir()
{
	static std::string dir;
	if (dir.empty())
	{
		const char* base = SDL_GetBasePath();
		dir = std::string(base ? base : "") + "assets/";
	}
	return dir;
}

// A file inside the assets folder, e.g. assetPath("maps/village.txt").
inline std::string assetPath(const std::string& relative) { return assetDir() + relative; }

// Generic texture loading + cleanup. Nothing in here knows about
// idle/run/enemy/bullet -- that vocabulary is specific to each game's
// Resources struct, which should hold one of these instead of duplicating
// loadTexture()/unload().
class TextureCache
{
	std::vector<SDL_Texture*> textures;

public:
	// `filepath` is relative to the assets folder (see assetDir()).
	SDL_Texture* load(SDL_Renderer* renderer, const std::string& filepath,
	                   SDL_ScaleMode scaleMode = SDL_SCALEMODE_NEAREST)
	{
		std::string fullPath = assetPath(filepath);

		SDL_Log("Loading texture: %s", fullPath.c_str());
		SDL_Texture* tex = IMG_LoadTexture(renderer, fullPath.c_str());
		if (!tex)
		{
			SDL_Log("FAILED: %s", SDL_GetError());
			return nullptr;
		}
		SDL_SetTextureScaleMode(tex, scaleMode);
		textures.push_back(tex);
		return tex;
	}

	void unload()
	{
		for (SDL_Texture* tex : textures)
			SDL_DestroyTexture(tex);
		textures.clear();
	}

	~TextureCache() { unload(); }
};

} // namespace engine
