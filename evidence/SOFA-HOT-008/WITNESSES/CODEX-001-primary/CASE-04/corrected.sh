#!/usr/bin/env bash
set -u

URL=$1
PAYLOAD=$2
MAX_ATTEMPTS=${MAX_ATTEMPTS:-3}
NO_SLEEP=${NO_SLEEP:-0}
attempt=0
delays=""

while :; do
  attempt=$((attempt + 1))
  headers=$(mktemp)
  body=$(mktemp)
  status=$(curl --silent --show-error --output "$body" --dump-header "$headers" \
    --write-out '%{http_code}' --header 'User-Agent: CodexSyntheticFixture/1.0' \
    --header 'Accept: application/json' --header 'Content-Type: application/json' \
    --data-binary @"$PAYLOAD" "$URL")
  content_type=$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/{gsub("\r", ""); sub(/^[^:]*:[[:space:]]*/, ""); value=$0} END{print value}' "$headers")
  retry_after=$(awk 'BEGIN{IGNORECASE=1} /^Retry-After:/{gsub("\r", ""); sub(/^[^:]*:[[:space:]]*/, ""); value=$0} END{print value}' "$headers")
  rm -f "$headers" "$body"

  case "$status" in
    429|503)
      if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
        action=retry_exhausted
        break
      fi
      case "$retry_after" in
        ''|*[!0-9]*) delay=$((2 ** (attempt - 1))) ;;
        *) delay=$retry_after ;;
      esac
      if [ -n "$delays" ]; then delays="$delays,$delay"; else delays="$delay"; fi
      if [ "$NO_SLEEP" != 1 ]; then sleep "$delay"; fi
      ;;
    403) action=forbidden_no_retry_no_rotation; break ;;
    404) action=not_found_no_retry; break ;;
    2??) action=success; break ;;
    *) action=terminal_unhandled; break ;;
  esac
done

printf 'status=%s attempts=%s delays=%s action=%s content_type=%s\n' \
  "$status" "$attempt" "$delays" "$action" "$content_type"
