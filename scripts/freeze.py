#!/usr/bin/env python3
"""Freeze of the final census numbers. Own code, stdlib only, no network. Reads local files only.
Outputs aggregate numbers only (no per-account lists) to stdout as JSON."""
import os, json, sys, array, collections, datetime as dt, math, os
S = os.environ.get("CENSUS_DATA", "./data") .rstrip("/") + "/"
FZ = os.path.dirname(os.path.abspath(__file__)) + "/"
VARIANT = set(sys.argv[1:])           # 'nosample', 'noretry', 'watchlist'
B0, T0 = 52606050, 1792001447          # Base: block 52,606,050 = 2026-10-14T18:10:47Z, 2.0 s/block
def btime(b): return dt.datetime.fromtimestamp(T0 + 2 * (b - B0), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
T_ANN = dt.datetime(2026, 10, 15, 17, 47, tzinfo=dt.timezone.utc)
T_CHANGE = "2026-10-19T09:36:36Z"
OUT = {}

# ---------------- chain ----------------
EVF = ["vote-transfers-events.jsonl", "vote-transfers-2-events.jsonl", "vote-transfers-3-events.jsonl",
       "vote-transfers-events-2026-10-19.jsonl", "verify-indep/taskD/d1_vote_logs.jsonl",
       "vote-transfers-4-events.jsonl", "vote-transfers-5-events.jsonl"]
ev = {}; per_file = {}; conflicts = 0
for f in EVF:
    n = 0
    for line in open(S + f):
        d = json.loads(line); n += 1
        k = (d["tx"].lower(), int(d.get("logIndex", d.get("li"))))
        v = (int(d["block"]), d["kind"], int(d["tokenId"]), d["from"].lower(), d["to"].lower())
        if k in ev and ev[k] != v: conflicts += 1
        ev[k] = v
    per_file[f] = n
evs = sorted((v[0], k[1], v[1], v[2], v[3], v[4]) for k, v in ev.items())
# cross-check against the full independent re-pull (two providers) to the same head
full = {}
for line in open(FZ + "full-events.jsonl"):
    d = json.loads(line); full[(d["tx"].lower(), int(d["logIndex"]))] = (d["block"], d["kind"], d["tokenId"])
fullmeta = json.load(open(FZ + "full-meta.json"))
HEAD = fullmeta["head"]
union_keys = set(ev); full_keys = set(full)
held = {}; nmint = collections.Counter(); first_mint_block = {}; last_mint_block = {}
for b, li, kind, tid, fr, to in evs:
    if kind == "mint":
        nmint[tid] += 1; first_mint_block.setdefault(tid, b); last_mint_block[tid] = b; held[tid] = True
    elif kind == "burn":
        held[tid] = False
    else:
        held[tid] = True
H = {t for t, v in held.items() if v}
M = set(first_mint_block)
kinds = collections.Counter(e[2] for e in evs)
OUT["chain"] = {
    "contract": "0x4ecfed276c566aeb49da1f3a888e8dbb7263028d (Base)", "head_block": HEAD, "head_time": fullmeta["head_time"],
    "head_hash": fullmeta["head_hash"], "files": per_file, "union_events": len(evs), "conflicting_duplicates": conflicts,
    "mints": kinds["mint"], "burns": kinds["burn"], "transfers": kinds["transfer"],
    "distinct_fids_minted": len(M), "fids_minted_twice": sum(1 for v in nmint.values() if v > 1),
    "holders": len(H), "max_block_in_union": evs[-1][0], "last_event_time": btime(evs[-1][0]),
    "crosscheck_full_repull": {"from_block": fullmeta["from_block"], "head": HEAD, "events": len(full_keys),
                               "in_union_not_repull": len(union_keys - full_keys), "in_repull_not_union": len(full_keys - union_keys),
                               "providers_identical": fullmeta["only_A"] == 0 and fullmeta["only_B"] == 0,
                               "pulled_at": fullmeta["pulled_at"]},
    "block_time_check": {"52606050": btime(52606050), str(HEAD): btime(HEAD)},
}
def holders_at(block):
    st = {}
    for b, li, kind, tid, fr, to in evs:
        if b > block: break
        st[tid] = kind != "burn"
    return {t for t, v in st.items() if v}
H_52839970 = holders_at(52839970)

# ---------------- statuses ----------------
NMAX = 3_400_000
ST = ["opted_in", "opted_out", "moderated_out", "pending"]; CODE = {s: i + 1 for i, s in enumerate(ST)}
status = bytearray(NMAX); src = bytearray(NMAX); nvalid = bytearray(NMAX)
ever_oo = bytearray(NMAX); ever_mo = bytearray(NMAX); had404 = bytearray(NMAX); hadErr = bytearray(NMAX)
last_kind = bytearray(NMAX); cfc = array.array("i", [-1]) * NMAX; uname_test = bytearray(NMAX)
PF1 = "optin-scan-prefiltered-300k-1550k.jsonl"; SEG1_END = 317678
ZC_OFF = int(open(FZ + "zerocast-offset.txt").read())
BATCHES = [
    ("optin-scan-1-50000.jsonl", 0, None, "17 Oct 03-05Z"),
    ("optin-sample-50k-3355k.jsonl", 0, None, "sample 17 Oct 13:05-14:37Z"),
    ("optin-retry.jsonl", 0, None, "retry 17 Oct ~13:38Z"),
    ("optin-scan-800k-1550k.jsonl", 0, None, "17 Oct ~16:20Z"),
    ("optin-scan-50k-300k.jsonl", 0, None, "17-18 Oct 00:02Z"),
    ("optin-scan-3300k-3355k.jsonl", 0, None, "-> 18 Oct 00:04Z"),
    ("optin-scan-300k-800k.jsonl", 0, None, "18 Oct ~00:10Z"),
    (PF1, 0, SEG1_END, "queue2 run1 18 Oct 00:30-13:55Z"),
    ("optin-scan-priority-fc1k.jsonl", 0, None, "priority 18 Oct 13:55-15:03Z"),
    (PF1, SEG1_END + 1, None, "queue2 run2 18 Oct 15:00Z-19 Oct 11:57Z"),
    ("optin-scan-retry.jsonl", 0, None, "retry 19 Oct 12:02Z"),
    ("optin-scan-prefiltered-1550k-3300k.jsonl", 0, None, "stage2 19 Oct 12:03Z-20 Oct 03:22Z"),
    ("optin-scan-zerocast.jsonl", 0, None, "zero-cast tail 20 Oct (frozen)"),
    ("optin-recheck-final.jsonl", 0, None, "recheck 20 Oct 03:23-03:26Z"),
    ("independent-check-final.jsonl", 0, None, "independent 20 Oct 03:26-03:39Z"),
]
if "nosample" in VARIANT: BATCHES = [b for b in BATCHES if b[0] != "optin-sample-50k-3355k.jsonl"]
if "noretry" in VARIANT: BATCHES = [b for b in BATCHES if b[0] != "optin-retry.jsonl"]
rows_read = collections.Counter(); valid_by_batch = collections.Counter(); oo_by_batch = collections.Counter()
recheck_fids = set(); indep_fids = set(); zc_fids = set(); zc_after = collections.Counter()
for bi, (f, lo, hi, label) in enumerate(BATCHES, start=1):
    with open(S + f, "rb") as fh:
        data = fh.read(ZC_OFF) if f == "optin-scan-zerocast.jsonl" else fh.read()
    for i, raw in enumerate(data.split(b"\n")):
        if not raw.strip(): continue
        if i < lo or (hi is not None and i > hi): continue
        r = json.loads(raw); fid = r["fid"]; h = r.get("http"); s = r.get("optInStatus", r.get("status"))
        rows_read[label] += 1
        if f == "optin-recheck-final.jsonl": recheck_fids.add(fid)
        if f == "independent-check-final.jsonl": indep_fids.add(fid)
        if f == "optin-scan-zerocast.jsonl": zc_fids.add(fid)
        u = r.get("username")
        if u and u.startswith("test-acc"): uname_test[fid] = 1
        if h == 200 and s in CODE:
            c = CODE[s]; status[fid] = c; src[fid] = bi; nvalid[fid] = min(255, nvalid[fid] + 1)
            fc = r.get("followerCount", r.get("followers"))
            cfc[fid] = fc if fc is not None else 0
            valid_by_batch[label] += 1; last_kind[fid] = 1
            if s == "opted_out": ever_oo[fid] = 1; oo_by_batch[label] += 1
            if s == "moderated_out": ever_mo[fid] = 1
        elif h == 404:
            had404[fid] = 1; last_kind[fid] = 2
        else:
            hadErr[fid] = 1
            if last_kind[fid] == 0: last_kind[fid] = 3
OUT["status_input"] = {"batches_in_order": [[b[0], b[1], b[2], b[3], rows_read[b[3]], valid_by_batch[b[3]]] for b in BATCHES],
                       "zerocast_frozen_bytes": ZC_OFF, "zerocast_rows_used": rows_read["zero-cast tail 20 Oct (frozen)"],
                       "opted_out_reads_by_batch": dict(oo_by_batch),
                       "overlap_zerocast_recheck": len(zc_fids & recheck_fids), "overlap_zerocast_independent": len(zc_fids & indep_fids),
                       "overlap_recheck_independent": len(recheck_fids & indep_fids), "recheck_fids": len(recheck_fids), "independent_fids": len(indep_fids)}

# hub table (followers as of the 18 Oct 17:41Z pull; reg times)
hfc = array.array("i", [-1]) * NMAX; reg = {}
REG_ANN_OK = bytearray(NMAX)  # 1 = registered before announcement, 2 = after, 0 = unknown
hub_max = 0; hub_bad = 0
with open(S + "hypersnap-users-all.jsonl", "rb") as fh:
    for raw in fh:
        r = json.loads(raw)
        if r.get("missing") or r.get("error") or "fc" not in r: hub_bad += 1; continue
        x = r["fid"]; hfc[x] = r.get("fc") or 0; hub_max = max(hub_max, x)
        t = r.get("reg")
        if t:
            REG_ANN_OK[x] = 2 if dt.datetime.fromisoformat(t.replace("Z", "+00:00")) > T_ANN else 1
newest_max = 0
for line in open(S + "hub-users-newest-1720-2026-10-19.jsonl"):
    r = json.loads(line); x = r["fid"]; newest_max = max(newest_max, x)
    if r.get("reg") and REG_ANN_OK[x] == 0:
        REG_ANN_OK[x] = 2 if dt.datetime.fromisoformat(r["reg"].replace("Z", "+00:00")) > T_ANN else 1
first_post_ann_fid = min(x for x in range(3_300_000, hub_max + 1) if REG_ANN_OK[x] == 2)
last_pre_ann_fid = max(x for x in range(3_300_000, hub_max + 1) if REG_ANN_OK[x] == 1)
OUT["hub_table"] = {"file": "hypersnap-users-all.jsonl (pulled 18 Oct 13:19-13:41Z; fids 1-3,355,300)", "max_fid": hub_max, "bad_rows": hub_bad,
                    "newest_file": "hub-users-newest-1720-2026-10-19.jsonl (written 19 Oct 16:15Z)", "newest_max_fid": newest_max,
                    "first_fid_registered_after_announcement": first_post_ann_fid, "last_fid_registered_before_announcement": last_pre_ann_fid}

# ---------------- restricted / left ----------------
FIDS = range(1, NMAX)
latest = collections.Counter(ST[status[x] - 1] for x in FIDS if status[x])
mo_latest = [x for x in FIDS if status[x] == CODE["moderated_out"]]
R = [x for x in mo_latest if x not in H]
ever_mo_set = [x for x in FIDS if ever_mo[x]]
reinst = [x for x in ever_mo_set if x in H]
oo_set = [x for x in FIDS if ever_oo[x]]
oo_hold = [x for x in oo_set if x in H]
oo_hold_52839970 = [x for x in oo_set if x in H_52839970]
oo_and_R = [x for x in oo_set if x in set(R)]
Rset = set(R)
leavers_noV = [x for x in oo_set if x not in H and x not in Rset]
oo_latest = collections.Counter(ST[status[x] - 1] for x in oo_set)
mo_ever_latest = collections.Counter(ST[status[x] - 1] for x in ever_mo_set)
def binname(v):
    for lo_, name in ((10000, ">=10k"), (5000, "5k-10k"), (1000, "1k-5k"), (100, "100-1k"), (10, "10-100")):
        if v >= lo_: return name
    return "<10"
OUT["restricted"] = {
    "definition": "latest valid read moderated_out (recheck 20 Oct 03:23-03:26Z and independent sampler 03:26-03:39Z applied last), minus fids holding VOTE at the head block",
    "latest_moderated_out": len(mo_latest), "of_them_hold_vote_at_head": len(mo_latest) - len(R), "R": len(R),
    "R_read_in_recheck": sum(1 for x in R if x in recheck_fids), "R_last_read_by": dict(collections.Counter(BATCHES[src[x] - 1][3] for x in R)),
    "ever_read_moderated_out": len(ever_mo_set), "ever_moderated_out_latest_status": dict(mo_ever_latest),
    "ever_moderated_out_now_hold_vote": len(reinst),
    "R_app_followers_lt10": sum(1 for x in R if cfc[x] < 10), "R_hub_followers_lt10": sum(1 for x in R if hfc[x] < 10),
    "R_by_hub_followers": dict(collections.Counter(binname(hfc[x]) for x in R)),
    "R_username_test_acc": sum(1 for x in R if uname_test[x]),
    "R_by_range": dict(collections.Counter("1-300k" if x <= 300000 else ("3.3M+" if x > 3300000 else "300k-3.3M") for x in R)),
}
OUT["left_historical"] = {
    "definition": "fids ever read opted_out; every such read is before 19 Oct 09:36:36Z (API stopped returning opted_out between 09:36:36Z and 09:43:07Z)",
    "ever_read_opted_out": len(oo_set), "hold_vote_at_head": len(oo_hold), "hold_vote_at_block_52839970": len(oo_hold_52839970),
    "without_vote_at_head": len(oo_set) - len(oo_hold), "latest_status_now": dict(oo_latest),
    "also_in_R": len(oo_and_R), "hub_10k_plus": sum(1 for x in oo_set if hfc[x] >= 10000),
    "hub_10k_plus_without_vote": sum(1 for x in leavers_noV if hfc[x] >= 10000),
}

# ---------------- tiers ----------------
leaver_noV = set(leavers_noV)
tiers = {}
for T in (10000, 5000, 1000, 100):
    pool = [x for x in range(1, hub_max + 1) if hfc[x] >= T]
    c = collections.Counter()
    opted_in_no_token = 0
    for x in pool:
        if x in H: c["signed"] += 1
        elif x in Rset: c["restricted"] += 1
        elif x in leaver_noV: c["left_by_19_Oct"] += 1
        elif status[x]:
            c["no_vote"] += 1
            if status[x] == CODE["opted_in"]: opted_in_no_token += 1
        elif had404[x]: c["http404"] += 1
        else: c["unread_or_error"] += 1
    known = c["signed"] + c["restricted"] + c["left_by_19_Oct"] + c["no_vote"]
    tiers[f">={T}"] = {"pool": len(pool), "known": known, "known_pct": round(100 * known / len(pool), 2), **dict(c),
                       "pct_of_known": {k: round(100 * c[k] / known, 2) for k in ("signed", "left_by_19_Oct", "restricted", "no_vote")},
                       "no_vote_includes_opted_in_without_token": opted_in_no_token,
                       "signed_without_valid_read": sum(1 for x in pool if x in H and not status[x])}
OUT["tiers_hub_followers"] = tiers

# ---------------- exact layer & 404 ----------------
n404 = sum(1 for x in FIDS if not status[x] and had404[x])
n404_noV = sum(1 for x in FIDS if not status[x] and had404[x] and x not in H)
OUT["exact_layer"] = {"fids_with_valid_status": sum(latest.values()), "latest_status": dict(latest),
                      "http404_no_valid_read": n404, "http404_no_valid_read_not_holding": n404_noV,
                      "http404_hub_ge_1k": sum(1 for x in FIDS if not status[x] and had404[x] and hfc[x] >= 1000),
                      "opted_in_latest_without_token": sum(1 for x in FIDS if status[x] == 1 and x not in H),
                      "holders_with_latest_status_not_opted_in": dict(collections.Counter(ST[status[x] - 1] for x in H if status[x] and status[x] != 1)),
                      "holders_without_any_valid_read": sum(1 for x in H if not status[x])}

# ---------------- new accounts among holders ----------------
def post_ann(x):
    if REG_ANN_OK[x] == 2: return True
    if REG_ANN_OK[x] == 1: return False
    return x > newest_max or x > hub_max   # beyond both tables -> registered after 19 Oct ~20Z (fid > last pre-announcement fid)
new_h = [x for x in H if post_ann(x)]
new_h_known = sum(1 for x in new_h if REG_ANN_OK[x] == 2)
new_m = [x for x in M if post_ann(x)]
OUT["new_accounts"] = {"announcement": "2026-10-15T17:47Z", "holders": len(H), "holders_registered_after_announcement": len(new_h),
                       "of_which_reg_time_from_hub": new_h_known, "of_which_fid_beyond_hub_tables": len(new_h) - new_h_known,
                       "pct_of_holders": round(100 * len(new_h) / len(H), 2),
                       "distinct_minted_fids_registered_after_announcement": len(new_m), "distinct_minted": len(M),
                       "pct_of_minted": round(100 * len(new_m) / len(M), 2),
                       "holders_fid_gt_3355300": sum(1 for x in H if x > 3355300), "holders_fid_gt_newest_table": sum(1 for x in H if x > newest_max),
                       "unknown_reg_but_le_tables": sum(1 for x in H if REG_ANN_OK[x] == 0 and x <= max(newest_max, hub_max))}
# batch of one registrant (D / V12: 758 fids registered by EOA 0x6BBd...1633 through 19 Oct ~22:45Z on OP)
dj = json.load(open(S + "verify-indep/taskD/d3b_registrant.json")); batch = set(dj["eoa_fids"])
pat = json.load(open(S + "verify-indep/taskD/d3_pattern.json"))
OUT["registrant_batch"] = {"batch_fids_known": len(batch), "fid_range": [min(batch), max(batch)], "hold_vote_at_head": len(batch & H),
                           "hold_vote_at_52823117_per_D": 341, "minted_ever": len(batch & M),
                           "share_of_holders_pct": round(100 * len(batch & H) / len(H), 2),
                           "share_of_new_account_holders_pct": round(100 * len(batch & H) / len(new_h), 1),
                           "holders_with_fid_gt_batch_max_not_attributable": sum(1 for x in H if x > max(batch))}

# ---------------- non-voter split ----------------
info = json.load(open(FZ + "info-haatz.quilibrium.com.json")); HUBN = info["dbStats"]["numFidRegistrations"]
NFID = int(json.loads(open(FZ + "idcounter.json").read().split("}")[0] + "}")["result"], 16)
SQUAT = 163299; BAO = (1647091, 1593579, 1700603)
nonv = NFID - len(H)
OUT["fids"] = {"fids_issued_idCounter": NFID, "idCounter_source": "IdRegistry 0x00000000Fc6c5F01Fc30151999387Bb99A9f489b idCounter() on OP mainnet, block 158,436,270, read 2026-10-20T04:41:57Z (two public RPCs agree)", "hub_numFidRegistrations": HUBN, "hub_source": "haatz /v1/info and snap.farcaster.xyz:3381 /v1/info, both 3,356,088 at 2026-10-20T04:38Z",
               "holders": len(H), "holders_pct": round(100 * len(H) / NFID, 3), "no_vote": nonv, "no_vote_pct": round(100 * nonv / NFID, 3),
               "holders_fid_gt_NFID": sum(1 for x in H if x > NFID)}
OUT["non_voter_split"] = {
    "no_vote_fids": nonv,
    "base_app_only_estimate": {"point": BAO[0], "ci95": [BAO[1], BAO[2]], "pct_of_all_fids_at_C": 49.1,
                               "note": "V12 §5 / C: uniform 3,000 fids 300,001-3,300,000 + 400 in 3.3M+, hubs snap+haatz, 19 Oct; 0 of them voted (census of all 1,841 minters >=1.5M)"},
    "squat_2023": SQUAT, "squat_holders": sum(1 for x in H if 24277 <= x <= 187684),
    "others": [nonv - BAO[0] - SQUAT, nonv - BAO[2] - SQUAT, nonv - BAO[1] - SQUAT],
    "others_pct_of_fids": [round(100 * (nonv - BAO[0] - SQUAT) / NFID, 1), round(100 * (nonv - BAO[2] - SQUAT) / NFID, 1), round(100 * (nonv - BAO[1] - SQUAT) / NFID, 1)],
    "base_app_only_pct_of_no_vote": round(100 * BAO[0] / nonv, 1), "squat_pct_of_no_vote": round(100 * SQUAT / nonv, 1),
}
# ---------------- turnout among farcaster.xyz-key holders above fid 300k ----------------
CMAX = 3355706; D9152 = (1114133, 1062595, 1165671)
num_h = sum(1 for x in H if 300000 < x <= CMAX); num_m = sum(1 for x in M if 300000 < x <= CMAX)
num_h_all = sum(1 for x in H if x > 300000)
OUT["turnout_9152_gt_300k"] = {
    "denominator_estimate": {"point": D9152[0], "ci95": [D9152[1], D9152[2]], "frame": "fids 300,001-3,355,706 (C, 19 Oct)"},
    "numerator_holders_in_frame": num_h, "numerator_minted_in_frame": num_m, "holders_gt_300k_all": num_h_all,
    "turnout_holders_pct": [round(100 * num_h / D9152[0], 2), round(100 * num_h / D9152[2], 2), round(100 * num_h / D9152[1], 2)],
    "turnout_minted_pct": [round(100 * num_m / D9152[0], 2), round(100 * num_m / D9152[2], 2), round(100 * num_m / D9152[1], 2)],
    "C_value_at_52818299": "1.63 % [1.56-1.71] (18,216 minted fids / 1,114,133)",
    "assumption": "every minter holds a farcaster.xyz key (census: 1,841 of 1,841 minters >=1.5M; sample 400 of 400 in 300k-1.5M)"}
# ---------------- shares of votes ----------------
OUT["vote_share"] = {"holders_over_holders_plus_leavers_without_vote": round(100 * len(H) / (len(H) + len(oo_set) - len(oo_hold)), 2)}
# ---- extra checks ----
def state_at(block):
    st = {}; mints = burns = 0
    for b, li, kind, tid, fr, to in evs:
        if b > block: break
        st[tid] = kind != "burn"; mints += kind == "mint"; burns += kind == "burn"
    return mints, burns, sum(st.values())
X = {}
for blk in (52818299, 52823117, 52839128, 52839970):
    X[str(blk)] = dict(zip(("mints", "burns", "holders"), state_at(blk)), time=btime(blk))
# new accounts by first-mint order
order = []; seen = set()
for b, li, kind, tid, fr, to in evs:
    if kind == "mint" and tid not in seen: seen.add(tid); order.append(tid)
mint_events = [tid for b, li, kind, tid, fr, to in evs if kind == "mint"]
first17817 = mint_events[:17817]; rest = mint_events[17817:]
X["new_by_mint_order"] = {"first_17817_mint_events_new": sum(1 for t in first17817 if post_ann(t)), "first_17817": len(first17817),
                          "after_17817_mint_events_new": sum(1 for t in rest if post_ann(t)), "after_17817": len(rest),
                          "mint_events_new_total": sum(1 for t in mint_events if post_ann(t)), "mint_events": len(mint_events)}
# non-voter 'others' sub-split (estimate)
h_le300 = sum(1 for x in H if x <= 300000); h_sq = sum(1 for x in H if 24277 <= x <= 187684)
X["others_subsplit"] = {"fids_le_300k_not_squat": 300000 - SQUAT, "holders_le_300k": h_le300,
                        "nonvoters_le_300k_not_squat": 300000 - SQUAT - h_le300,
                        "nonvoters_gt_300k_with_9152_key_est": [D9152[0] - num_h, D9152[1] - num_h, D9152[2] - num_h],
                        "fids_gt_300k": NFID - 300000,
                        "gt_300k_neither_base_only_nor_9152_est": NFID - 300000 - BAO[0] - D9152[0]}
OUT["checks_at_earlier_blocks"] = {k: v for k, v in X.items() if k[0].isdigit()}
OUT["new_accounts"]["by_mint_order"] = X["new_by_mint_order"]
OUT["non_voter_split"]["others_subsplit_estimate"] = X["others_subsplit"]
# ---- coverage (stderr) ----
import glob as _g
pf = bytearray(NMAX); chunks = 0
for done in _g.glob(S + "prefilter/fids-with-casts-*.txt.done"):
    d = json.load(open(done)); chunks += 1
    for x in range(d["lo"], d["hi"] + 1): pf[x] = 1
    for tok in open(done[:-5]).read().split(): pf[int(tok)] = 2
cov = collections.Counter()
for x in range(1, NFID + 1):
    rng = "1-300k" if x <= 300000 else ("300k-3.3M" if x <= 3300000 else ("3.3M-3,355,300" if x <= 3355300 else ">3,355,300"))
    layer = {0: "nopf", 1: "zero", 2: "casts"}[pf[x]] if rng == "300k-3.3M" else "all"
    st_ = "valid" if status[x] else ("404" if had404[x] else ("err" if hadErr[x] else "unread"))
    cov[f"{rng}|{layer}|{st_}"] += 1
OUT["coverage"] = {"prefilter_chunks": chunks, "by_range_layer_state": dict(sorted(cov.items())),
  "R_in_zero_cast_layer": sum(1 for x in R if pf[x] == 1), "valid_reads_zero_cast_layer": sum(1 for x in range(300001, 3300001) if pf[x] == 1 and status[x]),
  "moderated_out_ever_in_zero_cast_layer": sum(1 for x in range(300001, 3300001) if pf[x] == 1 and ever_mo[x]),
  "R_in_fid_gt_3355300": sum(1 for x in R if x > 3355300)}
print(json.dumps(OUT, indent=1))
