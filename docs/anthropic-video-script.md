# Anthropic Featured-Video Script

**Project:** VárzeaNav — Amazon Seasonal Navigation
**Team:** Gabriel and Ayaan
**Target length:** ~4 minutes (~565 words at 140 WPM)
**Speaker split:** Gabriel takes Q1, Q2, Q4. Ayaan takes Q3 ("How did you use Claude?").
**Voice:** mirrors the [landing page](https://site-virid-zeta-12.vercel.app) — same headlines and key phrases, so the video and the site reinforce each other.

---

## 1. What did you build? *(Gabriel — ~50 sec)*

Hi, I'm Gabriel — and along with my teammate Ayaan, we built **VárzeaNav: Amazon seasonal navigation.**

It's a routing tool for a stretch of river the world map forgot about. We classify every 30-meter pixel of the Amazon basin from JRC Global Surface Water — Copernicus' satellite dataset — into five classes: permanent water, seasonal-active, seasonal-inactive, rarely inundated, and land. Then we run A* shortest-path between two waypoints, every month of the year. Drag the slider — the route reshapes. In dry months it's a 12-kilometer detour through permanent channels. In wet months a **6-kilometer shortcut emerges through flooded forest**, drawn as a dashed line, because that channel only exists for part of the year.

The headline is three numbers: **8 million people. 6,400 kilometers of river. Zero commercial maps for seasonal water.**

---

## 2. Why does it matter? *(Gabriel — ~55 sec)*

In the Amazon, **the river is the road.** School boats. Ambulances. Supply runs. They all plan around the long, year-round route — because the seasonal shortcuts open for about six months a year and disappear from every commercial map. Local operators carry that knowledge in their heads. Outsiders don't.

That's 8 million Amazonians outside the cities for whom the river is their only road. Six months of every year that shortcuts are open and unmapped. Zero commercial mapping services that account for seasonal flooding.

We're not trying to replace local knowledge. We're trying to make the seasonal shape of the Amazon legible to people who don't have ten years on these specific waters — emergency responders, new operators, healthcare logistics, fishing families relocating. **Every minute counts when the river is the road.**

---

## 3. How did you use Claude? *(Ayaan — ~70 sec)*

I'm Ayaan, and I want to tell you exactly how Claude shows up — because it shows up in two very different places.

**First, during development.** Claude Code was our pair-programming partner. It wrote much of our rasterio and numpy plumbing. It tuned the A* cost function — permanent water at 1.0, seasonal-active at 1.5, everything else blocked. It built the test harness that lets unit tests run on toy 4-by-4 rasters instead of downloading 470 megabytes of satellite data on every run. It generated our Playwright end-to-end suite. Plan mode for the architecture. Autonomous execution for the rest.

**Second — inside the running app — Claude does exactly one thing.** We send Sonnet 4.5 the route's length, the kilometers in permanent water, the kilometers in seasonal water, and the longest seasonal segment, and we ask for one sentence — 25 words max — for a small-craft operator. That's the entire AI surface in production. Our system prompt is six lines long. We published it verbatim on the landing page, in a code block, so anyone can read it.

---

## 4. What made your approach thoughtful or different? *(Gabriel — ~65 sec)*

We wrote our position on the landing page in big letters: **"Claude is the translator, not the decoration."**

The polyline you see, every route distance, every pixel classification — all numpy, all A*, fully deterministic. **Pixel counts are scientific data. They're correct, and they're useless to a boat captain.** So Claude does the one thing language models are good at: it turns numbers into a sentence a person can act on. If it's geometric, it came from satellite data. If it's a sentence, it came from Claude.

We made that boundary visible in the UI. The sidebar has an "Input to Claude" panel that shows the literal values being sent on every request — model, system prompt, every number. Without an API key the app falls back to a deterministic stub, so the demo still works offline.

That's the opposite of how AI usually ships, where the seam is hidden so the magic feels seamless. **We wanted the magic to feel earned.**

---

## Timing breakdown

| Section | Speaker | Words | Time @ 140 WPM |
|---|---|---:|---:|
| Q1 — What did you build | Gabriel | ~140 | ~1:00 |
| Q2 — Why does it matter | Gabriel | ~150 | ~1:04 |
| Q3 — How did you use Claude | Ayaan | ~170 | ~1:13 |
| Q4 — Thoughtful approach | Gabriel | ~155 | ~1:06 |
| **Total** | | **~615** | **~4:23** |

If you need to hit 4:00 flat, trim Q2 (drop the "emergency responders, new operators..." list) and Q4 (drop "if it's geometric / if it's a sentence" — that's the second-strongest line, but the strongest is "translator not the decoration").

## Delivery notes

- **B-roll cut points** (where the editor can drop in the live demo without a hard pause):
  - End of Q1, after "...zero commercial maps for seasonal water" → cut to slider drag dry → wet
  - End of Q2, after "...the river is the road" → cut to school boat / ambulance / supply imagery if available
  - Mid-Q3, after "...published it verbatim on the landing page" → cut to the system-prompt code block on the landing page
  - End of Q4, after "...feel earned" → close on the VárzeaNav logo + URL

- **On-screen text** (chyron / lower thirds): the landing page already has these as headlines, reuse them word-for-word so the video reinforces the site:
  - "Routes that change with the river."
  - "Every minute counts."
  - "Five classes of pixel. One adaptive route."
  - "Claude is the translator, not the decoration."

- **Pull-quote candidates** for the thumbnail / clip teasers:
  1. "Claude is the translator, not the decoration."
  2. "Pixel counts are scientific data. They're correct, and they're useless to a boat captain."
  3. "If it's geometric, it came from satellite data. If it's a sentence, it came from Claude."
  4. "We wanted the magic to feel earned."

- **Tone:** match the landing page — confident, declarative, no hedging. The site doesn't say "we hope this helps" or "we believe this could"; neither should the speech.
