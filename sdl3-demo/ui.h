#pragma once
// Text and panels: dialogue box, memory cards, the long message, title.
//
// Everything here draws in window pixels (logical presentation switched
// off), laid out relative to the letterboxed game area, so text is crisp
// and sized to the screen. Text uses SDL's built-in 8x8 bitmap font at an
// integer scale -- plain ASCII only.
#include <SDL3/SDL.h>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>
#include "world.h"

namespace ui {

const SDL_Color INK{ 58, 38, 48, 255 };
const SDL_Color PAPER{ 255, 249, 236, 255 };
const SDL_Color BORDER{ 74, 52, 66, 255 };
const SDL_Color ACCENT{ 232, 110, 140, 255 };
const SDL_Color WHITE{ 255, 255, 255, 255 };

struct Frame
{
	SDL_Renderer* r = nullptr;
	SDL_FRect game{};   // the letterboxed game area, in window pixels
	float unit = 1;     // window pixels per logical game pixel
	int text = 1;       // text scale (8x8 glyphs drawn at 8*text pixels)

	float glyph() const { return 8.0f * text; }
	float lineH() const { return glyph() * 1.6f; }
	float u(float logical) const { return logical * unit; }
};

inline Frame begin(SDL_Renderer* r, int logW, int logH)
{
	Frame f;
	f.r = r;
	SDL_GetRenderLogicalPresentationRect(r, &f.game);
	f.unit = f.game.w / logW;
	// about 10 logical pixels per glyph, so it's readable on a phone
	f.text = std::max(1, static_cast<int>(std::lround(f.unit * 1.25f)));
	SDL_SetRenderLogicalPresentation(r, 0, 0, SDL_LOGICAL_PRESENTATION_DISABLED);
	SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
	return f;
}

inline void end(SDL_Renderer* r, int logW, int logH)
{
	SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
	SDL_SetRenderLogicalPresentation(r, logW, logH, SDL_LOGICAL_PRESENTATION_LETTERBOX);
}

inline void color(SDL_Renderer* r, SDL_Color c, float alpha = 1.0f)
{
	SDL_SetRenderDrawColor(r, c.r, c.g, c.b, static_cast<Uint8>(c.a * alpha));
}

inline void text(const Frame& f, float x, float y, const std::string& s, SDL_Color c, int scale = 0)
{
	int sc = scale ? scale : f.text;
	color(f.r, c);
	SDL_SetRenderScale(f.r, static_cast<float>(sc), static_cast<float>(sc));
	SDL_RenderDebugText(f.r, std::floor(x / sc), std::floor(y / sc), s.c_str());
	SDL_SetRenderScale(f.r, 1, 1);
}

inline void textCentered(const Frame& f, float cx, float y, const std::string& s, SDL_Color c, int scale = 0)
{
	int sc = scale ? scale : f.text;
	text(f, cx - s.size() * 8.0f * sc / 2, y, s, c, sc);
}

// Word-wrap to at most `maxChars` per line. '\n' forces a break; an empty
// string in the result is a blank line.
inline std::vector<std::string> wrap(const std::string& s, size_t maxChars)
{
	std::vector<std::string> lines;
	size_t start = 0;
	while (start <= s.size())
	{
		size_t nl = s.find('\n', start);
		std::string para = s.substr(start, nl == std::string::npos ? std::string::npos : nl - start);
		std::string line;
		size_t i = 0;
		while (i < para.size())
		{
			size_t sp = para.find(' ', i);
			std::string word = para.substr(i, sp == std::string::npos ? std::string::npos : sp - i);
			i = sp == std::string::npos ? para.size() : sp + 1;
			if (!line.empty() && line.size() + 1 + word.size() > maxChars)
			{
				lines.push_back(line);
				line.clear();
			}
			line += (line.empty() ? "" : " ") + word;
		}
		lines.push_back(line);
		if (nl == std::string::npos) break;
		start = nl + 1;
	}
	return lines;
}

inline void panel(const Frame& f, SDL_FRect rc, SDL_Color fill = PAPER, SDL_Color border = BORDER)
{
	float b = std::max(2.0f, f.u(2));
	color(f.r, border);
	SDL_FRect outer{ rc.x - b, rc.y, rc.w + 2 * b, rc.h };
	SDL_RenderFillRect(f.r, &outer);
	SDL_FRect outer2{ rc.x, rc.y - b, rc.w, rc.h + 2 * b };
	SDL_RenderFillRect(f.r, &outer2);
	color(f.r, fill);
	SDL_RenderFillRect(f.r, &rc);
	// a soft inner line, like an old RPG text box
	color(f.r, border, 0.25f);
	SDL_FRect inner{ rc.x + b, rc.y + b, rc.w - 2 * b, rc.h - 2 * b };
	SDL_RenderRect(f.r, &inner);
}

// A small bouncing "next" arrow.
inline void nextArrow(const Frame& f, float x, float y, float time)
{
	float s = f.u(3), bob = std::sin(time * 6) > 0 ? f.u(1) : 0;
	color(f.r, ACCENT);
	for (int i = 0; i < 3; i++)
	{
		SDL_FRect row{ x - s + i * s / 3 * 1.0f, y + bob + i * s / 3, (3 - i) * s * 2 / 3, s / 3 };
		SDL_RenderFillRect(f.r, &row);
	}
}

// Dialogue box along the bottom of the screen. `shown` = characters revealed
// so far (typewriter effect); returns the total length so the caller knows
// when it's fully shown.
inline size_t dialogue(const Frame& f, const char* speaker, const std::string& line, size_t shown, float time)
{
	float margin = f.u(8);
	float padX = f.u(9), padY = f.u(7);
	SDL_FRect box{ f.game.x + margin, 0, f.game.w - 2 * margin, 0 };
	size_t maxChars = static_cast<size_t>((box.w - 2 * padX) / f.glyph());
	std::vector<std::string> lines = wrap(line, maxChars);
	box.h = padY * 2 + std::max<size_t>(lines.size(), 2) * f.lineH() - (f.lineH() - f.glyph());
	box.y = f.game.y + f.game.h - margin - box.h;
	panel(f, box);

	if (speaker && *speaker)
	{
		std::string name(speaker);
		SDL_FRect tag{ box.x + padX * 0.6f, box.y - f.glyph() - f.u(6), name.size() * f.glyph() + f.u(10), f.glyph() + f.u(6) };
		panel(f, tag, ACCENT, BORDER);
		text(f, tag.x + f.u(5), tag.y + f.u(3), name, WHITE);
	}

	size_t total = 0, left = shown;
	for (size_t i = 0; i < lines.size(); i++)
	{
		std::string visible = lines[i].substr(0, std::min(left, lines[i].size()));
		text(f, box.x + padX, box.y + padY + i * f.lineH(), visible, INK);
		left -= std::min(left, lines[i].size());
		total += lines[i].size();
	}
	if (shown >= total)
		nextArrow(f, box.x + box.w - padX, box.y + box.h - padY - f.u(3), time);
	return total;
}

// A short line of text in a little box at the top centre (e.g. the time).
inline void caption(const Frame& f, const std::string& s, float alpha)
{
	float w = s.size() * f.glyph() + f.u(16), h = f.glyph() + f.u(12);
	SDL_FRect box{ f.game.x + (f.game.w - w) / 2, f.game.y + f.u(14), w, h };
	panel(f, box, SDL_Color{ PAPER.r, PAPER.g, PAPER.b, static_cast<Uint8>(255 * alpha) },
	      SDL_Color{ BORDER.r, BORDER.g, BORDER.b, static_cast<Uint8>(255 * alpha) });
	text(f, box.x + f.u(8), box.y + f.u(6), s, SDL_Color{ INK.r, INK.g, INK.b, static_cast<Uint8>(255 * alpha) });
}

inline void dim(const Frame& f, float alpha)
{
	SDL_SetRenderDrawColor(f.r, 20, 14, 24, static_cast<Uint8>(255 * alpha));
	SDL_FRect all{ 0, 0, 100000, 100000 };
	SDL_RenderFillRect(f.r, &all);
}

// A memory: dimmed screen, the pixel-art photo in a frame, title and caption.
inline void memoryCard(const Frame& f, SDL_Texture* photo, const char* title, const char* caption, float appear, float time)
{
	dim(f, 0.6f * appear);
	float pw = photo ? photo->w * f.unit : f.u(200), ph = photo ? photo->h * f.unit : f.u(150);
	float pad = f.u(10), margin = f.u(6);
	// long captions use the full screen width, and the photo shrinks if it must
	std::vector<std::string> lines = wrap(caption, static_cast<size_t>((f.game.w - 2 * margin - 2 * pad) / f.glyph()));
	float textW = 0;
	for (const std::string& line : lines) textW = std::max(textW, line.size() * f.glyph());
	float textH = pad + f.lineH() + pad * 0.6f + lines.size() * f.lineH() + pad * 0.6f;
	float shrink = std::min(1.0f, (f.game.h - 2 * margin - textH) / ph);
	pw *= shrink;
	ph *= shrink;
	float w = std::max(std::max(pw, textW) + pad * 2, f.u(150));
	float h = textH + ph;
	float slide = (1 - appear) * f.u(20);
	SDL_FRect card{ f.game.x + (f.game.w - w) / 2, f.game.y + (f.game.h - h) / 2 + slide, w, h };
	panel(f, card);
	textCentered(f, card.x + w / 2, card.y + pad * 0.8f, title, ACCENT);
	SDL_FRect dst{ card.x + (w - pw) / 2, card.y + pad + f.lineH(), pw, ph };
	color(f.r, BORDER);
	SDL_FRect frameRc{ dst.x - f.u(2), dst.y - f.u(2), dst.w + f.u(4), dst.h + f.u(4) };
	SDL_RenderFillRect(f.r, &frameRc);
	if (photo) SDL_RenderTexture(f.r, photo, nullptr, &dst);
	for (size_t i = 0; i < lines.size(); i++)
		textCentered(f, card.x + w / 2, dst.y + ph + pad * 0.8f + i * f.lineH(), lines[i], INK);
	if (appear >= 1)
		nextArrow(f, card.x + w - pad, card.y + h - pad * 0.7f, time);
}

// Split the message into pages that fit the message panel.
struct MessageLayout
{
	SDL_FRect box{};
	float pad = 0;
	std::vector<std::vector<std::string>> pages;
};

inline MessageLayout layoutMessage(const Frame& f, const std::string& message)
{
	MessageLayout m;
	m.pad = f.u(14);
	float margin = f.u(10);
	m.box = { f.game.x + margin, f.game.y + margin, f.game.w - 2 * margin, f.game.h - 2 * margin };
	size_t maxChars = static_cast<size_t>((m.box.w - 2 * m.pad) / f.glyph());
	size_t perPage = static_cast<size_t>((m.box.h - 2 * m.pad - f.lineH()) / f.lineH());
	perPage = std::max<size_t>(perPage, 3);
	std::vector<std::string> lines = wrap(message, maxChars);
	std::vector<std::string> page;
	for (const std::string& line : lines)
	{
		if (page.empty() && line.empty()) continue; // no blank line at the top of a page
		page.push_back(line);
		if (page.size() >= perPage)
		{
			m.pages.push_back(page);
			page.clear();
		}
	}
	while (!page.empty() && page.back().empty()) page.pop_back();
	if (!page.empty()) m.pages.push_back(page);
	return m;
}

inline void messagePage(const Frame& f, const MessageLayout& m, int page, float appear, float time)
{
	dim(f, 0.45f * appear);
	panel(f, m.box);
	if (page < 0 || page >= static_cast<int>(m.pages.size())) return;
	const std::vector<std::string>& lines = m.pages[page];
	for (size_t i = 0; i < lines.size(); i++)
		text(f, m.box.x + m.pad, m.box.y + m.pad + i * f.lineH(), lines[i], INK);

	// footer: "< Back" on the left, page count in the middle, and on the right
	// a "next" arrow, or on the last page a nudge that the next tap moves on
	const SDL_Color faint{ INK.r, INK.g, INK.b, 120 };
	float y = m.box.y + m.box.h - m.pad - f.glyph();
	float left = m.box.x + m.pad, right = m.box.x + m.box.w - m.pad, mid = m.box.x + m.box.w / 2;
	bool last = page + 1 == static_cast<int>(m.pages.size());
	if (page > 0) text(f, left, y, "< Back", faint);
	std::string counter = std::to_string(page + 1) + "/" + std::to_string(m.pages.size());
	std::string done = "Finished reading? >";
	float doneX = right - done.size() * f.glyph();
	if (!last || doneX > mid + (counter.size() / 2.0f + 1) * f.glyph())
		textCentered(f, mid, y, counter, faint);
	if (appear < 1) return;
	if (last) text(f, doneX, y, done, ACCENT);
	else nextArrow(f, right, y + f.glyph() - f.u(3), time);
}

inline void heart(const Frame& f, const Sprite& s, float cx, float cy, float scale, float time)
{
	if (!s.tex) return;
	float beat = 1.0f + 0.08f * std::max(0.0f, std::sin(time * 5.0f));
	float w = s.fw * f.unit * scale * beat, h = s.fh * f.unit * scale * beat;
	SDL_FRect dst{ cx - w / 2, cy - h / 2, w, h };
	SDL_RenderTexture(f.r, s.tex, nullptr, &dst);
}

} // namespace ui
