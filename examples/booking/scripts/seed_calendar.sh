#!/bin/bash
# Create calendar + slots for tomorrow
API_URL=${1:-http://localhost:8001}
DATE=$(date -v+1d +%Y-%m-%d)

CAL_ID=$(curl -s -X POST "$API_URL/calendars" \
  -H "Content-Type: application/json" \
  -d '{"name": "Dr. Smith", "type": "provider"}' | jq -r .id)

echo "Created calendar: $CAL_ID"

# 9am-5pm, 30min slots
for HOUR in 09 10 11 12 14 15 16; do
  for MIN in 00 30; do
    curl -s -X POST "$API_URL/calendars/$CAL_ID/slots" \
      -H "Content-Type: application/json" \
      -d "{\"start\": \"${DATE}T${HOUR}:${MIN}:00\", \"duration_min\": 30}" > /dev/null
    echo "  Created slot: ${HOUR}:${MIN}"
  done
done
echo "Done: 14 slots created"
