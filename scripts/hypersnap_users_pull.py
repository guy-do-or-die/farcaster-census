"""Pull the whole fid space from the public Hypersnap read node (no auth, no rate limit per docs).
GET https://haatz.quilibrium.com/v2/farcaster/user/bulk?fids=a,b,c  (100 fids per call, 8 threads)
Writes JSONL: fid, u (username), fc (follower_count), fg (following_count), reg (registered_at), pfp (bool), va (# verified eth addrs).
Missing fids are omitted by the API; we write {"fid":N,"missing":true} for them.
usage: python3 -I scripts/hypersnap_users_pull.py <lo> <hi> <out.jsonl> [threads]
"""
import os, sys, json, time, urllib.request, urllib.error, concurrent.futures as cf, os, threading
lo, hi, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
threads = int(sys.argv[4]) if len(sys.argv) > 4 else 8
UA = "census-research (contact: %s)" % os.environ.get("CENSUS_CONTACT", "unset; set CENSUS_CONTACT")
done = set()
if os.path.exists(out):
    with open(out) as f:
        for line in f:
            try: done.add(json.loads(line)["fid"])
            except Exception: pass
todo = [f for f in range(lo, hi + 1) if f not in done]
chunks = [todo[i:i + 100] for i in range(0, len(todo), 100)]
print(f"todo {len(todo)} fids in {len(chunks)} calls (skipping {len(done)} done)", flush=True)
lock = threading.Lock()
def fetch(chunk):
    url = "https://haatz.quilibrium.com/v2/farcaster/user/bulk?fids=" + ",".join(map(str, chunk))
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                users = json.load(r).get("users", [])
            got = {u["fid"]: u for u in users}
            rows = []
            for f in chunk:
                u = got.get(f)
                if not u: rows.append({"fid": f, "missing": True}); continue
                rows.append({"fid": f, "u": u.get("username"), "fc": u.get("follower_count"), "fg": u.get("following_count"),
                             "reg": u.get("registered_at"), "pfp": bool(u.get("pfp_url")),
                             "va": len(((u.get("verified_addresses") or {}).get("eth_addresses") or []))})
            return rows
        except Exception as e:
            time.sleep(2 * (attempt + 1))
    return [{"fid": f, "error": True} for f in chunk]
t0 = time.time(); n = 0
with open(out, "a") as fo, cf.ThreadPoolExecutor(threads) as ex:
    for i, rows in enumerate(ex.map(fetch, chunks)):
        for r in rows: fo.write(json.dumps(r, ensure_ascii=False) + "\n")
        n += len(rows)
        if i % 500 == 0:
            fo.flush(); print(f"{i}/{len(chunks)} calls, {n} fids, {time.time()-t0:.0f}s", flush=True)
print(f"HSPULL DONE {n} fids in {time.time()-t0:.0f}s", flush=True)
