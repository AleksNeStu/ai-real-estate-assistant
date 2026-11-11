# Materials — the house style

> **Status:** Rule (operator, 2026-11-09). Applies to everything the studio
> publishes about this project.
> **Rule:** the materials are **dark**.

## What the rule covers

| Material | Where it lives | Theme |
|---|---|---|
| The README and the images in it | `README.md`, `assets/screenshots/` | dark |
| The screenshots of the application | `assets/screenshots/*-dark.png` | dark |
| The social preview card | `.github/social-preview.svg` + `.png` | dark |
| The demo clips and the creatives | `assets/` | dark |
| The launch drafts | `docs/marketing/` | dark where they carry an image |
| The design references | `docs/reviews/` | dark |

The application itself keeps both themes — the visitor chooses in the top bar.
The rule is about the **materials**, not about the product: a link preview, a
directory listing and a README are read on a screen, and the dark material is
the one that survives the crop.

## How the screenshots are made

One command, from the repository root:

```bash
node scripts/utils/take_screenshots.js https://realty.kittray.com dark assets/screenshots -dark
```

| Argument | Meaning |
|---|---|
| the address | the deployment the material shows — always the live one, never a local build |
| the theme | `dark` for the materials |
| the folder | `assets/screenshots` for the dark set, `docs/screenshots` for the light one |
| the suffix | `-dark`, so both sets can live side by side |

The script captures the chat with a real question and waits for the answer, so
the image shows a conversation rather than an empty panel. The first-visit tour
is remembered as seen, and the service worker is left alone (it does not
interfere with the capture).

## How the clip is made

The six-second clip is three scenes of the live deployment — the landing, the
search with its results, the assistant answering with its sources — cut into one
master and one inline GIF.

```bash
node scripts/utils/capture_demo_clip.js https://realty.kittray.com chat
bash scripts/utils/build_demo_clip.sh
```

| Asset | Where | What it is |
|---|---|---|
| The frames | `tmp/clip/*.png` | the three scenes, an intermediate, not published |
| `demo-6s.mp4` | `assets/clips/` | the master — what the landing plays |
| `demo-6s.gif` | `assets/clips/` | what a forum post inlines |
| `poster.png` | `assets/clips/` | the frame the landing shows before the play button |

Two traps, both of them paid for in a real published frame:

- **The free tier answers with the error inside a 200.** An address gets 20
  requests an hour and 200 a day (`apps/api/utils/free_tier.py`), and the chat
  delivers "Hourly limit exceeded" as a normal answer. A capture that checks
  only the status code publishes the error. The capture reads the pane and
  rejects the frame.
- **At document-start `document.documentElement` is still null.** A
  `classList.add("dark")` in an init script throws there, and inside one script
  every statement after the throw is skipped — including the flag that
  dismisses the onboarding tour. Every statement carries its own guard, and the
  two init scripts stay separate.

## The old set — retired

`assets/screenshots/slideshow.gif` was the light-theme animation of the
application from before the redesign (2026-06-17). It was **retired** on
2026-11-11 rather than re-cut: nothing referenced it, it showed screens that
no longer exist, and the light theme breaks the house style. The dark
animation is `assets/clips/demo-6s.gif` — the six-second clip of the
application as it runs.

## How the copy is written

The rules of the design system apply to the materials as well:

1. **Mono for data.** Every number, price, route and argument is in mono —
   `17` providers, `$29/mo`, `/en/search`. Mono is for data, never for labels.
2. **No eyebrows.** A label states what a thing is; it does not shout.
3. **Ledgers, not cards.** A list, a comparison or a set of features is rows
   with a rule between them. A card is for an object that is an object.
4. **One teal action.** One primary action per screen, per image, per card.
5. **Geist and Geist Mono only.** No serif, no italic. Weight carries the
   hierarchy.

## The palette the materials use

The tokens live in `apps/web/src/app/globals.css` and are asserted against the
prototype by `apps/web/src/lib/__tests__/palette-tokens.test.ts`:

| Role | Token |
|---|---|
| The chrome | `--background`, `--card`, `--border` — the zinc scale |
| The one action | `--action` / `--action-foreground` — teal |
| The attention | `--warning-surface`, `--warning` — amber, for what needs a key |
| The status | `--success`, `--destructive` — green and red keep their meaning |
| The data | Geist Mono, for every number, price, route and argument |
