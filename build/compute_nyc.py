#!/usr/bin/env python3
"""Full citywide pipeline: heat model + leg decomposition + Future Heat Service Risk -> thi.json (ALL NYC)."""
import json, os, re, math, pickle, datetime as dt, warnings
warnings.filterwarnings("ignore")
import numpy as np, networkx as nx
from shapely.geometry import shape, Point, MultiLineString
from shapely.ops import unary_union, transform as shp_transform
from shapely.strtree import STRtree
from shapely.prepared import prep
from scipy.spatial import cKDTree
from pyproj import Transformer
import shapely
np.seterr(all="ignore")
D=os.path.dirname(__file__); DATA=os.path.join(D,"..","data"); T=__import__("time").time
t0=T()
def log(m): print(f"[{T()-t0:5.0f}s] {m}",flush=True)

# ---------- HEAT MODEL ----------
ride=json.load(open(os.path.join(DATA,"ridership_afternoon_nyc.json")))
wx=json.load(open(os.path.join(DATA,"weather_daily.json")))
app={t:v for t,v in zip(wx["time"],wx["apparent_temperature_max"])}
precip={t:(v or 0.0) for t,v in zip(wx["time"],wx["precipitation_sum"])}
HOL={"2022-05-30","2022-06-20","2022-07-04","2022-09-05","2023-05-29","2023-06-19","2023-07-04","2023-09-04","2024-05-27","2024-06-19","2024-07-04","2024-09-02"}
comp={}
for r in ride:
    day=r["day"][:10]
    if day not in app: continue
    try: rd=float(r["rides"])
    except: continue
    d=comp.setdefault(r["station_complex_id"],{"name":r["station_complex"],"boro":r.get("borough",""),"lat":float(r["lat"]),"lon":float(r["lon"]),"rows":[]})
    d["rows"].append((day,rd))
log(f"complexes: {len(comp)}")
def design(days):
    hot=[];wet=[];dow=[];mon=[];yr=[];hol=[]
    for day in days:
        dd=dt.date.fromisoformat(day)
        hot.append(max(0.0,app[day]-80.0));wet.append(min(precip.get(day,0.0),2.0))
        dow.append(dd.weekday());mon.append(dd.month);yr.append(dd.year);hol.append(1.0 if day in HOL else 0.0)
    n=len(days);cols=[np.ones(n),np.array(hot),np.array(wet)];names=["c","hot","precip"]
    for kk in range(1,7): cols.append((np.array(dow)==kk).astype(float));names.append(f"dow{kk}")
    for m in[6,7,8,9]: cols.append((np.array(mon)==m).astype(float));names.append(f"m{m}")
    for y in[2023,2024]: cols.append((np.array(yr)==y).astype(float));names.append(f"y{y}")
    cols.append(np.array(hol));names.append("hol")
    return np.column_stack(cols),names
model={}
for cid,d in comp.items():
    rows=[(day,rd) for day,rd in d["rows"] if rd>=50]
    if len(rows)<150: continue
    days=[r[0] for r in rows];y=np.log(np.array([r[1] for r in rows]))
    X,names=design(days);keep=[i for i in range(X.shape[1]) if names[i]=="c" or X[:,i].std()>0]
    X=X[:,keep];names=[names[i] for i in keep]
    beta,_,rank,_=np.linalg.lstsq(X,y,rcond=None)
    if rank<X.shape[1]: continue
    resid=y-X@beta;dof=len(y)-X.shape[1];sig2=(resid@resid)/dof
    se=np.sqrt(np.clip(np.diag(np.linalg.pinv(X.T@X))*sig2,0,None))
    hi=names.index("hot");b=beta[hi];sb=se[hi];tv=b/sb if sb>0 else 0
    if not(np.isfinite(b) and np.isfinite(tv)): continue
    pen95=(math.exp(b*15)-1)*100
    reg="suppressed" if(tv<=-2 and pen95<=-2) else "attractor" if(tv>=2 and pen95>=2) else "neutral"
    model[cid]={"name":d["name"],"boro":d["boro"],"lat":d["lat"],"lon":d["lon"],
        "pen95":round(pen95,1),"t":round(float(tv),2),"regime":reg,"mean_rides":float(np.exp(np.mean(y)))}
log(f"modeled: {len(model)}")

# ---------- STRUCTURE ----------
struct=json.load(open(os.path.join(DATA,"subway_structure.json")))
cx={}
for s in struct:
    cid=s.get("complex_id")
    if cid is None: continue
    cx.setdefault(str(cid),set()).add(s.get("structure"))
def ptype_of(cid):
    ss=cx.get(str(cid),set())
    if ss & {"Elevated","Viaduct"}: return "elevated"
    if ss & {"Open Cut","At Grade","Embankment"}: return "open"
    return "underground"

# ---------- LEGS via NYC graph ----------
Gp=pickle.load(open(os.path.join(D,"nyc_walk_graph.pkl"),"rb"));CRS=Gp.graph["crs"]
fwd=Transformer.from_crs("EPSG:4326",CRS,always_xy=True).transform
inv=Transformer.from_crs(CRS,"EPSG:4326",always_xy=True).transform
nx_x={n:d["x"] for n,d in Gp.nodes(data=True)};nx_y={n:d["y"] for n,d in Gp.nodes(data=True)}
keep=set()
for c in nx.weakly_connected_components(Gp):
    if len(c)>=100: keep|=c
gnodes=np.array(list(keep));gkdt=cKDTree(np.array([(nx_x[n],nx_y[n]) for n in gnodes]))
log(f"graph {len(Gp.nodes)} nodes, snap pool {len(keep)}")
def projpts(rows):
    lon=np.array([float(r["longitude"]) for r in rows]);lat=np.array([float(r["latitude"]) for r in rows])
    x,yv=fwd(lon,lat);return np.column_stack([x,yv])
trees=json.load(open(os.path.join(DATA,"trees_nyc.json")));tx=projpts(trees)
hw={"Good":1.0,"Fair":0.7,"Poor":0.4};twt=np.array([hw.get((r.get("health") or "Good"),0.7) for r in trees]);tzip=[r.get("zipcode") for r in trees]
bx=projpts(json.load(open(os.path.join(DATA,"benches_nyc.json"))))
hx=projpts(json.load(open(os.path.join(DATA,"shelters_nyc.json"))))
tree_tree=STRtree(shapely.points(tx));bench_tree=STRtree(shapely.points(bx));shel_tree=STRtree(shapely.points(hx))
hvi_map={r["zcta20"]:int(r["hvi"]) for r in json.load(open(os.path.join(DATA,"hvi_zcta.json"))) if r.get("hvi") not in(None,"")}
tkdt=cKDTree(tx)
log(f"trees {len(tx)} benches {len(bx)} shelters {len(hx)}")
CUT=400.0;BUF=18.0
def shed(node):
    H=nx.ego_graph(Gp,node,radius=CUT,distance="length");g=[]
    for u,v,dd in H.edges(data=True):
        ge=dd.get("geometry")
        if ge is None: ge=MultiLineString([[(nx_x[u],nx_y[u]),(nx_x[v],nx_y[v])]]).geoms[0]
        g.append(ge)
    if not g: return Point(nx_x[node],nx_y[node]).buffer(CUT*0.6)
    return MultiLineString(g).buffer(BUF,cap_style=2,join_style=1)
def count_in(strt,pp,poly,coords,idxsub=None):
    return sum(1 for i in strt.query(poly) if pp.contains(Point(coords[i])))

items=list(model.items())
for n,(cid,m) in enumerate(items):
    x,yv=fwd(m["lon"],m["lat"]);node=gnodes[gkdt.query([x,yv])[1]]
    poly=shed(node);pp=prep(poly);area=poly.area/1e6
    ti=[i for i in tree_tree.query(poly) if pp.contains(Point(tx[i]))]
    m["canopy"]=round(len(ti)/area,0) if area>0 else 0
    m["seats"]=count_in(bench_tree,pp,poly,bx)+count_in(shel_tree,pp,poly,hx)
    m["_walk_raw"]=m["canopy"];m["_seat_raw"]=m["seats"]
    zs=[tzip[i] for i in ti if tzip[i]]
    zc=max(set(zs),key=zs.count) if zs else tzip[int(tkdt.query([x,yv])[1])]
    m["hvi"]=hvi_map.get(zc,3);m["ptype"]=ptype_of(cid)
    if n%80==0: log(f"  legs {n}/{len(items)}")
log("legs done")

# leg burdens (normalized citywide)
def mm(v):
    v=np.array(v,float);lo,hi=v.min(),v.max();return (v-lo)/(hi-lo) if hi>lo else np.zeros_like(v)
canopy_n=mm([m["canopy"] for _,m in items]);seat_n=mm([m["seats"] for _,m in items])
PB={"elevated":100,"open":70,"underground":55}
for i,(cid,m) in enumerate(items):
    m["walk"]=round(100*(1-canopy_n[i]));m["wait"]=round(100*(1-seat_n[i]));m["platform"]=PB[m["ptype"]]
    legs={"walk":m["walk"],"wait":m["wait"],"platform":m["platform"]};m["dominant"]=max(legs,key=legs.get)
    m["burden"]=round((m["walk"]+m["wait"]+m["platform"])/3)

# ---------- FHSR + fields ----------
EXT={"2020s":6,"2030s":15,"2050s":37};TYPE={"elevated":"Elevated / Open","open":"Open Cut","underground":"Underground"}
FB={"platform_elevated":["direct sun","platform too hot","no airflow"],"platform_open":["direct sun","exposed platform"],
    "platform_underground":["stuffy","no airflow","platform heat"],"wait":["long wait","no seating","no shelter"],
    "walk":["hot walk","no shade on approach"],"attractor":["crowded platform","sun exposure","long exposed wait"],"neutral":["warm platform","occasional crowding"]}
def prescribe(reg,dom,pt):
    # Every complex here is an MTA-operated subway station; MTA owns and maintains the
    # whole envelope (platform, mezzanine, waiting area). Only the "walk" leg — the public
    # sidewalk approach, cooled by street trees — leaves MTA property. Station type (pt)
    # sets the nature of the on-station fix.
    if reg=="attractor": return("Seasonal shade + water + crowd readiness","MTA / Parks","Seasonal","$$")
    if reg=="neutral": return("Monitor + rider feedback","MTA","Monitor","$")
    if dom=="walk": return("Street trees + shaded approach","Parks / DOT","Years","$")
    if dom=="wait":
        # waiting happens on the platform/mezzanine, inside the station -> MTA
        if pt=="underground": return("Platform seating + mezzanine cooling","MTA","Months","$$")
        return("Platform shade + seating","MTA","Weeks","$")
    if pt=="underground": return("Ventilation + thermal management","MTA","Years","$$$")
    return("Shade canopy + reflective roof","MTA","Months","$$")
def conf(t):
    a=abs(t);return "High" if a>=3.5 else "Medium–High" if a>=2.5 else "Medium" if a>=2 else "Low–Medium"
rid=np.array([m["mean_rides"] for _,m in items]);hvi_n=mm([m["hvi"] for _,m in items]);bur_n=mm([m["burden"] for _,m in items])
def trips_of(m,days): return (abs(m["pen95"])/100.0 if m["regime"]=="suppressed" else 0.0)*m["mean_rides"]*days
def rtier(x):
    q=np.quantile(rid,[.33,.66]);return "High" if x>=q[1] else "Medium" if x>=q[0] else "Low"
stations=[]
for i,(cid,m) in enumerate(items):
    action,owner,delivery,cost=prescribe(m["regime"],m["dominant"],m["ptype"])
    trips={d:round(trips_of(m,EXT[d])) for d in EXT}
    fhsr={}
    for d in EXT:
        wtd=[trips_of(items[j][1],EXT[d])*(1+0.5*hvi_n[j])*(1+0.3*bur_n[j]) for j in range(len(items))]
        fhsr[d]=round(100*mm(wtd)[i]) if m["regime"]=="suppressed" else 0
    fbkey=("platform_"+m["ptype"]) if m["dominant"]=="platform" else (m["dominant"] if m["regime"]=="suppressed" else m["regime"])
    stations.append({"name":re.sub(r'\s*\(.*$','',m["name"]).strip(),"label":m["name"],"boro":m["boro"],
        "routes":re.findall(r'[A-Z0-9]+(?=[,)])|(?<=\()[A-Z0-9]+',m["name"])[:6],
        "regime":m["regime"],"penalty":m["pen95"],"t":m["t"],"walk":m["walk"],"wait":m["wait"],"platform":m["platform"],
        "dominant":m["dominant"],"type":TYPE[m["ptype"]],"owner":owner,"delivery":delivery,"cost":cost,
        "confidence":conf(m["t"]),"action":action,"feedback":FB.get(fbkey,FB["neutral"]),
        "canopy":m["canopy"],"seats":m["seats"],"hvi":m["hvi"],"rides":round(m["mean_rides"]),
        "ridersTier":rtier(m["mean_rides"]),"tripsLost":trips,"fhsr":fhsr,"lat":m["lat"],"lon":m["lon"]})
for d in EXT:
    vals=sorted((s["fhsr"][d] for s in stations if s["fhsr"][d]>0),reverse=True);nn=len(vals)
    hi=vals[int(nn*.33)] if nn else 9e9;mid=vals[int(nn*.66)] if nn else 9e9
    for s in stations:
        f=s["fhsr"][d];s.setdefault("tier",{})[d]="none" if f<=0 else "red" if f>=hi else "amber" if f>=mid else "green"
stations.sort(key=lambda s:-s["fhsr"]["2050s"])

# ---------- exemplar curves (citywide) ----------
BINS=[(60,75),(75,82),(82,88),(88,94),(94,110)];LAB=["<75","75-82","82-88","88-94","94+"]
wkr={}
for r in ride:
    day=r["day"][:10]
    if day not in app or dt.date.fromisoformat(day).weekday()>=5: continue
    try: rd=float(r["rides"])
    except: continue
    wkr.setdefault(r["station_complex"],[]).append((app[day],rd))
def curve(nm):
    d=wkr.get(nm,[]);means=[]
    for lo,hi in BINS:
        v=[rd for t,rd in d if lo<=t<hi];means.append(np.mean(v) if v else np.nan)
    base=means[1] if not np.isnan(means[1]) else np.nanmean(means)
    return [None if np.isnan(x) else round(x/base*100,1) for x in means]
def pick(reg):
    c=[s for s in stations if s["regime"]==reg];c.sort(key=lambda s:-s["rides"]);return c[0]["label"] if c else None
ex=[]
for nm,reg in [(pick("suppressed"),"suppressed"),(pick("neutral"),"neutral"),(pick("attractor"),"attractor")]:
    if nm: ex.append({"name":re.sub(r'\s*\(.*$','',nm),"regime":reg,"curve":curve(nm)})

# ---------- map rings (all NYC) ----------
gj=json.load(open(os.path.join(DATA,"nyc_boroughs.geojson")))
geom=unary_union([shape(f["geometry"]) for f in gj["features"]]).simplify(0.0006,preserve_topology=True)
polys=[geom] if geom.geom_type=="Polygon" else list(geom.geoms)
polys=[p for p in polys if p.area>2e-5];polys.sort(key=lambda p:p.area,reverse=True)
rings=[[[round(x,5),round(y,5)] for x,y in p.exterior.coords] for p in polys]
xs=[pt[0] for r in rings for pt in r];ys=[pt[1] for r in rings for pt in r]
bounds=[min(xs),min(ys),max(xs),max(ys)]

meta={"n":len(stations),"sig":sum(1 for s in stations if abs(s["t"])>=2),
      "suppressed":sum(1 for s in stations if s["regime"]=="suppressed"),
      "neutral":sum(1 for s in stations if s["regime"]=="neutral"),
      "attractor":sum(1 for s in stations if s["regime"]=="attractor")}
dom={k:sum(1 for s in stations if s["dominant"]==k and s["regime"]=="suppressed") for k in("platform","wait","walk")}
play={"elevated":sum(1 for s in stations if s["regime"]=="suppressed" and s["dominant"]=="platform" and s["type"]=="Elevated / Open"),
      "wait":dom["wait"],"underground":sum(1 for s in stations if s["regime"]=="suppressed" and s["type"]=="Underground"),
      "walk":dom["walk"],"beach":meta["attractor"]}
out={"stations":stations,"meta":meta,"bins":LAB,"exemplars":ex,"ext":EXT,"dom":dom,"play":play,"bounds":bounds,"rings":rings}
json.dump(out,open(os.path.join(D,"thi.json"),"w"))
tot={d:sum(s["tripsLost"][d] for s in stations) for d in EXT}
log(f"DONE. stations={len(stations)} meta={meta}")
log(f"trips lost/yr: {tot}")
print("Top 8 by 2050s FHSR:")
for s in stations[:8]:
    print(f"  {s['fhsr']['2050s']:>3} {s['tier']['2050s']:>5} {s['boro'][:2]:2} {s['penalty']:>5}% r{s['rides']:>6} hvi{s['hvi']} {s['name'][:24]:24} {s['dominant'][:4]} {s['owner']}")
import os as _o;print("thi.json KB:",round(_o.path.getsize(os.path.join(D,'thi.json'))/1024,1))
