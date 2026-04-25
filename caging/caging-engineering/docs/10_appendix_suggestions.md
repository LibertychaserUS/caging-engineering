# Appendix: Suggestions and Research Discipline

## 1. Keep the framework bounded

Caging Engineering should not become a term for everything in agent systems.

Recommended boundary:

> Caging Engineering studies how to design an agent's reachable space so that goals remain reachable, unsafe states become unreachable, and invalid paths are pruned after verification.

If a concept does not affect reachability, safety, verification, memory integrity, or path convergence, it should not be forced into the framework.

## 2. Avoid over-abstracting before prototyping

The theory is already broad enough for v0.1.

Recommended next step:

```text
Choose one narrow task domain.
Build a minimal caged agent template.
Measure whether it reduces failure and hallucination.
```

## 3. Prioritize verifier-first prototypes

The strongest near-term implementation path is not a fully autonomous agent.

It is a system where the model produces candidates and external tools verify them.

Recommended loop:

```text
Generate
→ Verify
→ Repair
→ Verify again
→ Commit
→ Prune paths
→ Consolidate memory
```

## 4. Do not overtrust model-level memory

Model-as-Database is powerful but dangerous.

Recommended principle:

```text
External repo memory first.
Parametric memory only after repeated verification.
Base model remains protected.
```

## 5. Publish concept, protect implementation

For public positioning:

```text
Publish terminology.
Publish high-level architecture.
Publish non-sensitive templates.
Publish open questions.
```

For private development:

```text
Keep evaluator datasets private.
Keep verifier rules private if commercially sensitive.
Keep automation workflows private.
Keep real user documents private.
Keep model-routing details private until stable.
```

## 6. Define a minimal public benchmark

A future benchmark could include:

```text
well-defined tasks
ill-defined tasks
missing-knowledge tasks
missing-verifier tasks
permission-limited tasks
memory-pollution tasks
semantic-bypass tasks
```

## 7. Suggested evaluation metrics

```text
Task success rate
Verifier pass rate
Unsafe action rate
Unverified completion rate
Repeat failure rate
Irrelevant action count
Memory pollution count
Cage expansion quality
Human correction time
```

## 8. Research posture

The current framework is best treated as a research scaffold, not a finished theory.

The next scientific step is not to add more concepts, but to operationalize the existing ones.

Recommended motto:

> Define less. Test more.
