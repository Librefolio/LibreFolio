#!/usr/bin/env python3
"""Capture the gallery dashboard report from a server running on a real-data WORKING copy.

The same request as the browser-console procedure in ``scripts/normalize_dashboard_fixture.py``, as a script: it signs
in, asks for every report section in one POST and writes the raw JSON. Standard library only.

    python3 capture_dashboard_report.py http://127.0.0.1:<WORK_PORT> <username> <password-file> <raw.json> \
        [--brokers 2,1] [--currency EUR]

- The password is read from a 0600 file, never from the command line (see «Credentials» in SKILL.md).
- The range is the last year ending today.
- Write ``raw.json`` OUTSIDE the repository (the session folder) and delete it after the normalization.
"""

import argparse
import datetime
import http.cookiejar
import json
import pathlib
import urllib.request

SECTIONS = ("summary", "history", "allocation_history", "breakdown", "positions_contribution", "broker_pnl_history", "pnl_candles", "income_history", "cost_history", "deposit_history", "acquisition_funding")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base")
    parser.add_argument("username")
    parser.add_argument("password_file", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--brokers", default="2,1", help="broker ids, comma separated (at least two: the per-broker P&L overlay needs them)")
    parser.add_argument("--currency", default="EUR")
    args = parser.parse_args()

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def post(path: str, body: dict) -> dict:
        request = urllib.request.Request(args.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with opener.open(request, timeout=600) as response:
            return json.loads(response.read())

    post("/api/v1/auth/login", {"username": args.username, "password": args.password_file.read_text().strip()})
    end = datetime.date.today()
    payload = {f"include_{name}": True for name in SECTIONS}
    payload |= {"broker_ids": [int(x) for x in args.brokers.split(",")], "date_range": {"start": end.replace(year=end.year - 1).isoformat(), "end": end.isoformat()}, "target_currency": args.currency}
    report = post("/api/v1/portfolio/report", payload)
    args.out.write_text(json.dumps(report))
    print("sections:", ", ".join(sorted(report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
