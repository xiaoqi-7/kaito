# Streaming Mutation Test

**Purpose:** Validate that ext_proc can mutate streaming chunks without breaking the stream.

**Single Question:** Can ext_proc mutate streaming content before releasing it downstream?

## What This Tests

**Mutation:** foo → ***

**Verification:**
1. ✅ foo chunk is successfully mutated to ***
2. ✅ hello and world chunks are unchanged
3. ✅ Chunk order preserved (hello → *** → world)
4. ✅ Stream still flows (not buffered)
5. ✅ Content-Length/framing handled correctly

## Setup

**Mock Backend Output:**
```
hello
foo
world
```

**Ext_proc Action:**
```python
if b'foo' in body:
    body = body.replace(b'foo', b'***')
    yield BodyMutation(body=body)
```

## Deployment

```bash
cd examples/gateway-api-inference-extension/streaming-mutation

# Build (if needed)
docker build -t yiqi685/llm-guard-ext-proc:streaming .
docker push yiqi685/llm-guard-ext-proc:streaming

# Deploy
kubectl apply -f mock-backend.yaml
kubectl apply -f deployment.yaml
kubectl apply -f envoyfilter.yaml
kubectl apply -f mock-route.yaml

# Wait for pods
kubectl wait --for=condition=ready pod -l app=mock-simple-backend --timeout=60s
kubectl wait --for=condition=ready pod -l app=streaming-mutation-ext-proc --timeout=60s

# Get Gateway URL
GATEWAY_IP=$(kubectl get svc -l gateway.networking.k8s.io/gateway-name=inference-gateway -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}')
GATEWAY_URL="http://$GATEWAY_IP"

# Test
chmod +x test-mutation.sh
GATEWAY_URL=$GATEWAY_URL ./test-mutation.sh
```

## Expected Output

```
✅ PASS: 'foo' was mutated to '***'
✅ PASS: Chunk 'hello' preserved
✅ PASS: Chunk 'world' preserved
✅ PASS: Chunk order preserved (hello → *** → world)
✅ PASS: Response streaming (not buffered)
✅ PASS: Ext_proc logged mutation

Conclusion: Envoy ext_proc CAN mutate streaming content
```

## If Test Fails

**If passthrough works but mutation fails:**
- Blocker is in Envoy's BodyMutation API support for FULL_DUPLEX_STREAMED
- May need to adjust how we send BodyMutation or use different processing_mode
- Suggests gateway-level streaming mutation may not be supported

**If streaming is lost after mutation:**
- Blocker is Content-Length/framing handling after mutation
- Envoy may not be recalculating headers properly
