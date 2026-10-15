#!/bin/bash
# SCALE calculator script for fz (all Scale-* models)
#
# Runs scalerte on the input file given by fz, then decides success from the
# SCALE output (<input>.out and <input>.msg), never from the scalerte exit
# code: scalerte returns 0 even when the sequence failed (verified on SCALE
# 6.2.4, see tests/scale_probe).
#
# Environment (all optional):
#   SCALE_CMD      scalerte executable (default: $SCALE_HOME/bin/scalerte, else
#                  scalerte on PATH, else the newest of /SCALE/scale6*,
#                  /opt/scale*, /opt/SCALE*, ~/opt/SCALE*, ~/opt/scale*)
#   SCALE_HOME     SCALE installation directory (contains bin/scalerte)
#   SCALE_THREADS  number of threads (scalerte -I N)
#   SCALE_MPI      number of MPI processes (scalerte -N N; MPI builds only)
#   SCALE_TMPDIR   SCALE temporary directory (scalerte -T DIR)
#   SCALE_OPTS     extra scalerte options, appended as given (e.g. "-r")
#
# Input file: the first argument named *.inp, else the first regular file that
# is not a SCALE/fz output file.
#
# Exit codes:
#   0 normal end ('SCALE is finished on ...', no error message), or data check
#     only ('=csas6 parm=check': 'This problem will not be run because parm=check ...')
#   1 no input file           2 usage
#   4 scalerte not found      5 no .out produced
#   6 SCALE errors (message on stderr)
#   7 .out without end banner (run interrupted or crashed)

if [ $# -eq 0 ]; then
  echo "Usage: $0 <input file ...|input_directory>" >&2
  exit 2
fi
if [ -d "$1" ]; then
  cd "$1" || exit 1
  set -- *
fi

is_output() {
  case "$1" in
    *.out|*.msg|*.html|*.htmd|*.sdf|*.h5|*.3dmap|*.btf|PID) return 0 ;;
    out.txt|err.txt|log.txt|info.txt|history.txt|.fz_hash) return 0 ;;
  esac
  return 1
}

INP=""
for f in "$@"; do
  case "$f" in
    *.inp) [ -f "$f" ] && { INP="$f"; break; } ;;
  esac
done
if [ -z "$INP" ]; then
  for f in "$@"; do
    if [ -f "$f" ] && ! is_output "$f"; then INP="$f"; break; fi
  done
fi
if [ -z "$INP" ]; then
  echo "No SCALE input file found in: $*" >&2
  exit 1
fi

# scalerte executable
if [ -z "${SCALE_CMD:-}" ]; then
  if [ -n "${SCALE_HOME:-}" ]; then
    SCALE_CMD="$SCALE_HOME/bin/scalerte"
  else
    SCALE_CMD="$(command -v scalerte 2>/dev/null)"
    if [ -z "$SCALE_CMD" ]; then
      for c in $(ls -d /SCALE/scale6* /opt/scale* /opt/SCALE* "$HOME"/opt/SCALE* "$HOME"/opt/scale* 2>/dev/null | sort -V -r); do
        [ -x "$c/bin/scalerte" ] && { SCALE_CMD="$c/bin/scalerte"; break; }
      done
    fi
  fi
fi
if [ -z "$SCALE_CMD" ] || { [ ! -x "$SCALE_CMD" ] && ! command -v "$SCALE_CMD" >/dev/null 2>&1; }; then
  echo "scalerte not found${SCALE_CMD:+: $SCALE_CMD} (set SCALE_HOME or SCALE_CMD, or put scalerte on PATH)" >&2
  exit 4
fi
# SCALE helper commands (copy_graphic, ...) live in cmds/, next to bin/
SCALE_ROOT="$(cd "$(dirname "$SCALE_CMD")/.." 2>/dev/null && pwd)"
[ -d "$SCALE_ROOT/cmds" ] && export PATH="$PATH:$SCALE_ROOT/cmds"

OPTS=()
[ -n "${SCALE_THREADS:-}" ] && OPTS+=(-I "$SCALE_THREADS")
[ -n "${SCALE_MPI:-}" ] && OPTS+=(-N "$SCALE_MPI")
[ -n "${SCALE_TMPDIR:-}" ] && OPTS+=(-T "$SCALE_TMPDIR")

# scalerte names its outputs after the input basename, without extension
BASE="${INP%.*}"
OUT="$BASE.out"
MSG="$BASE.msg"
# never parse a previous run's output
rm -rf "$OUT" "$MSG" "$BASE.html" "$BASE.htmd"

# fz stops a run (timeout, interrupt) by sending SIGTERM to this shell only:
# relay it to scalerte, which then stops its whole process tree and cleans up
# its temporary directory (an orphaned SCALE run would go on otherwise)
"$SCALE_CMD" "${OPTS[@]}" ${SCALE_OPTS:-} "$INP" &
PID_SCALE=$!
trap 'kill -TERM $PID_SCALE 2>/dev/null; wait $PID_SCALE; exit 143' TERM INT HUP
wait $PID_SCALE
RC=$?
trap - TERM INT HUP

if [ ! -f "$OUT" ]; then
  echo "SCALE produced no $OUT (scalerte exit code $RC)" >&2
  [ -f "$MSG" ] && tail -5 "$MSG" >&2
  exit 5
fi

# Error markers verified on SCALE 6.2.4 (tests/fixtures/scale6.2.4); anchored so
# that the echoed input (comment and title lines are copied to the .out) never
# matches. Same rules as the "scale_status" output of the models.
ERRORS=$( {
  [ -f "$MSG" ] && grep -E '^error: ' "$MSG"
  # '***** error ***** <module> message number <id> follows:' + message on the next line
  LC_ALL=C awk '/^ *\*\*\*\*\* error \*\*\*\*\* / {h=$0; sub(/^ *\*+ error \*+ */, "", h); if ((getline n) > 0) {sub(/^ +/, "", n); h=h " " n}; print h}' "$( [ -f "$MSG" ] && echo "$MSG" || echo "$OUT")"
  grep -E '^line:[0-9]+ column:[0-9]+ - Parse Error:' "$OUT"
  grep -E '^[A-Za-z0-9_-]+ failed to execute\. error code' "$OUT"
  grep -E '^ *(execution )?terminated due to errors\. completion code' "$OUT"
  grep -E '^error: |^\*\*\*Error: ' "$OUT"
} 2>/dev/null | head -8)
if [ -n "$ERRORS" ]; then
  echo "SCALE errors ($OUT, $MSG):" >&2
  echo "$ERRORS" >&2
  exit 6
fi
if ! grep -q -E '^ *SCALE is finished on ' "$OUT"; then
  echo "$OUT has no end banner ('SCALE is finished on ...'): run interrupted or crashed (scalerte exit code $RC)" >&2
  # glibc abort message, e.g. 'double free or corruption (out)' (tests/fixtures/scale6.2.4/err_array_undefined)
  [ -f "$MSG" ] && grep -E '^(free\(\): |double free|malloc\(\): |munmap_chunk|corrupted |Segmentation fault|Program received signal|Fortran runtime error|Backtrace)' "$MSG" | head -3 >&2
  exit 7
fi
exit 0
