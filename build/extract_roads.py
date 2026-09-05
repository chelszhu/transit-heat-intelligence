#!/usr/bin/env python3
"""Extract a basic major-road network from the cached NYC walk graph -> thi.json."""
import json, os, pickle, warnings
warnings.filterwarnings("ignore")
from shapely.geometry import LineString
from pyproj import Transformer
D=os.path.dirname(__file__)
Gp=pickle.load(open(os.path.join(D,"nyc_walk_graph.pkl"),"rb"))
inv=Transformer.from_crs(Gp.graph["crs"],"EPSG:4326",always_xy=True).transform
MAJOR={"motorway","trunk","primary","secondary","motorway_link","trunk_link","primary_link"}
nx_x={n:d["x"] for n,d in Gp.nodes(data=True)};nx_y={n:d["y"] for n,d in Gp.nodes(data=True)}
seen=set();roads=[]
for u,v,data in Gp.edges(data=True):
    hw=data.get("highway"); hwset=set(hw) if isinstance(hw,list) else {hw}
    if not (hwset & MAJOR): continue
    key=(min(u,v),max(u,v))
    if key in seen: continue
    seen.add(key)
    g=data.get("geometry")
    pts=list(g.coords) if g is not None else [(nx_x[u],nx_y[u]),(nx_x[v],nx_y[v])]
    line=LineString(pts).simplify(20)
    ll=[inv(x,y) for x,y in line.coords]
    roads.append([[round(lo,5),round(la,5)] for lo,la in ll])
print("major-road segments:",len(roads))
t=json.load(open(os.path.join(D,"thi.json")))
t["roads"]=roads
json.dump(t,open(os.path.join(D,"thi.json"),"w"))
print("thi.json KB:",round(os.path.getsize(os.path.join(D,"thi.json"))/1024,1))
