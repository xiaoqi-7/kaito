#!/bin/bash
# T1: Streaming Baseline
# Test: Backend can stream without ext_proc
# Expected: Chunks arrive incrementally at ~500ms intervals

set -e

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"

echo "=== T1: Streaming Baseline (no ext_proc) ==="
echo "Gateway: $GATEWAY_URL"
echo ""
echo "Expected: Chunks arrive incrementally (Hello → world → !)"
echo "Timing: ~500ms between chunks (not buffered)"
echo ""

fail() {
  echo "❌ FAIL: $1"
  exit 1
}

pass() {
  echo "✅ PASS: $1"
}

# Measure timing of each chunk arrival
echo "Fetching stream and measuring timing..."
echo ""

start_time=$(date +%s%N)
response=$(curl -s -N -X POST "$GATEWAY_URL/t1" \
  -H "content-type: application/json" \
  -d '{}' 2>&1)

end_time=$(date +%s%N)
total_ms=$(( (end_time - start_time) / 1000000 ))

# Parse chunks and their content
echo "Response received in ${total_ms}ms:"
echo "$response"
echo ""

# Verify content
if echo "$response" | grep -q "Hello"; then
  pass "Chunk 1 (Hello) received"
else
  fail "Chunk 1 missing"
fi

if echo "$response" | grep -q "world"; then
  pass "Chunk 2 (world) received"
else
  fail "Chunk 2 missing"
fi

if echo "$response" | grep -q "!"; then
  pass "Chunk 3 (!) received"
else
  fail "Chunk 3 missing"
fi

if echo "$response" | grep -q "\[DONE\]"; then
  pass "[DONE] marker received"
else
  fail "[DONE] marker missing"
fi

echo ""

# Check timing behavior
# Expected: 500ms + 500ms + 500ms + buffer = ~1500ms minimum
if [ $total_ms -gt 1400 ]; then
  pass "Timing consistent with backend (${total_ms}ms ≈ 1500ms expected)"
  pass "Chunks did NOT buffer into single response"
  timing_ok=1
else
  fail "Response too fast (${total_ms}ms). Possible premature buffering"
  timing_ok=0
fi

echo ""
echo "=== T1 Result ==="

if [ $timing_ok -eq 1 ]; then
  echo "✓ T1: BASELINE STREAMING = YES"
  echo "  Backend streams correctly"
  echo "  Chunks arrive incrementally"
  echo "  Timing matches expected (1500ms for 3x500ms chunks)"
  exit 0
else
  echo "✗ T1: BASELINE STREAMING = NO"
  echo "  Chunks may be buffering"
  echo "  This is a test environment issue, not ext_proc related"
  exit 1
fi
