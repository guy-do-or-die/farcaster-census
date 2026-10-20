"""Post-announcement casting activity of restricted/departed accounts, measured on public Snapchain nodes.
Reads exact optInStatus rows from sources/optin-scan-*.jsonl, probes /v1/castsByFid on the fork node (haatz.quilibrium.com)
and on the farcaster.xyz node (snap.farcaster.xyz:3381), compares latest-cast hashes. Writes counts only; per-fid rows stay in memory and are never written.
usage: python3 -I scripts/hypersnap_activity.py [sample_size=300] [seed=7]
"""
import os, sys, json, random, datetime, collections, urllib.request, urllib.error, concurrent.futures as cf
S=os.environ.get("CENSUS_DATA", "./data")
N=int(sys.argv[1]) if len(sys.argv)>1 else 300; SEED=int(sys.argv[2]) if len(sys.argv)>2 else 7
UA="census-research (contact: %s)" % os.environ.get("CENSUS_CONTACT", "unset; set CENSUS_CONTACT"); FE=1609459200
ANN=datetime.datetime(2026,10,15,17,47,tzinfo=datetime.timezone.utc)
FORK="https://haatz.quilibrium.com"; NS="https://snap.farcaster.xyz:3381"
def get(url,timeout=40):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return r.status, json.load(r)
    except urllib.error.HTTPError as e: return e.code, None
    except Exception: return -1, None
def casts(host,fid,n=25):
    s,j=get(f"{host}/v1/castsByFid?fid={fid}&pageSize={n}&reverse=true")
    if s!=200 or not j: return None
    return [(m.get("hash"),datetime.datetime.fromtimestamp(m["data"]["timestamp"]+FE,datetime.timezone.utc)) for m in j.get("messages",[])]
rows={}
for f in ["optin-scan-1-50000.jsonl","optin-scan-50k-300k.jsonl","optin-scan-prefiltered-300k-1550k.jsonl","optin-scan-3300k-3355k.jsonl"]:
    for line in open(f"{S}/{f}"):
        try: r=json.loads(line)
        except: continue
        if r.get("http")==200 and r.get("optInStatus"): rows[r["fid"]]=r
random.seed(SEED)
groups={"moderated_out":[r for r in rows.values() if r["optInStatus"]=="moderated_out"],
        "opted_out":[r for r in rows.values() if r["optInStatus"]=="opted_out"],
        "opted_in_base":random.sample([r for r in rows.values() if r["optInStatus"]=="opted_in" and (r.get("followerCount") or 0)>=100],N),
        "pending_base":random.sample([r for r in rows.values() if r["optInStatus"]=="pending" and (r.get("followerCount") or 0)>=100],N)}
def probe(r):
    c=casts(NS,r["fid"])
    if c is None: return None
    ts=[t for _,t in c]; last=max(ts) if ts else None
    out={"fid":r["fid"],"n":len(ts),"last":last and last.isoformat(),"post_ann":sum(1 for t in ts if t>ANN),"fc":r.get("followerCount") or 0}
    if out["post_ann"]>0:
        f=casts(FORK,r["fid"],1); out["fork_same_hash"]=bool(f and c and f[0][0]==c[0][0])
    return out
report={"ts":datetime.datetime.now(datetime.timezone.utc).isoformat(),"groups":{}}
for g,items in groups.items():
    with cf.ThreadPoolExecutor(6) as ex: res=[x for x in ex.map(probe,items) if x]
    n=len(res); pa=[x for x in res if x["post_ann"]>0]
    d14=sum(1 for x in res if x["last"] and 0<=(ANN-datetime.datetime.fromisoformat(x["last"])).total_seconds()<=14*86400)
    d60=sum(1 for x in res if x["last"] and (ANN-datetime.datetime.fromisoformat(x["last"])).total_seconds()>60*86400)
    same=sum(1 for x in pa if x.get("fork_same_hash"))
    print(f"{g}: n={n} | cast after announcement {len(pa)} ({len(pa)/n*100:.0f}%) | latest hash identical on fork node {same}/{len(pa)} | last cast within 14 d before {d14} ({d14/n*100:.0f}%) | last cast >60 d before {d60} ({d60/n*100:.0f}%)")
    report["groups"][g]={"n":n,"post_ann":len(pa),"fork_same_hash":same,"within14d_before":d14,"over60d_before":d60}
json.dump(report,open(f"{S}/hypersnap-activity-report.json","w"))
print("saved", f"{S}/hypersnap-activity-report.json")
