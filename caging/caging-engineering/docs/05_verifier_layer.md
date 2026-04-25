# Verifier Layer

## 1. Why external verification matters

An AI agent should not rely only on self-reflection to determine correctness.

Self-reflection remains inside the language model's own generative space. Many errors require external feedback.

Examples:

```text
Generated code should be tested.
Generated math should be calculated or checked.
Generated structured data should be schema-validated.
Generated documents should be layout-validated.
Generated claims should be source-checked.
```

## 2. Verifier Layer

A **Verifier Layer** is a set of external tools, programs, rules, tests, or human review processes that judge whether an output satisfies the task specification.

It turns vague confidence into auditable feedback.

## 3. Generate-Verify-Repair loop

Recommended execution pattern:

```text
Generate candidate
→ Verify externally
→ If failed, repair with evidence
→ Verify again
→ Commit only after passing
```

This is superior to:

```text
Generate candidate
→ Claim completion
```

## 4. Verification routing

The agent should learn when to call which verifier.

A **Verification Routing Operator** decides:

```text
Does this output require external validation?
Which verifier should be used?
Is the verifier result sufficient?
Should the agent repair, escalate, or stop?
```

## 5. Types of verifiers

Possible verifiers include:

```text
unit tests
integration tests
linters
type checkers
build systems
schema validators
calculators
symbolic algebra systems
citation checkers
layout checkers
security scanners
human review
```

## 6. Verifier integrity

The agent must not silently modify verifiers to make its output pass.

Protected items may include:

```text
tests
schemas
rubrics
checklists
permission policies
authority rankings
success predicates
```

## 7. Token efficiency

External verification can save tokens.

Instead of spending long reasoning chains on uncertain calculations, formatting, or execution predictions, the agent can call a deterministic tool.

This reduces:

```text
hallucination
arithmetic error
formatting error
false confidence
unnecessary explanation
```

## 8. Verifier as a cage component

Verification is not merely a final step. It shapes the agent's reachable space.

If a path cannot pass verification, it should be pruned.

Therefore:

```text
Verifiers define which regions count as completed states.
```
