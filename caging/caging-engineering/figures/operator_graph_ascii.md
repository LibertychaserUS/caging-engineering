# Cognitive Operator Graph

```text
Task
 │
 ▼
[S] Specification Operator
 │   converts raw intent into structured task
 ▼
[K] Knowledge Operator
 │   retrieves and ranks relevant knowledge
 ▼
[M] Memory Operator
 │   loads task memory, accepted paths, failed paths
 ▼
[P] Planning Operator
 │   proposes low-risk candidate paths
 ▼
[C] Caging Operator
 │   checks reachable boundaries and permissions
 ▼
[A] Action Operator
 │   executes tool calls, edits, or artifact operations
 ▼
[V] Verification Operator
 │   validates output externally
 ▼
[Q] Pruning / Consolidation Operator
 │   preserves accepted paths and compresses failures
 ▼
Final Output + Updated Memory
```

Compact expression:

```text
Agent = Compose(S, K, M, P, C, A, V, Q)
```

Long-term direction:

```text
External agentic architecture
→ verified execution traces
→ cognitive operator training
→ system-to-model distillation
```
