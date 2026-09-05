#!/usr/bin/env python3
"""Build + cache the ALL-NYC pedestrian street network (osmnx)."""
import json, os, time, pickle, warnings
warnings.filterwarnings("ignore")
import osmnx as ox
from shapely.geometry import shape
from shapely.ops import unary_union

DATA=os.path.join(os.path.dirname(__file__),"..","data")
OUT=os.path.join(os.path.dirname(__file__),"..","build")
gj=json.load(open(os.path.join(DATA,"nyc_boroughs.geojson")))
poly=unary_union([shape(f["geometry"]) for f in gj["features"]])
print("union area(deg^2):",round(poly.area,4),"type:",poly.geom_type,flush=True)
ox.settings.log_console=False; ox.settings.requests_timeout=600; ox.settings.use_cache=True
t0=time.time()
print("downloading ALL-NYC walk network (Overpass, this is large)...",flush=True)
G=ox.graph_from_polygon(poly,network_type="walk",simplify=True,retain_all=True)
print(f"  fetched {time.time()-t0:.0f}s nodes={len(G.nodes)} edges={len(G.edges)}",flush=True)
Gp=ox.project_graph(G)
with open(os.path.join(OUT,"nyc_walk_graph.pkl"),"wb") as f: pickle.dump(Gp,f)
print(f"saved nyc_walk_graph.pkl crs={Gp.graph['crs']} total {time.time()-t0:.0f}s",flush=True)
