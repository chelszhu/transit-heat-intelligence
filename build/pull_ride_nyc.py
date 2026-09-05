#!/usr/bin/env python3
"""Citywide afternoon ridership, chunked by year (more robust)."""
import json, os, time, urllib.parse, urllib.request
DATA=os.path.join(os.path.dirname(__file__),"..","data")
def soda(params,page=50000):
    base="https://data.ny.gov/resource/wujg-7c2s.json";out=[];off=0
    while True:
        p=dict(params);p["$limit"]=page;p["$offset"]=off
        url=base+"?"+urllib.parse.urlencode(p,quote_via=urllib.parse.quote)
        req=urllib.request.Request(url,headers={"User-Agent":"thi"})
        for a in range(5):
            try:
                with urllib.request.urlopen(req,timeout=300) as r: chunk=json.load(r);break
            except Exception as e:
                if a==4: raise
                time.sleep(4*(a+1))
        out.extend(chunk)
        if len(chunk)<page: break
        off+=page
    return out
allrows=[]
for yr in (2022,2023,2024):
    t=time.time()
    where=(f"date_extract_hh(transit_timestamp) between 12 and 19 "
           f"AND transit_timestamp between '{yr}-05-01T00:00:00' and '{yr}-10-01T00:00:00'")
    rows=soda({"$select":"station_complex_id,station_complex,borough,date_trunc_ymd(transit_timestamp) as day,"
                         "avg(latitude) as lat,avg(longitude) as lon,sum(ridership) as rides",
               "$where":where,"$group":"station_complex_id,station_complex,borough,day"})
    print(f"{yr}: {len(rows)} rows in {time.time()-t:.0f}s",flush=True)
    allrows.extend(rows)
json.dump(allrows,open(os.path.join(DATA,"ridership_afternoon_nyc.json"),"w"))
print(f"TOTAL {len(allrows)} station-day rows",flush=True)
