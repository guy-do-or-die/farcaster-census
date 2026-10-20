#!/usr/bin/env python3
"""Pull all ERC-721 Transfer logs of the VOTE NFT on Base and classify per address:
mint (from 0x0), burn (to 0x0), re-mint after burn. Read-only JSON-RPC, chunked eth_getLogs.
Usage: python3 -I vote_transfers.py OUT_PREFIX [from_block]
"""
import os, sys, json, time, urllib.request

VOTE = "0x4ecfed276c566aeb49da1f3a888e8dbb7263028d"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # Transfer(address,address,uint256)
RPCS = ["https://base.rpc.thirdweb.com", "https://base.gateway.tenderly.co"]
out = sys.argv[1]
FROM = int(sys.argv[2]) if len(sys.argv) > 2 else 52_600_000  # ~13 Oct 2026; Base ≈ 2 s/block
CHUNK = 1000
rid = 0

def rpc(url, method, params):
    global rid; rid += 1
    body = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "vote-transfer-survey/0.1"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    if "error" in d: raise RuntimeError(d["error"])
    return d["result"]

_rot = [0]
def call(method, params):
    last = None
    _rot[0] += 1
    for url in RPCS[_rot[0] % len(RPCS):] + RPCS[:_rot[0] % len(RPCS)]:
        for _ in range(2):
            try: return rpc(url, method, params)
            except Exception as e: last = e; time.sleep(0.5)
    raise last

head = int(call("eth_blockNumber", []), 16)
logs = []
stack = []
b = FROM
while b <= head:
    stack.append((b, min(b + CHUNK - 1, head))); b += CHUNK
stack.reverse()
done_blocks = 0
while stack:
    lo, hi = stack.pop()
    try:
        res = call("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "address": VOTE, "topics": [TOPIC]}])
        logs += res; done_blocks += hi - lo + 1
        if done_blocks % (CHUNK * 200) < (hi - lo + 1):
            print(f"blocks done {done_blocks}, up to {hi}/{head}, logs {len(logs)}", file=sys.stderr, flush=True)
    except Exception as ex:
        if hi - lo >= 10:
            mid = (lo + hi) // 2
            stack.append((mid + 1, hi)); stack.append((lo, mid))
            print(f"split {lo}-{hi}: {str(ex)[:80]}", file=sys.stderr, flush=True)
        else:
            print(f"GIVING UP {lo}-{hi}: {ex}", file=sys.stderr, flush=True)
        time.sleep(1.0)
        continue
    time.sleep(0.2)

# block timestamps for the blocks that have logs (cache)
ts = {}
def block_ts(bn):
    if bn not in ts:
        ts[bn] = int(call("eth_getBlockByNumber", [hex(bn), False])["timestamp"], 16)
    return ts[bn]

events = []
for l in logs:
    frm = "0x" + l["topics"][1][-40:]; to = "0x" + l["topics"][2][-40:]; tid = int(l["topics"][3], 16); bn = int(l["blockNumber"], 16)
    kind = "mint" if int(frm, 16) == 0 else ("burn" if int(to, 16) == 0 else "transfer")
    events.append({"block": bn, "tx": l["transactionHash"], "logIndex": int(l["logIndex"], 16), "kind": kind, "from": frm, "to": to, "tokenId": tid})
events.sort(key=lambda x: (x["block"], x["logIndex"]))
blocks_needed = sorted({e["block"] for e in events if e["kind"] == "burn"} | {e["block"] for e in events if e["kind"] == "mint"})
# fetch timestamps lazily only for burn blocks and for mints of addresses that have burns, to limit RPC calls
addr = {}
for e in events:
    a = e["to"] if e["kind"] == "mint" else e["from"]
    addr.setdefault(a, []).append(e)
burn_addrs = {a for a, evs in addr.items() if any(x["kind"] == "burn" for x in evs)}
for a in burn_addrs:
    for e in addr[a]:
        e["ts"] = block_ts(e["block"])
with open(out + "-events.jsonl", "w") as f:
    for e in events: f.write(json.dumps(e) + "\n")
summary = {"head": head, "from_block": FROM, "mints": sum(e["kind"] == "mint" for e in events), "burns": sum(e["kind"] == "burn" for e in events),
           "transfers": sum(e["kind"] == "transfer" for e in events), "distinct_minters": len(addr), "addresses_with_burn": len(burn_addrs)}
pairs = []
for a in burn_addrs:
    evs = sorted(addr[a], key=lambda x: (x["block"], x["logIndex"]))
    seq = [(x["kind"], x["ts"], x["tokenId"], x["block"]) for x in evs]
    first_mint = next((x for x in evs if x["kind"] == "mint"), None)
    burns = [x for x in evs if x["kind"] == "burn"]
    remints = [x for x in evs if x["kind"] == "mint" and burns and x["block"] > burns[0]["block"]]
    pairs.append({"address": a, "sequence": seq, "first_mint_ts": first_mint["ts"] if first_mint else None,
                  "burn_ts": burns[0]["ts"] if burns else None, "secs_mint_to_burn": (burns[0]["ts"] - first_mint["ts"]) if (burns and first_mint) else None,
                  "reminted": bool(remints), "remint_ts": remints[0]["ts"] if remints else None})
summary["reminted_after_burn"] = sum(p["reminted"] for p in pairs)
summary["burn_within_10min_of_mint"] = sum(1 for p in pairs if p["secs_mint_to_burn"] is not None and p["secs_mint_to_burn"] <= 600)
with open(out + "-burn-pairs.json", "w") as f: json.dump({"summary": summary, "pairs": sorted(pairs, key=lambda p: p["burn_ts"] or 0)}, f, indent=1)
print(json.dumps(summary))
