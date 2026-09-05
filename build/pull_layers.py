#!/usr/bin/env python3
"""Pull base-layer geometry (HVI choropleth via MODZCTA, parks) + labels; merge into thi.json."""
import json, os, urllib.request, warnings, statistics
warnings.filterwarnings("ignore")
from shapely.geometry import shape
D=os.path.dirname(__file__); DATA=os.path.join(D,"..","data")
def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"thi"}),timeout=90))
def rings_of(geom, tol):
    g=shape(geom).simplify(tol,preserve_topology=True)
    polys=[g] if g.geom_type=="Polygon" else list(getattr(g,"geoms",[]))
    return [[[round(x,5),round(y,5)] for x,y in p.exterior.coords] for p in polys if p.area>1e-6]

hvi_map={r["zcta20"]:int(r["hvi"]) for r in json.load(open(os.path.join(DATA,"hvi_zcta.json"))) if r.get("hvi") not in(None,"")}

print("MODZCTA + HVI...",flush=True)
mz=get("https://data.cityofnewyork.us/resource/pri4-ifjk.geojson?$limit=500")
hviPolys=[]
for f in mz["features"]:
    p=f.get("properties",{})
    zs=[z.strip() for z in (p.get("zcta") or p.get("modzcta") or "").split(",")]
    hs=[hvi_map[z] for z in zs if z in hvi_map]
    hvi=round(statistics.mean(hs)) if hs else hvi_map.get(p.get("modzcta"),3)
    for ring in rings_of(f["geometry"],0.0004):
        hviPolys.append({"h":hvi,"r":ring})
print(f"  hvi polys: {len(hviPolys)}",flush=True)

print("Parks (acres>15)...",flush=True)
pk=get("https://data.cityofnewyork.us/resource/enfh-gkve.geojson?$where=acres>15&$limit=1000")
parks=[]
for f in pk["features"]:
    if not f.get("geometry"): continue
    parks+=rings_of(f["geometry"],0.0004)
print(f"  park rings: {len(parks)}",flush=True)

labels=[["MANHATTAN",-73.968,40.782],["THE BRONX",-73.868,40.845],["BROOKLYN",-73.949,40.650],
        ["QUEENS",-73.816,40.712],["STATEN ISLAND",-74.145,40.580],
        ["Harlem",-73.945,40.811],["Midtown",-73.982,40.755],["Downtown",-74.008,40.710],
        ["Astoria",-73.921,40.771],["Flushing",-73.833,40.759],["Jamaica",-73.792,40.702],
        ["Williamsburg",-73.957,40.714],["Flatbush",-73.958,40.651],["Coney Island",-73.983,40.575],
        ["Rockaway",-73.815,40.585]]
labels=[{"t":t,"x":x,"y":y,"b":t.isupper()} for t,x,y in labels]

t=json.load(open(os.path.join(D,"thi.json")))
t["hviPolys"]=hviPolys; t["parks"]=parks; t["labels"]=labels
json.dump(t,open(os.path.join(D,"thi.json"),"w"))
print("merged into thi.json; KB:",round(os.path.getsize(os.path.join(D,'thi.json'))/1024,1))
