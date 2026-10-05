#!/bin/bash
# gen_retry.sh NAME FILES PROMPT_FILE — one Gemini generation with the stall/limit rules.
#   NAME         sprite name (also used for the session + log names)
#   FILES        reference images, comma-separated ("" for none)
#   PROMPT_FILE  text file holding the prompt
# A Gemini image job that has not finished in 3 minutes is stuck: kill it and retry in a
# fresh conversation (up to ATTEMPTS times). If Gemini answers with the image-limit message
# ("... limit resets ..."), retrying is pointless — print LIMIT and exit 3 so a batch stops.
# Prints "OK <path to raw png>" on success (exit 0); exit 1 when every attempt failed.
#
# env: OUT_DIR   sprite_gen output dir (default ./sprites)
#      LOG_DIR   per-attempt logs (default $OUT_DIR/logs)
#      CATEGORY  sprite_gen category (default character)
#      TIMEOUT_S stall timeout in seconds (default 180)
#      ATTEMPTS  max attempts (default 4)
set -u
[ $# -ge 3 ] || { awk 'NR>1 && !/^#/{exit} NR>1' "$0"; exit 2; }
SG="$(cd "$(dirname "$0")" && pwd)/sprite_gen.py"
NAME=$1; FILES=$2; PROMPT=$(cat "$3")
OUT=${OUT_DIR:-./sprites}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
LOGS=${LOG_DIR:-$OUT/logs}; mkdir -p "$LOGS"
CAT=${CATEGORY:-character}; TMO=${TIMEOUT_S:-180}; TRIES=${ATTEMPTS:-4}
FARGS=(); [ -n "$FILES" ] && FARGS=(--files "$FILES")
for attempt in $(seq 1 "$TRIES"); do
  SESS="${NAME}-$(date +%m%d%H%M%S)-$attempt"
  LOG="$LOGS/${NAME}_${attempt}.log"
  python3 "$SG" generate "$PROMPT" --output-dir "$OUT" --name "$NAME" --category "$CAT" --session "$SESS" ${FARGS[@]+"${FARGS[@]}"} > "$LOG" 2>&1 &
  PID=$!
  for _ in $(seq 1 $(( TMO / 5 ))); do perl -e 'select(undef,undef,undef,5)'; kill -0 $PID 2>/dev/null || break; done
  if kill -0 $PID 2>/dev/null; then
    kill $PID; echo "[$NAME] attempt $attempt: no result after ${TMO}s — retrying in a new conversation"
  elif grep -q '"success": true' "$LOG"; then
    P=$(python3 -c 'import json,sys; t=open(sys.argv[1]).read(); i=t.rfind("{\n  \"success\": true"); print(json.loads(t[i:])["entry"]["path"])' "$LOG")
    echo "OK $OUT/$P"
    python3 "$SG" end-session "$SESS" --output-dir "$OUT" >/dev/null 2>&1
    exit 0
  elif grep -q 'limit resets' "$LOG"; then
    python3 "$SG" end-session "$SESS" --output-dir "$OUT" >/dev/null 2>&1
    echo "LIMIT"; exit 3
  else
    echo "[$NAME] attempt $attempt failed: $(grep -vE '^\s*$' "$LOG" | tail -2 | tr '\n' ' ' | cut -c1-220)"
  fi
  python3 "$SG" end-session "$SESS" --output-dir "$OUT" >/dev/null 2>&1
done
exit 1
