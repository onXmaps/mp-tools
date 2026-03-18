#!/usr/bin/env python3
"""
audit-production.py — Audit production data packs via the getPackageList API.

Uses the embedded timestamp baked into each pack file as the authoritative build
date (200-byte Range request on the uncompressed .txt file). Falls back to the
CDN Last-Modified header (HEAD on .gz) for Climb, or the API buildDate field for
AP projects, if the .txt Range request fails.

Packs are judged against the most recent build date within their project:
  CURRENT — within 3 days of the most recent pack
  BEHIND  — 3–14 days behind (missed one weekly generation cycle)
  STALE   — >14 days behind (missed multiple cycles)

Usage:
    python3 audit-production.py
    python3 audit-production.py --project climb
    python3 audit-production.py --project hike
    python3 audit-production.py --verbose
"""

import argparse
import json
import ssl
import struct
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Production domains per project type
PROJECTS = {
    "climb":    "www.mountainproject.com",
    "hike":     "www.hikingproject.com",
    "mtb":      "www.mtbproject.com",
    "ski":      "www.powderproject.com",
    "trailrun": "www.trailrunproject.com",
}

CDN_BASE      = "https://cdn2.apstatic.com"
API_PARAMS    = "apiVersion=2&os=iOS&osVersion=18.0&v=4.6.0&deviceId=00000000-0000-0000-0000-000000000000"
CURRENT_DAYS  = 3    # within this many days of latest → CURRENT
BEHIND_DAYS   = 14   # beyond this → STALE (between CURRENT_DAYS and this → BEHIND)
MAX_WORKERS   = 20

RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN  = "\033[0;32m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
NC     = "\033[0m"

def c(text, code):
    return f"{code}{text}{NC}"

def fmt_date(ts):
    if not ts:
        return "unknown   "
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

def fmt_size(n):
    if n is None: return "    ?"
    if n < 1024:  return f"{n}B"
    if n < 1024 ** 2: return f"{n // 1024}KB"
    return f"{n / 1024 ** 2:.1f}MB"

def age_days(ts, ref=None):
    if not ts: return None
    return ((ref or time.time()) - ts) / 86400


# ── HTTP helpers ──────────────────────────────────────────────────────────────

_ssl_ctx = ssl.create_default_context()

def _req(url, method="GET", headers=None, rng=None):
    h = {"User-Agent": "datapack-auditor/1.0"}
    if headers: h.update(headers)
    if rng is not None: h["Range"] = f"bytes=0-{rng}"
    req = urllib.request.Request(url, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=15) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, b"", e.headers
    except Exception:
        return None, b"", {}

def fetch_json(url):
    _, body, _ = _req(url)
    return json.loads(body.decode("utf-8"))


# ── Timestamp extraction ──────────────────────────────────────────────────────

def embedded_ts_climb(area_id):
    """
    Range-fetch the first 300 bytes of the uncompressed .txt pack.
    Climb packs use a binary framed format:
      [8B length LE][8B type LE][JSON payload]
    The PACKAGE record (type=1) is always first and contains buildDate.
    """
    status, body, _ = _req(f"{CDN_BASE}/mobile/climb/V2-{area_id}.txt", rng=299)
    if status not in (200, 206) or len(body) < 16:
        return None
    try:
        length  = struct.unpack_from("<Q", body, 0)[0]
        payload = body[16:16 + min(length, len(body) - 16)]
        return json.loads(payload).get("buildDate")
    except Exception:
        return None

def embedded_ts_ap(project, area_id):
    """
    Range-fetch the first 150 bytes of the uncompressed .txt pack.
    AP packs use a plaintext format: Package_{id}_{timestamp}_{json}\\n
    """
    status, body, _ = _req(f"{CDN_BASE}/mobile/{project}/V2-{area_id}.txt", rng=149)
    if status not in (200, 206) or not body:
        return None
    try:
        line  = body.split(b"\n")[0].decode("utf-8", errors="replace")
        parts = line.split("_", 3)
        return int(parts[2]) if len(parts) >= 3 else None
    except Exception:
        return None

def last_modified_ts(url_gz):
    """HEAD the .gz and parse Last-Modified as a fallback."""
    status, _, hdrs = _req(url_gz, method="HEAD")
    if status not in (200, 206):
        return None
    lm = hdrs.get("Last-Modified")
    try:
        return int(parsedate_to_datetime(lm).timestamp()) if lm else None
    except Exception:
        return None

def pack_date_climb(area_id):
    """Embedded buildDate primary; Last-Modified on .gz as fallback."""
    ts = embedded_ts_climb(area_id)
    if ts is None:
        ts = last_modified_ts(f"{CDN_BASE}/mobile/climb/V2-{area_id}.txt.gz")
    return ts

def pack_date_ap(project, area_id, api_build_date=None):
    """Embedded timestamp primary; API buildDate as fallback."""
    ts = embedded_ts_ap(project, area_id)
    if ts is None and api_build_date:
        ts = api_build_date
    return ts


# ── Audit functions ───────────────────────────────────────────────────────────

def audit_climb(verbose):
    url = f"https://{PROJECTS['climb']}/api?action=getPackageList&{API_PARAMS}"
    print(f"\n{c('=== climb ===', BOLD)}", flush=True)

    try:
        data     = fetch_json(url)
        packages = data.get("packages", [])
    except Exception as e:
        print(c(f"  [ERROR] getPackageList failed: {e}", RED))
        return 0, 0, 1

    print(f"  {len(packages)} packs — fetching embedded timestamps in parallel...", flush=True)

    # Fetch all dates in parallel
    rows = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(pack_date_climb, p["id"]): p for p in packages}
        for fut in as_completed(futs):
            p  = futs[fut]
            ts = fut.result()
            rows[p["id"]] = {**p, "_ts": ts}

    # Determine most recent date among all packs
    valid_ts = [r["_ts"] for r in rows.values() if r["_ts"]]
    if not valid_ts:
        print(c("  [ERROR] No timestamps retrieved", RED))
        return 0, 0, 1
    latest_ts = max(valid_ts)
    latest_dt = fmt_date(latest_ts)
    now       = time.time()

    current_packs = [r for r in rows.values() if r["_ts"] and age_days(r["_ts"], latest_ts) <= CURRENT_DAYS]
    behind_packs  = [r for r in rows.values() if r["_ts"] and CURRENT_DAYS < age_days(r["_ts"], latest_ts) <= BEHIND_DAYS]
    stale_packs   = [r for r in rows.values() if r["_ts"] and age_days(r["_ts"], latest_ts) > BEHIND_DAYS]
    nodate_packs  = [r for r in rows.values() if not r["_ts"]]

    print(f"  Most recent pack: {latest_dt} ({age_days(latest_ts, now):.1f}d ago)")
    print(f"  {c(f'CURRENT: {len(current_packs)}', GREEN)}  "
          f"{c(f'BEHIND: {len(behind_packs)}', YELLOW)}  "
          f"{c(f'STALE: {len(stale_packs)}', RED)}  "
          f"NO_DATE: {len(nodate_packs)}")

    def print_pack(r, status_color, lag_str):
        pid   = r["id"]
        title = r["title"][:40]
        size  = fmt_size(r["size"])
        dt    = fmt_date(r["_ts"])
        routes = r.get("numRoutes", 0)
        print(f"    {dt}  {lag_str:>14}  routes={routes:>5}  {size:>8}  {title}")

    if behind_packs:
        behind_packs.sort(key=lambda r: r["_ts"])
        print(f"\n  {c(f'BEHIND ({len(behind_packs)} packs — missed last run):', YELLOW)}")
        for r in behind_packs:
            lag = age_days(r["_ts"], latest_ts)
            print_pack(r, YELLOW, f"+{lag:.0f}d behind")

    if stale_packs:
        stale_packs.sort(key=lambda r: r["_ts"])
        print(f"\n  {c(f'STALE ({len(stale_packs)} packs):', RED)}")
        for r in stale_packs:
            lag = age_days(r["_ts"], latest_ts)
            print_pack(r, RED, f"+{lag:.0f}d behind")

    if verbose and current_packs:
        current_packs.sort(key=lambda r: r["title"])
        print(f"\n  {c(f'CURRENT ({len(current_packs)} packs):', GREEN)}")
        for r in current_packs:
            print_pack(r, GREEN, "current")

    if nodate_packs:
        print(f"\n  {c(f'NO DATE ({len(nodate_packs)} packs):', DIM)}")
        for r in nodate_packs:
            print(f"    {r['title']}")

    n_fail = len(stale_packs)
    n_warn = len(behind_packs)
    n_ok   = len(current_packs)
    return n_ok, n_warn, n_fail


def audit_ap(project, verbose):
    url = f"https://{PROJECTS[project]}/api?action=getPackageList&{API_PARAMS}"
    print(f"\n{c(f'=== {project} ===', BOLD)}", flush=True)

    try:
        packages = fetch_json(url)
        if not isinstance(packages, list):
            raise ValueError(f"Unexpected response type: {type(packages)}")
    except Exception as e:
        print(c(f"  [ERROR] getPackageList failed: {e}", RED))
        return 0, 0, 1

    print(f"  {len(packages)} packs — fetching embedded timestamps in parallel...", flush=True)

    rows = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {
            ex.submit(pack_date_ap, project, p["id"], p.get("buildDate")): p
            for p in packages
        }
        for fut in as_completed(futs):
            p  = futs[fut]
            ts = fut.result()
            rows[p["id"]] = {**p, "_ts": ts}

    valid_ts = [r["_ts"] for r in rows.values() if r["_ts"]]
    if not valid_ts:
        print(c("  [ERROR] No timestamps retrieved", RED))
        return 0, 0, 1
    latest_ts = max(valid_ts)
    now       = time.time()

    current_packs = [r for r in rows.values() if r["_ts"] and age_days(r["_ts"], latest_ts) <= CURRENT_DAYS]
    behind_packs  = [r for r in rows.values() if r["_ts"] and CURRENT_DAYS < age_days(r["_ts"], latest_ts) <= BEHIND_DAYS]
    stale_packs   = [r for r in rows.values() if r["_ts"] and age_days(r["_ts"], latest_ts) > BEHIND_DAYS]
    nodate_packs  = [r for r in rows.values() if not r["_ts"]]

    print(f"  Most recent pack: {fmt_date(latest_ts)} ({age_days(latest_ts, now):.1f}d ago)")
    print(f"  {c(f'CURRENT: {len(current_packs)}', GREEN)}  "
          f"{c(f'BEHIND: {len(behind_packs)}', YELLOW)}  "
          f"{c(f'STALE: {len(stale_packs)}', RED)}  "
          f"NO_DATE: {len(nodate_packs)}")

    def print_pack(r, lag_str):
        pid   = r["id"]
        title = r["title"][:40]
        dt    = fmt_date(r["_ts"])
        trails = r.get("numTrails", "?")
        print(f"    {dt}  {lag_str:>14}  trails={trails:>5}  {title}")

    if behind_packs:
        behind_packs.sort(key=lambda r: r["_ts"])
        print(f"\n  {c(f'BEHIND ({len(behind_packs)} packs — missed last run):', YELLOW)}")
        for r in behind_packs:
            lag = age_days(r["_ts"], latest_ts)
            print_pack(r, f"+{lag:.0f}d behind")

    if stale_packs:
        stale_packs.sort(key=lambda r: r["_ts"])
        print(f"\n  {c(f'STALE ({len(stale_packs)} packs):', RED)}")
        for r in stale_packs:
            lag = age_days(r["_ts"], latest_ts)
            print_pack(r, f"+{lag:.0f}d behind")

    if verbose and current_packs:
        current_packs.sort(key=lambda r: r["title"])
        print(f"\n  {c(f'CURRENT ({len(current_packs)} packs):', GREEN)}")
        for r in current_packs:
            print_pack(r, "current")

    if nodate_packs:
        print(f"\n  {c(f'NO DATE ({len(nodate_packs)} packs):', DIM)}")
        for r in nodate_packs:
            print(f"    {r['title']}")

    return len(current_packs), len(behind_packs), len(stale_packs)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Audit production data pack build dates via embedded timestamps."
    )
    parser.add_argument(
        "--project",
        choices=list(PROJECTS.keys()) + ["all"],
        default="all",
        help="Project type to audit (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Also print CURRENT (passing) packs",
    )
    args = parser.parse_args()

    projects = list(PROJECTS.keys()) if args.project == "all" else [args.project]

    total_ok = total_behind = total_stale = 0
    for project in projects:
        if project == "climb":
            ok, behind, stale = audit_climb(args.verbose)
        else:
            ok, behind, stale = audit_ap(project, args.verbose)
        total_ok     += ok
        total_behind += behind
        total_stale  += stale

    print(f"\n{'=' * 55}")
    print(
        f"Summary:  {c(f'CURRENT={total_ok}', GREEN)}"
        f"  {c(f'BEHIND={total_behind}', YELLOW)}"
        f"  {c(f'STALE={total_stale}', RED)}"
    )
    print(f"{'=' * 55}")

    sys.exit(0 if (total_behind + total_stale) == 0 else 1)


if __name__ == "__main__":
    main()
