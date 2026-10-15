#!/bin/bash
# Run the SCALE probe cases (cases/*.inp) with scalerte and record, for each
# case: exit code, produced files, end banners and extracted markers.
#
# Usage: [SCALE_HOME=/path/to/SCALE-6.2.x] [SCALE_LABEL=scale624] [JOBS=4] ./run_probe.sh ['glob']
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PATTERN="${1:-*}"
SCALERTE="${SCALE_HOME:+$SCALE_HOME/bin/}scalerte"
command -v "$SCALERTE" >/dev/null 2>&1 || { echo "scalerte not found (set SCALE_HOME)" >&2; exit 4; }
LABEL="${SCALE_LABEL:-scale}"
OUT="$HERE/results-$LABEL-$(date +%Y%m%d)"
mkdir -p "$OUT"

run_case() {
  inp="$1"; name="$(basename "$inp" .inp)"; d="$OUT/$name"
  rm -rf "$d"; mkdir -p "$d"; cp "$inp" "$d/"
  cd "$d" || return
  start=$(date +%s)
  "$SCALERTE" "$name.inp" > stdout.txt 2> stderr.txt
  echo "$?" > exit_code.txt
  echo $(( $(date +%s) - start )) > seconds.txt
  rm -rf ./*.htmd   # html report companion directory: not needed
}
export -f run_case; export OUT SCALERTE
ls "$HERE"/cases/$PATTERN.inp | xargs -P "${JOBS:-4}" -I{} bash -c 'run_case "$@"' _ {}

python3 "$HERE/summarize.py" "$OUT" | tee "$OUT/summary.txt"
