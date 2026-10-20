# Method

Numbers frozen 20 Oct 2026: votes at Base block 52,840,567 (04:28:01 UTC), statuses read 17 Oct 03:00 – 20 Oct 04:39 UTC, fid count read 04:41:57 UTC. Aggregates are in [`data/final-numbers.json`](data/final-numbers.json); every other figure on the page is in [`data/page-figures.json`](data/page-figures.json).

## Sources

| What | Where | Login |
|---|---|---|
| Vote status per fid | `GET https://client.farcaster.xyz/v2/user?fid=N` → `result.user.viewerContext.optInStatus` (`opted_in`, `opted_out`, `moderated_out`, `pending`) | none |
| Votes | Transfer events of the VOTE token `0x4ecfed276c566aeb49da1f3a888e8dbb7263028d` on Base; tokenId = fid; only "stay" is minted | none |
| Fid count | `IdRegistry.idCounter()` on OP Mainnet `0x00000000Fc6c5F01Fc30151999387Bb99A9f489b` | none |
| Profiles, casts, keys | Public hub nodes `https://haatz.quilibrium.com` (Hypersnap, read-only) and `https://snap.farcaster.xyz:3381` (a mainnet validator labelled Merkle in the Snapchain repo) | none |

## What was read

- **Every fid 1–300,000**, every fid **3,300,001–3,355,300**, every fid with **1,000+ hub followers**, and **every fid 300,001–3,300,000 that has at least one cast**: 1.53M fids with a valid status.
- Fids with no casts at all in 300,001–3,300,000 (~1.81M) were sampled, not read. None of the 263 restricted accounts is among the 300k–3.3M fids with zero casts, and none of the 42,849 zero-cast fids that were read was ever restricted.
- 1,125 fids with casts never returned a valid status (errors); the 942 newest fids were not read. 5,437 fids returned only 404s and are counted apart; the API gives no reason for a 404 or a restriction.
- Every restricted, departed and large-404 fid (1,131) was re-read on 20 Oct 03:23–03:26 UTC; a separate single-threaded reader then checked a random 2,000 fids (03:26–03:39 UTC). The latest valid read wins.

## How the headline numbers are built

- **Signed** = current VOTE holders: 24,596 mints − 18 burns = 24,578 (logs pulled twice, two providers, identical).
- **Restricted** = latest read `moderated_out` and no VOTE now: 263. 276 were ever read restricted; 10 have since signed, 3 now read `pending`.
- **Left** = ever read `opted_out` before 19 Oct 09:36 UTC: 481, a minimum. 57 of them hold VOTE now.
- **Leave votes after 19 Oct.** Between 09:36 and 09:44 UTC on 19 Oct the API stopped returning `opted_out`: 0 in 417,518 later reads. Before the change the 300k–1.55M scan saw 299 in 743,532 reads, about one per 45 `opted_in` answers. Later reads were mostly of quieter fids and returned 1,137 `opted_in` answers, so ~25–29 leave answers were due; about 6 even at the most cautious rate. The client's opt-in endpoints and the vote page text are the same as on 16 Oct, none of the endpoints resets or cancels a vote, and after a stay vote the app shows no leave button; no announcement was found. So nobody outside can count leave votes now.
- **Not signed** = fids − holders = 3,331,664 (99.3% of 3,356,242). Fids are not people.
- **Base-App-only** ≈1,647,091 [1,593,579–1,700,603]: fids whose every key came from Base App (app fid 309857), from two hub samples. None of them signed; every signer above fid 1.5M holds a farcaster.xyz key (app fid 9152).
- **2023 bulk registration**: 163,299 fids within 24,278–187,684 (108 organic fids sit inside the span), one operator, 13 Oct 2023, a clone contract per fid, no storage, recovery 0x0. They cannot add a key (strong inference from bytecode, not simulated).
- **Turnout** among fids above 300k that ever had a farcaster.xyz key: 18,858 / ~1,114,133 = 1.69% [1.62–1.77].
- **Stay share of the votes seen**: 24,578 / (24,578 + 424) = 98.3%, a ceiling: leave votes I couldn't see would only push it lower.
- **Tiers** use hub follower counts (≈2.9× the app's count), status known for 98.9–99.5%.

## Other checks

- **Who can burn a token.** The VOTE contract's source is not published. `revoke()` reverts with `InvalidAuthorizerSignature` when called from the holder, the owner or a random address; the one real revoke checked was signed by the operator's authorizer. 5 function selectors are unresolved.
- **Hidden in the app.** farcaster.xyz, logged out, does not serve casts that non-signers made after 15 Oct ~17:00 UTC, restricted or not, in every case checked: 46 of 46 active non-signers among 101 bots and agents (19 Oct) and 15 former leavers (20 Oct). Logged-in feeds were not tested.
- **Kept on the network.** Some restricted accounts still post through other clients: of the 194 restricted on 18 Oct, 27 had cast after the announcement and at least 16 cast between two restricted reads; the casts carry the same hashes on both hub nodes. After the announcement, 4 restricted fids made 52 casts with the farcaster.xyz key, all while the fid held VOTE.
- **New accounts.** Fids registered after the announcement hold 675 of 24,578 VOTE tokens (2.7%); 343 come from one address's batch of 758 fids.
- **Second pass.** A separate re-implementation of my own recomputed the headline figures from the raw files; where it disagreed, the published number is the recomputed one.

## Limits

- `moderated_out` has no reason attached; spam removals and conduct restrictions share it.
- Statuses are snapshots; appeals and new restrictions move them.
- The client API can change without notice (it did on 19 Oct).
- Estimates come with 95% Wilson intervals; anything marked ~ is an estimate.
- Per-account reads are not published.
