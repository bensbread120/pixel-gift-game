#pragma once
// The whole story, as data: every line of text and the order things happen.
// This is the placeholder story; each gift replaces the names and words here.
//
// The built-in font is plain ASCII, so stick to straight quotes (') and
// "..." rather than curly quotes or emoji.
#include <vector>

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

// Shorthand used in BEATS below.
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

// Speaker names. The game uses PET_NAME to know when the pet is talking.
inline const char* PET_NAME = "Biscuit";
inline const char* PARTNER_NAME = "Sam";

inline const char* TITLE = "A Little Adventure";
inline const char* DEDICATION = "For Alex, with love. Sam";
inline const char* FINAL_LINE = "Happy anniversary";

struct Memory
{
	const char* image;   // assets/memories/<image>.png
	const char* title;
	const char* caption;
};

inline const Memory MEMORIES[] = {
	{ "memory1", "The beginning", "The day we met. I knew straight away there was something about you." },
	{ "memory2", "First trip", "Our first trip away together, and the start of a lot of adventures." },
	{ "memory3", "Home", "The first place that was ours. Small, a bit draughty, and perfect." },
	{ "memory4", "Outdoors", "Long walks, wrong turns and the best views, always with you." },
	{ "memory5", "Dressed up", "We scrub up pretty well together." },
	{ "memory6", "Now", "And here we are. Still my favourite person." },
};

// Things the hero can inspect by facing them and pressing the action button.
// `what` is the object or ground letter from the map legend (world.h).
struct Inspect
{
	const char* map;
	char what;
	const char* text;
};

inline const Inspect INSPECTS[] = {
	{ "bedroom", 'B', "Still warm. Five more minutes...? Biscuit says no." },
	{ "bedroom", 'W', "The sun's up and it's a lovely day." },
	{ "bedroom", 'K', "A whole shelf of well-loved books." },
};

// The long message at the end. Blank lines separate paragraphs; pages are
// split automatically to fit the screen.
inline const char* MESSAGE =
	"Dear Alex,\n"
	"\n"
	"This is where the long message goes. It is the heart of the game, so it "
	"can be as long as you like: the pages are split to fit the screen.\n"
	"\n"
	"Write about the times you've shared, what you love about each other, and "
	"what you're looking forward to next.\n"
	"\n"
	"Love,\n"
	"Sam";

inline const std::vector<Beat> BEATS = {
	title(),

	// --- Scene 1: the bedroom, then downstairs --------------------------------
	label("bedroom"),
	map("bedroom"),
	caption("6:00 am"),
	say(PET_NAME, "Alex! Alex!! Wake up!"),
	say(PET_NAME, "Quick, quick, you HAVE to come outside!"),
	say(PET_NAME, "No time to explain. I'll explain outside. Probably."),
	wake(),
	petGo('v'),
	waitOn('v'),
	label("living"),
	map("living"),
	say(PET_NAME, "This way! Come ON!"),
	waitOn('e'),

	// --- Scene 2: the village ---------------------------------------------------
	label("village"),
	map("village"),
	say(PET_NAME, "Okay! Sam's waiting for you somewhere."),
	say(PET_NAME, "Don't worry, I know EXACTLY where. Follow me!"),

	label("stop1"),
	petGo('1'),
	waitNear('1'),
	say(PET_NAME, "Ooh, WATER. Hang on, I need a drink."),
	memory(0),
	say(PET_NAME, "Right! Sam. Yes. This way!"),

	label("stop2"),
	petGo('2'),
	waitNear('2'),
	say(PET_NAME, "This tree smells like EVERY dog in the village."),
	memory(1),
	say(PET_NAME, "Okay, okay, I'm focused now."),

	label("stop3"),
	petGo('3'),
	waitNear('3'),
	say(PET_NAME, "Shh... it's sleeping. I think we could be friends."),
	memory(2),
	say(PET_NAME, "Fine. Let's go before it wakes up."),

	label("stop4"),
	petGo('4'),
	waitNear('4'),
	say(PET_NAME, "DUCKS."),
	memory(3),
	say(PET_NAME, "They didn't want to be friends. Onwards!"),

	label("stop5"),
	petGo('5'),
	waitNear('5'),
	say(PET_NAME, "Do you smell that? Sausages. I'm sure of it."),
	memory(4),
	say(PET_NAME, "No sausages. Tragic. This way."),

	label("stop6"),
	petGo('6'),
	waitNear('6'),
	say(PET_NAME, "I thought I saw a possum!"),
	memory(5),
	say(PET_NAME, "Sam's just past here. I PROMISE."),

	// --- Scene 3: the field -------------------------------------------------------
	label("field"),
	petGo('7'),
	waitNear('b'),
	say(PET_NAME, "See? Told you I knew the way. Totally planned all that."),
	say(PARTNER_NAME, "There you are. Did Biscuit take the scenic route?"),
	say(PARTNER_NAME, "I'm so glad you could both make it. You're just in time."),

	// --- Scene 4: the picnic ending -------------------------------------------------
	label("ending"),
	ending(),
	message(),
};

} // namespace story
