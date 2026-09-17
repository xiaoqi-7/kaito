# T2: Streaming Passthrough

**Question:** Can ext_proc preserve streaming when just passing through?

**Setup:**
- Backend: Same SSE + 500ms chunks as T1
- ext_proc: FULL_DUPLEX_STREAMED passthrough (no modification)
- Expected: Same timing as T1 (~1500ms total)

**PASS if:**
✅ Content matches T1 exactly
✅ Total time ~1500ms (NOT instant)
✅ Chunks still incremental
❌ NOT buffered into single response

**Key insight:**
If T1=YES but T2=NO (instant response), blocker is Envoy buffering in ext_proc path.

## Deploy

```bash
kubectl apply -f backend.yaml
kubectl apply -f ext_proc.yaml
./test.sh
```

**Answer: PASSTHROUGH = YES/NO**
