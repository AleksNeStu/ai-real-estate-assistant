# Accessibility — WCAG 2.2 AA

**Standard:** WCAG 2.2 Level AA
**Audited:** 2026-11-18 (the previous audit, 2026-05-09, was WCAG 2.1 and covered the components only)
**Scope:** the assembled routes of the application, in both themes, plus the shared primitives

## The gate

The accessibility of the product is held by a scan, not by a promise.

| The gate | Where it runs | What it proves |
|---|---|---|
| **axe-core over every route** | `e2e/accessibility/accessibility.spec.ts` — 19 routes × 2 themes, at the WCAG 2.2 A/AA rules | the rendered page carries no violation a machine can see |
| **The static rules** | `eslint-plugin-jsx-a11y` in `apps/web/eslint.config.mjs` — the recommended set | the mistake is caught at the line it was written |
| **The unit suites** | `jest-axe` in `apps/web/src/components/ui/__tests__/` | the shared primitives stay clean |
| **Lighthouse** | `apps/web/lighthouserc.js` — accessibility ≥ 0.9 | the pages keep their score in the pipeline |

The axe scan runs inside the CI **e2e** job, so a violation fails the job and the pipeline goes red with
it; the job's summary names the routes it scanned. Nothing is opted in: the scan is part of the
e2e run.

```bash
# the scan, against a running application
cd apps/web && npm run build && npx next start -p 3000 &
PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test e2e/accessibility
```

## What the scan found, and what was changed (2026-11-18)

| The defect | The cause | The fix |
|---|---|---|
| 32 nodes failed the contrast: the muted grey on a muted panel (4.39:1) and the status green as small text (3.03:1) | the tokens were the prototype's shades — a 600-shade green on a light panel is below AA for small text | the status colours moved to the 700 shade of the same hue (`--success`, `--destructive`, `--caution`), the muted grey moved a shade darker, and the chart ramp followed the status green as it already followed `--info` |
| 37 nodes failed "the accessible name must carry the visible text" | the language switcher's name left out the code it shows, and the user menu's name left out the account it shows | the names carry what the reader sees, and the initials and the account's name are two words in the DOM, separated by a real space |
| 6 inputs on the valuation form had no label | the `Field` component rendered a `<label>` without `htmlFor` | the field ties the label to the input with a generated id |
| 13 static findings from the lint rules | a focusable `autoFocus`, a `<dialog>` with a pointer-only backdrop click, a redundant `role="article"`, click handlers on non-interactive elements, a menu that could not take the focus | each one fixed in the component; the backdrop click keeps an `eslint-disable` with the reason (Escape is the keyboard's way out) |

The colours that changed are the ones the acceptance measures against the prototype. The mapping
survived: the prototype's `--ok` and `--er` still match repository tokens by colour, inside the
analyser's threshold — `scripts/design/design_gap.py` reports 12 of 13 tokens matched by colour and
one that is not a colour (`--tilef`, the map's tile filter).

## The known limitation — the map

Three map components draw their markers imperatively, because Leaflet and Mapbox GL build the marker
DOM themselves:

| Component | Library | Limitation |
|-----------|---------|------------|
| `search/property-map.tsx` | Leaflet | markers via `divIcon` with an HTML string |
| `search/property-mapbox-map.tsx` | Mapbox GL JS | markers via `document.createElement` |
| `search/geo-draw-control.tsx` | Mapbox Draw | returns `null`; third-party controls |

A canvas map cannot be read by a screen reader. This is a structural limit, not a list of bugs, and
the conformant path is beside the map: `search/map-controls.tsx` carries the zoom, the filters and
the heat legend as real controls, and the results list beside the map carries every listing as a
link. The axe scan covers those routes and reports them clean.

## The half no scanner can do

The scan sees the markup. It does not see the journey. These are the manual passes, and they belong
to whoever changes a route:

- **The focus order.** Tab through the route: the order follows the reading order, and nothing takes
  the focus that the reader did not ask for.
- **The visible focus.** Every control that takes the focus shows the ring (`--ring`, the teal).
- **The dialog.** `components/ui/modal.tsx` opens with `showModal()`, so the focus is trapped and
  returned to the control that opened it; Escape closes it.
- **The keyboard path of the map.** The controls next to the map are reachable and operable without
  a mouse; the map itself is not, and does not pretend to be.
- **The reduced motion.** The landing's demo clip is never loaded under `prefers-reduced-motion`.

## The files that hold the primitives

| The file | What it holds |
|---|---|
| `apps/web/src/lib/axe-helper.ts` | the `checkA11y` helper the unit suites use |
| `apps/web/src/components/ui/__tests__/*.a11y.test.tsx` | the axe suites over the shared primitives |
| `e2e/accessibility/accessibility.spec.ts` | the axe scan over the assembled routes |
| `apps/web/eslint.config.mjs` | the static rules |
| `apps/web/src/app/globals.css` | the tokens, and their contrast |
