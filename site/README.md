# VárzeaNav — Landing Page (`/site/`)

Marketing landing page for **VárzeaNav**, the Amazon seasonal-navigation
hackathon project (CBC AI Builders Hackathon, IIT, May 2026).

> **This directory is independent of `/backend/` (Flask) and `/frontend/`
> (Leaflet).** Building, installing, or running the site does not require
> Python, does not import from those directories, and does not change them.
> Edit those projects in their own directories.

## Stack

- React 18 + TypeScript (strict mode)
- Vite 5
- Tailwind CSS 3 (`darkMode: "class"`)
- Framer Motion for entrance/scroll animations
- `lucide-react` icons
- `clsx` + `tailwind-merge` via a tiny `cn()` helper

## Install & run

```bash
cd site
npm install        # or pnpm install / yarn
npm run dev        # http://localhost:5173
npm run build      # type-checks then bundles to dist/
npm run preview    # serve the production build
```

## Environment

Copy `.env.example` to `.env.local` to point the "See the live demo" CTAs
somewhere other than the default localhost backend:

```env
# .env.local
VITE_DEMO_URL=http://localhost:5050         # default
# VITE_DEMO_URL=https://demo.varzeanav.app   # override for ngrok / prod
```

If `VITE_DEMO_URL` resolves to `localhost`, the Demo section also renders a
small grey hint reminding visitors to start the Flask backend with
`python backend/app.py` from the repo root.

## Demo screenshots

The Demo section renders dashed 16:10 placeholders until you drop in:

- `site/public/demo-classification.png` — VárzeaNav classification map (the
  Leaflet view on `/frontend/` with the green/red corridor routes visible).
- `site/public/demo-satellite.png` — the same viewport on the satellite
  basemap.

Recommended resolution: 1600×1000 (or any 16:10 PNG / WebP).

## Fonts

Loaded via Google Fonts in `index.html`:

- **Outfit** (display + wordmark)
- **Inter** (body)
- **JetBrains Mono** (coordinates, system-prompt callout)

Swap in `index.html` and `tailwind.config.ts → theme.extend.fontFamily` if the
deck uses different families.

## Theme

- `useTheme` reads `localStorage.theme`, falls back to `prefers-color-scheme`.
- A synchronous inline script in `index.html` `<head>` applies `.dark` to
  `<html>` before React mounts, so there is no flash of incorrect theme.
- The toggle button (top-right of nav, mirrored in footer) animates a 150ms
  cross-fade between sun and moon icons.

## Deploying to Vercel

The site lives in a subdirectory of a Python monorepo, so Vercel needs to know
which folder to build. Two paths:

### Option A — GitHub import (recommended)

1. Push the repo to GitHub if you haven't already.
2. In the Vercel dashboard: **Add New → Project**, pick the repo.
3. On the configuration screen, set **Root Directory** to `site`. Vercel will
   auto-detect Vite from `site/package.json` and use the `site/vercel.json`
   config (build command `npm run build`, output `dist`).
4. Add the env var **`VITE_DEMO_URL`** under Project Settings → Environment
   Variables. Set it to your live Flask backend URL (or leave it unset to fall
   back to `http://localhost:5050`, which is fine for previews).
5. Deploy. Subsequent pushes to the default branch auto-deploy.

### Option B — Vercel CLI

```bash
npm i -g vercel
cd site                        # ← run from inside site/, not repo root
vercel                         # first run links the project
vercel --prod                  # production deploy
```

Set `VITE_DEMO_URL` with `vercel env add VITE_DEMO_URL`.

## Project layout

```
site/
├── public/
│   ├── demo-classification.png   ← drop in
│   └── demo-satellite.png        ← drop in
├── src/
│   ├── components/
│   │   ├── Demo.tsx
│   │   ├── Footer.tsx
│   │   ├── Hero.tsx
│   │   ├── HowItWorks.tsx
│   │   ├── Logo.tsx
│   │   ├── Nav.tsx
│   │   ├── Problem.tsx
│   │   ├── Roadmap.tsx
│   │   ├── ThemeToggle.tsx
│   │   └── UseOfAI.tsx
│   ├── hooks/useTheme.ts
│   ├── lib/cn.ts
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
├── index.html
├── package.json
├── tailwind.config.ts
├── postcss.config.js
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── .env.example
└── .gitignore
```

## Judgment calls

A few decisions made without round-tripping for clarification — all easy to
change in one place:

1. **`npm` instead of `pnpm`.** The brief asked for pnpm, but no pnpm binary
   was available on the build machine. The lockfile-agnostic `package.json`
   works the same with `pnpm install`; switch freely.
2. **Logo SVG.** Recreated from the description in the brief: light-green
   radial-gradient outer disk, two diagonal river swooshes (one green, one
   green→blue), centered dark-green map pin. The two swooshes rotate
   together at 60s linear infinite, gated by `prefers-reduced-motion`.
   Replace `src/components/Logo.tsx` if the deck has a tighter spec.
3. **GitHub URL** is a placeholder (`https://github.com/`) in `Nav.tsx` and
   `Footer.tsx`. Edit both constants when the public repo URL is final.
4. **Mobile menu** is a full-bleed sheet below the sticky header (not a
   hamburger drawer), per the spec's "full-height sheet with the same
   anchors." Background uses `bg-bg/98 backdrop-blur-md` for readability.
5. **Demo screenshot placeholders** render as dashed 16:10 boxes labeled
   with their target file path. They become real `<img>` tags as soon as
   you drop the PNGs in `public/` — no code change needed beyond replacing
   the `Placeholder` component if you want HTML semantics, but the dashed
   look is intentional until the assets land.
6. **Claude advisory quote** in the Demo section is the illustrative example
   from the brief. The real advisory is generated by the live demo at the
   linked URL — this page just shows what one looks like.
7. **System-prompt callout** is quoted byte-for-byte from
   `backend/advisory.py`. Verify if `advisory.py` changes.
