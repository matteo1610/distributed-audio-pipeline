#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TOTAL_UPLOADS="${TOTAL_UPLOADS:-50}"
CONCURRENCY="${CONCURRENCY:-10}"
PATTERN="${PATTERN:-mixed}"
PASSWORD="${PASSWORD:-supersecret123}"
WAV_MIN_SECONDS="${WAV_MIN_SECONDS:-1}"
WAV_MAX_SECONDS="${WAV_MAX_SECONDS:-6}"
WAV_SAMPLE_RATE="${WAV_SAMPLE_RATE:-16000}"
WAV_CHANNELS="${WAV_CHANNELS:-1}"

if [[ "$TOTAL_UPLOADS" -lt 1 ]]; then
  echo "TOTAL_UPLOADS must be >= 1"
  exit 1
fi

if [[ "$CONCURRENCY" -lt 1 ]]; then
  echo "CONCURRENCY must be >= 1"
  exit 1
fi

if [[ "$WAV_MIN_SECONDS" -lt 1 ]]; then
  echo "WAV_MIN_SECONDS must be >= 1"
  exit 1
fi

if [[ "$WAV_MAX_SECONDS" -lt "$WAV_MIN_SECONDS" ]]; then
  echo "WAV_MAX_SECONDS must be >= WAV_MIN_SECONDS"
  exit 1
fi

if [[ "$WAV_CHANNELS" -lt 1 ]]; then
  echo "WAV_CHANNELS must be >= 1"
  exit 1
fi

if [[ "$PATTERN" != "mixed" && "$PATTERN" != "steady" && "$PATTERN" != "ramp" && "$PATTERN" != "burst" ]]; then
  echo "PATTERN must be one of: mixed, steady, ramp, burst"
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

generate_wav() {
  local output_path="$1"
  local duration_seconds="$2"
  local sample_rate="$3"
  local channels="$4"
  local tone_hz="$5"

  python3 - "$output_path" "$duration_seconds" "$sample_rate" "$channels" "$tone_hz" <<'PY'
import math
import struct
import sys
import wave

output_path = sys.argv[1]
duration_seconds = float(sys.argv[2])
sample_rate = int(sys.argv[3])
channels = int(sys.argv[4])
tone_hz = float(sys.argv[5])

frame_count = max(1, int(sample_rate * duration_seconds))
amplitude = 0.25

with wave.open(output_path, "wb") as wav_file:
    wav_file.setnchannels(channels)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)

    buffer = bytearray()
    for index in range(frame_count):
        sample = int(32767 * amplitude * math.sin(2 * math.pi * tone_hz * index / sample_rate))
        frame = struct.pack("<h", sample)
        buffer.extend(frame * channels)
        if len(buffer) >= 32768:
            wav_file.writeframes(buffer)
            buffer.clear()

    if buffer:
        wav_file.writeframes(buffer)
PY
}

profile_for_index() {
  local idx="$1"
  local bucket

  case "$PATTERN" in
    steady)
      printf '%s %s %s %s %s\n' 2 "$WAV_SAMPLE_RATE" "$WAV_CHANNELS" 500k 0
      ;;
    ramp)
      bucket=$(((idx - 1) * 3 / TOTAL_UPLOADS))
      case "$bucket" in
        0)
          printf '%s %s %s %s %s\n' "$WAV_MIN_SECONDS" 8000 1 1m 0
          ;;
        1)
          printf '%s %s %s %s %s\n' 3 12000 1 500k 1
          ;;
        *)
          printf '%s %s %s %s %s\n' "$WAV_MAX_SECONDS" "$WAV_SAMPLE_RATE" 2 180k 2
          ;;
      esac
      ;;
    burst)
      if [[ "$idx" -le $((TOTAL_UPLOADS * 2 / 10)) ]]; then
        printf '%s %s %s %s %s\n' "$WAV_MIN_SECONDS" 8000 1 1m 0
      elif [[ "$idx" -le $((TOTAL_UPLOADS * 8 / 10)) ]]; then
        printf '%s %s %s %s %s\n' "$WAV_MAX_SECONDS" "$WAV_SAMPLE_RATE" 2 180k 0
      else
        printf '%s %s %s %s %s\n' 2 12000 1 700k 2
      fi
      ;;
    mixed|*)
      bucket=$(((idx - 1) * 4 / TOTAL_UPLOADS))
      case "$bucket" in
        0)
          printf '%s %s %s %s %s\n' "$WAV_MIN_SECONDS" 8000 1 1m 0
          ;;
        1)
          printf '%s %s %s %s %s\n' 3 12000 1 500k 0
          ;;
        2)
          printf '%s %s %s %s %s\n' "$WAV_MAX_SECONDS" "$WAV_SAMPLE_RATE" 2 180k 1
          ;;
        *)
          printf '%s %s %s %s %s\n' 2 8000 2 700k 2
          ;;
      esac
      ;;
  esac
}

run_one() {
  local idx="$1"
  local payload_path="$WORKDIR/upload-${idx}.wav"
  local profile
  local duration_seconds
  local sample_rate
  local channels
  local rate_limit
  local pre_sleep
  local tone_hz
  local code

  profile="$(profile_for_index "$idx")"
  read -r duration_seconds sample_rate channels rate_limit pre_sleep <<< "$profile"
  tone_hz="$((220 + (idx * 37) % 660))"

  if [[ "$pre_sleep" -gt 0 ]]; then
    sleep "$pre_sleep"
  fi

  generate_wav "$payload_path" "$duration_seconds" "$sample_rate" "$channels" "$tone_hz"

  code=$(curl -s --limit-rate "$rate_limit" -o "$WORKDIR/upload-${idx}.json" -w "%{http_code}" \
    -X POST "$BASE_URL/api/uploads" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@${payload_path};type=audio/wav")

  if [[ "$code" == "200" ]]; then
    echo "ok" >> "$WORKDIR/results.ok"
  else
    echo "fail:$code" >> "$WORKDIR/results.fail"
  fi
}

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

seq 1 "$TOTAL_UPLOADS" > "$WORKDIR/indices.txt"

export BASE_URL TOKEN WORKDIR PATTERN WAV_MIN_SECONDS WAV_MAX_SECONDS WAV_SAMPLE_RATE WAV_CHANNELS TOTAL_UPLOADS
export -f generate_wav profile_for_index run_one

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
echo "pattern=$PATTERN"
echo "ok=$OK_COUNT"
echo "failed=$FAIL_COUNT"
echo "duration_seconds=$DURATION"
echo "approx_success_rps=$RPS"
echo "tip=watch Grafana panels for uploads_total, jobs_completed_total, and upload latency while this runs."
echo "tip=try PATTERN=ramp for a rising curve or PATTERN=burst for a sharp spike."
