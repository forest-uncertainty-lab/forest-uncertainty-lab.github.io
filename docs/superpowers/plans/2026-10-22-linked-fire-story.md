# Linked fire storytelling execution plan

The first increment implements the approved comparison and explanatory sequence in the existing application. After that, later increments add evidence products only when their required inputs exist. Execution continues inline on the current feature branch, with one independent review at completion.

## 1. Derive trustworthy comparison records

### How to develop

Extend `site/fire-data.js` with `comparisonRows(history, {year, measure})`, `placeSummary(history, {year, row, measure})` and `methodExample(step)`. Each comparison record carries its key, names, province keys, recorded total, historical median, ratio and coverage status. All years use `history.running.week` completed weeks. Exclude the selected year and years with missing days from the historical median.

For Papua, aggregate the Papua and West Papua series before taking the historical median. Likewise, aggregate Maluku and North Maluku separately. Preserve provincial model intervals only for current-year summaries supplied by `history.unusual`; do not manufacture combined-region intervals.

- [x] Add Node cases for aggregation before division, selected-year exclusion, missing periods, a zero historical median and the three explicit illustration totals.
- [x] Implement the functions and run `node --test tests/fire-data.test.cjs`.
- [x] Keep the existing legacy row-key and missing-week cases passing.

## 2. Build the shared chart renderer

### How to develop

Create `site/chart-kit.js` with `bars(host, records, {value, label, selected, reference, unit, lang})` and `days(host, records, {lang})`. Use the locally available D3 7.9.0 distribution in `site/vendor/`, preserve its ISC licence and record its origin. Each renderer measures its container, creates a responsive SVG and adds native SVG titles. It treats a null value as unavailable and a true zero as zero.

Create responsive styles in `site/haze.css`. Use existing colour variables, with amber for detections and a dashed mark for estimates. Moreover, preserve readable label sizes on a 390-pixel viewport instead of shrinking a wide desktop chart.

- [x] Check zero, null and very large values in the browser.
- [x] Confirm resize, keyboard controls and both themes.
- [x] Verify that the chart works with external networking disabled.

## 3. Link the comparison to the existing explorer

### How to develop

Create `site/fire-compare.js`. Render five regional comparisons and province buttons, with raw and relative modes, a selected-place sentence, source metadata and a table. Insert the comparison before the existing national year chart in `site/index.html`, and move the weekly detail chart beside its selection context.

Call `FireCompare.render(history, state, onChange)` from `fires.js`. Keep `fires.js` as the state owner and reuse its row and year selection functions. Extend `shell.js` with validated `comparison` and `explain` URL fields. Preserve explicit links, including `row=total` and historical province selections. Use Central Sulawesi only when no place is already selected.

- [x] Exercise regional selection, province selection, both measures, both comparison modes and a historical year.
- [x] Assert that the caption, table, selected row and weekly chart identify the same place and period.
- [x] Round-trip the URL and verify EN/ID text, focus and mobile layout.

## 4. Explain the estimate without disguising an illustration

### How to develop

Add three text steps and Previous/Next controls in the comparison module. Use `methodExample(step)` for the seven daily positions and totals 54, 73.6 and 93.6. Mark the missing day and future days with distinct labels and line styles. Moreover, keep an explicit illustration label beside the graphic in both languages.

Use CSS sticky positioning for the graphic on a wide screen. An intersection observer can select the corresponding complete state as the reader scrolls, while buttons remain available. On mobile, stack the explanation and graphic without changing native scrolling. Keep a user-selected step until the reader enters another step, and disable automatic step changes under reduced motion.

Show the actual selected-year filled-day count across Indonesia and the selected place’s running-week interval in a separate paragraph when those values exist. Label their different geographic scopes explicitly. The actual record must never be added to illustrative values.

- [x] Jump directly to every step and move backwards without an invalid intermediate state.
- [x] Verify the illustration label, arithmetic, missing-day marker and estimate labels.
- [x] Check reduced motion, keyboard navigation and direct URL entry.

## 5. Add Observable Plot after the real package is available

### How to develop

Retrieve a pinned Plot distribution and licence through the normal package source. After that, add a Plot implementation behind the same renderer interface for bars, interval plots and repeated province charts. Run the same data and browser cases with the real library. Keep statistics in Python or the tested data adapter, so changing the renderer cannot change the reported values.

This task is pending package retrieval. D3 already provides the working first increment. Do not ship a guessed Plot API adapter or describe Plot as installed before its actual bundle has been checked.

## 6. Extend transparency to every chart

### How to develop

Move repeated metadata, table rendering, CSV export and number formatting into the chart layer after two real consumers establish the shared interface. Extend the existing Haze chart with those helpers. Export the selected data together with place, period, unit, completeness, source and generation date. Likewise, retain the all-data JSON download.

Correct the two existing minor findings during this chart migration. A rounded zero interval bound must not be described as a zero historical baseline, and a future-week tooltip must say season outlook.

Acceptance requires matching values between chart, caption, table and export, including Indonesian decimal formatting and missing values. Moreover, old shared links must continue to select the same region.

## 7. Develop a reported Sulawesi or Papua case study

### How to develop

Begin with a claim ledger containing the question, dataset, exact time window, supporting rows and unresolved evidence. After that, write a short sequence of a regional comparison, a local detail and its limitation. Use real interviews, incident records or photographs only when supplied or obtained through authorised reporting. Keep source dates and publication dates separate.

Create a reviewed land-cover join before adding a forest-share chart. Document map year, resolution, classification choices, geographic boundaries and ambiguous matches. Also validate a sample of joined detections by location. Keep burned area separate from active detections.

Keep attention analysis in the backlog unless the owner reopens it. If reopened, define the coverage measure, language, outlets, time window, duplicate handling and denominator before ranking places. No fire-count proxy may stand in for attention.

## Final checks and delivery

- [x] Run the existing Python suite and Node calculation cases.
- [x] Build the static site and PDF through the available renderer.
- [x] Render EN dark desktop and ID light mobile, including a Papua selection and a historical year.
- [x] Exercise unavailable data, a zero baseline, a zero ratio and the first week of January.
- [x] Review prose using the requested editing skills and the project’s uppercase and colon rules.
- [x] Request one independent review and fix material findings.
- [ ] Commit using the configured human identity, with no AI attribution.
- [ ] Push only the feature branch when networking permits.

The main review risks are mismatched time windows, aggregated ratios calculated in the wrong order, illustration values appearing to be observations, lost URL state, and resize observers triggering repeated full-page redraws. Each risk has a calculation or browser case in the first four tasks.
