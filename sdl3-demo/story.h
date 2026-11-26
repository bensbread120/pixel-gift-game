#pragma once
// The whole story, as data: every line of text and the order things happen.
//
// The story here is a TEMPLATE, the same for every gift. {hero}, {partner}
// and {pet} are filled in at startup from assets/gift.txt, which also holds
// everything else a gift changes: the title, the dedication, the six memory
// captions, the long message and the final line. tools/gift.py writes that
// file from an order; the committed one is the placeholder story (Alex, Sam
// and Biscuit the dog). One build of the game serves every gift.
//
// The built-in font is plain ASCII, so stick to straight quotes (') and
// "..." rather than curly quotes or emoji. tools/gift.py cleans gift text.
#include <SDL3/SDL.h>
#include <cstring>
#include <deque>
#include <string>
#include <vector>
#include "engine/texture_cache.h"

enum class Op
{
	Title,     // title screen; waits for any key or tap
	Map,       // fade to another map (a = map name)
	Caption,   // centred text at the top for a couple of seconds (a)
	Say,       // dialogue box (a = speaker, b = line); waits for a tap
	Wake,      // the hero gets out of bed
	PetGo,     // the pet walks to a marker (m) and waits there; doesn't block
	WaitNear,  // free roam until the hero is near marker m (and the pet has arrived)
	WaitOn,    // free roam until the hero steps on a cell of ground kind m
	Memory,    // show memory card n
	Ending,    // everyone lies down on the picnic mat
	Message,   // the long message, then the final card and "play again"
	Label,     // a named point to skip to while testing (a)
};

struct Beat
{
	Op op;
	const char* a = nullptr;
	const char* b = nullptr;
	char m = 0;
	int n = 0;
};

namespace story {

// Shorthand used in TEMPLATE below.
inline Beat title() { return { Op::Title }; }
inline Beat map(const char* name) { return { Op::Map, name }; }
inline Beat caption(const char* text) { return { Op::Caption, text }; }
inline Beat say(const char* who, const char* line) { return { Op::Say, who, line }; }
inline Beat wake() { return { Op::Wake }; }
inline Beat petGo(char marker) { return { Op::PetGo, nullptr, nullptr, marker }; }
inline Beat waitNear(char marker) { return { Op::WaitNear, nullptr, nullptr, marker }; }
inline Beat waitOn(char ground) { return { Op::WaitOn, nullptr, nullptr, ground }; }
inline Beat memory(int index) { return { Op::Memory, nullptr, nullptr, 0, index }; }
inline Beat ending() { return { Op::Ending }; }
inline Beat message() { return { Op::Message }; }
inline Beat label(const char* name) { return { Op::Label, name }; }

// Speakers, as written in the template.
inline const char* PET = "{pet}";
inline const char* PARTNER = "{partner}";

// Things the hero can inspect by facing them and pressing the action button.
// `what` is the object or ground letter from the map legend (world.h).
struct Inspect
{
	const char* map;
	char what;
	const char* text;
};

inline const Inspect INSPECT_TEMPLATE[] = {
	{ "bedroom", 'B', "Still warm. Five more minutes...? {pet} says no." },
	{ "bedroom", 'W', "The sun's up and it's a lovely day." },
	{ "bedroom", 'K', "A whole shelf of well-loved books." },
};

inline const std::vector<Beat> TEMPLATE = {
	title(),

	// --- Scene 1: the bedroom, then downstairs --------------------------------
	label("bedroom"),
	map("bedroom"),
	caption("6:00 am"),
	say(PET, "{hero}! {hero}!! Wake up!"),
	say(PET, "Quick, quick, you HAVE to come outside!"),
	say(PET, "No time to explain. I'll explain outside. Probably."),
	wake(),
	petGo('v'),
	waitOn('v'),
	label("living"),
	map("living"),
	say(PET, "This way! Come ON!"),
	waitOn('e'),

	// --- Scene 2: the village ---------------------------------------------------
	label("village"),
	map("village"),
	say(PET, "Okay! {partner}'s waiting for you somewhere."),
	say(PET, "Don't worry, I know EXACTLY where. Follow me!"),

	label("stop1"),
	petGo('1'),
	waitNear('1'),
	say(PET, "Ooh, WATER. Hang on, I need a drink."),
	memory(0),
	say(PET, "Right! {partner}. Yes. This way!"),

	label("stop2"),
	petGo('2'),
	waitNear('2'),
	say(PET, "This tree smells like EVERY dog in the village."),
	memory(1),
	say(PET, "Okay, okay, I'm focused now."),

	label("stop3"),
	petGo('3'),
	waitNear('3'),
	say(PET, "Shh... it's sleeping. I think we could be friends."),
	memory(2),
	say(PET, "Fine. Let's go before it wakes up."),

	label("stop4"),
	petGo('4'),
	waitNear('4'),
	say(PET, "DUCKS."),
	memory(3),
	say(PET, "They didn't want to be friends. Onwards!"),

	label("stop5"),
	petGo('5'),
	waitNear('5'),
	say(PET, "Do you smell that? Sausages. I'm sure of it."),
	memory(4),
	say(PET, "No sausages. Tragic. This way."),

	label("stop6"),
	petGo('6'),
	waitNear('6'),
	say(PET, "I thought I saw a possum!"),
	memory(5),
	say(PET, "{partner}'s just past here. I PROMISE."),

	// --- Scene 3: the field -------------------------------------------------------
	label("field"),
	petGo('7'),
	waitNear('b'),
	say(PET, "See? Told you I knew the way. Totally planned all that."),
	say(PARTNER, "There you are. Did {pet} take the scenic route?"),
	say(PARTNER, "I'm so glad you could both make it. You're just in time."),

	// --- Scene 4: the picnic ending -------------------------------------------------
	label("ending"),
	ending(),
	message(),
};

// ---------------------------------------------------------------------------
// The gift: loaded from assets/gift.txt by load()
// ---------------------------------------------------------------------------
constexpr int MEMORY_COUNT = 6;

struct Memory
{
	std::string image;   // assets/memories/<image>.png
	std::string title;
	std::string caption;
};

inline std::string HERO_NAME = "Hero";
inline std::string PARTNER_NAME = "Partner";
inline std::string PET_NAME = "Pet";
inline std::string TITLE = "A Little Adventure";
inline std::string DEDICATION;
inline std::string FINAL_LINE = "The end";
inline std::string MESSAGE;
inline std::vector<Memory> MEMORIES;
inline std::vector<Inspect> INSPECTS;
inline std::vector<Beat> BEATS;       // TEMPLATE with the names filled in

// Filled-in text lives here; Beat and Inspect point into it. A deque never
// moves what it already holds, so the pointers stay valid.
inline std::deque<std::string> TEXT;

inline const char* fill(const char* s)
{
	if (!s) return nullptr;
	std::string out = s;
	const std::pair<const char*, const std::string*> names[] = {
		{ "{hero}", &HERO_NAME }, { "{partner}", &PARTNER_NAME }, { "{pet}", &PET_NAME },
	};
	for (const auto& [key, value] : names)
		for (size_t at = out.find(key); at != std::string::npos; at = out.find(key, at + value->size()))
			out.replace(at, std::strlen(key), *value);
	return TEXT.emplace_back(std::move(out)).c_str();
}

// gift.txt is "key: value" lines; "\n" in a value is a line break and "\\"
// a backslash. Lines starting with # are comments. Unknown keys are ignored.
inline std::string unescape(const std::string& s)
{
	std::string out;
	for (size_t i = 0; i < s.size(); i++)
	{
		if (s[i] == '\\' && i + 1 < s.size())
		{
			char c = s[++i];
			out += c == 'n' ? '\n' : c;
		}
		else out += s[i];
	}
	return out;
}

// Read assets/gift.txt and fill in the template. Missing keys keep the
// defaults above, so a half-written file still runs.
inline bool load()
{
	MEMORIES.assign(MEMORY_COUNT, {});
	for (int i = 0; i < MEMORY_COUNT; i++)
		MEMORIES[i].image = "memory" + std::to_string(i + 1);

	std::string path = engine::assetPath("gift.txt");
	size_t size = 0;
	char* data = static_cast<char*>(SDL_LoadFile(path.c_str(), &size));
	bool ok = data != nullptr;
	if (!ok) SDL_Log("Couldn't load %s: %s", path.c_str(), SDL_GetError());
	std::string text = ok ? std::string(data, size) : std::string();
	SDL_free(data);

	size_t pos = 0;
	while (pos < text.size())
	{
		size_t end = text.find('\n', pos);
		if (end == std::string::npos) end = text.size();
		std::string line = text.substr(pos, end - pos);
		pos = end + 1;
		if (!line.empty() && line.back() == '\r') line.pop_back();
		size_t colon = line.find(':');
		if (line.empty() || line[0] == '#' || colon == std::string::npos) continue;
		std::string key = line.substr(0, colon);
		std::string value = unescape(line.substr(colon + 1 + (colon + 1 < line.size() && line[colon + 1] == ' ')));

		if (key == "hero") HERO_NAME = value;
		else if (key == "partner") PARTNER_NAME = value;
		else if (key == "pet") PET_NAME = value;
		else if (key == "title") TITLE = value;
		else if (key == "dedication") DEDICATION = value;
		else if (key == "final_line") FINAL_LINE = value;
		else if (key == "message") MESSAGE = value;
		else if (key.size() > 7 && key.compare(0, 6, "memory") == 0)
		{
			// memory1_title, memory1_caption ... memory6_caption
			int i = key[6] - '1';
			if (i < 0 || i >= MEMORY_COUNT) continue;
			if (key.compare(7, std::string::npos, "_title") == 0) MEMORIES[i].title = value;
			if (key.compare(7, std::string::npos, "_caption") == 0) MEMORIES[i].caption = value;
		}
	}

	TEXT.clear();
	BEATS = TEMPLATE;
	for (Beat& b : BEATS)
	{
		b.a = fill(b.a);
		b.b = fill(b.b);
	}
	INSPECTS.clear();
	for (const Inspect& in : INSPECT_TEMPLATE)
		INSPECTS.push_back({ in.map, in.what, fill(in.text) });
	return ok;
}

} // namespace story
