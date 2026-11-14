"""Submit 3 SMALL AppEEARS point-sample requests, wait for them and download the results.

Run it yourself in a terminal (it asks for your Earthdata login; the password is typed by you,
kept in memory only, never printed and never written to disk):

    python scripts/appeears_request.py            # submit, then wait and download
    python scripts/appeears_request.py --no-wait  # only submit
    python scripts/appeears_request.py --netrc    # use your own _netrc entry instead of typing

What it does
  1. logs in to the AppEEARS API (https://appeears.earthdatacloud.nasa.gov/api/) -> temporary token
  2. submits three small requests for Karshi_field1 and Fergana_field1:
       smap_fast      SPL4SMGP.008  Geophysical_Data_sm_rootzone      2024-01-01 .. 2026-11-10
       ecostress_fast ECO_L4T_ESI.002 ESI + ECO_L3T_JET.002 ETdaily   2025-06-01 .. 2025-09-30
       hls_fast       HLSL30_VI.020 NDVI + HLSS30_VI.020 NDVI         2025-03-01 .. 2026-11-10
  3. asks (y/N) whether to delete the old big requests hls_green, ecostress_stress and smap_soil
  4. checks every 10 minutes; when a request is done, downloads only its *-results.csv into data/appeears/
  5. logs out (the token is invalidated)
"""
from __future__ import annotations

import argparse
import getpass
import sys
import time
from pathlib import Path

import requests

API = "https://appeears.earthdatacloud.nasa.gov/api"
OUT = Path(__file__).resolve().parents[1] / "data" / "appeears"
POINTS = [
    {"id": "Karshi_field1", "category": "Karshi", "latitude": 38.91903, "longitude": 65.62044},
    {"id": "Fergana_field1", "category": "Fergana", "latitude": 40.49067, "longitude": 71.63369},
]
REQUESTS = {
    "smap_fast": ("01-01-2024", "11-10-2026", [("SPL4SMGP.008", "Geophysical_Data_sm_rootzone")]),
    "ecostress_fast": ("06-01-2025", "09-30-2025", [("ECO_L4T_ESI.002", "ESI"), ("ECO_L3T_JET.002", "ETdaily")]),
    "hls_fast": ("03-01-2025", "11-10-2026", [("HLSL30_VI.020", "NDVI"), ("HLSS30_VI.020", "NDVI")]),
}
OLD = ["hls_green", "ecostress_stress", "smap_soil"]


def login(use_netrc: bool = False) -> str:
    creds = None
    if use_netrc:   # your own _netrc / .netrc entry for urs.earthdata.nasa.gov (read only on your machine)
        import netrc
        import os
        home = Path(os.environ.get("USERPROFILE") or Path.home())
        for f in [os.environ.get("NETRC"), home / ".netrc", home / "_netrc", home / "_netrc.txt", home / ".netrc.txt",
                  Path.home() / "_netrc", Path.home() / ".netrc"]:
            if f and Path(f).is_file():
                try:
                    creds = netrc.netrc(str(f)).authenticators("urs.earthdata.nasa.gov")
                except netrc.NetrcParseError as e:
                    print(f"Could not read {f}: {e.msg} (line {e.lineno})")
                if creds:
                    print(f"Using the urs.earthdata.nasa.gov entry in {f}")
                    break
        if not creds:
            print(f"No netrc entry for urs.earthdata.nasa.gov found (looked for .netrc, _netrc and _netrc.txt in {home})"
                  " - type your login instead.")
    if creds:
        user, _, pw = creds
    else:
        user = input("Earthdata username: ").strip()
        pw = getpass.getpass("Earthdata password (not shown): ")
    r = requests.post(f"{API}/login", auth=(user, pw), timeout=60)
    del pw
    if r.status_code != 200:
        sys.exit(f"Login failed ({r.status_code}). Check the username/password.")
    return r.json()["token"]


def submit(h: dict) -> dict:
    ids = {}
    for name, (start, end, layers) in REQUESTS.items():
        task = {"task_type": "point", "task_name": name,
                "params": {"dates": [{"startDate": start, "endDate": end}],
                           "layers": [{"product": p, "layer": l} for p, l in layers],
                           "coordinates": POINTS}}
        r = requests.post(f"{API}/task", json=task, headers=h, timeout=120)
        if r.status_code not in (200, 202):
            print(f"  {name}: NOT accepted ({r.status_code}) {r.text[:300]}")
            continue
        ids[name] = r.json()["task_id"]
        print(f"  {name}: accepted, task_id {ids[name]}")
    return ids


def delete_old(h: dict) -> None:
    tasks = requests.get(f"{API}/task", headers=h, timeout=60).json()
    old = [t for t in tasks if t.get("task_name") in OLD]
    if not old:
        return
    print("Old big requests:", ", ".join(f"{t['task_name']} ({t['status']})" for t in old))
    if input("Delete them now? [y/N] ").strip().lower() == "y":
        for t in old:
            r = requests.delete(f"{API}/task/{t['task_id']}", headers=h, timeout=60)
            print(f"  deleted {t['task_name']}" if r.status_code in (200, 204) else f"  could not delete {t['task_name']} ({r.status_code})")


def download(h: dict, name: str, task_id: str) -> None:
    bundle = requests.get(f"{API}/bundle/{task_id}", headers=h, timeout=60).json()
    OUT.mkdir(parents=True, exist_ok=True)
    for f in bundle.get("files", []):
        if f["file_name"].endswith("-results.csv"):
            r = requests.get(f"{API}/bundle/{task_id}/{f['file_id']}", headers=h, timeout=600, allow_redirects=True)
            path = OUT / f"{name}-{Path(f['file_name']).name}"
            path.write_bytes(r.content)
            print(f"  downloaded {path} ({len(r.content) / 1024:.0f} KB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--every", type=int, default=600, help="seconds between status checks")
    ap.add_argument("--netrc", action="store_true", help="use your _netrc entry for urs.earthdata.nasa.gov")
    args = ap.parse_args()
    token = login(args.netrc)
    h = {"Authorization": f"Bearer {token}"}
    try:
        print("Submitting 3 small requests ...")
        ids = submit(h)
        delete_old(h)
        if args.no_wait or not ids:
            return
        left = dict(ids)
        while left:
            for name, tid in list(left.items()):
                st = requests.get(f"{API}/task/{tid}", headers=h, timeout=60).json().get("status")
                print(time.strftime("%H:%M"), name, st)
                if st == "done":
                    download(h, name, tid)
                    left.pop(name)
                elif st in ("error", "expired"):
                    print(f"  {name} ended with status {st}")
                    left.pop(name)
            if left:
                time.sleep(args.every)
        print("All done. Tell Claude the files are in data/appeears/.")
    finally:
        requests.post(f"{API}/logout", headers=h, timeout=30)


if __name__ == "__main__":
    main()
