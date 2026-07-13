# Design handoff — BeardMeatsFood stats site restyle

**Date:** 2026-07-13 · **From:** build session · **To:** design session
**Repo:** `C:\dev\BeardArmy` (GitHub: hamishcrichton/BeardArmy, all work on `main`)

## What this is

A four-page fan/stats site for the BeardMeatsFood YouTube channel (Adam Moran, competitive
eater; ~750 restaurant food challenges since 2015, 91% win rate). The data layer is done and
trustworthy — transcripts-based extraction, geocoded venues, weights, collaborators, tours.
The current styling was built quickly by engineers and the owner wants a proper design pass.

## The brief

Owner feedback on the current site — **all four of these need to change**:

1. **Generic dashboard look** — dark cards + bars reads like an admin panel, not a site with
   personality about a man eating a 20 lb Christmas dinner.
2. **Typography** — display font never loads ("Thunder" isn't shipped; falls back to Impact),
   body is default Roboto/Arial. Feels cheap.
3. **Colour scheme** — near-black `#1a1a1a` + neon yellow `#e0ff00` accent isn't appealing.
4. **Layout & density** — long single-column card stacks; no hierarchy, no hero moments, no
   imagery outside the Wall of Shame.

**Direction: designer's choice.** Deliberately not prescribed. Expected flow:

> **First propose 3–4 distinct visual directions** (each: background/surface palette, accent
> system, display + body typefaces, and one hero-section mock of the Overview page, with a
> one-line rationale). The owner picks one; only then restyle the site. Avoid generic-AI
> aesthetics: no Inter/Roboto, no purple-gradient-on-dark, no cookie-cutter dashboard shells.

## How to view the current state

```bash
cd C:\dev\BeardArmy
python -m http.server 8123
# then open:
#   http://localhost:8123/preview/index.html      (Overview: stat tiles, form guide, challenge calendar)
#   http://localhost:8123/preview/map.html        (Map & Tours: cluster map*, trip scrubber, world choropleth)
#   http://localhost:8123/preview/analytics.html  (charts: cuisine/country win rates, per-year, weights, views, collaborators)
#   http://localhost:8123/preview/records.html    (superlatives cards, Wall of Shame)
# *basemap needs a free MapTiler key pasted into the page (remembered in localStorage)
```

## What design owns (change freely)

- `frontend/styles/tokens.css` — the design-token surface (colours, type, spacing, radii, shadows).
- `preview/assets/app.css` — shared component styles (cards, tiles, nav, badges, charts, tooltip).
- All four page files (`preview/*.html`) — markup, layout, IA. The four-page split is a
  suggestion, not a law; merge or re-split if a better structure emerges.
- Fonts: self-host in `preview/assets/` or load from a font CDN — both fine. This is a normal
  website (no CSP restrictions); CDNs are already used for MapLibre.
- Chart *styling* (colours, marks, spacing, labels) — the chart *logic* is hand-rolled SVG in
  each page's script and is easy to restyle via constants.

## Contract to keep (do not break)

- **Data plumbing:** `preview/assets/app.js` — `BMF.loadData()` returns `{rows, features, stats}`
  from `public/data/table.json` + `challenges.geojson`. Row fields: `video_id, title, restaurant,
  city, country_code, date_attempted, result (success|failure|unknown), type, cuisine, food_type,
  weight_lb, view_count, collaborators[], trip_name, thumbnail_url, place_source` + six 0-10
  difficulty scores. Keep pages reading from this contract; extend `app.js` if needed.
- **Result semantics are sacred:** win/loss/unknown must stay distinguishable for colour-blind
  users (current pair `#00d084`/`#ff4d4f` passes deutan ΔE 24.8 on the dark surface — if the
  palette changes, re-validate) and results must **never be encoded by colour alone**
  (current redundancies: position in the form guide, labelled badges, tooltips, legends).
- **Chart integrity:** one axis per chart, no dual-axis; sequential scales = one hue; direct
  labels over label-every-point; legends whenever >1 series.
- **No build step** unless the chosen direction genuinely requires it — the repo ethos is
  static files + CDN. If a build is proposed, flag it explicitly before implementing.
- **Performance:** 747 rows client-side is trivial today; the Wall of Shame lazy-loads ~60
  YouTube thumbnails; the world map is a vendored 108 KB topojson. Keep it that light.

## Content worth designing around (all real, from the data)

- Career record **625–62** (91.0% win rate), longest win streak **49**, current streak 15.
- The **challenge calendar** shows his upload discipline (every Sunday for 2 years straight).
- His weakest cuisines: **fish & chips (80%)** and **desserts (82%)** — a British eater beaten
  most often by the national dish.
- **Mrs Beard**: 51 collaborations. Cameos from Randy Santel, Joey Chestnut.
- The heaviest conquest: a **20 lb Christmas dinner**. Modal challenge weight: 4–6 lb.
- The **Wall of Shame** — the ~60 challenges that beat him (YouTube thumbnails, high-energy
  imagery — currently the most characterful element on the site).
- Every row links to its YouTube video; thumbnails exist for all 747 (`thumbnail_url`, 480p).
- `view_count` per video is being backfilled today — "most-viewed" and "does failure sell?"
  visuals light up automatically once it lands.

## Channel brand — observed 2026-07-13 (not from memory)

Reviewed youtube.com/@BeardMeatsFood (6.66M subs, 746 videos) and beardmeatsfood.co.uk:

- **The logo is the brand**: a circular butcher-shop-style stamp/roundel — "BEARD · MEATS ·
  FOOD" stacked in bold condensed block caps, a beard silhouette integrated into the
  lettering, crossed knife-and-fork on top, and a curved strapline underneath: *"THE UK'S
  HAIRIEST COMPETITIVE EATER"*. Vintage label/craft aesthetic, not sports-graphics. Exists in
  black-on-light (YouTube avatar) and grey/white-on-dark (official site header) versions.
- **Official site** (beardmeatsfood.co.uk, merch-led): near-black background (~#191919),
  monochrome white/grey logo and type, minimal chrome (hamburger + SHOP button). So a dark,
  monochrome, logo-centric identity is authentic to the brand — but note the owner dislikes
  the current site's colour treatment, so "dark" is not automatically the answer.
- **The neon yellow `#e0ff00` in our tokens.css is NOT observed core brand.** The channel and
  official site are black/white/grey; bright yellow appears only incidentally (restaurant
  walls in some thumbnails). Treat the neon as an assumption to be re-examined, not a brand
  requirement.
- **Thumbnails are the personality**: real photography, notably restrained for YouTube — no
  text overlays, no arrows, no shocked faces. Format: Adam (backwards black cap, beard, dark
  t-shirt) seated behind an absurdly large food spread in an actual restaurant interior,
  warm saturated food tones, staff/locals often in frame. We have one per video
  (`thumbnail_url`) — photography can and should carry the site's character.
- **Voice**: all-caps narrative titles ("NOBODY HAS EVER BEATEN 'THE EIGHTH WONDER OF THE
  WORLD' CHALLENGE!"), self-deprecating tagline ("That hairy guy who eats a lot…"), British
  understatement in the endings. Any copy in the redesign should sound like that — confident,
  wry, never corporate.
- **Type feel in the logo**: condensed industrial block caps (think tall grotesque/athletic
  block, hand-finished edges) — a good anchor for display-type choices.

## Other reference material

- Current token values: see `frontend/styles/tokens.css` (dark bg + neon accent,
  Thunder/Roboto stack, spacing/radius/shadow scales) — replace wholesale if the chosen
  direction differs.
- `docs/tokens-audit.md` — an earlier audit of the token set.

## Out of scope

- The ingestion pipeline, database, eval harness, CI — all frozen for this pass.
- Data corrections (restaurant names, results) — handled separately.
- Deployment changes (Flask/`application.py` serves `preview/` + `public/data/` as-is).
