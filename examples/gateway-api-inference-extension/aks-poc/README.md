# AKS PoC: 4 Tier Streaming Validation

**Objective:** Validate Envoy ext_proc feasibility for streaming guardrails.

## The 4 Tests

| Test | Purpose | ext_proc Role | PASS Criteria |
|------|---------|---------------|---------------|
| **T1** | Baseline | None | Backend streams, chunks ~500ms apart |
| **T2** | Passthrough | Pass-through only | Streaming preserved (not buffered) |
| **T3** | Mutation | Modify content | Mutation + streaming both work |
| **T4** | Cross-chunk | Holdback buffer | Cross-chunk secrets don't leak |

## Quick Start

```bash
cd examples/gateway-api-inference-extension/aks-poc

# T1: No ext_proc
kubectl apply -f t1-baseline/backend.yaml
./t1-baseline/test.sh

# T2: ext_proc passthrough (if T1 = YES)
kubectl apply -f t2-passthrough/backend.yaml
kubectl apply -f t2-passthrough/ext_proc.yaml
./t2-passthrough/test.sh

# T3: ext_proc mutation (if T2 = YES)
kubectl apply -f t3-mutation/backend.yaml
kubectl apply -f t3-mutation/ext_proc.yaml
./t3-mutation/test.sh

# T4: Cross-chunk holdback (if T3 = YES)
kubectl apply -f t4-holdback/backend.yaml
kubectl apply -f t4-holdback/ext_proc.yaml
./t4-holdback/test.sh
```

## Expected Results

```
T1: YES ✅  (baseline confirmed)
  ↓
T2: YES ✅  (passthrough works)
  ↓
T3: YES ✅  (mutation works)
  ↓
T4: YES/NO  (holdback feasible/blocker)
```

Each test produces a single answer: YES / NO

## Files

- `t1-baseline/` - No ext_proc, pure streaming test
- `t2-passthrough/` - ext_proc passthrough validation
- `t3-mutation/` - Simple "hello" → "hello [GATEWAY_TEST]" mutation
- `t4-holdback/` - Cross-chunk secret protection validation
