#!/usr/bin/env python3
"""Read-only pull of VOTE (0x4ecfed27...) Transfer logs on Base, 1,000-block windows, from two
public RPCs independently; compares the two result sets and fetches the head block timestamp.
usage: python3 -I pull.py FROM_BLOCK OUT_PREFIX [HEAD]
writes OUT_PREFIX-events.jsonl (format of sources/vote-transfers-*-events.jsonl) and OUT_PREFIX-meta.json"""
import sys, json, time, urllib.request
VOTE = "0x4ecfed276c566aeb49da1f3a888e8dbb7263028d"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
SRC = {"A": ["https://base.rpc.thirdweb.com", "https://base-rpc.publicnode.com"],
       "B": ["https://mainnet.base.org", "https://base.gateway.tenderly.co"]}
FROM = int(sys.argv[1]); OUT = sys.argv[2]
rid = [0]
def rpc(url, method, params):
    rid[0] += 1
    body = json.dumps({"jsonrpc": "2.0", "id": rid[0], "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "vote-transfer-survey/0.2"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    if "error" in d: raise RuntimeError(d["error"])
    return d["result"]
def call(urls, method, params):
    last = None
    for attempt in range(4):
        for u in urls:
            try: return rpc(u, method, params), u
            except Exception as e: last = e; time.sleep(0.6 * (attempt + 1))
    raise last
head_hex, _ = call(SRC["A"], "eth_blockNumber", [])
HEAD = int(sys.argv[3]) if len(sys.argv) > 3 else int(head_hex, 16)
hb, hu = call(SRC["A"], "eth_getBlockByNumber", [hex(HEAD), False])
hb2, hu2 = call(SRC["B"], "eth_getBlockByNumber", [hex(HEAD), False])
assert hb["hash"] == hb2["hash"], ("head hash differs", hb["hash"], hb2["hash"])
HEAD_TS = int(hb["timestamp"], 16)
res = {}; used = {}
for name, urls in SRC.items():
    logs = {}; b = FROM; windows = 0
    while b <= HEAD:
        hi = min(b + 999, HEAD)
        r, u = call(urls, "eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(hi), "address": VOTE, "topics": [TOPIC]}])
        used[u] = used.get(u, 0) + 1
        for l in r:
            if l.get("removed"): continue
            logs[(l["transactionHash"], int(l["logIndex"], 16))] = l
        b = hi + 1; windows += 1; time.sleep(0.12)
        if windows % 50 == 0: print(name, "windows", windows, "up to", hi, "logs", len(logs), file=sys.stderr, flush=True)
    res[name] = logs
ka, kb = set(res["A"]), set(res["B"])
events = []
for k in sorted(ka | kb):
    l = res["A"].get(k) or res["B"].get(k)
    frm = "0x" + l["topics"][1][-40:]; to = "0x" + l["topics"][2][-40:]
    kind = "mint" if int(frm, 16) == 0 else ("burn" if int(to, 16) == 0 else "transfer")
    events.append({"block": int(l["blockNumber"], 16), "tx": l["transactionHash"], "logIndex": int(l["logIndex"], 16),
                   "kind": kind, "from": frm, "to": to, "tokenId": int(l["topics"][3], 16)})
events.sort(key=lambda e: (e["block"], e["logIndex"]))
# timestamps for burn-address events, as scripts/vote_transfers.py does
burn_addrs = {e["from"] for e in events if e["kind"] == "burn"}
tsc = {}
for e in events:
    a = e["to"] if e["kind"] == "mint" else e["from"]
    if a in burn_addrs:
        if e["block"] not in tsc:
            bb, _ = call(SRC["A"], "eth_getBlockByNumber", [hex(e["block"]), False]); tsc[e["block"]] = int(bb["timestamp"], 16)
        e["ts"] = tsc[e["block"]]
with open(OUT + "-events.jsonl", "w") as f:
    for e in events: f.write(json.dumps(e) + "\n")
meta = {"from_block": FROM, "head": HEAD, "head_hash": hb["hash"], "head_ts": HEAD_TS,
        "head_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(HEAD_TS)),
        "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "window_blocks": 1000, "logs_A": len(ka), "logs_B": len(kb), "only_A": len(ka - kb), "only_B": len(kb - ka),
        "events": len(events), "mints": sum(e["kind"] == "mint" for e in events), "burns": sum(e["kind"] == "burn" for e in events),
        "transfers": sum(e["kind"] == "transfer" for e in events), "rpc_calls_by_url": used,
        "sources": {k: v for k, v in SRC.items()}}
json.dump(meta, open(OUT + "-meta.json", "w"), indent=1)
print(json.dumps(meta))
