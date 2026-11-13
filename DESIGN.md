# CPBL-baseball: interface design

Reference: [nike design analysis](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/nike/DESIGN.md), curated by VoltAgent. This is an independent adaptation; no affiliation, brand assets or proprietary fonts.

## Concept: a sports daily's front page

The site reads like a monochrome sports newspaper. The snapshot date is the edition date, the computed headline insight is the lead story, the experiments are secondary stories, and every table is a box score.

- **Masthead.** A dateline row carries the edition date from `provenance.json` and says the data is frozen. The front page gets a centred nameplate between a thin and a thick rule; inside pages use a one-line flag. Phones get the nameplate with search, the dateline, and a boxed three-column section index whose cells are 48px tall.
- **Front page.** Static banner headline with deck and actions, then lead story + standings box, a numbers strip, four secondary stories with column rules, and one data graphic.
- **Feature spreads.** Lineup lab and season simulation open with an oversized headline beside the deck; editor's notes (freeze notice, assumptions) run underneath. The lineup editor is a scorecard of nine ruled rows; the method note is a boxed sidebar.
- **Box scores.** Tables use 14px tabular figures, a 2px rule above the head and below the body, and 1px hairlines between rows.
- **Rules, not boxes.** Sections start with a 1px ink rule (4px for major sections); columns are separated by hairlines drawn inside the page.

## Type

Platform CJK faces only (`PingFang TC`, `Microsoft JhengHei`, `Noto Sans CJK TC`) with weights 400 and 700; the variable Noto Sans TC face cost about 0.9 s of first layout on a 4x-throttled phone. Georgia is used for Latin nameplate and figures only. Headlines balance their lines and break between phrases; body copy uses `line-break: strict` and default wrapping (`text-wrap: pretty` is limited to decks for layout cost).

## Contracts

Colour values in `tokens.css` are fixed; new tokens may only alias existing ones. Keep semantic data colours distinct from decorative accents. Preserve data labels, warnings, freeze notices, keyboard focus, chart tables, cancellation and existing route contracts. No external font or asset requests. Controls are at least 44px tall. `main` reserves a full viewport so the footer never shifts while data loads. All pages reflow at 200% text; wide data tables scroll inside named keyboard-accessible regions. No infinite animation on loaded content; motion respects `prefers-reduced-motion`.

The source collection is MIT licensed. Token and component adaptations retain its notice in THIRD_PARTY_DESIGN_NOTICES.txt.
