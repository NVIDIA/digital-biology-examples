#!/bin/bash
# Test MSA endpoint directly with curl

MSA_ENDPOINT="${MSA_NIM_URL:-http://localhost:8000}"

echo "Testing MSA Endpoint: $MSA_ENDPOINT"
echo "======================================="

# Test 1: Check if endpoint is alive
echo -e "\n1. Testing endpoint health..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" $MSA_ENDPOINT/health || echo "Health check failed"

# Test 2: Get available databases
echo -e "\n2. Getting available databases..."
curl -s $MSA_ENDPOINT/databases | python -m json.tool || echo "Failed to get databases"

# Test 3: Simple search with ubiquitin (should always find homologs)
echo -e "\n3. Testing MSA search with ubiquitin..."
UBIQUITIN="MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"

curl -X POST $MSA_ENDPOINT/search \
  -H "Content-Type: application/json" \
  -d "{
    \"sequence\": \"$UBIQUITIN\",
    \"databases\": [\"Uniref30_2302\"],
    \"max_msa_sequences\": 10,
    \"e_value\": 10.0,
    \"output_alignment_formats\": [\"a3m\"]
  }" | python -m json.tool | head -50

echo -e "\n\nIf the above tests fail, check:"
echo "1. Is the MSA NIM service running?"
echo "2. Is the endpoint URL correct?"
echo "3. Are there firewall/network issues?"
echo "4. Check MSA NIM logs for errors"
