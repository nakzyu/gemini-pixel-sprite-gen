#!/bin/bash
# batch_gen.sh WORKDIR — run every job in WORKDIR/jobs.json: generate (gen_retry.sh) -> qc_frame -> snap_char.
#   WORKDIR/jobs.json        [{"name": "knight_idle", "files": "ref.png,liked_12x.png",
#                              "kind": "idle|action|swing", "monster": false, "idle": true}, ...]
#   WORKDIR/prompts/NAME.txt prompt per job
#   WORKDIR/snap/NAME.png    snapped result (written)
#   WORKDIR/results.tsv      NAME  RAW  QC  SNAP   (written; jobs already listed here are skipped,
#                            so re-running after an image limit resumes where it stopped)
# Humanoid idle jobs must carry 2 reference images (base ref + liked same-family sprite at 12x);
# with only one the face drifts to someone else's — such jobs are recorded as REFS1 and skipped.
# Stops the whole batch on Gemini's image-limit message.
# env: OUT_DIR (raw output, default WORKDIR/raw) + the gen_retry.sh env vars.
set -u
[ $# -ge 1 ] || { awk 'NR>1 && !/^#/{exit} NR>1' "$0"; exit 2; }
SC="$(cd "$(dirname "$0")" && pwd)"
W=$(cd "$1" && pwd); cd "$W" || exit 2
export OUT_DIR=${OUT_DIR:-$W/raw}; export LOG_DIR=${LOG_DIR:-$W/logs}
mkdir -p snap
python3 -c "import json; [print(j['name'], j['files'] or '-', j['kind'], int(j['monster']), int(j['idle'])) for j in json.load(open('jobs.json'))]" | while read -r NAME FILES KIND MON IDLE; do
  [ "$FILES" = - ] && FILES=""
  grep -q "^$NAME	" results.tsv 2>/dev/null && continue
  if [ "$IDLE" = 1 ] && [ "$MON" = 0 ] && [ "${FILES#*,}" = "$FILES" ]; then printf "%s\t-\tREFS1\tidle needs 2 refs\n" "$NAME" >> results.tsv; continue; fi
  OUT=$("$SC/gen_retry.sh" "$NAME" "$FILES" "prompts/$NAME.txt" | tail -1)
  case "$OUT" in LIMIT) echo "image limit reached — stopping (resume from $NAME later)"; break;; esac
  case "$OUT" in OK*) RAW=${OUT#OK };; *) printf "%s\t-\tGENFAIL\t-\n" "$NAME" >> results.tsv; continue;; esac
  Q=$(python3 "$SC/qc_frame.py" "$RAW" --kind "$KIND" 2>&1 | head -1 | awk '{print $1}')
  FL=(); [ "$MON" = 1 ] && FL+=(--monster); [ "$IDLE" = 1 ] && FL+=(--idle)
  S=$(python3 "$SC/snap_char.py" "$RAW" "snap/$NAME.png" "${FL[@]}" 2>&1 | tail -1 | grep -oE "char [0-9]+x[0-9]+" || echo "SNAPFAIL")
  printf "%s\t%s\t%s\t%s\n" "$NAME" "$RAW" "$Q" "$S" >> results.tsv
done
echo "done — $(wc -l < results.tsv 2>/dev/null || echo 0) rows in results.tsv"
