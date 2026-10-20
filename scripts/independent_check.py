#!/usr/bin/env python3
"""Independent live read of the public optInStatus for a list of fids (written from scratch, stdlib only).

usage: python3 -I independent_check.py FIDS.txt OUT.jsonl [--no-retry]

For each fid (one integer per line in FIDS.txt; blank lines and '#' comments ignored, duplicates read once)
it sends GET https://client.farcaster.xyz/v2/user?fid=N without auth and writes one JSONL row:
    {"fid": N, "status": result.user.viewerContext.optInStatus, "followers": result.user.followerCount,
     "http": <HTTP code, or -1 for a network/timeout error>, "ts": "<UTC time of the response>"}
plus "err" when something failed. Usernames are never stored or printed.

Politeness and limits:
  * single thread; request starts are spaced >= 0.35 s apart, so never more than 3 requests per second
    (retries count against the same spacing);
  * HTTP 429: sleep 60 s and retry, at most 3 retries per fid (4 attempts); if still 429 the row is written
    with http 429 and the run continues; after 3 fids in a row end on 429 the run stops (exit code 2);
  * HTTP 5xx or a network error: one retry after 5 s;
  * --no-retry disables every retry (exactly one request per fid), for smoke tests.
Resuming: if OUT.jsonl exists, fids that already have a row with http 200 or 404 are skipped and new rows
are appended, so a stopped run can simply be started again.
Progress goes to stderr every 100 fids; a JSON summary goes to stdout at the end.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = "https://client.farcaster.xyz/v2/user?fid={}"
HEADERS = {"User-Agent": "independent-optin-check/1.0 (read-only public status survey)",
           "Accept": "application/json"}
MIN_SPACING = 0.35          # seconds between request starts -> at most 2.86 req/s
RETRIES_429 = 3
SLEEP_429 = 60
RETRIES_TRANSIENT = 1
SLEEP_TRANSIENT = 5
TIMEOUT = 20
ABORT_AFTER_429_FIDS = 3

_last_start = [0.0]


def _pace():
    wait = _last_start[0] + MIN_SPACING - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_start[0] = time.monotonic()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


def request_once(fid):
    """One HTTP request. Returns (http_code, parsed_json_or_None, error_text_or_None, ts)."""
    _pace()
    req = urllib.request.Request(URL.format(fid), headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            code = resp.status
            body = resp.read()
        ts = _now()
        try:
            return code, json.loads(body), None, ts
        except ValueError:
            return code, None, "response is not JSON", ts
    except urllib.error.HTTPError as e:
        return e.code, None, None, _now()
    except Exception as e:  # timeouts, DNS, TLS, connection resets
        return -1, None, f"{type(e).__name__}: {e}"[:120], _now()


def extract(doc):
    """Return (status, followers, err) from a 200 response body."""
    if not isinstance(doc, dict):
        return None, None, "no JSON object"
    user = (doc.get("result") or {}).get("user")
    if not isinstance(user, dict):
        return None, None, "no result.user"
    followers = user.get("followerCount")
    vc = user.get("viewerContext")
    status = vc.get("optInStatus") if isinstance(vc, dict) else None
    if not isinstance(status, str) or not status:
        return None, followers, "no result.user.viewerContext.optInStatus"
    return status, followers, None


def read_fid(fid, allow_retry):
    n429 = ntrans = 0
    while True:
        code, doc, err, ts = request_once(fid)
        if code == 429 and allow_retry and n429 < RETRIES_429:
            n429 += 1
            print(f"fid {fid}: HTTP 429, sleeping {SLEEP_429}s (retry {n429}/{RETRIES_429})",
                  file=sys.stderr, flush=True)
            time.sleep(SLEEP_429)
            continue
        if (code == -1 or 500 <= code < 600) and allow_retry and ntrans < RETRIES_TRANSIENT:
            ntrans += 1
            time.sleep(SLEEP_TRANSIENT)
            continue
        rec = {"fid": fid, "status": None, "followers": None, "http": code, "ts": ts}
        if code == 200:
            status, followers, perr = extract(doc) if err is None else (None, None, err)
            rec["status"], rec["followers"] = status, followers
            err = perr
        if err:
            rec["err"] = err
        return rec


def load_fids(path):
    seen, fids = set(), []
    with open(path) as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            fid = int(line)
            if fid <= 0:
                raise ValueError(f"bad fid {fid}")
            if fid not in seen:
                seen.add(fid)
                fids.append(fid)
    return fids


def already_done(out_path):
    done = set()
    if not os.path.exists(out_path):
        return done
    with open(out_path) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("http") in (200, 404) and (r.get("http") == 404 or r.get("status")):
                done.add(int(r["fid"]))
    return done


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) != 2 or flags - {"--no-retry"}:
        print(__doc__, file=sys.stderr)
        return 64
    fids_path, out_path = args
    allow_retry = "--no-retry" not in flags
    fids = load_fids(fids_path)
    done = already_done(out_path)
    todo = [f for f in fids if f not in done]
    print(f"{len(fids)} fids, {len(fids) - len(todo)} already in {out_path}, {len(todo)} to read; "
          f"<= {1 / MIN_SPACING:.2f} req/s, retries {'on' if allow_retry else 'off'}",
          file=sys.stderr, flush=True)
    tally, streak429, t0, n = {}, 0, time.time(), 0
    aborted = False
    with open(out_path, "a") as out:
        for fid in todo:
            rec = read_fid(fid, allow_retry)
            out.write(json.dumps(rec, sort_keys=True) + "\n")
            out.flush()
            n += 1
            key = rec["status"] or f"http{rec['http']}"
            tally[key] = tally.get(key, 0) + 1
            streak429 = streak429 + 1 if rec["http"] == 429 else 0
            if n % 100 == 0:
                print(f"{n}/{len(todo)} read, {int(time.time() - t0)}s, {json.dumps(tally, sort_keys=True)}",
                      file=sys.stderr, flush=True)
            if allow_retry and streak429 >= ABORT_AFTER_429_FIDS:
                print(f"ABORT: {streak429} fids in a row still 429 after {RETRIES_429} retries each",
                      file=sys.stderr, flush=True)
                aborted = True
                break
    print(json.dumps({"read": n, "to_read": len(todo), "seconds": int(time.time() - t0),
                      "aborted": aborted, "tally": tally}, sort_keys=True))
    return 2 if aborted else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
