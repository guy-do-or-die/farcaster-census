# Farcaster vote, counted

An independent count of the Farcaster vote that Network School (NS) ran after agreeing to buy Farcaster: on 15 Oct 2026 it asked farcaster.xyz users to vote to stay under its new rules or to leave. Public data only, read-only scripts, no per-account lists.

A stay vote mints a VOTE token on Base, so stays can be counted in full. A leave vote writes nothing on-chain that I can find; it could only be read through the app's API, and since 19 Oct the API no longer returns it. This repo counts what can be counted from outside and records where the count stops.

The page: https://census.untitl.eth.limo (IPFS folder `bafybeid5cbecsuqoiv55omx7a5t57qijb3355xrkiausd7j35vtunmcwry` with the page and its preview image, the ENS contenthash of census.untitl.eth); source [`site/index.html`](site/index.html). After that upload the source got small corrections that the live page does not have yet: 34 → 37 leavers who signed before the change, 100 of 101 (not 103 of 103) posters with identical messages on both hubs, 743,532 → 743,533 reads, 14–20 Oct (not 15–20) for the mints, "at least 57%". They are listed in `data/page-figures.json`.

## The numbers (votes on-chain 20 Oct 2026, Base block 52,840,567 = 04:28 UTC; statuses read 17–20 Oct)

| | Value | How |
|---|---|---|
| Signed (holds the VOTE token) | 24,578 | Every Transfer event of the VOTE contract on Base, pulled twice through two providers |
| Not signed | 99.3% of 3,356,242 fids | Fids, not people; includes the restricted and the leavers without a token |
| … only ever had Base App keys | ~1.65M (49%) | Estimate from two hub samples; the vote ran only in farcaster.xyz and needed its key |
| … keyless 2023 bulk registration | 163,299 (5%) | One operator, 13 Oct 2023; no keys |
| Restricted (`moderated_out`) | 263 | Status read for every fid that has cast, bar 1,125 failed reads and the 942 newest; re-read 20 Oct 03:23–03:39 UTC |
| Left (`opted_out`), by 19 Oct | 481 | Read 17 Oct – 19 Oct 09:36 UTC; a minimum; 57 of them signed later |
| Stay share of the votes seen | ≤98.3% | Estimate and ceiling: 24,578 stays now against 424 leaves read by 19 Oct with no VOTE |
| Turnout among fids above 300k with a farcaster.xyz key | ~1.7% | Estimate, 95% interval 1.62–1.77% |

On 19 Oct between 09:36 and 09:44 UTC the farcaster.xyz API stopped returning leave votes. Former leavers now read like non-voters to logged-out reads, and 5 of 5 did in my own logged-in session (20 Oct); a leaver's own view is untested. Since then nobody outside can count leave votes.

Full tables, dates and caveats: [`data/final-numbers.json`](data/final-numbers.json), [`data/page-figures.json`](data/page-figures.json) for every other figure on the page, [`data/vote-hourly.json`](data/vote-hourly.json) for the hour-by-hour signing curve, and [`METHOD.md`](METHOD.md).

## Reproduce

Python 3, standard library only. Set `CENSUS_CONTACT` (goes into the User-Agent) and `CENSUS_DATA` (a folder for the raw files).

1. `scripts/vote_transfers.py OUT_PREFIX [from_block]`: every mint and burn of the VOTE token (`0x4ecfed276c566aeb49da1f3a888e8dbb7263028d`, Base; tokenId = fid).
2. `scripts/hub_prefilter.py START END OUT_PREFIX`: which fids have at least one cast (public hub node).
3. `scripts/optin_scan.py START END OUT.jsonl` or `scripts/optin_scan.py FIDS.txt OUT.jsonl`: `GET client.farcaster.xyz/v2/user?fid=N` → `viewerContext.optInStatus`, no login, ~7 requests/s, backs off on 429.
4. `scripts/hypersnap_users_pull.py`: profile table for every fid from the Hypersnap public node (followers, names, registration time).
5. `scripts/hypersnap_activity.py`: do restricted and departed accounts still post, compared across two hub nodes.
6. `scripts/independent_check.py FIDS.txt OUT.jsonl`: a separate, single-threaded status reader used to cross-check a random 2,000-fid sample.
7. `scripts/pull.py`, `scripts/freeze.py`, `scripts/build.py`: the final freeze; dedup events, latest valid read wins, aggregates only.
8. `scripts/hourly.py EVENTS.jsonl OUT.json`: the hourly signing curve and its checkpoints.

`data/sample-fids.txt` is the random sample used for the parts that were estimated.

Not published: the raw per-fid status reads and the Transfer log that `freeze.py` expects under `CENSUS_DATA` (`full-events.jsonl`, `full-meta.json`, `idcounter.json`, the hub `/v1/info` snapshots and the zero-cast offset). Re-running steps 1–6 recreates them. Status strings in the JSON that cite V1–V13, B, C or D refer to my private working notes.

## Rules followed

- One scanner at a time against the client API: 8 threads, ~7 requests/s in total; after 10 consecutive 429/5xx answers it pauses 60 s; no IP rotation.
- `moderated_out` gives no reason: spam removals and conduct restrictions share the flag.
- `pending` is the default for every account, including dormant ones and the ones that never had the key to vote.
- No lists of restricted or departed accounts are published, and none should be built from this.

## Disclosure

guy-do-or-die on Farcaster (fid 321301). I voted stay on 16 Oct; Network School accepted me on 17 Oct, I haven't booked yet; I'm a member of the Hypersnap fork's Telegram. The analysis was AI-assisted. Every headline number was checked by a second method or pass of my own; there has been no outside re-check yet.

## Credits

@suji (Firefly) pointed out on 17 Oct that fids 1.5M–3M are likely Base App accounts. @0xael.eth (Allthing) and @duckfacts.eth showed the per-account status endpoint publicly before this count.

## License

Code: MIT. Text and aggregated data: CC BY 4.0.
