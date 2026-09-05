#!/usr/bin/env python3
"""Citywide amenities: trees, benches, shelters."""
import json, os, time, urllib.parse, urllib.request
DATA=os.path.join(os.path.dirname(__file__),"..","data")
def soda(dom,ds,params,page=50000):
    base=f"https://{dom}/resource/{ds}.json";out=[];off=0
    while True:
        p=dict(params);p["$limit"]=page;p["$offset"]=off
        url=base+"?"+urllib.parse.urlencode(p,quote_via=urllib.parse.quote)
        req=urllib.request.Request(url,headers={"User-Agent":"thi"})
        for a in range(5):
            try:
                with urllib.request.urlopen(req,timeout=240) as r: chunk=json.load(r);break
            except Exception:
                if a==4: raise
                time.sleep(4*(a+1))
        out.extend(chunk)
        if len(chunk)<page: break
        off+=page; print(f"    ...{len(out)}",flush=True)
    return out
print("trees...",flush=True)
tr=soda("data.cityofnewyork.us","uvpi-gqnh",{"$select":"latitude,longitude,health,spc_common,zipcode","status":"Alive"})
json.dump(tr,open(os.path.join(DATA,"trees_nyc.json"),"w"));print(f"trees {len(tr)}",flush=True)
print("benches...",flush=True)
be=soda("data.cityofnewyork.us","kuxa-tauh",{"$select":"latitude,longitude,boroname"})
json.dump(be,open(os.path.join(DATA,"benches_nyc.json"),"w"));print(f"benches {len(be)}",flush=True)
print("shelters...",flush=True)
sh=soda("data.cityofnewyork.us","t4f2-8md7",{"$select":"latitude,longitude,boro_name"})
json.dump(sh,open(os.path.join(DATA,"shelters_nyc.json"),"w"));print(f"shelters {len(sh)}",flush=True)
print("AMEN DONE",flush=True)
