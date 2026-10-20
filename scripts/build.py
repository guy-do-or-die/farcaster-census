#!/usr/bin/env python3
"""Compose data/final-numbers.json from scripts/freeze-out.json, the output of freeze.py (aggregates only, every figure dated).
freeze.py needs the raw Transfer log and status reads, which are not published."""
import json, os
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.dirname(H)
o = json.load(open(H + "/freeze-out.json"))
c = o["chain"]; R = o["restricted"]; L = o["left_historical"]; T = o["tiers_hub_followers"]; E = o["exact_layer"]
N = o["new_accounts"]; B = o["registrant_batch"]; F = o["fids"]; NV = o["non_voter_split"]; TU = o["turnout_9152_gt_300k"]; CV = o["coverage"]
CH = f"Base block {c['head_block']:,} = {c['head_time']}"
ST_READ = "statuses read 17 Oct 03:00Z - 20 Oct 03:39Z (restricted/left/404 re-read 20 Oct 03:23-03:26Z, independent sampler 03:26-03:39Z)"
HUB = "hub follower counts from the hub table pulled 18 Oct 13:19-13:41Z (hypersnap-users-all.jsonl)"
def pct(a, b, d=1): return round(100 * a / b, d)
def pk(t, k, d=1):  # share of known from raw counts
    v = T[t]; return f"{100 * v[k] / v['known']:.{d}f}"
tiers = {}
for k, v in T.items():
    tiers[k.replace(">=", "hub_ge_")] = {
        "pool": v["pool"], "known": v["known"], "known_pct": v["known_pct"],
        "signed": v["signed"], "left_by_19_Oct": v["left_by_19_Oct"], "restricted": v["restricted"], "no_vote": v["no_vote"],
        "http404": v.get("http404", 0), "unread_or_error": v.get("unread_or_error", 0),
        "pct_of_known": v["pct_of_known"], "no_vote_includes_opted_in_without_token": v["no_vote_includes_opted_in_without_token"],
        "as_of": f"signed: {CH}; restricted: 20 Oct 03:23-03:39Z; left: reads 17 Oct - 19 Oct 09:36Z, without VOTE at the same block; followers: hub table 18 Oct 13:41Z",
        "status": "VERIFIED" if k != ">=100" else "VERIFIED (label 'status known for %.1f%%')" % (100 * v["known"] / v["pool"])}
out = {
 "frozen_at": {"chain_head": "2026-10-20T04:28:01Z (Base block 52,840,567)", "status_files": "2026-10-20T04:39Z (zero-cast tail cut at 23,562 rows)", "fid_count": "2026-10-20T04:41:57Z", "built": "2026-10-20T04:50Z"},
 "author": "guy-do-or-die (Farcaster fid 321301)",
 "privacy": "aggregates only; no fids or names of restricted or left accounts in this file",
 "legend": {"VERIFIED": "two separate methods or passes of mine agree; true on the stated date; no outside re-check",
            "VERIFIED-ONE-METHOD": "one method or one pass", "ESTIMATE": "estimate with interval"},
 "frames": {"chain": CH, "statuses": ST_READ, "followers": HUB,
            "opted_out_change": "farcaster.xyz API stopped returning opted_out on 19 Oct between 09:36:36Z and 09:43:07Z (outer 09:36:25-09:43:25Z); post text: 'between 09:36 and 09:44 UTC' (V13)",
            "announcement": "2026-10-15T17:47Z"},
 "chain": {
   "as_of": CH, "head_hash": c["head_hash"], "contract": c["contract"],
   "mints": c["mints"], "burns": c["burns"], "transfers": c["transfers"],
   "distinct_fids_minted": c["distinct_fids_minted"], "fids_minted_twice": c["fids_minted_twice"],
   "holders_signed": c["holders"], "last_event": c["last_event_time"],
   "method": "union of 7 local Transfer files deduped by (tx, logIndex) = 24,614 events, identical to an independent re-pull 52,600,000-head (1,000-block windows) from two providers (thirdweb, tenderly), 0 differences; time = 2.0 s/block from block 52,606,050 = 2026-10-14T18:10:47Z (matches the head block's own timestamp)",
   "status": "VERIFIED",
   "draft_correction": {"draft_03_40Z": {"block": 52839128, "mints": 24519, "holders": 24501},
                        "correct_at_same_block": o["checks_at_earlier_blocks"]["52839128"],
                        "cause": "files 3 (head 52,818,305) and 4 (from 52,818,852) leave a gap; 30 mints in blocks 52,818,313-52,818,840 were missing from files 1-4 (present in the D pull)"},
   "earlier_blocks": o["checks_at_earlier_blocks"]},
 "fids": {
   "fids_issued": F["fids_issued_idCounter"], "as_of": "IdRegistry.idCounter() on OP mainnet, block 158,436,270, read 2026-10-20T04:41:57Z (two RPCs agree)",
   "hub_numFidRegistrations": F["hub_numFidRegistrations"], "hub_as_of": "haatz and snap.farcaster.xyz:3381 /v1/info, 2026-10-20T04:38Z (both)",
   "signed_pct_of_fids": round(F["holders_pct"], 2), "no_vote": F["no_vote"], "no_vote_pct": round(F["no_vote_pct"], 1),
   "status": "VERIFIED", "wording": "99.3% of 3.36M fids (Farcaster IDs) have no vote - never 'accounts'"},
 "restricted": {
   "R": R["R"], "as_of": "latest reads 20 Oct 03:23-03:39Z; VOTE checked at " + CH,
   "definition": R["definition"], "latest_moderated_out": R["latest_moderated_out"], "of_them_hold_vote": R["of_them_hold_vote_at_head"],
   "ever_read_moderated_out": R["ever_read_moderated_out"], "ever_restricted_now_signed": R["ever_moderated_out_now_hold_vote"],
   "ever_restricted_now_pending_not_in_R": R["ever_moderated_out_latest_status"].get("pending", 0),
   "app_followers_lt10": R["R_app_followers_lt10"], "hub_followers_lt10": R["R_hub_followers_lt10"],
   "hub_ge_10k": R["R_by_hub_followers"][">=10k"], "by_hub_followers": R["R_by_hub_followers"],
   "operator_test_accounts_by_name": R["R_username_test_acc"],
   "coverage": {"read_all": "fids 1-300,000 and 3,300,001-3,355,300; fids with casts in 300,001-3,300,000 (hub prefilter 18-19 Oct)",
                "with_casts_error_only_unread": CV["by_range_layer_state"]["300k-3.3M|casts|err"],
                "zero_cast_unread": CV["by_range_layer_state"]["300k-3.3M|zero|unread"],
                "zero_cast_read": CV["valid_reads_zero_cast_layer"], "zero_cast_ever_restricted": CV["moderated_out_ever_in_zero_cast_layer"],
                "fids_gt_3355300_unread": CV["by_range_layer_state"][">3,355,300|all|unread"]},
   "status": "VERIFIED (two computations over the same reads; one API source; recheck and independent sampler agree on 29 of 29 shared fids)",
   "wording": "restricted (moderated_out in farcaster.xyz), not 'banned'; read for every account that has cast except 1,125 error-only fids; 942 fids above 3,355,300 not read"},
 "left_historical": {
   "ever_read_opted_out": L["ever_read_opted_out"], "as_of": "reads 17 Oct 03:00Z - 19 Oct 09:36Z; VOTE checked at " + CH,
   "now_signed": L["hold_vote_at_head"], "without_vote": L["without_vote_at_head"], "read_now": L["latest_status_now"],
   "hub_ge_10k_ever": L["hub_10k_plus"], "hub_ge_10k_without_vote": L["hub_10k_plus_without_vote"],
   "network_total_estimate": {"range": [490, 510], "status": "ESTIMATE (V13 §4.1: fids with casts above ~1.425M were read only after the change)"},
   "status": "VERIFIED (V13 BEHAVIOUR re-read + own union of all scan files; on-chain)",
   "wording": "Left 481 by 19 Oct (read as 'voted to leave' 17-19 Oct); 57 of them have since signed. No current leave count exists: since 19 Oct 09:36-09:44Z the API shows former leavers as 'pending'."},
 "tiers_hub_followers": tiers,
 "http404": {"fids_404_no_valid_read": E["http404_no_valid_read"], "of_them_hub_ge_1k": E["http404_hub_ge_1k"],
             "of_them_hold_vote": E["http404_no_valid_read"] - E["http404_no_valid_read_not_holding"],
             "as_of": "reads to 20 Oct 04:39Z (zero-cast tail frozen at 23,562 rows)", "status": "VERIFIED-ONE-METHOD"},
 "exact_layer": {"fids_with_valid_status": E["fids_with_valid_status"], "latest_status": E["latest_status"],
                 "opted_in_without_token": E["opted_in_latest_without_token"], "holders_without_any_valid_read": E["holders_without_any_valid_read"],
                 "valid_reads_since_change_with_opted_out": {"valid_reads": 391104 + 250 + 23407 + 757 + 2000, "opted_out": 0,
                     "as_of": "19 Oct 09:36:36Z - 20 Oct 04:39Z (stage 1 rest 53,406; stage 2 337,698; retry 250; zero-cast 23,407; recheck 757; sampler 2,000)"},
                 "as_of": "20 Oct 04:39Z"},
 "non_voters": {
   "no_vote_fids": NV["no_vote_fids"], "as_of": "fids at OP block 158,436,270 (04:41:57Z) minus holders at " + CH,
   "base_app_only": {"point": 1647091, "ci95": [1593579, 1700603], "pct_of_all_fids": 49.1, "pct_of_no_vote": NV["base_app_only_pct_of_no_vote"],
                     "as_of": "C sample read 19 Oct (V12 §5, c_results.json 19 Oct 19:27Z); structural, not re-run",
                     "voted": 0, "status": "VERIFIED (V11 + C, two methods) / interval = ESTIMATE",
                     "wording": "about half of all fids are Base App accounts that never had a farcaster.xyz key; none of them voted. Do not write 'could not vote'."},
   "bulk_registration_2023": {"fids": 163299, "pct_of_all_fids": round(100 * 163299 / F["fids_issued_idCounter"], 1), "as_of": "V9 + D (19 Oct)", "status": "VERIFIED",
                  "wording": "163,299 (~163k) fids from one operator's keyless registration of 13 Oct 2023 (fid 24,277 moved out in 2023; not '163,300')"},
   "others": {"point": NV["others"][0], "range": [NV["others"][1], NV["others"][2]], "pct_of_all_fids": NV["others_pct_of_fids"],
              "status": "ESTIMATE (arithmetic; inherits the Base App interval)",
              "subsplit_estimate": {
                 "non_signing_fids_gt_300k_with_farcaster_xyz_key": NV["others_subsplit_estimate"]["nonvoters_gt_300k_with_9152_key_est"],
                 "non_signing_fids_le_300k_outside_bulk_registration_exact": NV["others_subsplit_estimate"]["nonvoters_le_300k_not_squat"],
                 "fids_gt_300k_neither_base_only_nor_farcaster_xyz_key": NV["others_subsplit_estimate"]["gt_300k_neither_base_only_nor_9152_est"],
                 "note": "C frame ends at fid 3,355,706; ~500-fid frame mismatch absorbed in the last bucket"}}},
 "turnout_farcaster_xyz_key_gt_300k": {
   "pct": TU["turnout_holders_pct"][0], "ci": [TU["turnout_holders_pct"][1], TU["turnout_holders_pct"][2]],
   "numerator_holders": TU["numerator_holders_in_frame"], "denominator": {"point": 1114133, "ci95": [1062595, 1165671], "as_of": "C, 19 Oct"},
   "as_of": "numerator at " + CH + "; denominator C 19 Oct", "previous": TU["C_value_at_52818299"] + " at Base block 52,818,299 = 19 Oct 16:05:45Z",
   "status": "ESTIMATE", "assumption": TU["assumption"],
   "wording": "of ~1.1M fids above 300k with a farcaster.xyz key, ~1.7% have signed (20 Oct 04:28Z). Only above fid 300k."},
 "new_accounts": {
   "holders_registered_after_announcement": N["holders_registered_after_announcement"], "holders": N["holders"], "pct": round(100 * N["holders_registered_after_announcement"] / N["holders"], 1),
   "reg_time_from_hub": N["of_which_reg_time_from_hub"], "fid_beyond_hub_tables": N["of_which_fid_beyond_hub_tables"],
   "first_fid_after_announcement": o["hub_table"]["first_fid_registered_after_announcement"],
   "by_mint_order": {"first_17817_mints": [N["by_mint_order"]["first_17817_mint_events_new"], 17817, round(100 * N["by_mint_order"]["first_17817_mint_events_new"] / 17817, 2)],
                     "after_17817": [N["by_mint_order"]["after_17817_mint_events_new"], N["by_mint_order"]["after_17817"], round(100 * N["by_mint_order"]["after_17817_mint_events_new"] / N["by_mint_order"]["after_17817"], 2)],
                     "mint_17817_time": "2026-10-17T15:38:13Z"},
   "as_of": CH + "; registration times from hub tables 18 Oct 13:41Z and 19 Oct 16:15Z (fids above 3,355,559 counted as new)",
   "status": "VERIFIED (method reproduces D: 657 of 24,091 and 484 of 6,274 at block 52,823,117)"},
 "registrant_batch": {
   "registrant": "one EOA 0x6BBd...1633 (V10/V12 D)", "fids_registered_known": B["batch_fids_known"], "as_of_list": "D, OP to block 158,418,397 (19 Oct ~18:50Z)",
   "hold_vote": B["hold_vote_at_head"], "hold_vote_as_of": CH, "hold_vote_19_Oct_18_46Z": 341,
   "share_of_holders_pct": B["share_of_holders_pct"], "share_of_new_account_holders_pct": B["share_of_new_account_holders_pct"],
   "pattern_named_in_batch": 326, "holders_above_list_max_unattributed": B["holders_with_fid_gt_batch_max_not_attributable"],
   "status": "VERIFIED-ONE-METHOD (registrant list from one pass; holders recomputed); a floor: the EOA kept registering",
   "wording": "343 of the votes from accounts created after the announcement come from one registrant's batch (758 fids); farm or test harness cannot be told from outside"},
 "vote_share": {"signed_over_signed_plus_left_without_vote_pct": o["vote_share"]["holders_over_holders_plus_leavers_without_vote"],
                "as_of": CH + "; left = 424 read by 19 Oct (floor)", "status": "ESTIMATE", "wording": "'94.4%' is a share of votes (I get ~98%), not of accounts"},
}
P = {
 "SIG": f"{c['holders']:,} (on-chain, 20 Oct 04:28Z)", "MINTS": f"{c['mints']:,}", "BURNS": str(c["burns"]),
 "LEFT": "481 by 19 Oct", "LEFTALL": "481", "REJ": "57",
 "R": str(R["R"]), "RA": str(R["R_app_followers_lt10"]), "T10RN": str(R["R_by_hub_followers"][">=10k"]), "LEFT10": str(T[">=10000"]["left_by_19_Oct"]),
 "REINST": str(R["ever_moderated_out_now_hold_vote"]),
 "NV": "99.3", "T10": f"10k+ (2,739): signed {pk('>=10000','signed')}%, left {pk('>=10000','left_by_19_Oct')}% ({T['>=10000']['left_by_19_Oct']}), restricted {pk('>=10000','restricted')}% ({T['>=10000']['restricted']}), no vote {pk('>=10000','no_vote')}%",
 "T1": f"1k+ (81,168): signed {pk('>=1000','signed')}%, left {pk('>=1000','left_by_19_Oct',2)}%, restricted {pk('>=1000','restricted',2)}% ({T['>=1000']['restricted']}), no vote {pk('>=1000','no_vote')}%",
 "T1N": pk(">=1000", "no_vote"), "T1S": pk(">=1000", "signed"),
 "NEWN": str(N["holders_registered_after_announcement"]), "NEWALL": "2.7", "NEWSPLIT": "1% of the first 17.8k votes, 7% after",
 "BATCH": str(B["hold_vote_at_head"]), "N404": f"{E['http404_no_valid_read']:,}", "N404_1K": str(E["http404_hub_ge_1k"]),
 "TURNOUT": "~1.7% of ~1.1M fids above 300k with a farcaster.xyz key", "BASEAPP": "half (~1.65M) never had a farcaster.xyz key",
 "SQUAT": "163k keyless 2023 bulk registration", "KNOWN10K": f"{100 * T['>=10000']['known'] / T['>=10000']['pool']:.1f}", "KNOWN1K": f"{100 * T['>=1000']['known'] / T['>=1000']['pool']:.1f}",
 "KNOWN100": f"{100 * T['>=100']['known'] / T['>=100']['pool']:.1f}",
 "DATEFRAME": "statuses read 17-20 Oct; votes on-chain 20 Oct 04:28Z",
}
out["placeholders"] = P
out["disclosure"] = "guy-do-or-die (Farcaster fid 321301). I voted stay 16 Oct; Network School accepted me 17 Oct, I haven't booked yet; I'm in the Hypersnap fork's Telegram. Counted from public data (farcaster.xyz client API without login, public hub nodes, Base and OP chains). AI-assisted analysis. No per-account lists."
out["credits"] = {"base_app_observation": "Suji (Firefly founder, fid 966), cast 17 Oct 16:03Z: fids 1.5M-3M likely Base App-only users",
                  "status_endpoint_shown_publicly_earlier": ["Allthing (0xael.eth, docs/VOTE.md, from 18 Oct 01:59Z)", "duckfacts.eth (19 Oct 12:17Z)"]}
out["do_not_claim"] = ["banned (except quoting)", "3.36M accounts (say fids)", "any current leave count; Left only as '481 by 19 Oct'", "NS reset/deleted/hid leave votes; 'silently'", "~10:12 UTC", "could not vote (Base App)", "163,300", "we were the first", "names of restricted accounts or Telegram members"]
out["not_refreshed_carry_with_date"] = [
 {"figure": "restricted posters after 15 Oct: 27 of 194 (V8 set, B rerun 19 Oct); of 255 read restricted 34 cast, of 247 without late mint 29 (B, 19 Oct ~22Z)", "status": "VERIFIED (B) on its date; not recomputed on the final 263"},
 {"figure": "17 cast between two restricted readings (V8 skeptic 18 Oct; B 16-17)", "status": "VERIFIED"},
 {"figure": "never with the NS client's key: all 52 casts of restricted fids with app fid 9152 fall inside windows when the fid held VOTE (B, 19 Oct)", "status": "VERIFIED"},
 {"figure": "81% of 194 restricted cast within 60 days before 15 Oct; 95% of 300 sampled non-voters with 100+ followers idle 60+ days (V8, 18 Oct)", "status": "VERIFIED-ONE-METHOD"},
 {"figure": "57% [53.5-60.4] of 800 sampled signers idle since before July; up to 1/3 mostly template casts (V7, sampled 17 Oct)", "status": "VERIFIED-ONE-METHOD / ESTIMATE"},
 {"figure": "since 15 Oct ~17:00Z farcaster.xyz omits new casts of non-signers in every case checked; 46 of 46 active non-signers checked (V10, 19 Oct)", "status": "VERIFIED-ONE-METHOD"},
 {"figure": "hub followers ~2.9x the app's (median 2.912, n~14.6k)", "status": "VERIFIED"},
 {"figure": "validators: 6 seen, 4 labelled Merkle/Neynar; v18 swaps two ~22 Oct for two with no named operator (18-19 Oct)", "status": "VERIFIED / VERIFIED-ONE-METHOD"},
]
json.dump(out, open(S + "/data/final-numbers.json", "w"), indent=1)
print(json.dumps(P, indent=1))
