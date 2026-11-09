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
