#!/usr/bin/env python3
"""Fetch High Brooms <-> London Bridge departures from the Rail Data Marketplace
(National Rail LDBWS REST) and write a compact departures.json.

Environment:
  RDM_API_KEY    consumer key from the RDM subscription (GitHub secret)
  RDM_BOARD_URL  board endpoint up to the method name, e.g.
                 https://api1.raildata.org.uk/1010-live-arrival-and-departure-boards-arr-and-dep1_1/LDBWS/api/20220120/GetArrDepBoardWithDetails
  OUT            output path (default departures.json)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROUTES = [("HIB", "LBG"), ("LBG", "HIB")]
ROWS = 8


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get(d, *keys, default=None):
    """Read a field that may come back camelCase or PascalCase."""
    if not isinstance(d, dict):
        return default
    for k in keys:
        for cand in (k, k[:1].upper() + k[1:]):
            if cand in d and d[cand] is not None:
                return d[cand]
    return default


def fetch(url, key):
    req = urllib.request.Request(url, headers={"x-apikey": key, "Accept": "application/json",
                                               "User-Agent": "commute-trains/1.0"})
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(3)
    raise last


def arrival_at(svc, crs):
    """Scheduled and expected arrival at the destination station, if listed."""
    for group in get(svc, "subsequentCallingPoints", default=[]) or []:
        for cp in get(group, "callingPoint", default=[]) or []:
            if get(cp, "crs") == crs:
                return get(cp, "st"), get(cp, "et") or get(cp, "at")
    return None, None


def board(base, key, frm, to):
    url = f"{base.rstrip('/')}/{frm}?numRows={ROWS}&filterCrs={to}&filterType=to"
    try:
        data = fetch(url, key)
    except Exception as e:  # report, never crash the whole run
        code = getattr(e, "code", None)
        return {"from": frm, "to": to, "ok": False,
                "error": f"HTTP {code}" if code else type(e).__name__,
                "generatedAt": now_iso()}

    trains = []
    for svc in get(data, "trainServices", default=[]) or []:
        dest = get(svc, "destination", default=[]) or []
        dest_name = " & ".join(get(x, "locationName", default="?") for x in dest) or None
        sta, eta = arrival_at(svc, to)
        trains.append({
            "std": get(svc, "std"),
            "etd": get(svc, "etd"),
            "platform": get(svc, "platform"),
            "dest": dest_name,
            "coaches": get(svc, "length") or None,
            "cancelled": bool(get(svc, "isCancelled", default=False)),
            "reason": get(svc, "cancelReason") or get(svc, "delayReason"),
            "arr": sta,
            "eta": eta,
        })

    msgs = []
    for m in get(data, "nrccMessages", default=[]) or []:
        text = get(m, "value", "Value") if isinstance(m, dict) else m
        if text:
            msgs.append(" ".join(str(text).split()))

    return {"from": frm, "to": to, "ok": True,
            "generatedAt": get(data, "generatedAt") or now_iso(),
            "messages": msgs, "trains": trains}


def main():
    key = os.environ.get("RDM_API_KEY", "").strip()
    base = os.environ.get("RDM_BOARD_URL", "").strip()
    if not key or not base:
        print("RDM_API_KEY and RDM_BOARD_URL must both be set", file=sys.stderr)
        return 2

    out = {"fetchedAt": now_iso(), "source": "Rail Data Marketplace (Darwin LDBWS)",
           "boards": {f"{f}-{t}": board(base, key, f, t) for f, t in ROUTES}}

    path = os.environ.get("OUT", "departures.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)

    for k, b in out["boards"].items():
        print(k, "ok" if b["ok"] else b["error"], len(b.get("trains", [])), "trains")
    # Fail the run only if both directions failed, so the data branch still updates.
    return 0 if any(b["ok"] for b in out["boards"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
