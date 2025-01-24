$response = Invoke-RestMethod `
  -Uri "http://193.164.4.35:9200/leaks/_search?pretty" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{
    "size": 0,
    "aggs": {
      "unique_file_names": {
        "composite": {
          "sources": [
            { "file_name": { "terms": { "field": "file_name" } } }
          ],
          "size": 1000
        }
      }
    }
  }'

# Process results and handle pagination
$results = @()
$results += $response.aggregations.unique_file_names.buckets.key.file_name

while ($response.aggregations.unique_file_names.after_key) {
    $response = Invoke-RestMethod `
      -Uri "http://193.164.4.35:9200/leaks/_search?pretty" `
      -Method POST `
      -Headers @{ "Content-Type" = "application/json" } `
      -Body (@{
        "size" = 0
        "aggs" = @{
          "unique_file_names" = @{
            "composite" = @{
              "sources" = @(@{ "file_name" = @{ "terms" = @{ "field" = "file_name" } } })
              "size" = 1000
              "after" = $response.aggregations.unique_file_names.after_key
            }
          }
        }
      } | ConvertTo-Json -Depth 10)

    $results += $response.aggregations.unique_file_names.buckets.key.file_name
}

# Print results
$results
