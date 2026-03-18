#!/usr/bin/env python3
"""
audit-production.py — Audit production data packs via the getPackageList API.

For each project type, queries the production getPackageList endpoint and checks
pack sizes and staleness. For AP projects (no size in response), also HEADs the
CDN URL to get file size.

Usage:
    python3 audit-production.py
    python3 audit-production.py --project climb
    python3 audit-production.py --project hike
"""

import argparse
import json
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone

# Production domains per project type
PROJECTS = {
    "climb":    "www.mountainproject.com",
    "hike":     "www.hikingproject.com",
    "mtb":      "www.mtbproject.com",
    "ski":      "www.powderproject.com",
    "trailrun": "www.trailrunproject.com",
}

CDN_BASE = "https://cdn2.apstatic.com"

# Thresholds
STALE_DAYS = 14           # flag packs older than this
MIN_SIZE_BYTES = 50_000   # 50 KB — anything smaller is suspicious

# ANSI colors
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN  = "\033[0;32m"
BOLD   = "\033[1m"
NC     = "\033[0m"

def c(text, code):
    return f"{code}{text}{NC}"


def make_ssl_ctx():
    return ssl.create_default_context()


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "datapack-auditor/1.0"})
    with urllib.request.urlopen(req, context=make_ssl_ctx(), timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def head_size(url):
    """Return Content-Length from a HEAD request, or None on failure."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "datapack-auditor/1.0"})
    try:
        with urllib.request.urlopen(req, context=make_ssl_ctx(), timeout=15) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else None
    except Exception as e:
        return None


def fmt_size(bytes_):
    if bytes_ is None:
        return "??KB"
    if bytes_ < 1024:
        return f"{bytes_}B"
    if bytes_ < 1024 * 1024:
        return f"{bytes_ // 1024}KB"
    return f"{bytes_ / (1024 * 1024):.1f}MB"


def fmt_date(ts):
    if not ts:
        return "unknown"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def age_days(ts):
    if not ts:
        return None
    return (time.time() - ts) / 86400


def audit_climb():
    """
    Climb getPackageList returns:
      { "packages": [{ "id", "title", "size" (bytes), "x", "y", "intl", "numRoutes" }],
        "lastBuild": <epoch> }
    Size is included per-pack. No per-pack buildDate — only top-level lastBuild.
    """
    domain = PROJECTS["climb"]
    url = (f"https://{domain}/api?action=getPackageList&apiVersion=2"
           f"&os=iOS&osVersion=18.0&v=4.6.0&deviceId=00000000-0000-0000-0000-000000000000")
    print(f"\n{c('=== climb ===', BOLD)}")

    try:
        data = fetch_json(url)
    except Exception as e:
        print(c(f"  [ERROR] getPackageList failed: {e}", RED))
        return 0, 1, 0

    packages  = data.get("packages", [])
    last_build = data.get("lastBuild", 0)
    lb_age    = age_days(last_build)

    if lb_age is not None:
        lb_color = YELLOW if lb_age > STALE_DAYS else GREEN
        print(f"  lastBuild: {c(f'{lb_age:.1f}d ago', lb_color)} ({fmt_date(last_build)})")
    print(f"  {len(packages)} pack(s) in list")

    passes = fails = stale = 0
    for pkg in packages:
        pid   = pkg.get("id", "?")
        title = pkg.get("title", "?")[:45]
        size  = pkg.get("size", 0)
        notes = [fmt_size(size)]

        if size == 0 or size < MIN_SIZE_BYTES:
            status, sc = "FAIL", RED
            fails += 1
            if size == 0:
                notes.append("ZERO SIZE")
            else:
                notes.append("TOO SMALL")
        else:
            status, sc = "OK", GREEN
            passes += 1

        print(f"  {c(f'[{status}]', sc)} id={pid:<12} {title:<45}  {' '.join(notes)}")

    return passes, fails, stale


def audit_ap(project):
    """
    AP getPackageList returns an array:
      [{ "id", "title", "photoUrl", "buildDate" (epoch), "intl", "x", "y",
         "searchRadius", "l", "t", "r", "b", "polygon", "numTrails", "lengthOfAllTrails" }]
    No size in response — must HEAD the CDN URL to get file size.
    """
    domain = PROJECTS[project]
    url = (f"https://{domain}/api?action=getPackageList&apiVersion=2"
           f"&os=iOS&osVersion=18.0&v=4.6.0&deviceId=00000000-0000-0000-0000-000000000000")
    print(f"\n{c(f'=== {project} ===', BOLD)}")

    try:
        packages = fetch_json(url)
    except Exception as e:
        print(c(f"  [ERROR] getPackageList failed: {e}", RED))
        return 0, 1, 0

    if not isinstance(packages, list):
        print(c(f"  [ERROR] Unexpected response format: {type(packages)}", RED))
        return 0, 1, 0

    print(f"  {len(packages)} pack(s) in list")

    passes = fails = stale = 0
    for pkg in packages:
        pid        = pkg.get("id", "?")
        title      = pkg.get("title", "?")[:45]
        build_date = pkg.get("buildDate", 0)
        cdn_url    = f"{CDN_BASE}/mobile/{project}/V2-{pid}.txt.gz"

        size  = head_size(cdn_url)
        notes = [fmt_size(size)]
        ba    = age_days(build_date)
        if ba is not None:
            notes.append(f"age={ba:.0f}d")

        if size is None:
            status, sc = "FAIL", RED
            notes.append("CDN unreachable")
            fails += 1
        elif size < MIN_SIZE_BYTES:
            status, sc = "FAIL", RED
            notes.append("TOO SMALL" if size > 0 else "ZERO SIZE")
            fails += 1
        elif ba is not None and ba > STALE_DAYS:
            status, sc = "STALE", YELLOW
            stale += 1
        else:
            status, sc = "OK", GREEN
            passes += 1

        print(f"  {c(f'[{status}]', sc)} id={pid:<12} {title:<45}  {' '.join(notes)}")

    return passes, fails, stale


def main():
    parser = argparse.ArgumentParser(
        description="Audit production data packs via the getPackageList API."
    )
    parser.add_argument(
        "--project",
        choices=list(PROJECTS.keys()) + ["all"],
        default="all",
        help="Project type to audit (default: all)",
    )
    args = parser.parse_args()

    projects = list(PROJECTS.keys()) if args.project == "all" else [args.project]

    total_pass = total_fail = total_stale = 0
    for project in projects:
        if project == "climb":
            p, f, s = audit_climb()
        else:
            p, f, s = audit_ap(project)
        total_pass  += p
        total_fail  += f
        total_stale += s

    print(f"\n{'=' * 50}")
    print(
        f"Summary:  {c(f'PASS={total_pass}', GREEN)}"
        f"  {c(f'FAIL={total_fail}', RED)}"
        f"  {c(f'STALE={total_stale}', YELLOW)}"
    )
    print(f"{'=' * 50}")

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
