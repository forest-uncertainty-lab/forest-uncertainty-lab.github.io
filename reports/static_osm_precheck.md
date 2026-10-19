# Static-source sites in Morowali and Banggai: OpenStreetMap pre-check

Checked 2026-10-19 against OpenStreetMap data as of 2026-10-19 06:32 UTC (© OpenStreetMap contributors, ODbL). This helps with backlog item 6 but does not complete it: a mapped industrial area near a site makes a static source likely. It does not prove that the hotspots came from it, and an empty result proves nothing. The NGO reviewer's local knowledge, or a look at imagery, decides.

Method: one Overpass query per site for anything within 1.5 km tagged `landuse=industrial`, `industrial=*`, `landuse=quarry`, `power=plant|generator`, or `man_made=works|flare|chimney|kiln|petroleum_well|storage_tank`. "Centre" is the distance from the site to the middle of the mapped feature; a large area can touch the 1.5 km circle while its centre lies farther away.

Site IDs follow `static_review.md` as built on 2026-10-19. They are renumbered whenever the masks are rebuilt, so the coordinates are the stable reference.

| Site | District | Lat, lon | Detections, months | Mapped within 1.5 km | Result for the NGO to confirm |
|---|---|---|---|---|---|
| S002 | Morowali | -2.8505, 122.1639 | 3,333 in 12 months | Indonesia Morowali Industrial Park (`landuse=industrial`, way 299975400; centre 1.5 km) | Likely static: industrial park |
| S011 | Banggai | -1.3815, 122.4806 | 493 in 12 months | Two unnamed industrial areas (ways 873034362, 873034361; centres 0.2 and 1.0 km) | Likely static: unnamed industrial site, FIRMS marks 98% of its detections as static |
| S027 | Morowali | -2.2701, 121.7639 | 123 in 12 months | Indonesia Huabao Industrial Park (relation 19383700; centre 0.1 km); PLTU Ambunu coal power plant (way 1416911382; 1.5 km) | Likely static: industrial park |
| S040 | Banggai | -1.2482, 122.5916 | 66 in 9 months | Unnamed industrial area (way 873034363; centre 0.2 km) | Likely static: unnamed industrial site |
| S048 | Morowali | -2.7382, 122.0288 | 55 in 10 months | Wanxiang Nickel Indonesia (way 686769329; 0.4 km), its coal power plant (way 1325505504; 0.8 km), a chimney and two generators | Likely static: nickel plant |
| S089 | Morowali | -3.0424, 122.2649 | 17 in 7 months | Unnamed industrial area (way 1013955749; centre 1.0 km); quarry (relation 13570868) | Unclear: industrial area nearby, few detections |
| S128 | Banggai | -1.5480, 122.1582 | 4 in 2 months | Nothing | Unclear: no mapped industry; may be vegetation fires |
| S129 | Banggai | -1.5142, 122.2638 | 4 in 2 months | Nothing | Unclear: no mapped industry; may be vegetation fires |
| S153 | Banggai | -1.1116, 122.1154 | 1 in 1 month | Nothing | Unclear: one detection |

The last three sites have one to four detections, none of them typed static by FIRMS. They are flagged because they sit in or next to a cell that passed the recurrence rule or that holds a detection FIRMS typed as static. Whatever the review finds, they stay in the "static suspect" count until the mask rule changes; the review result goes in this file.
