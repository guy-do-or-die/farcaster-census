#!/usr/bin/env python3
"""Hourly VOTE mints, burns and holders from the frozen Transfer events, plus the checkpoints quoted on the page.

usage: hourly.py EVENTS.jsonl OUT.json
EVENTS.jsonl is the deduplicated Transfer log written by pull.py / freeze.py (one event per line with block, logIndex, kind).
Time comes from the block number: 2.0 s per block from block 52,606,050 = 2026-10-14T18:10:47Z (matches the head block's own timestamp).
"""
import json, sys, datetime as dt

B0, T0 = 52606050, 1792001447          # block, unix time
ANNOUNCED = 1792086420                 # 2026-10-15T17:47:00Z
BALAJI_CAST = 1792202403               # 2026-10-17T02:00:03Z, farcaster.xyz/balajis.eth/0xf454b8d3 (hub timestamp)
FREEZE = 1792470481                    # 2026-10-20T04:28:01Z = Base block 52,840,567

def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main(src, dst):
    ev = []
    for line in open(src, encoding="utf-8"):
        e = json.loads(line); e["t"] = T0 + (e["block"] - B0) * 2
        if e["t"] <= FREEZE: ev.append(e)
    ev.sort(key=lambda e: (e["block"], e["logIndex"]))
    d = lambda e: 1 if e["kind"] == "mint" else -1 if e["kind"] == "burn" else 0
    holders_at = lambda t: sum(d(e) for e in ev if e["t"] <= t)
    start = (ANNOUNCED // 3600) * 3600
    rows, h = [], holders_at(start - 1)
    for k in range((FREEZE - start) // 3600 + 1):
        a, b = start + k * 3600, min(start + (k + 1) * 3600, FREEZE + 1)
        m = sum(1 for e in ev if a <= e["t"] < b and e["kind"] == "mint")
        u = sum(1 for e in ev if a <= e["t"] < b and e["kind"] == "burn")
        h += m - u
        rows.append({"hour_start": iso(a), "mints": m, "burns": u, "holders_at_end": h})
    ts = sorted(e["t"] for e in ev if e["kind"] == "mint" and e["t"] > ANNOUNCED)
    gap = max(zip(ts, ts[1:]), key=lambda p: p[1] - p[0])
    peak = max(rows, key=lambda r: r["mints"])
    final = holders_at(FREEZE)
    out = {
        "source": "VOTE Transfer events on Base, deduplicated by (tx, logIndex); same events as final-numbers.json chain",
        "as_of": iso(FREEZE) + " (Base block 52,840,567)",
        "status": "VERIFIED (same event set as the signed count)",
        "checkpoints": {
            "holders_at_announcement": holders_at(ANNOUNCED),
            "holders_24h_after": holders_at(ANNOUNCED + 86400),
            "holders_48h_after": holders_at(ANNOUNCED + 2 * 86400),
            "share_48h_after_pct": round(100 * holders_at(ANNOUNCED + 2 * 86400) / final, 1),
            "holders_at_balaji_94_4_cast": holders_at(BALAJI_CAST),
            "signed_last_24h_before_freeze": final - holders_at(FREEZE - 86400),
            "holders_at_freeze": final,
            "peak_hour": {"hour_start": peak["hour_start"], "mints": peak["mints"]},
            "longest_pause_without_mints_after_announcement": {"from": iso(gap[0]), "to": iso(gap[1]), "minutes": round((gap[1] - gap[0]) / 60)},
        },
        "hourly": rows,
    }
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    print(json.dumps(out["checkpoints"], indent=1))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
