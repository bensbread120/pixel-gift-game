#pragma once
#include <SDL3/SDL.h>
#include <algorithm>
#include <cmath>
#include <unordered_map>

// The player's controls for this frame, merged from keyboard and touch so
// game logic doesn't care which one is being used.
struct PlayerInput
{
	bool up = false, down = false, left = false, right = false;
};

// On-screen d-pad (bottom left) and action button (bottom right) for phones.
// The action button talks, inspects and moves the story on; a tap anywhere
// else also counts as a tap (to skip through text).
// Hidden until the first touch, and hidden again on a key press, so desktop
// players never see them.
//
// Laid out and drawn in window pixels rather than the game's logical
// resolution, so the buttons can sit in the letterbox bars and stay a
// thumb-friendly size whatever the screen.
class TouchControls
{
	enum class Zone { None, Dpad, Action };
	struct Finger { Zone zone; float x, y; }; // position in output pixels

	std::unordered_map<SDL_FingerID, Finger> fingers;
	bool actionPressed = false;
	bool tapped = false;
	int dpadPress = 0;  // -1 / +1: the d-pad was pressed on its left / right side
	float w = 0, h = 0; // render output size in pixels, refreshed every frame

	// Button size scales with the shorter screen side.
	float unit() const { return std::min(w, h) * 0.12f; }
	float margin() const { return unit() * 0.5f; }
	SDL_FPoint dpadCentre() const { return { margin() + unit() * 1.5f, h - margin() - unit() * 1.5f }; }
	SDL_FPoint actionCentre() const { return { w - margin() - unit() * 1.2f, h - margin() - unit() * 1.5f }; }

	static float dist(float x, float y, SDL_FPoint p) { return std::hypot(x - p.x, y - p.y); }

	Zone zoneAt(float x, float y) const
	{
		// generous hit areas: thumbs are imprecise and you can't see under them
		if (dist(x, y, dpadCentre()) < unit() * 2.2f) return Zone::Dpad;
		if (dist(x, y, actionCentre()) < unit() * 1.4f) return Zone::Action;
		return Zone::None;
	}

public:
	bool visible = false;

	// Call once per frame before handling events, with the renderer's output size.
	void setScreenSize(float width, float height) { w = width; h = height; }

	// Returns true if the event was a touch event (consumed here).
	bool handleEvent(const SDL_Event& event)
	{
		switch (event.type)
		{
			case SDL_EVENT_KEY_DOWN:
				visible = false; // switched to a keyboard
				return false;
			case SDL_EVENT_FINGER_DOWN:
			{
				visible = true;
				// finger coordinates are normalised 0..1 across the window
				float x = event.tfinger.x * w, y = event.tfinger.y * h;
				Zone zone = zoneAt(x, y);
				fingers[event.tfinger.fingerID] = { zone, x, y };
				if (zone == Zone::Action) actionPressed = true;
				if (zone == Zone::None) tapped = true;
				if (zone == Zone::Dpad)
				{
					float dx = x - dpadCentre().x;
					if (std::abs(dx) > unit() * 0.35f) dpadPress = dx < 0 ? -1 : 1;
				}
				return true;
			}
			case SDL_EVENT_FINGER_MOTION:
			{
				auto it = fingers.find(event.tfinger.fingerID);
				if (it != fingers.end())
				{
					// a finger keeps the button it started on, so sliding a
					// thumb around the d-pad changes direction without lifting
					it->second.x = event.tfinger.x * w;
					it->second.y = event.tfinger.y * h;
				}
				return true;
			}
			case SDL_EVENT_FINGER_UP:
			case SDL_EVENT_FINGER_CANCELED:
				fingers.erase(event.tfinger.fingerID);
				return true;
		}
		return false;
	}

	// True once per press of the action button.
	bool consumeAction()
	{
		bool pressed = actionPressed;
		actionPressed = false;
		return pressed;
	}

	// True once per tap outside the buttons.
	bool consumeTap()
	{
		bool t = tapped;
		tapped = false;
		return t;
	}

	// -1 / +1 once per press on the left / right of the d-pad (for paging).
	int consumeDpadPress()
	{
		int d = dpadPress;
		dpadPress = 0;
		return d;
	}

	// OR the d-pad into `input`. A dead zone in the middle; past it, each axis
	// counts on its own, so diagonals work.
	void applyTo(PlayerInput& input) const
	{
		SDL_FPoint c = dpadCentre();
		float dead = unit() * 0.35f;
		for (const auto& [id, f] : fingers)
		{
			if (f.zone != Zone::Dpad) continue;
			float dx = f.x - c.x, dy = f.y - c.y;
			if (dx < -dead) input.left = true;
			if (dx > dead) input.right = true;
			if (dy < -dead) input.up = true;
			if (dy > dead) input.down = true;
		}
	}

	// Draw in output pixels. The caller must have logical presentation off.
	void draw(SDL_Renderer* renderer) const
	{
		if (!visible) return;

		PlayerInput held;
		applyTo(held);
		bool actionHeld = false;
		for (const auto& [id, f] : fingers)
			if (f.zone == Zone::Action) actionHeld = true;

		SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
		auto button = [&](float cx, float cy, float size, bool pressed) {
			SDL_FRect r{ cx - size / 2, cy - size / 2, size, size };
			SDL_SetRenderDrawColor(renderer, 255, 255, 255, pressed ? 140 : 60);
			SDL_RenderFillRect(renderer, &r);
			SDL_SetRenderDrawColor(renderer, 255, 255, 255, 160);
			SDL_RenderRect(renderer, &r);
		};

		float u = unit();
		SDL_FPoint d = dpadCentre();
		button(d.x, d.y - u, u, held.up);
		button(d.x, d.y + u, u, held.down);
		button(d.x - u, d.y, u, held.left);
		button(d.x + u, d.y, u, held.right);

		SDL_FPoint a = actionCentre();
		button(a.x, a.y, u * 1.4f, actionHeld);
		// an "A" on the action button
		float s = u * 0.12f;
		SDL_SetRenderDrawColor(renderer, 255, 255, 255, 200);
		SDL_SetRenderScale(renderer, s, s);
		SDL_RenderDebugText(renderer, (a.x - 4 * s) / s, (a.y - 4 * s) / s, "A");
		SDL_SetRenderScale(renderer, 1, 1);
		SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
	}
};
