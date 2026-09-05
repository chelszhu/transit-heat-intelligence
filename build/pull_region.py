#!/usr/bin/env python3
"""Pull surrounding regional land (NJ/NY/CT counties around NYC) for map context -> thi.json."""
import json, os, urllib.request, warnings
warnings.filterwarnings("ignore")
from shapely.geometry import shape, box
D=os.path.dirname(__file__)
URL="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
print("downloading US counties geojson...",flush=True)
gj=json.load(urllib.request.urlopen(urllib.request.Request(URL,headers={"User-Agent":"thi"}),timeout=120))
REGION=box(-74.75,40.30,-73.30,41.20)          # tri-state window around NYC
NYC={"36005","36047","36061","36081","36085"}  # 5 boroughs (drawn separately, detailed)
STATES={"34","36","09"}                          # NJ, NY, CT
region=[]
for f in gj["features"]:
    fips=f.get("id","")
    if fips[:2] not in STATES or fips in NYC: continue
    try: g=shape(f["geometry"])
    except: continue
    if not g.intersects(REGION): continue
    g=g.intersection(REGION).simplify(0.003,preserve_topology=True)
    polys=[g] if g.geom_type=="Polygon" else list(getattr(g,"geoms",[]))
    for p in polys:
        if p.area<3e-5: continue
        region.append([[round(x,5),round(y,5)] for x,y in p.exterior.coords])
print("region land rings:",len(region))
t=json.load(open(os.path.join(D,"thi.json")))
t["region"]=region
json.dump(t,open(os.path.join(D,"thi.json"),"w"))
print("thi.json KB:",round(os.path.getsize(os.path.join(D,"thi.json"))/1024,1))
