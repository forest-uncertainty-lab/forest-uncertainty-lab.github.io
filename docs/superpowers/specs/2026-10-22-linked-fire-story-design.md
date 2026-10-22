# Linked fire comparisons and explanatory graphics

The owner approved the linked-chart direction and requested a reference-based brainstorm, execution plan and practical development instructions. This design extends the existing static site and Python pipeline. Its first release helps a reader compare Sulawesi and Papua with other Indonesian regions, inspect a province and understand how estimates enter the charts.

## Editorial direction

The opening question is whether a region has more detections than usual for that region over the same completed weeks. Consequently, the opening comparison switches between recorded totals and a ratio to the historical median. Papua is separated from Maluku in this comparison by combining the historical Papua and West Papua province series. However, the existing historical boundaries still apply.

A selected province updates the weekly chart and a factual explanatory sentence together. Moreover, uncertainty appears beside the estimate it qualifies. Detection counts establish neither burned forest area nor uneven media attention. Those claims require additional evidence.

## References and the decisions they inform

| Reference | Inspected evidence | Application here |
|---|---|---|
| Reuters Graphics | The owner supplied this direction, but both Reuters graphics entry pages were inaccessible during this research | Use geography and comparisons to support a specific reporting question. Treat this as a proposed editorial direction, without claiming an inspected Reuters implementation |
| [The Pudding’s sticky graphic explanation](https://pudding.cool/process/scrollytelling-sticky/) | Its example keeps a graphic in view while separate text steps update it | Use one chart with explicit explanatory steps. Keep the text readable independently and let buttons provide a keyboard alternative |
| [The Pudding’s storytelling process](https://pudding.cool/process/how-to-make-dope-shit-part-3/) | It discusses explicit visual states and the implementation cost of scrolling narratives | Give each step a complete state, so jumping ahead or moving backwards does not depend on earlier animation |
| [OWID’s wildfire data page](https://ourworldindata.org/grapher/annual-area-burnt-by-wildfires-gwis?country=~OWID_WRL) | It exposes source, unit, coverage, update dates, processing and downloads | Give each chart a visible unit, period, source date, methods link, accessible table and download |
| The owner’s interview components | `interview-narrative.js` advances a caption and drawing together; `interview-anim.js` preserves a complete static picture and reduced-motion behaviour | Link captions to selection and expose all explanation text without requiring playback |

These references inform different parts of the product. Therefore, the site keeps its own typography, colour meanings, Indonesian geography and data definitions.

## Approaches considered

An expanded dashboard would add more chart types to the current explorer. However, it would still leave readers to discover the comparison question and interpret the estimates themselves.

A guided comparison with an attached explorer gives the reader a specific starting question, then lets each selection update the evidence. Therefore, this is the recommended first increment. It fits the current weekly data and shared URL state, while leaving the Haze tab available as a separate practical tool.

A fully reported scrolling essay could connect local experiences, maps and satellite records. However, the current project lacks the interviews, incident verification and forest classification required for that story. Consequently, the execution plan treats it as a reporting phase with evidence requirements.

## Existing capabilities and missing inputs

The existing `history.json` contains weekly count and heat-power series, historical rows, gap-day indicators, nowcasts and outlooks. Moreover, `shell.js` already stores selections in the URL, and `fires.js` links year and province controls to several charts. These interfaces support the first release without new services or keys.

The archive does not expose the amount contributed by gap filling in each weekly total. Therefore, a method demonstration must use an explicitly labelled illustration when showing an unfilled total changing into a filled total. Actual selected-place values remain separate. A later pipeline extension can replace the illustration with a complete real-data breakdown.

There is no forest classification or attention dataset in the current products. Consequently, neither receives a finished-looking factual chart in this release.

## First release

The first comparison displays Sulawesi, Papua, Maluku, Kalimantan and Sumatra, with Sulawesi first. A second control selects a province within the chosen region. Central Sulawesi is the initial province unless the URL already selects a place.

The comparison uses the same completed weeks in every year. Historical baselines exclude the selected year and any year with unresolved missing coverage. A missing baseline remains unavailable. Likewise, an incomplete selected period does not produce a relative-level estimate. Combined-region ratios use observed totals divided by the median of aggregated historical totals; they do not sum provincial ratios or uncertainty bounds.

The selected province retains the existing weekly chart, now adjacent to the comparison. Its explanatory sentence reports the selected period, recorded total and historical median. A current-year model interval appears only when the Python product supplies one for that exact row. Historical ratios remain descriptive comparisons.

The method illustration has three complete states. First, it shows four observed days totalling 54 detections. After that, it fills one missing day using 20 NOAA-20 detections multiplied by an illustrative ratio of 0.98, giving 73.6 detections. Finally, two future days at an illustrative recent average of 10 per day give an estimated weekly total of 93.6. All seven daily positions remain visible, and the text explicitly labels this as an illustration. The illustration does not claim a model confidence interval.

## Shared chart interfaces

`fire-data.js` derives comparison records from the existing JSON. `chart-kit.js` owns responsive axes, bars, formatting and accessible SVG descriptions. `fire-compare.js` owns the comparison controls, caption, table and method illustration. `fires.js` remains the owner of selected year, place and measure, so every linked view receives the same state.

D3 is available locally and can be bundled with its required licence. Observable Plot could not be downloaded because this environment cannot resolve its package host. Therefore, the first working renderer uses local D3, and the execution plan records Plot adoption as a separate adapter task with real-library checks. This keeps the data contract independent of either renderer.

The URL also records the comparison metric and explanatory step. Controls remain native buttons or selects, focus survives redraws, and charts resize without page overflow. Moreover, reduced motion disables any transitions while preserving every chart state.

## Later reporting features

A reported case study can connect a documented local experience with the corresponding place, dates and data. However, quotations, photographs and incident descriptions require actual reporting and permission where applicable. The plan includes a reporting template rather than invented testimony.

A forest-share chart requires a dated land-cover join and an explicit treatment of ambiguous pixels. A media-attention comparison requires an independent, reviewed measure and denominator. The owner previously dropped GDELT, so this plan does not reinstate it.
