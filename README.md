# Transit Heat Intelligence
**Station-Level Capital & Operational Decision-Support System** — full MTA subway (428 complexes, all 5 boroughs).

## The deliverable
- **`build/toolkit.html`** — the published app. **Open it directly in a browser** (double-click, or drag into a tab). It is a single self-contained file: all data, styling, and logic are inline.
  - It loads the Leaflet map library and the Esri "Light Gray Canvas" basemap tiles from their CDNs, so the **map needs an internet connection**. Everything else works offline.
  - Tabs: **Prioritize** (map + filters + station table + action panel) · **Analysis & Methodology** (technical report) · **Engage** (rider-intake concept) · **Ask AI Planner** (plain-language query over the stations).
- **`build/toolkit.template.html`** — the editable source (HTML + CSS + JS) with a `__DATADATA__` placeholder where the data is injected.
- **`build/thi.json`** — the computed data the app renders (428 stations + map geometry).

## Using the Prioritize tab
- **Filters** (left, all default to *All*): Route, Borough, Heat response, Dominant exposure, Station type, Owner, Cost. Changing any filter updates the KPI bar, the map, and the table together.
- **Select area** (button on the map): drag a rectangle to keep only the stations inside it.
- **Zoom-to**: clicking a station (map or table), or changing Route/Borough/area, zooms the map to that selection.
- **Station panel** (right): Overview · Evidence · Interventions · Feedback, plus **Export action card (PNG)** — downloads a one-page station summary card.

## Rebuild pipeline (all in `build/`)
1. `build_graph_nyc.py` → `nyc_walk_graph.pkl` (OSM pedestrian network, all NYC)
2. `pull_ride_nyc.py` → `data/ridership_afternoon_nyc.json` (MTA hourly ridership, afternoons, by year)
3. `pull_amen_nyc.py` → `data/trees_nyc.json`, `benches_nyc.json`, `shelters_nyc.json`
4. `pull_layers.py` / `pull_region.py` / `extract_roads.py` → HVI polygons, boroughs, subway-line geometry
5. `compute_nyc.py` → `thi.json` (heat-penalty model + walk/wait/platform legs + Future Heat Service Risk + map geometry)
6. Inject `thi.json` into `toolkit.template.html` → `toolkit.html`:
   ```python
   import re, json
   t = open('toolkit.template.html').read()
   d = json.load(open('thi.json'))
   for k in ('roads','region','parks','labels','rings'): d.pop(k, None)  # basemap now supplies these
   open('toolkit.html','w').write(t.replace('__DATADATA__', json.dumps(d)))
   ```

Other inputs in `data/`: `weather_daily.json` (Open-Meteo ERA5), `subway_structure.json` (MTA structure type), `hvi_zcta.json` (NYC Heat Vulnerability Index), `nyc_boroughs.geojson`.

## Method (one line)
Per-station OLS of log afternoon ridership on apparent temperature above 80°F (controls: day-of-week, month, year, holiday, rain) → heat regime (suppressed / neutral / attractor); 5-minute network walkshed → walk / wait / platform burden decomposition; **Future Heat Service Risk** = trips lost (sensitivity × riders × NPCC4 future-heat days) weighted by HVI equity & fixability. Full write-up is in the app's **Analysis & Methodology** tab.

## Transparent recommendation engine
The dashboard applies one station-level decision engine across the station card, interventions tab, methodology framework, and decision-path modal: **evidence → diagnosis → action → implementation filter → validation**. It maps the observed response, dominant journey burden, and explicit condition checks to a best-fit action, then shows owner, implementation type, delivery timeframe, and cost. Rider feedback is supporting/validation evidence, not an autonomous project selector. The natural-language planner is an interface over the structured station evidence and transparent rules; it does not invent interventions.

## Ownership model
Platform interventions are generally owned by **MTA Capital / Facilities**: canopy and reflective-roof work at elevated/open stations, or ventilation and thermal management underground. The primary wait intervention is **MTA Operations** — reducing exposure duration through frequency, reliability, and heat-day operations; platform cooling or hydration is complementary. The **walk** leg is primarily **Parks / DOT**, with possible MTA coordination at station entrances. Attractor operations may be owned by **MTA / Parks**, depending on station and destination context.

## Sharing
`toolkit.html` is the whole app in one file — email it, drop it in shared storage, or host it on any static web server / GitHub Pages. Recipients just open it in a browser (online, for the map tiles). To hand off the reproducible project, share the `walkshed/` folder; to hand off only the result, share `build/toolkit.html` alone.
