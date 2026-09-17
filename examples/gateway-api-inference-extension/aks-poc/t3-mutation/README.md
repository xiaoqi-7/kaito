# T3: Streaming Mutation

**Question:** Can ext_proc mutate streaming chunks AND maintain streaming?

**Mutation:** hello → hello [GATEWAY_TEST]

**Setup:**
- Backend: Same SSE stream
- ext_proc: Find "hello", append " [GATEWAY_TEST]"
- Expected: Modified content + still incremental

**PASS if:**
✅ "hello" becomes "hello [GATEWAY_TEST]"
✅ SSE JSON remains valid
✅ Other chunks unchanged
✅ Timing still ~1500ms (NOT buffered)

**Key insight:**
If T3=YES, streaming mutation is feasible. BodyMutation API works with FULL_DUPLEX_STREAMED.

## Deploy

```bash
kubectl apply -f backend.yaml
kubectl apply -f ext_proc.yaml
./test.sh
```

**Answer: MUTATION = YES/NO**
