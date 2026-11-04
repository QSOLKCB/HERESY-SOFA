#!/usr/bin/env bash
# A response-capture fragment. Tests provide only a synthetic loopback URL.
set -eu
: "${WEBHOOK_URL:?missing URL}"
: "${PAYLOAD_FILE:?missing payload file}"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
status=$(curl --silent --show-error \
    --dump-header "$work/headers" --output "$work/body" \
    --write-out '%{http_code}' \
    --header 'Content-Type: application/json' \
    --header 'User-Agent: SyntheticCorrectnessFixture/1.0' \
    --data-binary "@$PAYLOAD_FILE" "$WEBHOOK_URL")
# Response body and headers are separate from the numeric status. Do not log raw body.
case "$status" in
    2??) action=success ;;
    429) action=rate_limit ;;
    403|404) action=investigate ;;
    *) action=investigate ;;
esac
printf 'STATUS=%s\nACTION=%s\n' "$status" "$action"
