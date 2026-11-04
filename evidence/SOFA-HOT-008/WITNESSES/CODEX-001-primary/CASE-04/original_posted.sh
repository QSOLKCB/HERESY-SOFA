#!/usr/bin/env bash
WEBHOOK=$(grep '^WEBHOOK_URL=' ~/.hermes/discord.env | cut -d= -f2)
RESPONSE=$(curl -s -w "\n%{http_code}\n" -H "User-Agent: MilosCronBot/1.0" $WEBHOOK -d @payload.json | tr '\n' ' ')
STATUS=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
if [ "$STATUS" -eq 403 ]; then
  echo "403 detected – regenerating webhook"
  # Regenerate webhook via Discord API (API URL omitted for policy compliance)
  # Store the new URL back to ~/.hermes/discord.env
  # Example: echo "WEBHOOK_URL=$NEW_URL" > ~/.hermes/discord.env
fi
