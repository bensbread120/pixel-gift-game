#pragma once
// Maps: loading assets/maps/*.txt, choosing tiles, collision, and routes for
// Pet. Maps are made by tools/make_maps.py.
//
// Ground legend                         Object legend (anchor = top-left of footprint)
//   #  wall          W  wall + window     B bed         K bookshelf    p plant
//   .  wood floor    r  rug               S sofa        A table
//   v  stairs down   ^  stairs up         C D G cottages (red, blue, green)
//   e  doormat (exit)                     F fountain    Y big tree     R dragon
//   ,  grass         ;  grass + flowers   M bakery stall               q possum
//   =  path          ~  water             d duck        m picnic mat   k basket
//   H  bridge (E-W)  I  bridge (N-S)      n signpost    L lamp post
//   f  fence         h  hedge             Markers: @ Hero   & Pet   b Partner
//   o  rock          *  flowerbed                  1-7 Pet's spot at each stop
//   l  long grass    w  wildflowers
//   T  tree          (space) nothing, solid
#include <SDL3/SDL.h>
#include <glm/glm.hpp>
#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <queue>
#include <functional>
#include <algorithm>
#include <cstring>
#include <cstdint>
#include <cmath>
#include <iterator>
#include "engine/texture_cache.h"
#include "art_gen.h"

const int TILE = 32;

enum class Dir { Down, Up, Left, Right };

inline glm::vec2 dirVector(Dir d)
{
	switch (d)
	{
		case Dir::Up: return { 0, -1 };
		case Dir::Left: return { -1, 0 };
		case Dir::Right: return { 1, 0 };
		default: return { 0, 1 };
	}
}

inline Dir dirTowards(glm::vec2 v)
{
	if (std::abs(v.x) > std::abs(v.y)) return v.x < 0 ? Dir::Left : Dir::Right;
	return v.y < 0 ? Dir::Up : Dir::Down;
}

// A sprite strip: `frames` equal-width frames side by side.
struct Sprite
{
	SDL_Texture* tex = nullptr;
	int frames = 1;
	float fw = 0, fh = 0; // frame size in game pixels

	void draw(SDL_Renderer* r, float x, float y, int frame, float alpha = 1.0f) const
	{
		if (!tex) return;
		SDL_FRect src{ (frame % frames) * fw, 0, fw, fh };
		SDL_FRect dst{ SDL_roundf(x), SDL_roundf(y), fw, fh };
		if (alpha < 1.0f) SDL_SetTextureAlphaModFloat(tex, alpha);
		SDL_RenderTexture(r, tex, &src, &dst);
		if (alpha < 1.0f) SDL_SetTextureAlphaModFloat(tex, 1.0f);
	}
};

class SpriteBank
{
	std::unordered_map<std::string, Sprite> sprites;
	Sprite missing;

public:
	SDL_Texture* tiles = nullptr;

	void load(SDL_Renderer* r, engine::TextureCache& cache)
	{
		tiles = cache.load(r, "tiles.png");
		for (const art::SpriteDef& def : art::SPRITES)
		{
			Sprite s;
			s.tex = cache.load(r, std::string("sprites/") + def.name + ".png");
			s.frames = def.frames;
			if (s.tex)
			{
				s.fw = static_cast<float>(s.tex->w / def.frames);
				s.fh = static_cast<float>(s.tex->h);
			}
			sprites[def.name] = s;
		}
	}

	const Sprite& get(const std::string& name) const
	{
		auto it = sprites.find(name);
		return it == sprites.end() ? missing : it->second;
	}
};

struct PropDef
{
	char ch;
	const char* sprite;
	int fw, fh;        // footprint in tiles
	bool solid;
	bool flat;         // drawn flat on the ground, under characters
	float frameTime;   // seconds per frame for animated props (0 = still)
	float shadow;      // drop shadow width, as a fraction of the footprint width (0 = none)
};

inline const PropDef PROP_DEFS[] = {
	{ 'B', "bed", 1, 2, true, false, 0, 0.95f },
	{ 'K', "bookshelf", 1, 1, true, false, 0, 1.0f },
	{ 'p', "plant", 1, 1, true, false, 0, 0.8f },
	{ 'S', "sofa", 2, 1, true, false, 0, 1.0f },
	{ 'A', "table", 2, 1, true, false, 0, 0.95f },
	{ 'C', "cottage_red", 3, 2, true, false, 0, 1.08f },
	{ 'D', "cottage_blue", 3, 2, true, false, 0, 1.08f },
	{ 'G', "cottage_green", 3, 2, true, false, 0, 1.08f },
	{ 'F', "fountain", 3, 2, true, false, 0.35f, 1.0f },
	{ 'Y', "bigtree", 2, 1, true, false, 0, 1.7f },
	{ 'R', "dragon", 4, 2, true, false, 1.1f, 1.0f },
	{ 'M', "stall", 3, 2, true, false, 0, 1.04f },
	{ 'm', "picnic_mat", 2, 2, false, true, 0, 0 },
	{ 'k', "basket", 1, 1, true, false, 0, 0.9f },
	{ 'n', "signpost", 1, 1, true, false, 0, 0.6f },
	{ 'L', "lamppost", 1, 1, true, false, 0, 0.55f },
	{ 'd', "duck", 1, 1, false, false, 0.7f, 0 },
	{ 'q', "possum", 1, 1, true, false, 1.3f, 0.9f },
	{ 'T', "tree0", 1, 1, true, false, 0, 1.1f },
};

struct Prop
{
	const PropDef* def;
	const Sprite* sprite;
	glm::ivec2 cell;  // footprint top-left
	float phase = 0;  // so animated props don't all move in sync

	// world position of the image: bottom-aligned to the footprint, centred across it
	glm::vec2 imagePos() const
	{
		float footW = def->fw * TILE, footBottom = (cell.y + def->fh) * TILE;
		return { cell.x * TILE + (footW - sprite->fw) / 2, footBottom - sprite->fh };
	}
	float sortY() const { return static_cast<float>((cell.y + def->fh) * TILE); }
};

struct Map
{
	std::string name;
	int cols = 0, rows = 0;
	std::vector<std::string> ground, objects;
	std::vector<int> tileA, tileB;   // atlas index per cell (B = 2nd animation frame), -1 = nothing
	std::vector<uint8_t> solid;
	std::vector<Prop> props;
	std::map<char, glm::ivec2> markers;
	SDL_Color background{ 0, 0, 0, 255 };

	char groundAt(int c, int r) const { return inside(c, r) ? ground[r][c] : ' '; }
	bool inside(int c, int r) const { return c >= 0 && r >= 0 && c < cols && r < rows; }
	bool isSolid(int c, int r) const { return !inside(c, r) || solid[r * cols + c]; }
	float width() const { return static_cast<float>(cols * TILE); }
	float height() const { return static_cast<float>(rows * TILE); }

	glm::ivec2 marker(char m) const
	{
		auto it = markers.find(m);
		if (it != markers.end()) return it->second;
		// fall back to the first ground cell of that kind (e.g. stairs)
		for (int r = 0; r < rows; r++)
			for (int c = 0; c < cols; c++)
				if (ground[r][c] == m) return { c, r };
		return { 0, 0 };
	}

	const Prop* propAt(int c, int r) const
	{
		for (const Prop& p : props)
			if (c >= p.cell.x && c < p.cell.x + p.def->fw && r >= p.cell.y && r < p.cell.y + p.def->fh && p.def->ch != 'T')
				return &p;
		return nullptr;
	}

	bool load(const std::string& mapName, const SpriteBank& sprites)
	{
		*this = Map{};
		name = mapName;
		std::string path = engine::assetPath("maps/" + mapName + ".txt");
		size_t size = 0;
		char* data = static_cast<char*>(SDL_LoadFile(path.c_str(), &size));
		if (!data)
		{
			SDL_Log("Couldn't load map %s: %s", path.c_str(), SDL_GetError());
			return false;
		}
		std::string text(data, size);
		SDL_free(data);

		std::vector<std::string>* layer = nullptr;
		size_t pos = 0;
		while (pos < text.size())
		{
			size_t end = text.find('\n', pos);
			if (end == std::string::npos) end = text.size();
			std::string line = text.substr(pos, end - pos);
			pos = end + 1;
			if (!line.empty() && line.back() == '\r') line.pop_back();
			if (line.empty() || line[0] == '#' && layer == nullptr) continue;
			if (line == "ground") { layer = &ground; continue; }
			if (line == "objects") { layer = &objects; continue; }
			if (layer) layer->push_back(line);
		}
		rows = static_cast<int>(ground.size());
		cols = rows ? static_cast<int>(ground[0].size()) : 0;
		objects.resize(rows, std::string(cols, '.'));

		bool outdoors = false;
		for (const std::string& r : ground)
			if (r.find_first_of(",=T") != std::string::npos) outdoors = true;
		background = outdoors ? SDL_Color{ 40, 84, 46, 255 } : SDL_Color{ 16, 12, 18, 255 };

		buildTiles();
		buildProps(sprites);
		return true;
	}

private:
	static unsigned hash(int c, int r) { return static_cast<unsigned>(c * 73856093 ^ r * 19349663); }

	int mask(int c, int r, const char* same) const
	{
		auto is = [&](int cc, int rr) {
			if (!inside(cc, rr)) return true; // continues off the edge of the map
			return std::strchr(same, ground[rr][cc]) != nullptr;
		};
		return (is(c, r - 1) ? 1 : 0) | (is(c + 1, r) ? 2 : 0) | (is(c, r + 1) ? 4 : 0) | (is(c - 1, r) ? 8 : 0);
	}

	void buildTiles()
	{
		tileA.assign(rows * cols, -1);
		tileB.assign(rows * cols, -1);
		solid.assign(rows * cols, 0);
		for (int r = 0; r < rows; r++)
		{
			for (int c = 0; c < cols; c++)
			{
				int i = r * cols + c;
				unsigned h = hash(c, r);
				int t = -1;
				bool s = false;
				switch (ground[r][c])
				{
					case '#': t = art::TILE_WALL; s = true; break;
					case 'W': t = art::TILE_WALL_WINDOW; s = true; break;
					case '.': t = art::TILE_FLOOR + h % art::TILE_FLOOR_COUNT; break;
					case 'r': t = art::TILE_RUG + mask(c, r, "r"); break;
					case 'v': t = art::TILE_STAIRS_DOWN; break;
					case '^': t = art::TILE_STAIRS_UP; break;
					case 'e': t = art::TILE_DOORMAT; break;
					case ',': case 'T': t = art::TILE_GRASS + h % art::TILE_GRASS_COUNT; s = ground[r][c] == 'T'; break;
					case ';': t = art::TILE_FLOWERS + h % art::TILE_FLOWERS_COUNT; break;
					case '=': t = art::TILE_PATH + mask(c, r, "=HI"); break;
					case '~':
						t = art::TILE_WATER + mask(c, r, "~HI");
						tileB[i] = art::TILE_WATER2 + mask(c, r, "~HI");
						s = true;
						break;
					case 'H': t = art::TILE_BRIDGE_H; break;
					case 'I': t = art::TILE_BRIDGE_V; break;
					case 'f': t = art::TILE_FENCE + mask(c, r, "f"); s = true; break;
					case 'h': t = art::TILE_HEDGE + mask(c, r, "h"); s = true; break;
					case 'o': t = art::TILE_ROCK; s = true; break;
					case '*': t = art::TILE_FLOWERBED + h % art::TILE_FLOWERBED_COUNT; s = true; break;
					case 'l': t = art::TILE_LONG_GRASS + h % art::TILE_LONG_GRASS_COUNT; break;
					case 'w': t = art::TILE_WILDFLOWERS + h % art::TILE_WILDFLOWERS_COUNT; break;
					default: s = true; break; // empty space outside the room
				}
				tileA[i] = t;
				if (tileB[i] == -1) tileB[i] = t;
				solid[i] = s;
			}
		}
	}

	void buildProps(const SpriteBank& sprites)
	{
		for (int r = 0; r < rows; r++)
		{
			for (int c = 0; c < cols; c++)
			{
				char g = ground[r][c];
				char o = objects[r][c];
				if (g == 'T')
				{
					static const PropDef* treeDef = &PROP_DEFS[std::size(PROP_DEFS) - 1];
					// mostly leafy trees, some pines, and the odd one turning orange
					unsigned h = hash(c, r);
					unsigned mixed = (h ^ (h >> 15)) * 2246822519u;
					mixed ^= mixed >> 13;
					const char* kind = h % 5 == 0 ? "tree1" : mixed % 7 == 0 ? "tree2" : "tree0";
					Prop p{ treeDef, &sprites.get(kind), { c, r } };
					props.push_back(p);
				}
				if (o == '.' || o == ' ') continue;
				if (o == '@' || o == '&' || o == 'b' || (o >= '1' && o <= '9'))
				{
					markers[o] = { c, r };
					continue;
				}
				for (const PropDef& def : PROP_DEFS)
				{
					if (def.ch != o) continue;
					Prop p{ &def, &sprites.get(def.sprite), { c, r }, static_cast<float>(hash(c, r) % 100) / 100.0f };
					props.push_back(p);
					if (def.solid)
						for (int y = r; y < r + def.fh; y++)
							for (int x = c; x < c + def.fw; x++)
								if (inside(x, y)) solid[y * cols + x] = 1;
				}
			}
		}
	}

public:
	// Cheapest walkable route between two cells, preferring paths and floors
	// so Pet sticks to the road. Returns the cells after `from`, ending at `to`.
	std::vector<glm::ivec2> route(glm::ivec2 from, glm::ivec2 to) const
	{
		auto idx = [&](glm::ivec2 p) { return p.y * cols + p.x; };
		std::vector<int> cost(rows * cols, INT32_MAX), prev(rows * cols, -1);
		using Item = std::pair<int, int>;
		std::priority_queue<Item, std::vector<Item>, std::greater<Item>> open;
		if (!inside(from.x, from.y) || !inside(to.x, to.y)) return {};
		cost[idx(from)] = 0;
		open.push({ 0, idx(from) });
		const glm::ivec2 steps[4] = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } };
		while (!open.empty())
		{
			auto [d, i] = open.top();
			open.pop();
			if (i == idx(to)) break;
			if (d > cost[i]) continue;
			glm::ivec2 p{ i % cols, i / cols };
			for (glm::ivec2 s : steps)
			{
				glm::ivec2 n = p + s;
				if (!inside(n.x, n.y) || (isSolid(n.x, n.y) && n != to)) continue;
				char g = ground[n.y][n.x];
				int step = (g == '=' || g == 'H' || g == 'I' || g == '.' || g == 'r') ? 1 : 4;
				int nd = d + step;
				if (nd < cost[idx(n)])
				{
					cost[idx(n)] = nd;
					prev[idx(n)] = i;
					open.push({ nd, idx(n) });
				}
			}
		}
		std::vector<glm::ivec2> path;
		for (int i = idx(to); i != -1 && i != idx(from); i = prev[i])
			path.push_back({ i % cols, i / cols });
		std::reverse(path.begin(), path.end());
		return path;
	}

	// Move a collider by `delta`, one axis at a time, stopping flush against
	// solid cells. Sliding along walls works because the axes are separate.
	glm::vec2 move(glm::vec2 pos, glm::vec2 delta, SDL_FRect box) const
	{
		for (int axis = 0; axis < 2; axis++)
		{
			glm::vec2 next = pos;
			next[axis] += delta[axis];
			float x0 = next.x + box.x, y0 = next.y + box.y, x1 = x0 + box.w, y1 = y0 + box.h;
			int c0 = static_cast<int>(std::floor(x0 / TILE)), c1 = static_cast<int>(std::floor((x1 - 0.01f) / TILE));
			int r0 = static_cast<int>(std::floor(y0 / TILE)), r1 = static_cast<int>(std::floor((y1 - 0.01f) / TILE));
			bool blocked = false;
			for (int r = r0; r <= r1 && !blocked; r++)
				for (int c = c0; c <= c1; c++)
					if (isSolid(c, r)) { blocked = true; break; }
			if (!blocked)
			{
				pos = next;
				continue;
			}
			// slide up to the edge of the blocking cell
			if (axis == 0)
				pos.x = delta.x > 0 ? (c1 * TILE) - box.x - box.w : ((c0 + 1) * TILE) - box.x;
			else
				pos.y = delta.y > 0 ? (r1 * TILE) - box.y - box.h : ((r0 + 1) * TILE) - box.y;
		}
		return pos;
	}
};
