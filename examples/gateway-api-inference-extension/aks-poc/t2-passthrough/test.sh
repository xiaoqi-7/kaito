#!/bin/bash
set -e
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
echo "=== T2: Streaming Passthrough (ext_proc passthrough) ==="
echo "Testing: ext_proc receives chunks, returns unchanged"
echo ""

start=$(date +%s%N)
response=$(curl -s -N -X POST "$GATEWAY_URL/t2" -H "content-type: application/json" -d '{}' 2>&1)
end=$(date +%s%N)
total_ms=$(( (end - start) / 1000000 ))

echo "Response (${total_ms}ms):"
echo "$response"
echo ""

# Check content preserved
if echo "$response" | grep -q "Hello"; then
  echo "✅ Content preserved: Hello"
else
  echo "❌ Content lost"
  exit 1
fi

# Check timing (should be ~1500ms like T1, not instant)
if [ $total_ms -gt 1400 ]; then
  echo "✅ Timing preserved: ${total_ms}ms (~1500ms expected)"
  echo ""
  echo "✓ T2: PASSTHROUGH = YES"
  echo "  ext_proc did NOT buffer the stream"
  exit 0
else
  echo "❌ Response too fast: ${total_ms}ms"
  echo "  ext_proc may have buffered"
  echo ""
  echo "✗ T2: PASSTHROUGH = NO"
  exit 1
fi
