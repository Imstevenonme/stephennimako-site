# content.json — Schema

Data file for the portfolio page (`index.html`). It is fetched with
`fetch("content.json")` on page load and rendered into the page with vanilla
JS. **All editable text from the original page lives here, copied verbatim.**
The only intentional text split is `hero.intro` / `hero.tagline` (see below).

## Text conventions

- **Bold:** the original used `<strong>` inside paragraphs and bullets.
  In JSON this is written as `**double asterisks**` (e.g.
  `"I'm an IT Support Engineer at **Amazon in Austin, Texas**, …"`).
  The renderer escapes the text first, then converts `**…**` to `<strong>` —
  JSON text can never inject raw HTML.
- **Escaping:** every JSON string reaches the DOM via `textContent` (or the
  `**bold**` rule above). Link `href`s are allow-listed to
  `https://`, `http://`, `mailto:`, `#anchor`, and relative paths ending in
  `.pdf` (for the résumé file served alongside the page) — anything else
  falls back to `#`.
- Dashes, middots, arrows, and `&` are stored as literal Unicode characters
  (`—`, `·`, `→`, `&`), exactly as they render.

## Top-level keys

```json
{
  "hero":           { "name", "role", "roles", "tagline", "intro", "ctas", "stats" },
  "about":          { "heading", "note", "paragraphs", "facts" },
  "experience":     [ { "company", "role", "period", "location", "current", "bullets", "tags" } ],
  "skills":         [ { "category", "blurb", "group", "icon", "items" } ],
  "certifications": [ { "name", "issuer", "date", "badge", "badgeAccent", "description", "meta", "credentialId" } ],
  "education":      { "school", "degree", "period", "mark", "description", "details", "tags" },
  "dojo":           [ { "title", "date", "summary", "tags", "link" } ],
  "dojo_loop":      { "title", "text", "steps" },
  "dojo_tracks":    [ { "title", "status", "statusClass", "description", "progress" } ],
  "dojo_empty":     { "mono", "text" },
  "path":           { "heading", "note", "intro", "milestones" },
  "contact":        { "heading", "subheading", "text", "email", "linkedin", "github" },
  "sections":       { "<id>": { "heading", "note"?, "sub"? } }
}
```

### `hero`

| field | type | notes |
|---|---|---|
| `name` | string | `"Stephen Nimako Jr"` — rendered as `Stephen Nimako <span class="jr">Jr</span>` (trailing ` Jr` becomes the styled suffix) |
| `role` | string | static role line text (`"IT Support Engineer"`); equals `roles[0]` |
| `roles` | string[] | the 6 typewriter-rotator phrases |
| `tagline` | string | the bold punchline from the hero sub-copy (`**Infrastructure-first, security-bound:** …`) |
| `intro` | string | the rest of the hero sub-copy. The original was one `<p>`; it is split here so the schema's `tagline`/`intro` pair both have verbatim text |
| `ctas` | array | `{ "label", "href", "style": "primary\|ghost", "icon": "linkedin\|github\|mail\|doc", "external": bool }`. `primary` → `btn-solid`, `ghost` → `btn-ghost`; `external` adds `target="_blank" rel="noopener"`. The first CTA is the résumé: `{ "label": "View Résumé", "href": "resume.pdf", "style": "primary", "icon": "doc", "external": true }` — `resume.pdf` is the master résumé served alongside the page |
| `stats` | array | `{ "value", "suffix", "label" }` — `suffix` holds the `+` that the original wrapped in `<em>` (styled gold); empty string when absent |

### `about`

`heading` (`"About"`), `note` (`"austin, tx"` — the small caps label next to the
heading), `paragraphs` (3, with `**bold**`), and `facts`: `{ "title": "Quick facts",
"rows": [{ "label", "value" }] }` — the 6-row definition list card.

### `experience` — 5 entries

| field | notes |
|---|---|
| `company` / `role` | e.g. `"Amazon"` / `"IT Support Engineer"` |
| `period` / `location` | e.g. `"Feb 2026 — Present"` / `"Austin, TX"` (rendered with a `<br>` between) |
| `current` | bool — renders the `<span class="badge-now">Current</span>` badge and the `current` class on the article |
| `bullets` | string[] with `**bold**` |
| `tags` | `{ "label", "hot": bool }` — `hot` renders `class="tag hot"` (gold pill) |

### `skills` — 6 cards

| field | notes |
|---|---|
| `category` | card title, e.g. `"Cloud Platforms"` |
| `blurb` | one-line card description |
| `group` | filter key for the spotlight toolbar: `cloud`, `network`, `endpoint`, `systems`, `lab` (the "How I Work" card spans `"cloud endpoint systems"`) |
| `icon` | `cloud\|network\|endpoint\|systems\|lab\|work` — maps to the card's SVG (kept as a constant in the page, not in JSON) |
| `items` | `{ "label", "core": bool }` — `core` renders `class="pill core"` (gold "daily driver" pill) |

### `certifications` — 4 entries

| field | notes |
|---|---|
| `name` / `issuer` | e.g. `"AWS Certified Solutions Architect — Professional"` / `"Amazon Web Services"` |
| `date` | `null` for all — the original carries no standalone date field; dates live verbatim inside `meta` |
| `badge` | short badge text (`"SA·P"`, `"CCNA"`, `"CP"`, `"N+"`) |
| `badgeAccent` | bool — `true` renders `class="cert-badge amber"` (only SA·P) |
| `description` | card paragraph |
| `meta` | verbatim meta line, e.g. `"Issued: Sep 24, 2026 · Valid through Sep 24, 2029 · Verification ID: NECDZVMCN896PDJ2"` or `"Status: Active"` |
| `credentialId` | `"NECDZVMCN896PDJ2"` for CCNA, else `null` (parsed out of `meta` for convenience) |

### `education`

`school` (`"Western Governors University"`), `degree`
(`"B.S. Cloud and Network Engineering"`), `period`
(`"In progress since June 2026, expected February 2027"` — verbatim from the
card copy), `mark` (`"WGU"` — the card monogram), `description` (card
paragraph), `details` (plain label list, schema-conformant), `tags`
(`{ "label", "hot" }` — the rendered pills; `"Cloud + Network Engineering"` is hot).

### `dojo` — build log (currently empty)

`[]` — the original page has **zero** build-log entries; the
`// build_log — entries: 0` empty state is preserved. New entries use:

```json
{ "title": "…", "date": "…", "summary": "…", "tags": ["…"], "link": "…" }
```

Entries render as `<article class="log-entry">` blocks (title, date, summary
with `**bold**`, tag pills, "Read the build log" link when `link` is set).
**Note:** the original CSS has no `.log-entry` styles — when the first entry
ships, add styles for `.log-list`, `.log-entry`, `.log-entry-top`,
`.log-date`, `.log-tags`, `.log-link` (or reuse existing card classes).

- `dojo_loop`: the "Mastery Loop" banner — `{ "title", "text", "steps" }`
  (`steps` = the 6 `1 · Brief` … `6 · Publish here` labels; arrows are chrome).
- `dojo_tracks`: the 6 curriculum track cards —
  `{ "title", "status" ("Starting"/"Queued"), "statusClass" ("now"/"next"),
  "description", "progress" (0–100, drives the `data-bar` progress fill) }`.
- `dojo_empty`: `{ "mono", "text" }` — the empty-state copy. The `mono` count
  (`entries: 0`) is computed from the entries array at render time.

### `path` — 4 milestones

`heading` (`"The Path"`), `note` (`"2026 — 2040"`), `intro` (the sub-copy),
`milestones`: `{ "when" ("2026 — 2027"), "title", "description",
"status": null, "tags": [{ "label", "hot" }] }`.
`status` is `null` for all four because the original marks no statuses —
set `"done"`, `"current"`, or `"next"` here if milestone status styling is
added later.

### `contact`

`heading` (`"Contact"`), `subheading` (`"Let's talk infrastructure."`),
`text`, `email`, `linkedin`, `github`. The LinkedIn/GitHub buttons and the
`mailto:` link are populated from these fields; the "Copy my email" button
copies `email` (falls back to the original address if JSON fails to load).

### `sections`

Per-section chrome for the section headers — the single source for each
`<div class="sec-head">`: `heading` (the `<h2>`), `note` (the small
`.sec-note` label, e.g. `"2019 — present"`), and `sub` (the `.sec-sub`
intro paragraph). Keys: `about`, `experience`, `skills`, `certifications`,
`education`, `dojo`, `path`, `contact`. (`about.heading`, `path.heading`,
and `contact.heading` intentionally duplicate the schema-required fields on
those objects.)

## What stays in `index.html` (not in JSON)

- `<head>`: title, meta, all CSS, Google Fonts links (the only external
  requests — unchanged from the original; nothing new added).
- Nav, SN monogram/brand, hero background image, footer — static chrome.
- SVG icon set (section icons, skill icons, CTA icons) — design constants in
  the renderer script, copied verbatim.
- Skill spotlight filter toolbar labels (`All`, `Cloud`, …) — UI chrome tied
  to the filter keys.
- Dojo banner background image (base64 data URI).
- All behaviors: typewriter rotator, reveal-on-scroll, progress bars, skill
  filter, nav scroll-spy, copy-email.
- Hero photo: `profile.jpg` (served alongside the page) rendered round at
  150px at the top of the hero; clicking/tapping it (or Enter/Space) opens a
  lightbox preview showing the photo large and round, closing on click, the
  × button, or Escape. If `profile.jpg` fails to load, an "SN" monogram is
  shown instead. `resume.pdf` (master résumé) is likewise a sibling file.

## Failure behavior

If `content.json` fails to load or parse, sections are left empty and the
page still works (nav, footer, scroll-spy); nothing throws. The copy-email
button falls back to the original address.
