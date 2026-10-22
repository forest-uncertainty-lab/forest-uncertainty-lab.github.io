# Linked fire comparison review

## Scope

The review covered Tasks 1–4 of the linked storytelling plan, including region aggregation, historical baselines, selected-place intervals, illustration boundaries, URL state, downloads and keyboard controls. Tasks 5–7 remain planned work.

## Findings and changes

The independent review found no material calculation or integration issue. However, it identified missing CSV units and lost keyboard focus when an explanation navigation button became disabled. Therefore, the export now includes an explicit unit column, and focus moves to the active step control at either endpoint. Browser regression cases exercise both fixes.

Moreover, the README now describes the actual D3 dependency and links the reference-based design and development plan. The design distinguishes inspected Pudding and OWID examples from the inaccessible Reuters pages. Observable Plot remains pending actual package retrieval.

## Verification

The Python suite passed all 177 tests, including its Node wrapper. Separately, all 10 Node calculation cases passed. The site and PDF build completed without notes.

The linked browser checks passed regional and provincial selection, both measures, historical selection, URL restoration, illustrative arithmetic, CSV units, explanation endpoint focus and desktop scroll selection. Furthermore, five Haze and Fire history browser views passed across English and Indonesian, desktop and mobile, and dark and light themes. Those views produced no page errors, invalid SVG values or horizontal overflow.

External browser requests were blocked during these checks. Consequently, they verify the built snapshots and bundled assets, rather than live provider availability. Existing dated observations were preserved without running a data refresh.
