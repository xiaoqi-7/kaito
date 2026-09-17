# Streaming Passthrough Validation

**Purpose:** Validate that Envoy ext_proc filter can sit in the streaming response path without breaking streaming.

**Single Question:** Can Envoy ext_proc sit in the streaming response path without breaking streaming?

## What This Tests

1. ✅ Client doesn't wait for complete response (TTFB check)
2. ✅ Client receives SSE chunks progressively
3. ✅ ext_proc logs each chunk
4. ✅ Chunk order is preserved
5. ✅ Content is not lost or truncated
6. ✅ [DONE] marker arrives properly
7. ✅ No stream hangs or connection errors

## Configuration

**Mock Backend:**
- Returns OpenAI-compatible SSE
- Chunks: "hello ", "from ", "streaming ", "backend", " ✨"
- Properly formatted `data: {...}\n\n`
- Ends with `data: [DONE]\n\n`

**Envoy Filter:**
- `response_body_mode: FULL_DUPLEX_STREAMED` (not BUFFERED)
- Processes each chunk as it arrives
- Does NOT buffer complete response

**Ext_proc Server:**
- Minimal: only log chunks, pass through unchanged
- `FULL_DUPLEX_STREAMED` mode
- No modification, no blocking

## Deployment

```bash
# Deploy mock SSE backend
kubectl apply -f mock-sse-backend.yaml

# Deploy streaming ext_proc service
kubectl apply -f deployment.yaml

# Deploy EnvoyFilter
kubectl apply -f envoyfilter.yaml

# Deploy HTTPRoute
kubectl apply -f mock-route.yaml
```

## Test

```bash
chmod +x test-streaming.sh

# Run validation (requires deployed gateway + services)
GATEWAY_URL=http://localhost:8080 ./test-streaming.sh
```

**Expected output:**
```
✅ PASS: SSE response received
✅ PASS: [DONE] marker present
✅ PASS: First byte received in Xms
✅ PASS: Chunk order preserved
✅ PASS: Ext_proc received and logged N chunks
✅ PASS: No connection errors

Conclusion: Envoy ext_proc CAN sit in streaming response path
```

## Result Interpretation

**If all 7 checks pass:**
```
✅ Blocker cleared. Proceed to L2 (streaming + guardrails)
```

**If any check fails:**
```
❌ Blocker found. Cannot do streaming guardrails at gateway level.
   May need alternative approach (in-process filtering, sidecar, etc.)
```

## Files

- `mock-sse-backend.yaml` - Python server returning OpenAI SSE
- `envoyfilter.yaml` - FULL_DUPLEX_STREAMED ext_proc filter
- `deployment.yaml` - ext_proc passthrough service
- `mock-route.yaml` - HTTPRoute to mock backend
- `test-streaming.sh` - Validation script
