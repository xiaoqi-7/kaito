# T1: Streaming Baseline

**Purpose:** Prove the test environment itself can stream without any ext_proc.

**What this does:**
- Backend returns SSE with 500ms delay between chunks
- No ext_proc involved
- Measures if chunks arrive incrementally or get buffered

**Expected behavior:**
```
0.0s  "Hello"
0.5s  "world"  
1.0s  "!"
1.5s  [DONE]
```

**PASS Criteria:**
- All chunks received: ✅
- [DONE] marker: ✅
- Total time ~1500ms (not instant): ✅
- NOT buffered (didn't arrive as one block): ✅

**FAIL Criteria:**
- Any chunk missing: ❌
- Response arrives instantly (<200ms): ❌ (means buffered)
- This indicates test env itself can't stream

## Deploy

```bash
kubectl apply -f backend.yaml
kubectl wait --for=condition=ready pod -l app=t1-backend --timeout=60s

# Test
GATEWAY_URL=http://<gateway-ip> ./test.sh
```

## Answer

If PASS: `T1 = YES` → proceed to T2
If FAIL: `T1 = NO` → fix test environment first
