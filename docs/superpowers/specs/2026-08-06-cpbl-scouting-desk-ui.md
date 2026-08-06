# CPBL Scouting Desk UI Design

## Product position

The application is an auditable CPBL season-data workbench for analysts. It
should feel like a composed scouting desk: compact, confident, and useful on a
second or third daily visit. It is not a live-score product, sports-news site,
or a generic dashboard template.

## Visual system

- Use a deep ink-green canvas, ivory content, muted blue-gray metadata, coral
  for selections and attention, mint for verified source status, and gold for
  numerical emphasis.
- Use straight 4-6px radii, fine dividers, tabular numerals, and an 8px spacing
  rhythm. Surfaces must be clearly separated without heavy shadows or gradients.
- Keep standard reading text large enough for data work: 18px base body, 16px
  metadata minimum, and fixed heading scales.
- Use color semantically. A chart must still be understandable from title,
  labels, values, and adjacent table data without color perception.

## Information hierarchy

1. Every page begins with an official-data / verified-date line, a single H1,
   and one concise decision-oriented description.
2. Essential current-state facts appear first as equal-height metric cells.
3. Controls are grouped by task and labelled in full. They must never require
   hover to understand.
4. Tables and plots follow the analysis result, with an export action placed
   consistently below each table.
5. Source lineage remains visible where rankings, percentiles, or LOG5 are
   interpreted, but never overwhelms the result.

## Page design

### Data signal overview

Lead with a season snapshot and the four real source-population counts. Present
three primary routes: shortlist players, inspect rankings, and examine a
hitter-pitcher scenario. The overview must identify the boundaries of the
available official aggregate data rather than fabricate trends or game context.

### Scouting workbench

Make the selection flow legible: population, team, qualification threshold,
then scouting priority. Present ranking evidence before comparison selection.
The comparison action stays limited to four real qualified candidates.

### Player dossier

Show the player's team, role, season, official-record status, current headline
statistics, evidence, league-relative tables, percentiles, and comparable
players in a stable order. A radar is a supplementary chart, not the page's
main evidence.

### League, rankings, and matchup

Share the same navigation vocabulary, control density, chart framing, and
table treatment. A matchup explicitly remains a LOG5 scenario calculation,
not a prediction or a claimed matchup history.

## Interaction and accessibility

- All buttons and controls use at least a 44px target; primary commands use
  48px.
- Keyboard focus is always visible; reduced-motion users receive no animated
  movement.
- The layout is validated at 1440px, 1024px, and 390px. Controls stack at
  small sizes and wide data tables remain scrollable within their own boundary.
- No player portraits, claimed live feeds, or decorative pseudo-data are used.
  Every displayed figure traces to the existing CPBL data process.

## Acceptance evidence

- Every Streamlit page renders with no exception and exactly one H1.
- Existing data, terminology, source-lineage, and export tests continue to
  pass; page/UI tests cover the new reusable layout markers.
- Browser screenshots at desktop and mobile widths show no clipped controls,
  overlapping content, or unequal repeated-card heights.
