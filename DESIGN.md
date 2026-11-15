# CPBL-baseball: interface design

References: [nike design analysis](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/nike/DESIGN.md) for the layout concept and [WIRED design analysis](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/wired/DESIGN.md) for type and editorial rules, curated by VoltAgent. This is an independent adaptation; no affiliation, brand assets or proprietary fonts.

## Concept: a sports daily's front page

The site reads like a monochrome sports newspaper. The snapshot date is the edition date, the computed headline insight is the lead story, the experiments are secondary stories, and every table is a box score.

- **Masthead.** A dateline row carries the edition date from `provenance.json` and says the data is frozen. The front page gets a centred nameplate between a thin and a thick rule; inside pages use a one-line flag. Phones get the nameplate with search, the dateline, and a boxed three-column section index whose cells are 48px tall.
- **Front page.** Static banner headline with deck and actions, then lead story + standings box, a numbers strip, four secondary stories with column rules, and one data graphic.
- **Feature spreads.** Lineup lab and season simulation open with an oversized headline beside the deck; editor's notes (freeze notice, assumptions) run underneath. The lineup editor is a scorecard of nine ruled rows; the method note is a boxed sidebar.
- **Box scores.** Tables use 14px tabular figures, a 2px rule above the head and below the body, and 1px hairlines between rows.
- **Rules, not boxes.** Sections start with a 1px ink rule (4px for major sections); columns are separated by hairlines drawn inside the page.

## Type

Platform CJK faces only (`PingFang TC`, `Microsoft JhengHei`, `Noto Sans CJK TC`) with weights 400 and 700; the variable Noto Sans TC face cost about 0.9 s of first layout on a 4x-throttled phone. Headlines balance their lines and break between phrases; body copy uses `line-break: strict` and default wrapping (`text-wrap: pretty` is limited to decks for layout cost).

## Editorial rules

參考 awesome-design-md（MIT）的 WIRED DESIGN.md 版面與字體規則，配色維持本站。The Verge DESIGN.md is used for headline rhythm only. Nothing else is taken: no colours (including the reference's link blue), fonts, logos or wording.

- **Three-tier type ladder.** `--font-display` for headlines (h1–h3, stat values, story step figures): Georgia for Latin and figures, then a platform Ming face only where a good one ships (`Songti TC`, `Noto Serif CJK TC`, `Source Han Serif TC`), otherwise the platform sans. `--font-body` is the CJK sans for reading; `--font-meta` (sans, 13px, tracked `0.06em`) carries kickers, bylines, datelines, nav, buttons, table heads and stat labels. Serif for narrative, sans for structure: h4 labels stay sans. Headlines keep weight 700 because CJK at 400 has too little colour on screen.
- **Headline hierarchy.** `--display-hero` (banner, spread openers, ≈88px) > `--display-lg` (lead story and inside-page h1, ≤50px) > `--display-md` (section headlines, ≈30px) > `--display-sm` (story cards, box titles, column heads, ≈23px). Figures in the numbers strip stay below the lead headline. Display leading is tight (1.04–1.3); reading copy is 1.7.
- **Rhythm.** Kicker 8px above the headline, headline 12px above the deck, metadata 8px under the deck.
- **Story cards.** Kicker (serif step figure + sans tag), serif headline, deck, then a metadata line on a hairline. On phones cards become story rows divided by one hairline each.
- **Metadata rows.** `.meta-row`: small sans items split by a short 1px divider drawn inside the item, so 44px tap targets don't stretch the rule. Used for the lead story's byline links.
- **Magazine grid.** Phone (≤640px): every grid is one column, story rows stack. Tablet (641–1099px): two-up stories and numbers. Desktop (≥1100px): lead + standings 7:5, four-up stories with column rules. The banner headline stays full width at every size.
- **Rules and radius.** 4px ink rule opens a major section, 1px ink rule a minor one, hairlines separate rows and columns. Every shape is square (`--radius-none`); only the loading spinner is round (`--radius-full`).
- **Elevation.** Flat; hairlines and ink rules carry hierarchy. No drop shadows (`--shadow: none`), including the search dialog.
- **Masthead.** Dateline and nav in the metadata face; the front page keeps the centred nameplate between a thin and a thick rule.

## Contracts

Colour values in `tokens.css` are fixed and no colour literal may be added anywhere; new tokens may only alias existing ones. Keep semantic data colours distinct from decorative accents. Preserve data labels, warnings, freeze notices, keyboard focus, chart tables, cancellation and existing route contracts. No external font or asset requests. Controls are at least 44px tall. `main` reserves a full viewport so the footer never shifts while data loads. All pages reflow at 200% text; wide data tables scroll inside named keyboard-accessible regions. No infinite animation on loaded content; motion respects `prefers-reduced-motion`.

The source collection is MIT licensed. Token and component adaptations retain its notice in THIRD_PARTY_DESIGN_NOTICES.txt.
