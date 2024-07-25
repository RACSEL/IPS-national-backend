if [ ! -f /status/script_executed ]; then
  echo "Waiting for Elasticsearch to be healthy..."
  sleep 30
  echo "Executing script..."
  echo "1. Setup backup repository"
  curl -X PUT "elasticsearch:9200/_snapshot/snowstorm_preload_server" -H 'Content-Type: application/json' -d'
{
  "type": "url",
  "settings": {
    "url": "https://storage.googleapis.com/snowstorm-preload/"
  }
}
' 
  echo "2. Delete existing data"
  curl -X DELETE elasticsearch:9200/_all
  echo "3. Download and restore data"
  curl -X POST "elasticsearch:9200/_snapshot/snowstorm_preload_server/snowstorm_10.3.1_spain_20240331/_restore?wait_for_completion=true" -H 'Content-Type: application/json' -d'
{
  "indices": "*",
  "ignore_unavailable": true
}
'
  echo "4. Saving status"
  echo "1" >> /status/script_executed
else
  echo "Initialization skipped"
fi