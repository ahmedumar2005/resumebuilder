#!/usr/bin/env bash
# Minimal smoke test for deployed app
# Usage: ./scripts/smoke_test.sh https://your-deploy-url.onrender.com

set -euo pipefail
URL=${1:-${SMOKE_URL:-http://localhost:5000}}

echo "Running smoke tests against: $URL"

echo "Checking /health"
status=$(curl -s -o /dev/null -w "%{http_code}" "$URL/health")
if [ "$status" -ne 200 ]; then
  echo "Health check failed: HTTP $status"
  exit 1
fi

echo "Fetching /"
status=$(curl -s -o /dev/null -w "%{http_code}" "$URL/")
if [ "$status" -ne 302 ] && [ "$status" -ne 200 ]; then
  echo "Root fetch failed: HTTP $status"
  exit 1
fi

# Check resume page redirect or presence
echo "Checking /resume (may redirect if no data)"
status=$(curl -s -o /dev/null -w "%{http_code}" "$URL/resume")
echo " /resume returned HTTP $status"

# Basic static asset check
echo "Checking static asset"
status=$(curl -s -o /dev/null -w "%{http_code}" "$URL/static/common.css")
if [ "$status" -ne 200 ]; then
  echo "Static asset fetch failed: HTTP $status"
  exit 1
fi

echo "Smoke tests passed against $URL"
exit 0
