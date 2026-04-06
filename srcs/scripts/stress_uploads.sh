#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TOTAL_UPLOADS="${TOTAL_UPLOADS:-50}"
CONCURRENCY="${CONCURRENCY:-10}"
PASSWORD="${PASSWORD:-supersecret123}"

if [[ "$TOTAL_UPLOADS" -lt 1 ]]; then
  echo "TOTAL_UPLOADS must be >= 1"
  exit 1
fi

if [[ "$CONCURRENCY" -lt 1 ]]; then
  echo "CONCURRENCY must be >= 1"
  exit 1
fi

USER_SUFFIX="$(date +%s)"
USERNAME="stress_${USER_SUFFIX}"
EMAIL="${USERNAME}@example.com"
WORKDIR="/tmp/distributed-audio-stress-${USER_SUFFIX}"
mkdir -p "$WORKDIR"

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

# Register once, login once, then reuse one token for parallel uploads.
REGISTER_CODE=$(curl -s -o "$WORKDIR/register.json" -w "%{http_code}" \
  -X POST "$BASE_URL/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USERNAME\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

if [[ "$REGISTER_CODE" != "201" ]]; then
  echo "Register failed: HTTP $REGISTER_CODE"
  cat "$WORKDIR/register.json"
  exit 1
fi

LOGIN_BODY=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data "username=$USERNAME&password=$PASSWORD")

TOKEN=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("access_token",""))' "$LOGIN_BODY")
if [[ -z "$TOKEN" ]]; then
  echo "Login failed"
  echo "$LOGIN_BODY"
  exit 1
fi

python3 - <<'PY'
import wave
with wave.open('/tmp/stress-sample.wav', 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(16000)
    w.writeframes(b'\x00\x00' * 16000)
PY

seq 1 "$TOTAL_UPLOADS" > "$WORKDIR/indices.txt"

run_one() {
  local idx="$1"
  local code
  code=$(curl -s -o "$WORKDIR/upload-${idx}.json" -w "%{http_code}" \
    -X POST "$BASE_URL/api/uploads" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/stress-sample.wav;type=audio/wav")

  if [[ "$code" == "200" ]]; then
    echo "ok" >> "$WORKDIR/results.ok"
  else
    echo "fail:$code" >> "$WORKDIR/results.fail"
  fi
}

export BASE_URL TOKEN WORKDIR
export -f run_one

START_TS=$(date +%s)
xargs -I{} -P "$CONCURRENCY" bash -lc 'run_one "$@"' _ {} < "$WORKDIR/indices.txt"
END_TS=$(date +%s)

OK_COUNT=0
FAIL_COUNT=0
if [[ -f "$WORKDIR/results.ok" ]]; then
  OK_COUNT=$(wc -l < "$WORKDIR/results.ok" | tr -d ' ')
fi
if [[ -f "$WORKDIR/results.fail" ]]; then
  FAIL_COUNT=$(wc -l < "$WORKDIR/results.fail" | tr -d ' ')
fi

DURATION=$((END_TS - START_TS))
if [[ "$DURATION" -eq 0 ]]; then
  DURATION=1
fi
RPS=$((OK_COUNT / DURATION))

echo "Stress test finished"
echo "user=$USERNAME"
echo "total_uploads=$TOTAL_UPLOADS"
echo "concurrency=$CONCURRENCY"
echo "ok=$OK_COUNT"
echo "failed=$FAIL_COUNT"
echo "duration_seconds=$DURATION"
echo "approx_success_rps=$RPS"

echo "Tip: watch Grafana panels for uploads_total, jobs_completed_total and upload latency while this runs."
