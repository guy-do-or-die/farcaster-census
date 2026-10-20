#!/usr/bin/env python3
"""Read-only scan of public optInStatus for a fid range via client.farcaster.xyz.

GET https://client.farcaster.xyz/v2/user?fid=N (no auth) -> result.user.viewerContext.optInStatus
Writes JSONL (fid, username, followerCount, optInStatus, http) and prints a tally. The output is raw per-fid data:
keep it out of the repo (see .gitignore) and never publish it.
Polite: 8 worker threads, rps is per thread (default 0.875, ~7 requests/s in total);
after 10 consecutive 429/5xx answers it pauses 60 s.
Usage: python3 -I optin_scan.py START END OUT.jsonl [rps]
"""
import os, sys, json, time, threading, queue, urllib.request, urllib.error

if sys.argv[1].endswith('.txt'):
    fids_list = [int(x) for x in open(sys.argv[1]).read().split()]
    start, end, out = min(fids_list), max(fids_list), sys.argv[2]
else:
    fids_list = None
    start, end, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
rps = float(sys.argv[-1]) if len(sys.argv) > (3 if fids_list else 4) else 0.875
UA = "optin-status-survey/0.1 (read-only research; contact: %s)" % os.environ.get("CENSUS_CONTACT", "unset; set CENSUS_CONTACT")

done = set()
try:
    for line in open(out):
        try:
            _r = json.loads(line)
            if _r.get("http") == 200 and _r.get("optInStatus"): done.add(_r["fid"])
        except Exception: pass
except FileNotFoundError:
    pass

q = queue.Queue()
for fid in (fids_list if fids_list else range(start, end + 1)):
    if fid not in done: q.put(fid)
total = q.qsize()
lock = threading.Lock()
errors = {"n": 0, "streak": 0}
tally = {}
fout = open(out, "a")

def fetch(fid):
    req = urllib.request.Request(f"https://client.farcaster.xyz/v2/user?fid={fid}", headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
            u = d.get("result", {}).get("user", {})
            return {"fid": fid, "username": u.get("username"), "followerCount": u.get("followerCount"),
                    "optInStatus": (u.get("viewerContext") or {}).get("optInStatus"), "http": 200}
    except urllib.error.HTTPError as e:
        return {"fid": fid, "http": e.code}
    except Exception as e:
        return {"fid": fid, "http": -1, "err": str(e)[:80]}

def worker():
    while True:
        try: fid = q.get_nowait()
        except queue.Empty: return
        rec = fetch(fid)
        with lock:
            fout.write(json.dumps(rec) + "\n"); fout.flush()
            if rec["http"] in (429, 500, 502, 503):
                errors["n"] += 1; errors["streak"] += 1
            else:
                errors["streak"] = 0
            k = rec.get("optInStatus") or f"http{rec['http']}"
            tally[k] = tally.get(k, 0) + 1
        if errors["streak"] >= 10:
            with lock:
                if errors["streak"] >= 10:
                    print("backoff 60s after sustained 429/5xx", file=sys.stderr, flush=True); errors["streak"] = 0
            time.sleep(60)
            if rec["http"] != 200: q.put(fid)
        time.sleep(1.0 / rps)  # per-thread pacing

threads = [threading.Thread(target=worker, daemon=True) for _ in range(8)]
t0 = time.time()
for t in threads: t.start()
while any(t.is_alive() for t in threads):
    time.sleep(30)
    with lock:
        n = sum(tally.values())
    print(f"{n}/{total} done, {int(time.time()-t0)}s, tally={json.dumps(tally, sort_keys=True)}", file=sys.stderr, flush=True)
with lock:
    print(json.dumps({"range": [start, end], "tally": tally, "errors": errors["n"], "seconds": int(time.time()-t0)}, sort_keys=True))
