# T4: Cross-Chunk Holdback

**Question:** Can ext_proc protect secrets split across chunks?

**Attack scenario:**
```
Chunk 1: "My API key is sk-"
Chunk 2: "123456789"
```

**Expected behavior:**
- Chunk 1 arrives → hold (partial match on sk-[0-9]+)
- Chunk 2 arrives → combine + check
- Secret detected → redact both
- Client sees: "My API key is [REDACTED]"

**PASS if:**
✅ Secret NOT leaked (no "sk-123456789" in client response)
✅ Holdback buffer works
✅ Combines chunks correctly
✅ Zero leaked bytes

**Key insight:**
If T4=YES, streaming guardrail is architecturally sound.
If T4=NO (secret leaks), holdback semantics need rethinking.

## Deploy

```bash
kubectl apply -f backend.yaml
kubectl apply -f ext_proc.yaml
./test.sh
```

**Answer: CROSS_CHUNK = YES/NO**
