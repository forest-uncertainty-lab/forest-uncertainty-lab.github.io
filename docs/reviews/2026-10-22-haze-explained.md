# Haze page review

The remaining page work adds the bilingual Haze and Fire history tabs and retains the original Sulawesi Tengah monitor. The design serves residents checking their air and readers comparing Indonesian provinces. Consequently, the page leads with readings and comparisons, while detailed methods follow the charts. Amber identifies detections, blue identifies model estimates, and dashed or hatched marks distinguish estimates and filled data.

An independent review found six issues affecting interpretation or failure handling. Each issue received a regression check that failed before its fix.

- Incomplete completed weeks no longer produce ratios, ranks or season outlooks. Moreover, the running-week estimate includes missing elapsed days. Historical years with unresolved missing days are excluded from the baseline.
- Continuous heat power uses weighted bootstrap rates. Therefore, changing between megawatts and kilowatts preserves the result after conversion.
- Failed haze sources retain previous successful components and their original retrieval times. Furthermore, wind paths, mapped fires and encounter counts remain from the same snapshot.
- Wind paths carry their actual duration and stop reason. Unavailable paths no longer count as evidence of zero fire encounters, and endpoint spread uses a shared duration.
- Singapore’s PSI still renders when hourly particle readings are unavailable. Moreover, a model comparison uses the matching measurement hour.
- A model series with fewer than 24 valid hours shows its actual coverage and latest hourly value. Consequently, it does not claim a 24-hour average or compare that partial average with the daily guideline.

The final Python suite passes all 177 tests, including the Node calculation checks. Moreover, all three browser regression cases pass, and JavaScript syntax and whitespace checks pass.

The browser checks cover English dark desktop, Indonesian light mobile, a historical Central Kalimantan selection, Papua, both measures, both periods, city selection, language, theme, URL state, keyboard tabs, source failures and the moved monitor. The build also produces a PDF brief through the available headless Chromium renderer.

The managed environment blocks external DNS, ordinary Chrome startup and removal of an existing generated output directory. Therefore, verification uses the existing installed Python environment, a temporary build directory and an isolated headless shell. Browser interception serves the actual built files as HTTP responses and rejects external calls, so these checks exercise fallback behaviour. However, they do not establish that external APIs are currently available. The refresh attempt records the source failures, and the last successful source components remain dated.

The following minor findings remain for a later chart pass.

- A rounded zero lower ratio bound can show the baseline-unavailable label even when the historical median is positive. The exported table retains the numerical interval.
- A future-week tooltip uses the running-week label for its season-outlook interval. The legend and methods distinguish both estimates.

## Writing and continuity checks

The no-ai-slop and humanizer reviews removed unsupported claims about the absence of monitoring stations, shortened the source explanations and kept observations separate from model results. Moreover, the web-design-specific review checked actual content, chart hierarchy, narrow screens and controls against The Generated Look. The explain-webpage review checked that each control changes an interpretable comparison and remains usable by keyboard.

The requested story skills require a fiction project for their registry workflows. This repository has no fiction project, so those workflows do not apply. Their relevant editorial principles informed the review instead. Worldbuilding supplied checks on place names, historical boundaries and local times; series-continuity supplied checks on names, dates and claims across the tabs; scene-craft informed the order of explanation beside a chart; plot-structure informed the progression from a national comparison to a province and its weekly evidence. Research supplied a record of primary sources and explicit unresolved claims. No fictional facts or story registries were added. Caveman governs brief chat updates; published prose uses complete sentences.

## Source checks

[Open-Meteo’s air quality documentation](https://open-meteo.com/en/docs/air-quality-api) supports the global model’s approximate 45 km grid, its 12-hour update interval and its underlying three-hour output. Moreover, [data.gov.sg’s real-time API guide](https://guide.data.gov.sg/developer-guide/real-time-apis) documents the Singapore feeds. [WHO’s guideline table](https://www.ncbi.nlm.nih.gov/books/NBK574582/table/fm-ch1.tab1/) gives 15 micrograms per cubic metre for the daily PM2.5 guideline. The page now explains that an individual hourly value cannot establish a daily exceedance.

The project still needs a dated land-cover join to substantiate forest-fire shares. Likewise, it needs an independent attention measure to substantiate uneven news coverage. Neither claim follows from the detection chart.

## Implementation decisions

The existing ledger records decisions from the earlier tasks. They remain part of the branch’s record, with these consequences.

- Province keys use unique Indonesian names throughout. A naming change would require coordinated producer changes.
- The haze mask removes known heat sources without restricting detections to Indonesian province polygons. A narrower filter would omit neighbouring-country detections.
- Reclassification of the fixed monitor store checked mask compatibility. All 660,002 stored detections retained their categories.
- The small-count interval test uses the Gamma distribution’s calculated bounds. Its earlier threshold was a test arithmetic error.
- Gap filling weights both counts and heat power. If that assumption is wrong, filled-day heat power inherits the satellite ratio’s error.
- December night passes retain their UTC+8 dates in the following year. This can move several hundred annual detections between calendar years.
- A filled UTC day is counted once in its UTC week. Consequently, the displayed filled-day count does not double-count a day crossing two local weeks.
- Ingestion records pre-filter raw-day availability separately from kept detections. This distinguishes an empty feed from a day whose detections were all filtered.
- FIRMS availability is parsed as CSV and kept separately for each satellite. Incorrect availability would cause extra requests or delay replacement with standard data.
- FRP unusualness uses a plain ratio without a Poisson probability interval. Its other uncertainty remains unquantified.
- Unfetched days remain missing, and readable row keys preserve the region names in shared links.
- The corrected historical test treats archive values as weekly counts. Its earlier expectation was a test arithmetic error.
- The wind grid uses requested coordinates because the provider may snap response coordinates. Incorrect alignment would change path positions.
- Paths stop before leaving the available wind grid. Consequently, an endpoint can be one hour short of a boundary crossing.
- Backfill is capped at 30 requests per refresh. Consequently, an initial deployment can need several runs.
- Wind requests pause after 500 locations. Consequently, a refresh takes longer but avoids the observed minute limit.
- Upwind counts exclude the first two hours of each path. Nearby detections can therefore be omitted from the upwind metric.
- Map detections are clipped to the configured region. Fires outside that view are not counted in its legend.
- The moved monitor’s path check uses the real files. The page check belongs to the later shell task.
- The chart displays fixed-baseline Poisson intervals with their exclusions stated. A fuller model remains necessary for broader confidence claims.
- Node calculation tests run through pytest when Node is available. Configuration discovery stops at the tests directory to avoid probing denied secret files.
- The existing branch and working directory were retained to preserve the interrupted implementation. No additional worktree was needed.
