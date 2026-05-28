#!/bin/bash
# Deletes all custom FHIR resources loaded into Snowstorm via load-package.
# SNOMED CT content (concept/description/relationship/member indices) is NOT affected.
#
# Usage: ./clear_fhir_resources.sh [elasticsearch_url]
#   Default elasticsearch_url: http://localhost:9200

ES=${1:-http://localhost:9200}

INDICES=(
  fhir-concept-map
  fhir-map-element
  fhir-value-set
  fhir-concept
  fhir-codesystem-version
  fhir-structure-definition
)

echo "Clearing custom FHIR resources from Snowstorm Elasticsearch at $ES"
echo ""

for index in "${INDICES[@]}"; do
  count=$(curl -s "$ES/$index/_count" | python3 -c "import sys,json; print(json.load(sys.stdin).get('count','?'))" 2>/dev/null)
  if [ "$count" = "0" ] || [ "$count" = "?" ]; then
    echo "  $index — skipped (empty or not found)"
    continue
  fi
  echo -n "  $index ($count docs) — deleting... "
  result=$(curl -s -X DELETE "$ES/$index" | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if d.get('acknowledged') else d)" 2>/dev/null)
  echo "$result"
done

echo ""
echo "Restarting Snowstorm to recreate empty indices..."
docker compose restart snowstorm
echo "Done."
