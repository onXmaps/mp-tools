#!/usr/bin/env bash
# audit-datapack-files.sh
# Scans the local mobile package directory and reports pack file status.
#
# Usage:
#   ./audit-datapack-files.sh [projectType]
#
# If no projectType is provided, audits all projects.
# Must be run from the adventure-project repo root.

set -euo pipefail

MOBILE_DIR="site/public/assets/mobile"
ALL_PROJECTS=(climb hike mtb ski trailrun)
MIN_SIZE_BYTES=1024    # packs smaller than 1KB are considered failures
STALE_DAYS=14          # packs older than this many days are flagged as stale

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

if [[ ! -d "$MOBILE_DIR" ]]; then
  echo "ERROR: $MOBILE_DIR not found. Run this script from the adventure-project repo root."
  exit 1
fi

if [[ $# -ge 1 ]]; then
  PROJECTS=("$1")
else
  PROJECTS=("${ALL_PROJECTS[@]}")
fi

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_STALE=0

for PROJECT in "${PROJECTS[@]}"; do
  DIR="$MOBILE_DIR/$PROJECT"
  if [[ ! -d "$DIR" ]]; then
    echo -e "${YELLOW}[SKIP]${NC} $PROJECT — directory $DIR not found"
    continue
  fi

  GZ_FILES=("$DIR"/V2-*.txt.gz)
  if [[ ${#GZ_FILES[@]} -eq 0 ]] || [[ ! -f "${GZ_FILES[0]}" ]]; then
    echo -e "${RED}[FAIL]${NC} $PROJECT — no .txt.gz files found in $DIR"
    ((TOTAL_FAIL++))
    continue
  fi

  echo ""
  echo "=== $PROJECT (${#GZ_FILES[@]} packs) ==="

  for GZ in "${GZ_FILES[@]}"; do
    BASENAME=$(basename "$GZ" .txt.gz)
    AREA_ID="${BASENAME#V2-}"
    SIZE=$(stat -f%z "$GZ" 2>/dev/null || stat -c%s "$GZ" 2>/dev/null || echo 0)
    MTIME=$(stat -f%m "$GZ" 2>/dev/null || stat -c%Y "$GZ" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    AGE_DAYS=$(( (NOW - MTIME) / 86400 ))
    TXT_FILE="${GZ%.gz}"

    STATUS="OK"
    COLOR="$GREEN"
    NOTES=""

    # Check size
    if [[ "$SIZE" -lt "$MIN_SIZE_BYTES" ]]; then
      STATUS="FAIL"
      COLOR="$RED"
      NOTES="${NOTES}size=${SIZE}B (too small) "
    fi

    # Check .txt companion
    if [[ ! -f "$TXT_FILE" ]]; then
      if [[ "$STATUS" == "OK" ]]; then
        STATUS="WARN"
        COLOR="$YELLOW"
      fi
      NOTES="${NOTES}missing .txt companion "
    fi

    # Check staleness
    if [[ "$AGE_DAYS" -gt "$STALE_DAYS" ]]; then
      if [[ "$STATUS" == "OK" ]]; then
        STATUS="STALE"
        COLOR="$YELLOW"
        ((TOTAL_STALE++))
      fi
      NOTES="${NOTES}age=${AGE_DAYS}d "
    fi

    if [[ "$STATUS" == "OK" ]]; then
      ((TOTAL_PASS++))
    elif [[ "$STATUS" == "FAIL" ]]; then
      ((TOTAL_FAIL++))
    fi

    SIZE_KB=$((SIZE / 1024))
    echo -e "  ${COLOR}[${STATUS}]${NC} area=${AREA_ID} size=${SIZE_KB}KB age=${AGE_DAYS}d ${NOTES}"
  done
done

echo ""
echo "=============================="
echo -e "Summary: ${GREEN}PASS=${TOTAL_PASS}${NC}  ${RED}FAIL=${TOTAL_FAIL}${NC}  ${YELLOW}STALE=${TOTAL_STALE}${NC}"
echo "=============================="

if [[ "$TOTAL_FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
