#!/usr/bin/env python3
"""Mark which fids have at least one cast, via a Snapchain read node (haatz.quilibrium.com).
Writes OUT_PREFIX-<lo>-<hi>.txt (fids with casts, one per line) and .done sentinel per chunk. Resumable.
Usage: python3 -I hub_prefilter.py START END OUT_PREFIX [chunk=50000] [threads=10]
"""
import os, sys, json, time, threading, queue, urllib.request, os

start, end, prefix = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
CHUNK = int(sys.argv[4]) if len(sys.argv) > 4 else 50000
THREADS = int(sys.argv[5]) if len(sys.argv) > 5 else 10
UA = {"User-Agent": "optin-status-survey/0.1 (read-only research; contact: %s)" % os.environ.get("CENSUS_CONTACT", "unset; set CENSUS_CONTACT")}

def has_casts(fid):
    for _ in range(3):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://haatz.quilibrium.com/v1/castsByFid?fid={fid}&pageSize=1&reverse=true", headers=UA), timeout=25))
            return 1 if d.get("messages") else 0
        except Exception:
            time.sleep(1.0)
    return -1  # unknown → keep (scan it anyway)

lo = start
while lo <= end:
    hi = min(lo + CHUNK - 1, end)
    out = f"{prefix}-{lo}-{hi}.txt"
    if os.path.exists(out + ".done"):
        lo = hi + 1; continue
    q = queue.Queue(); [q.put(f) for f in range(lo, hi + 1)]
    keep = []; lock = threading.Lock(); stats = {"zero": 0, "casts": 0, "unknown": 0}
    def worker():
        while True:
            try: fid = q.get_nowait()
            except queue.Empty: return
            r = has_casts(fid)
            with lock:
                if r == 0: stats["zero"] += 1
                else:
                    keep.append(fid); stats["casts" if r == 1 else "unknown"] += 1
            time.sleep(0.02)
    t0 = time.time()
    th = [threading.Thread(target=worker, daemon=True) for _ in range(THREADS)]
    [t.start() for t in th]; [t.join() for t in th]
    keep.sort()
    with open(out, "w") as f: f.write("\n".join(map(str, keep)))
    open(out + ".done", "w").write(json.dumps({"lo": lo, "hi": hi, "seconds": int(time.time() - t0), **stats}))
    print(f"chunk {lo}-{hi}: casts {stats['casts']}, zero {stats['zero']}, unknown {stats['unknown']}, {int(time.time()-t0)}s", file=sys.stderr, flush=True)
    lo = hi + 1
print("PREFILTER DONE")
