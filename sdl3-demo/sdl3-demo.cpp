// Pixel gift game: a personalised story you can play.
//
// The hero is woken by the pet, follows it out into the village past six
// memories, and finds the partner waiting with a picnic. The story
// itself -- every line and the order things happen -- lives in story.h;
// maps are in assets/maps (tools/make_maps.py) and art in assets/ (tools/make_art.py).
//
// SDL drives the loop through SDL_AppInit/Event/Iterate/Quit so the same
// code runs natively and in the browser.
#define SDL_MAIN_USE_CALLBACKS 1
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include <SDL3_image/SDL_image.h>
#include <glm/glm.hpp>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>

#include "engine/sdl_app.h"
#include "engine/texture_cache.h"
#include "input.h"
#include "world.h"
#include "story.h"
#include "ui.h"

using engine::SDLState;

const int LOGICAL_W = 384, LOGICAL_H = 288;
const float HERO_SPEED = 100.0f;
const float PET_SPEED = 94.0f;                 // a touch slower than Hero, so she can keep up
const float PET_WAIT_DISTANCE = 5.5f * TILE;   // Pet stops to wait if Hero falls this far behind...
const float PET_RESUME_DISTANCE = 3.0f * TILE; // ...and sets off again once she's this close
const float FADE_TIME = 0.35f;
const float MAX_DELTA_TIME = 0.05f;
const float MESSAGE_BACK_ZONE = 0.3f;            // taps on the left 30% of the screen page back
const float PLAY_AGAIN_DELAY = 1.2f;             // the final card ignores taps this long              // see the note in SDL_AppIterate
const SDL_FRect HERO_FEET{ 9, 19, 14, 11 };    // collider, relative to her 32x32 footprint

struct Actor
{
	const char* prefix = "hero";  // walk strips are <prefix>_walk_<dir>
	glm::vec2 pos{ 0 };              // top-left of the 32x32 footprint
	Dir facing = Dir::Down;
	bool moving = false;
	bool visible = true;
	std::string pose;                // a sprite that replaces the walk cycle (sitting, lying...)
	float animTime = 0;

	glm::vec2 centre() const { return pos + glm::vec2(TILE / 2.0f); }
	glm::ivec2 cell() const { return glm::ivec2(glm::floor(centre() / static_cast<float>(TILE))); }
};

struct Game
{
	SDLState state;
	engine::TextureCache cache;
	SpriteBank sprites;
	std::vector<SDL_Texture*> photos;
	TouchControls touch;

	Map map;
	Actor hero, pet, partner;
	bool partnerHere = false;
	bool heroInBed = false;
	glm::vec2 cam{ 0 };

	// Pet's walk to his next spot
	std::vector<glm::ivec2> route;
	size_t routeStep = 0;
	char petTarget = 0;
	bool petExcited = false; // "!" over his head at a stop
	bool petWaiting = false; // stopped on the way, waiting for Hero to catch up

	// the story
	size_t beat = 0;
	float beatTime = 0;
	bool mapLoaded = false;    // for Map/Ending beats: the switch has happened
	float fade = 0;            // 0 = clear, 1 = black
	std::string sayText;
	const char* saySpeaker = nullptr;
	float sayShown = 0;
	std::string inspectText;   // a "look at" message during free roam
	float inspectShown = 0;
	ui::MessageLayout message;
	bool messageReady = false;
	int messagePage = 0;
	bool finalCard = false;
	float pageTime = 0;
	bool ending = false;

	// input gathered this frame
	bool action = false, tap = false, anyKey = false;
	bool back = false, forward = false; // paging through the message
	float tapX = 0.5f;                  // where the tap landed, 0..1 across the game screen
	float fingerX = 0.5f;               // where the latest finger went down, likewise

	float time = 0;
	uint64_t prevTicks = 0;
	bool debug = false;

	// testing aid: Hero follows Pet and taps through text on her own
	bool autoplay = false;
	float autoTimer = 0, stuckTimer = 0;

	// testing aid: save a screenshot of the scene (no UI) and quit
	std::string shotPath;
	float shotTime = 1.5f;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const Beat& currentBeat(const Game& g) { return story::BEATS[g.beat]; }

glm::vec2 cellPos(glm::ivec2 c) { return glm::vec2(c) * static_cast<float>(TILE); }

const char* dirName(Dir d)
{
	switch (d)
	{
		case Dir::Up: return "up";
		case Dir::Left: return "left";
		case Dir::Right: return "right";
		default: return "down";
	}
}

bool petArrived(const Game& g) { return g.routeStep >= g.route.size(); }

void loadMap(Game& g, const std::string& name)
{
	g.map.load(name, g.sprites);
	g.hero = Actor{};
	g.hero.prefix = "hero";
	g.hero.pos = cellPos(g.map.marker('@'));
	g.heroInBed = name == "bedroom";
	g.hero.visible = !g.heroInBed;

	g.pet = Actor{};
	g.pet.prefix = "pet";
	g.pet.visible = g.map.markers.count('&') > 0;
	g.pet.pos = cellPos(g.map.marker('&'));
	g.pet.facing = name == "bedroom" ? Dir::Left : Dir::Down;
	g.route.clear();
	g.routeStep = 0;
	g.petTarget = 0;
	g.petExcited = false;
	g.petWaiting = false;

	g.partnerHere = g.map.markers.count('b') > 0;
	g.partner = Actor{};
	g.partner.prefix = "partner";
	g.partner.pose = "partner_sit";
	g.partner.visible = g.partnerHere;
	if (g.partnerHere)
	{
		glm::ivec2 b = g.map.marker('b');
		g.partner.pos = cellPos(b);
		g.map.solid[b.y * g.map.cols + b.x] = 1; // you can't walk through Partner
	}
	g.ending = false;
}

void petGo(Game& g, char marker)
{
	g.petTarget = marker;
	g.route = g.map.route(g.pet.cell(), g.map.marker(marker));
	g.routeStep = 0;
	g.pet.pose.clear();
	g.petExcited = false;
	g.petWaiting = false;
}

// What's in the cell Hero is facing, if it has something to say.
const char* inspectTarget(const Game& g)
{
	glm::vec2 probe = g.hero.pos + glm::vec2(HERO_FEET.x + HERO_FEET.w / 2, HERO_FEET.y + HERO_FEET.h / 2)
		+ dirVector(g.hero.facing) * 18.0f;
	glm::ivec2 c(glm::floor(probe / static_cast<float>(TILE)));
	const Prop* p = g.map.propAt(c.x, c.y);
	char what = p ? p->def->ch : g.map.groundAt(c.x, c.y);
	for (const story::Inspect& in : story::INSPECTS)
		if (g.map.name == in.map && in.what == what) return in.text;
	return nullptr;
}

void resetStory(Game& g);
void startBeat(Game& g);

void nextBeat(Game& g)
{
	g.beat++;
	if (g.beat >= story::BEATS.size())
	{
		resetStory(g);
		return;
	}
	startBeat(g);
}

void startBeat(Game& g)
{
	g.beatTime = 0;
	g.mapLoaded = false;
	const Beat& b = currentBeat(g);
	SDL_Log("beat %d: op %d %s %s %c", static_cast<int>(g.beat), static_cast<int>(b.op), b.a ? b.a : "", b.b ? b.b : "", b.m ? b.m : ' ');
	switch (b.op)
	{
		case Op::Title:
			// the village makes a pretty backdrop for the title
			loadMap(g, "village");
			g.pet.pose = "pet_sit";
			break;
		case Op::Say:
			g.saySpeaker = b.a;
			g.sayText = b.b ? b.b : "";
			g.sayShown = 0;
			if (b.a && std::strcmp(b.a, story::PET_NAME) == 0)
			{
				g.petExcited = false;
				if (petArrived(g) && g.pet.pose.empty())
					g.pet.facing = dirTowards(g.hero.centre() - g.pet.centre());
			}
			break;
		case Op::Wake:
			g.heroInBed = false;
			g.hero.visible = true;
			g.hero.facing = Dir::Right;
			nextBeat(g);
			break;
		case Op::PetGo:
			petGo(g, b.m);
			nextBeat(g);
			break;
		case Op::Label:
			nextBeat(g);
			break;
		case Op::Message:
			g.messageReady = false;
			g.messagePage = 0;
			g.finalCard = false;
			g.pageTime = 0;
			break;
		default:
			break;
	}
}

void resetStory(Game& g)
{
	g.beat = 0;
	g.fade = 0;
	g.inspectText.clear();
	startBeat(g);
}

// Jump straight to a labelled point in the story (for testing).
void jumpTo(Game& g, const std::string& label)
{
	size_t target = 0;
	for (size_t i = 0; i < story::BEATS.size(); i++)
		if (story::BEATS[i].op == Op::Label && label == story::BEATS[i].a) target = i;
	if (!target) return;
	std::string mapName = "village";
	char lastSpot = 0;
	for (size_t i = 0; i < target; i++)
	{
		if (story::BEATS[i].op == Op::Map) mapName = story::BEATS[i].a;
		if (story::BEATS[i].op == Op::PetGo) lastSpot = story::BEATS[i].m;
	}
	loadMap(g, mapName);
	if (lastSpot && g.map.markers.count(lastSpot))
	{
		g.pet.pos = cellPos(g.map.marker(lastSpot));
		g.hero.pos = g.pet.pos + glm::vec2(-TILE, 0);
	}
	g.fade = 0;
	g.beat = target;
	startBeat(g);
}

// ---------------------------------------------------------------------------
// Update
// ---------------------------------------------------------------------------
// Testing aid: walk Hero a little behind Pet, then on to wherever the
// story is waiting for her.
glm::vec2 autopilot(Game& g, float dt)
{
	const Beat& b = currentBeat(g);
	if (b.op != Op::WaitNear && b.op != Op::WaitOn) return glm::vec2(0);
	glm::vec2 target;
	if (!petArrived(g) && g.routeStep >= 2) target = cellPos(g.route[g.routeStep - 2]);
	else if (!petArrived(g)) target = g.hero.pos;
	else if (b.op == Op::WaitNear && b.m == 'b') target = cellPos(g.map.marker('b') + glm::ivec2(-1, 0));
	else target = cellPos(g.map.marker(b.m));
	glm::vec2 to = target - g.hero.pos;
	if (glm::length(to) < 3) { g.stuckTimer = 0; return glm::vec2(0); }
	g.stuckTimer += dt;
	if (g.stuckTimer > 1.5f) { g.hero.pos = target; g.stuckTimer = 0; } // snagged on a corner
	glm::vec2 in{ 0 };
	if (std::abs(to.x) > 2) in.x = to.x > 0 ? 1.0f : -1.0f;
	if (std::abs(to.y) > 2) in.y = to.y > 0 ? 1.0f : -1.0f;
	return in;
}

void updateHero(Game& g, float dt, bool canMove)
{
	glm::vec2 in{ 0 };
	if (canMove)
	{
		PlayerInput pi;
		const bool* k = g.state.keys;
		pi.left = k[SDL_SCANCODE_LEFT] || k[SDL_SCANCODE_A];
		pi.right = k[SDL_SCANCODE_RIGHT] || k[SDL_SCANCODE_D];
		pi.up = k[SDL_SCANCODE_UP] || k[SDL_SCANCODE_W];
		pi.down = k[SDL_SCANCODE_DOWN] || k[SDL_SCANCODE_S];
		g.touch.applyTo(pi);
		in = { (pi.right ? 1.0f : 0.0f) - (pi.left ? 1.0f : 0.0f), (pi.down ? 1.0f : 0.0f) - (pi.up ? 1.0f : 0.0f) };
		if (g.autoplay) in = autopilot(g, dt);
	}
	g.hero.moving = in != glm::vec2(0);
	if (g.hero.moving)
	{
		g.hero.facing = dirTowards(in);
		in = glm::normalize(in);
		glm::vec2 before = g.hero.pos;
		g.hero.pos = g.map.move(g.hero.pos, in * HERO_SPEED * dt, HERO_FEET);
		if (glm::length(g.hero.pos - before) > 0.2f) g.stuckTimer = 0;
		g.hero.animTime += dt;
	}
	else
	{
		g.hero.animTime = 0;
	}
}

void updatePet(Game& g, float dt)
{
	Actor& s = g.pet;
	s.moving = false;
	if (!s.visible) return;
	if (!petArrived(g))
	{
		// Waiting has two thresholds, so he doesn't flick between walking and
		// stopping every frame while she trails right at the edge of one.
		bool outdoors = g.map.name == "village";
		float gap = glm::length(g.hero.centre() - s.centre());
		if (!outdoors || gap < PET_RESUME_DISTANCE) g.petWaiting = false;
		else if (gap > PET_WAIT_DISTANCE) g.petWaiting = true;
		if (g.petWaiting)
		{
			// wait for her to catch up, looking back at her
			s.facing = dirTowards(g.hero.centre() - s.centre());
		}
		else
		{
			glm::vec2 target = cellPos(g.route[g.routeStep]);
			glm::vec2 to = target - s.pos;
			float dist = glm::length(to);
			float step = PET_SPEED * dt;
			if (dist <= step)
			{
				s.pos = target;
				g.routeStep++;
			}
			else
			{
				s.pos += to / dist * step;
				s.facing = dirTowards(to);
			}
			s.moving = true;
			s.animTime += dt;
			if (petArrived(g))
			{
				// made it: sit, and get excited about whatever's here
				s.pose = "pet_sit";
				g.petExcited = g.petTarget >= '1' && g.petTarget <= '6';
			}
		}
	}
	if (!s.moving) s.animTime = 0;
}

void update(Game& g, float dt)
{
	g.time += dt;
	g.beatTime += dt;
	if (g.autoplay)
	{
		g.autoTimer += dt;
		Op op = currentBeat(g).op;
		bool text = op == Op::Title || op == Op::Say || op == Op::Memory || op == Op::Message || !g.inspectText.empty();
		if (text && g.autoTimer > 0.9f) { g.tap = true; g.tapX = 0.5f; g.autoTimer = 0; }
	}
	const Beat& b = currentBeat(g);
	bool press = g.action || g.tap;
	bool freeRoam = (b.op == Op::WaitNear || b.op == Op::WaitOn) && g.inspectText.empty();

	switch (b.op)
	{
		case Op::Title:
			g.cam = cellPos(g.map.marker('1')) + glm::vec2(0, -TILE);
			if (g.beatTime > 0.3f && (press || g.anyKey)) nextBeat(g);
			break;

		case Op::Map:
			if (g.beatTime < FADE_TIME)
			{
				g.fade = std::max(g.fade, g.beatTime / FADE_TIME);
			}
			else
			{
				if (!g.mapLoaded)
				{
					loadMap(g, b.a);
					g.mapLoaded = true;
				}
				g.fade = std::max(0.0f, 1 - (g.beatTime - FADE_TIME) / FADE_TIME);
				if (g.beatTime >= FADE_TIME * 2) nextBeat(g);
			}
			break;

		case Op::Caption:
			if (g.beatTime > 2.4f || (g.beatTime > 0.5f && press)) nextBeat(g);
			break;

		case Op::Say:
		{
			g.sayShown += dt * 45.0f;
			size_t len = g.sayText.size();
			if (press && g.beatTime > 0.12f)
			{
				if (g.sayShown < len) g.sayShown = static_cast<float>(len);
				else nextBeat(g);
			}
			break;
		}

		case Op::WaitNear:
		{
			glm::vec2 spot = cellPos(g.map.marker(b.m)) + glm::vec2(TILE / 2.0f);
			float radius = (b.m == 'b' ? 2.6f : 2.3f) * TILE;
			if (glm::length(g.hero.centre() - spot) < radius && petArrived(g))
			{
				g.hero.moving = false;
				nextBeat(g);
			}
			break;
		}

		case Op::WaitOn:
		{
			glm::ivec2 c = g.hero.cell();
			if (g.map.groundAt(c.x, c.y) == b.m) nextBeat(g);
			break;
		}

		case Op::Memory:
			if (press && g.beatTime > 0.45f) nextBeat(g);
			break;

		case Op::Ending:
		{
			const float out = 0.7f;
			if (g.beatTime < out)
			{
				g.fade = g.beatTime / out;
			}
			else
			{
				if (!g.mapLoaded)
				{
					// everyone lies down on the picnic mat to watch the birds
					g.mapLoaded = true;
					g.ending = true;
					glm::vec2 mat{ 0 };
					for (const Prop& p : g.map.props)
						if (p.def->ch == 'm') mat = cellPos(p.cell);
					g.hero.pose = "hero_lying";
					g.hero.pos = mat + glm::vec2(-6, 2);
					g.pet.pose = "pet_lying";
					g.pet.pos = mat + glm::vec2(16, 22);
					g.partner.pose = "partner_lying";
					g.partner.pos = mat + glm::vec2(36, 2);
					g.petExcited = false;
				}
				g.fade = std::max(0.0f, 1 - (g.beatTime - out) / out);
				if (g.beatTime > out * 2 + 2.2f) nextBeat(g);
			}
			break;
		}

		case Op::Message:
		{
			// Forward: tap, action, Right. Back: tap the left side, Left,
			// Backspace, or the d-pad's left. Back works from the final card
			// too, and "play again" waits until its prompt has appeared.
			g.pageTime += dt;
			if (!g.messageReady) break;
			int last = static_cast<int>(g.message.pages.size()) - 1;
			bool back = g.back || (g.tap && g.tapX < MESSAGE_BACK_ZONE);
			bool forward = !back && (g.forward || press);
			if (back && g.pageTime > 0.2f)
			{
				if (g.finalCard)
				{
					g.finalCard = false;
					g.messagePage = last;
				}
				else if (g.messagePage > 0)
				{
					g.messagePage--;
				}
				g.pageTime = 0;
			}
			else if (forward && g.finalCard)
			{
				if (g.pageTime > PLAY_AGAIN_DELAY) resetStory(g);
			}
			else if (forward && g.pageTime > 0.35f)
			{
				if (g.messagePage < last) g.messagePage++;
				else g.finalCard = true;
				g.pageTime = 0;
			}
			break;
		}

		default:
			break;
	}

	// free roam: walk about, and look at things with the action button
	if (!g.inspectText.empty())
	{
		g.inspectShown += dt * 45.0f;
		if (press && g.inspectShown > 4)
		{
			if (g.inspectShown < g.inspectText.size()) g.inspectShown = static_cast<float>(g.inspectText.size());
			else g.inspectText.clear();
		}
	}
	else if (freeRoam && currentBeat(g).op == b.op && g.action)
	{
		if (const char* t = inspectTarget(g))
		{
			g.inspectText = t;
			g.inspectShown = 0;
		}
	}

	Op now = currentBeat(g).op;
	bool canMove = (now == Op::WaitNear || now == Op::WaitOn) && g.inspectText.empty() && !g.ending;
	updateHero(g, dt, canMove);
	updatePet(g, dt);
	if (!g.ending) g.partner.animTime += dt;

	// camera follows Hero (or the picnic, at the end), kept inside the map
	if (currentBeat(g).op != Op::Title)
	{
		glm::vec2 focus = g.hero.centre();
		if (g.ending) focus = g.partner.pos + glm::vec2(-4, 30);
		g.cam = focus;
	}
	glm::vec2 view(LOGICAL_W, LOGICAL_H);
	glm::vec2 c = g.cam - view / 2.0f;
	for (int a = 0; a < 2; a++)
	{
		float size = a == 0 ? g.map.width() : g.map.height();
		if (size <= view[a]) c[a] = (size - view[a]) / 2;
		else c[a] = std::clamp(c[a], 0.0f, size - view[a]);
	}
	g.cam = glm::floor(c + view / 2.0f);
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------
// A soft drop shadow on the ground: a translucent ellipse, stepped in 2px
// rows so it matches the chunky pixel art. Light comes from the top-left, so
// callers nudge it a little right of the thing casting it.
void drawShadow(SDL_Renderer* r, float cx, float cy, float rx, float ry)
{
	SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
	SDL_SetRenderDrawColor(r, 22, 38, 70, 72);
	for (float y = -ry; y < ry; y += 2)
	{
		float t = (y + 1) / ry;
		float half = rx * std::sqrt(std::max(0.0f, 1 - t * t));
		half = std::floor(half / 2) * 2;
		if (half <= 0) continue;
		SDL_FRect row{ std::floor((cx - half) / 2) * 2, std::floor((cy + y) / 2) * 2, half * 2, 2 };
		SDL_RenderFillRect(r, &row);
	}
	SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
}

// Indoors: give the room some depth. The walls along the top and left cast
// a shadow onto the floor, sunlight falls through each window onto the
// boards below it, and a dark frame stands in for the walls around the room.
void drawRoomDepth(const Game& g, SDL_Renderer* r, glm::vec2 origin)
{
	const Map& m = g.map;
	auto fill = [&](float x, float y, float w, float h, SDL_Color c) {
		SDL_SetRenderDrawColor(r, c.r, c.g, c.b, c.a);
		SDL_FRect rc{ x - origin.x, y - origin.y, w, h };
		SDL_RenderFillRect(r, &rc);
	};
	SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
	for (int c = 0; c < m.cols; c++)
	{
		char top = m.groundAt(c, 0);
		if (top != '#' && top != 'W') continue;
		fill(c * TILE, TILE, TILE, 4, { 30, 16, 30, 90 });
		fill(c * TILE, TILE + 4, TILE, 4, { 30, 16, 30, 45 });
		if (top == 'W')
		{
			// a slanted pool of light, falling down and to the right
			for (float y = 0; y < TILE * 2.5f; y += 2)
			{
				float fade = 1 - y / (TILE * 2.5f);
				SDL_Color sun{ 255, 240, 196, static_cast<Uint8>(72 * fade + 10) };
				fill(c * TILE + 6 + std::floor(y * 0.45f / 2) * 2, TILE + y, TILE - 12, 2, sun);
			}
		}
	}
	fill(0, TILE, 6, m.height() - TILE, { 30, 16, 30, 70 });
	fill(6, TILE, 4, m.height() - TILE, { 30, 16, 30, 30 });
	SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
	const SDL_Color frame{ 58, 38, 48, 255 }, edge{ 104, 70, 62, 255 };
	fill(-10, 0, 10, m.height() + 10, frame);
	fill(m.width(), 0, 10, m.height() + 10, frame);
	fill(-10, m.height(), m.width() + 20, 10, frame);
	fill(m.width(), 0, 2, m.height() + 2, edge);
	fill(0, m.height(), m.width() + 2, 2, edge);
}

void actorShadow(const Game& g, const Actor& a, glm::vec2 origin)
{
	if (!a.visible || g.ending) return;
	bool dog = std::strcmp(a.prefix, "pet") == 0;
	float rx = dog ? 12.0f : 13.0f;
	if (a.prefix == std::string("partner")) rx = 16;
	drawShadow(g.state.renderer, a.pos.x + TILE / 2 + 2 - origin.x, a.pos.y + TILE - origin.y, rx, 5.0f);
}

struct Drawable
{
	float sortY;
	const Sprite* sprite;
	glm::vec2 pos;
	int frame;
};

void drawActor(const Game& g, const Actor& a, std::vector<Drawable>& out)
{
	if (!a.visible) return;
	const Sprite* s;
	int frame = 0;
	if (!a.pose.empty())
	{
		s = &g.sprites.get(a.pose);
		frame = static_cast<int>(g.time * (a.pose == "partner_sit" ? 1.2f : 2.5f));
	}
	else
	{
		s = &g.sprites.get(std::string(a.prefix) + "_walk_" + dirName(a.facing));
		frame = a.moving ? static_cast<int>(a.animTime * 7.0f) % 4 : 0;
	}
	glm::vec2 p{ a.pos.x + (TILE - s->fw) / 2, a.pos.y + TILE - s->fh };
	if (g.ending) p = a.pos; // lying on the mat: positioned by hand
	float sortY = g.ending ? 1e9f + a.pos.y : a.pos.y + TILE;
	out.push_back({ sortY, s, p, frame });
}

void render(Game& g)
{
	SDL_Renderer* r = g.state.renderer;
	SDL_SetRenderDrawColor(r, g.map.background.r, g.map.background.g, g.map.background.b, 255);
	SDL_RenderClear(r);

	glm::vec2 view(LOGICAL_W, LOGICAL_H);
	glm::vec2 origin = g.cam - view / 2.0f;
	auto onScreen = [&](glm::vec2 p, glm::vec2 size) {
		return p.x + size.x > origin.x && p.x < origin.x + view.x && p.y + size.y > origin.y && p.y < origin.y + view.y;
	};

	// ground
	int c0 = std::max(0, static_cast<int>(origin.x / TILE) - 1), c1 = std::min(g.map.cols - 1, static_cast<int>((origin.x + view.x) / TILE) + 1);
	int r0 = std::max(0, static_cast<int>(origin.y / TILE) - 1), r1 = std::min(g.map.rows - 1, static_cast<int>((origin.y + view.y) / TILE) + 1);
	bool waterFrame = static_cast<int>(g.time / 0.6f) % 2 == 1;
	for (int y = r0; y <= r1; y++)
	{
		for (int x = c0; x <= c1; x++)
		{
			int i = y * g.map.cols + x;
			int t = waterFrame ? g.map.tileB[i] : g.map.tileA[i];
			if (t < 0) continue;
			SDL_FRect src{ static_cast<float>((t % art::ATLAS_COLS) * TILE), static_cast<float>((t / art::ATLAS_COLS) * TILE), TILE, TILE };
			SDL_FRect dst{ x * TILE - origin.x, y * TILE - origin.y, TILE, TILE };
			SDL_RenderTexture(r, g.sprites.tiles, &src, &dst);
		}
	}

	if (g.map.name != "village") drawRoomDepth(g, r, origin);

	// drop shadows, flat on the ground under everything standing on it
	for (const Prop& p : g.map.props)
	{
		if (p.def->shadow <= 0) continue;
		float w = p.def->fw * TILE * p.def->shadow;
		glm::vec2 base{ p.cell.x * TILE + p.def->fw * TILE * 0.5f, static_cast<float>((p.cell.y + p.def->fh) * TILE) };
		float ry = std::clamp(w * 0.18f, 6.0f, 18.0f);
		if (!onScreen(base - glm::vec2(w, ry * 2), { w * 2, ry * 4 })) continue;
		float lean = p.sprite->fh * 0.12f; // taller things cast their shadow further from the light
		drawShadow(r, base.x + lean - origin.x, base.y - ry * 0.4f - origin.y, w / 2, ry);
	}
	actorShadow(g, g.partner, origin);
	actorShadow(g, g.hero, origin);
	actorShadow(g, g.pet, origin);

	// props and characters, back to front
	std::vector<Drawable> list;
	const Prop* dragon = nullptr;
	for (const Prop& p : g.map.props)
	{
		const Sprite* s = p.sprite;
		if (p.def->ch == 'B' && g.heroInBed) s = &g.sprites.get("bed_sleeping");
		glm::vec2 pos = p.imagePos();
		if (!onScreen(pos, { s->fw, s->fh })) continue;
		int frame = p.def->frameTime > 0 ? static_cast<int>((g.time + p.phase * 3) / p.def->frameTime) : 0;
		float sortY = p.def->flat ? -1e9f : p.sortY();
		list.push_back({ sortY, s, pos, frame });
		if (p.def->ch == 'R') dragon = &p;
	}
	drawActor(g, g.partner, list);
	drawActor(g, g.hero, list);
	drawActor(g, g.pet, list);
	std::stable_sort(list.begin(), list.end(), [](const Drawable& a, const Drawable& b) { return a.sortY < b.sortY; });
	for (const Drawable& d : list)
		d.sprite->draw(r, d.pos.x - origin.x, d.pos.y - origin.y, d.frame);

	// little extras on top: the dragon's snores, Pet's "!", the birds
	if (dragon)
	{
		glm::vec2 p = dragon->imagePos() + glm::vec2(98, -6);
		g.sprites.get("zzz").draw(r, p.x - origin.x, p.y - origin.y, static_cast<int>(g.time / 0.8f));
	}
	if (g.petExcited && g.pet.visible)
	{
		float bob = std::sin(g.time * 8) > 0 ? -2.0f : 0.0f;
		g.sprites.get("bubble").draw(r, g.pet.pos.x + 6 - origin.x, g.pet.pos.y - 26 + bob - origin.y, 0);
	}
	if (g.partnerHere)
	{
		const Sprite& bird = g.sprites.get("bird");
		for (int i = 0; i < 4; i++)
		{
			float span = 26.0f * TILE;
			float x = g.partner.pos.x - 13 * TILE + std::fmod(g.time * (38 + i * 7) + i * 170, span);
			float y = g.partner.pos.y - 3.5f * TILE + i * 26 + std::sin(g.time * 1.7f + i) * 8;
			if (onScreen({ x, y }, { 16, 16 }))
				bird.draw(r, x - origin.x, y - origin.y, static_cast<int>(g.time * 5 + i));
		}
	}

	if (g.debug)
	{
		SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
		SDL_SetRenderDrawColor(r, 255, 0, 0, 70);
		for (int y = r0; y <= r1; y++)
			for (int x = c0; x <= c1; x++)
				if (g.map.isSolid(x, y))
				{
					SDL_FRect rc{ x * TILE - origin.x, y * TILE - origin.y, TILE, TILE };
					SDL_RenderFillRect(r, &rc);
				}
		SDL_SetRenderDrawColor(r, 0, 120, 255, 160);
		SDL_FRect feet{ g.hero.pos.x + HERO_FEET.x - origin.x, g.hero.pos.y + HERO_FEET.y - origin.y, HERO_FEET.w, HERO_FEET.h };
		SDL_RenderFillRect(r, &feet);
		SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
		glm::ivec2 kc = g.hero.cell();
		SDL_SetRenderDrawColor(r, 255, 255, 255, 255);
		SDL_RenderDebugText(r, 4, 4, (g.map.name + " beat " + std::to_string(g.beat) + " cell " + std::to_string(kc.x) + "," + std::to_string(kc.y)).c_str());
	}

	if (!g.shotPath.empty()) return; // screenshots are of the scene only

	// --- UI, in window pixels ---------------------------------------------------
	ui::Frame f = ui::begin(r, LOGICAL_W, LOGICAL_H);
	const Beat& b = currentBeat(g);

	if (g.fade > 0) ui::dim(f, g.fade);

	switch (b.op)
	{
		case Op::Title:
		{
			ui::dim(f, 0.35f);
			std::string title = story::TITLE;
			int big = std::max(1, std::min(f.text * 2, static_cast<int>(f.game.w * 0.85f / (title.size() * 8))));
			float maxW = f.game.w - f.u(24);
			// the dedication wraps if it's wider than the card can be
			std::vector<std::string> dedication = ui::wrap(story::DEDICATION, static_cast<size_t>((maxW - f.u(24)) / f.glyph()));
			float textW = title.size() * 8.0f * big;
			for (const std::string& line : dedication) textW = std::max(textW, line.size() * f.glyph());
			float w = std::min(maxW, textW + f.u(32));
			float h = 8.0f * big + dedication.size() * f.lineH() + f.u(44);
			SDL_FRect box{ f.game.x + (f.game.w - w) / 2, f.game.y + f.game.h * 0.24f, w, h };
			ui::panel(f, box);
			ui::textCentered(f, box.x + w / 2, box.y + f.u(12), title, ui::ACCENT, big);
			for (size_t i = 0; i < dedication.size(); i++)
				ui::textCentered(f, box.x + w / 2, box.y + f.u(22) + 8.0f * big + i * f.lineH(), dedication[i], ui::INK);
			ui::heart(f, g.sprites.get("heart"), box.x + w / 2, box.y + h - f.u(10), 1.5f, g.time);
			if (static_cast<int>(g.time * 2) % 2 == 0)
				ui::textCentered(f, f.game.x + f.game.w / 2, box.y + h + f.u(18), "Tap or press any key to start", ui::WHITE);
			break;
		}
		case Op::Caption:
		{
			float a = std::min(1.0f, std::min(g.beatTime / 0.3f, (2.4f - g.beatTime) / 0.3f));
			ui::caption(f, b.a, std::max(0.0f, a));
			break;
		}
		case Op::Say:
			ui::dialogue(f, g.saySpeaker, g.sayText, static_cast<size_t>(g.sayShown), g.time);
			break;
		case Op::Memory:
		{
			const story::Memory& m = story::MEMORIES[b.n];
			SDL_Texture* photo = b.n < static_cast<int>(g.photos.size()) ? g.photos[b.n] : nullptr;
			ui::memoryCard(f, photo, m.title, m.caption, std::min(1.0f, g.beatTime / 0.3f), g.time);
			break;
		}
		case Op::Message:
		{
			if (!g.messageReady)
			{
				g.message = ui::layoutMessage(f, story::MESSAGE);
				g.messageReady = true;
			}
			if (!g.finalCard)
			{
				ui::messagePage(f, g.message, g.messagePage, std::min(1.0f, g.beatTime / 0.25f), g.time);
			}
			else
			{
				ui::dim(f, 0.45f);
				std::string line = story::FINAL_LINE;
				int big = std::max(1, std::min(f.text * 2, static_cast<int>(f.game.w * 0.85f / (line.size() * 8))));
				float w = std::min(f.game.w - f.u(24), line.size() * 8.0f * big + f.u(40));
				float h = 8.0f * big + f.u(70);
				SDL_FRect box{ f.game.x + (f.game.w - w) / 2, f.game.y + (f.game.h - h) / 2 - f.u(10), w, h };
				ui::panel(f, box);
				ui::textCentered(f, box.x + w / 2, box.y + f.u(14), line, ui::ACCENT, big);
				ui::heart(f, g.sprites.get("heart"), box.x + w / 2, box.y + h - f.u(26), 2.5f, g.time);
				if (g.pageTime > PLAY_AGAIN_DELAY)
				{
					if (static_cast<int>(g.time * 2) % 2 == 0)
						ui::textCentered(f, f.game.x + f.game.w / 2, box.y + h + f.u(16), "Tap to play again", ui::WHITE);
					ui::text(f, f.game.x + f.u(10), f.game.y + f.game.h - f.u(10) - f.glyph(), "< Read it again", ui::WHITE);
				}
			}
			break;
		}
		default:
			break;
	}
	if (!g.inspectText.empty())
		ui::dialogue(f, nullptr, g.inspectText, static_cast<size_t>(g.inspectShown), g.time);

	g.touch.draw(r);
	ui::end(r, LOGICAL_W, LOGICAL_H);
}

// ---------------------------------------------------------------------------
// SDL callbacks
// ---------------------------------------------------------------------------
SDL_AppResult SDL_AppInit(void** appstate, int argc, char* argv[])
{
	Game* g = new Game;
	*appstate = g;
	g->state.width = 1152;
	g->state.height = 864;
	g->state.logW = LOGICAL_W;
	g->state.logH = LOGICAL_H;

	// desktop mouse clicks shouldn't pop up the touch controls
	SDL_SetHint(SDL_HINT_MOUSE_TOUCH_EVENTS, "0");

	if (!engine::initialise(g->state, story::TITLE)) {
		return SDL_APP_FAILURE;
	}

	g->sprites.load(g->state.renderer, g->cache);
	for (const story::Memory& m : story::MEMORIES)
		g->photos.push_back(g->cache.load(g->state.renderer, std::string("assets/memories/") + m.image + ".png"));

	resetStory(*g);
	// --start <label> jumps into the story, e.g. --start stop3 (for testing)
	// --auto turns on the autopilot (see autopilot())
	// --shot <file.png> [seconds] saves the scene after a moment (default 1.5 s) and quits
	for (int i = 1; i < argc; i++)
	{
		if (std::strcmp(argv[i], "--start") == 0 && i + 1 < argc) jumpTo(*g, argv[i + 1]);
		if (std::strcmp(argv[i], "--auto") == 0) g->autoplay = true;
		if (std::strcmp(argv[i], "--shot") == 0 && i + 1 < argc)
		{
			g->shotPath = argv[++i];
			if (i + 1 < argc && argv[i + 1][0] != '-') g->shotTime = static_cast<float>(SDL_atof(argv[++i]));
		}
	}

	g->prevTicks = SDL_GetTicksNS();
	return SDL_APP_CONTINUE;
}

// Where a click or touch landed, from 0 (left edge of the game screen) to 1
// (right edge); the letterbox bars fall outside that.
float screenX(const Game& g, const SDL_Event& event)
{
	SDL_Event e = event;
	SDL_ConvertEventToRenderCoordinates(g.state.renderer, &e);
	float x = e.type == SDL_EVENT_FINGER_DOWN ? e.tfinger.x : e.button.x;
	return x / LOGICAL_W;
}

SDL_AppResult SDL_AppEvent(void* appstate, SDL_Event* event)
{
	Game& g = *static_cast<Game*>(appstate);
	switch (event->type)
	{
		case SDL_EVENT_QUIT:
			return SDL_APP_SUCCESS;
		case SDL_EVENT_KEY_DOWN:
			g.touch.handleEvent(*event);
			if (event->key.repeat) break;
			g.anyKey = true;
			switch (event->key.scancode)
			{
				case SDL_SCANCODE_SPACE: case SDL_SCANCODE_RETURN: case SDL_SCANCODE_KP_ENTER:
				case SDL_SCANCODE_Z: case SDL_SCANCODE_X: case SDL_SCANCODE_E:
					g.action = true;
					break;
				case SDL_SCANCODE_LEFT: case SDL_SCANCODE_A: case SDL_SCANCODE_BACKSPACE: case SDL_SCANCODE_PAGEUP:
					g.back = true;
					break;
				case SDL_SCANCODE_RIGHT: case SDL_SCANCODE_D: case SDL_SCANCODE_PAGEDOWN:
					g.forward = true;
					break;
				case SDL_SCANCODE_1:
					g.debug = !g.debug;
					break;
				case SDL_SCANCODE_F:
					if (g.debug) g.autoplay = !g.autoplay;
					break;
				case SDL_SCANCODE_N:
					if (g.debug)
					{
						// debug: skip ahead to the next labelled point in the story
						for (size_t i = g.beat + 1; i < story::BEATS.size(); i++)
							if (story::BEATS[i].op == Op::Label) { jumpTo(g, story::BEATS[i].a); break; }
					}
					break;
				default:
					break;
			}
			break;
		case SDL_EVENT_MOUSE_BUTTON_DOWN:
			if (event->button.which != SDL_TOUCH_MOUSEID) // taps arrive as finger events
			{
				g.tap = true;
				g.tapX = screenX(g, *event);
			}
			break;
		case SDL_EVENT_WINDOW_RESIZED:
			g.state.width = event->window.data1;
			g.state.height = event->window.data2;
			g.messageReady = false; // re-flow the message for the new size
			break;
		default:
			if (event->type == SDL_EVENT_FINGER_DOWN) g.fingerX = screenX(g, *event);
			g.touch.handleEvent(*event);
			break;
	}
	return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppIterate(void* appstate)
{
	Game& g = *static_cast<Game*>(appstate);

	// Delta time, capped: browsers stop calling us while the tab is hidden,
	// and a huge first step back would teleport everyone through walls.
	uint64_t now = SDL_GetTicksNS();
	float dt = std::min((now - g.prevTicks) / 1e9f, MAX_DELTA_TIME);
	g.prevTicks = now;

	int w = 0, h = 0;
	SDL_GetRenderOutputSize(g.state.renderer, &w, &h);
	g.touch.setScreenSize(static_cast<float>(w), static_cast<float>(h));
	if (g.touch.consumeAction()) g.action = true;
	if (g.touch.consumeTap())
	{
		g.tap = true;
		g.tapX = g.fingerX;
	}
	int dpad = g.touch.consumeDpadPress();
	if (dpad < 0) g.back = true;
	if (dpad > 0) g.forward = true;

	update(g, dt);
	render(g);
	if (!g.shotPath.empty() && g.time >= g.shotTime)
	{
		// read back at the logical resolution, so one game pixel is one image pixel
		SDL_SetRenderLogicalPresentation(g.state.renderer, 0, 0, SDL_LOGICAL_PRESENTATION_DISABLED);
		SDL_Texture* target = SDL_CreateTexture(g.state.renderer, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_TARGET, LOGICAL_W, LOGICAL_H);
		SDL_SetRenderTarget(g.state.renderer, target);
		render(g);
		SDL_Surface* shot = SDL_RenderReadPixels(g.state.renderer, nullptr);
		bool saved = shot && IMG_SavePNG(shot, g.shotPath.c_str());
		SDL_Log(saved ? "saved %s" : "couldn't save %s", g.shotPath.c_str());
		SDL_DestroySurface(shot);
		SDL_SetRenderTarget(g.state.renderer, nullptr);
		SDL_DestroyTexture(target);
		return saved ? SDL_APP_SUCCESS : SDL_APP_FAILURE;
	}
	SDL_RenderPresent(g.state.renderer);

	g.action = g.tap = g.anyKey = g.back = g.forward = false;
	return SDL_APP_CONTINUE;
}

void SDL_AppQuit(void* appstate, SDL_AppResult result)
{
	Game* g = static_cast<Game*>(appstate);
	if (g)
	{
		g->cache.unload();
		engine::cleanup(g->state);
		delete g;
	}
}
