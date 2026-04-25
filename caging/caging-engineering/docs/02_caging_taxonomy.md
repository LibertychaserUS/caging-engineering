# Caging Taxonomy

This document describes the main types of cages in Caging Engineering.

## 1. Specification Cage

The Specification Cage defines the task.

It converts vague intent into a structured task object:

```text
Goal
Initial state
Success predicate
Constraints
Allowed actions
Forbidden actions
Knowledge requirements
Verification method
Cost function
Stop condition
```

Without a Specification Cage, reachability is not computable because the goal region is unclear.

## 2. Knowledge Cage

The Knowledge Cage governs what the agent can know, trust, cite, and use.

It must handle:

```text
source ranking
provenance
version conflicts
scope
freshness
authority conflict resolution
untrusted sources
```

A Knowledge Cage is not simply retrieval. It is retrieval plus trust control.

## 3. Memory Cage

The Memory Cage governs internal memory organization.

It should prevent:

```text
temporary thoughts becoming long-term facts
failed paths polluting main memory
old knowledge overriding current truth
unverified assumptions being promoted
```

Recommended memory classes:

```text
Working memory
Task memory
Project memory
Accepted paths
Failed path index
Dormant ideas
Model memory candidates
```

## 4. Action Cage

The Action Cage governs what the agent may execute.

It includes:

```text
file access
command access
network access
tool access
edit scope
write permissions
approval requirements
runtime limitations
```

An Action Cage should allow necessary actions while blocking dangerous or irrelevant actions.

## 5. Verification Cage

The Verification Cage governs how the agent checks correctness.

It prevents narrative completion, where the agent says a task is done without external validation.

Examples:

```text
unit tests
integration tests
linters
type checkers
schemas
format validators
calculators
external APIs
human approval
```

## 6. Convergence Cage

The Convergence Cage prevents endless expansion after a valid path has been found.

It enforces:

```text
accepted path preservation
failed path compression
dormant idea archiving
noise removal
stop condition enforcement
```

This is important because agents often fail not only by being wrong, but also by failing to stop.

## 7. Parametric Memory Cage

The Parametric Memory Cage governs writes into model-level memory.

A safe memory promotion pipeline should look like:

```text
Working memory
→ Task memory
→ Accepted path
→ Project memory
→ Repeated verified pattern
→ Model memory candidate
→ Parametric memory update
```

The base model or frozen core should not be casually modified by task-local information.

## 8. Meta-Cage

The Meta-Cage protects the cage itself.

It prevents the agent from silently modifying:

```text
verification rules
permission rules
task goals
authority rankings
memory promotion policies
forbidden action lists
```

Without a Meta-Cage, the agent may escape by rewriting the rules rather than solving the task.

## 9. Robotics-inspired closure types

Caging Engineering borrows structural inspiration from robotics, but it does not claim a direct identity with physical caging.

Robotics-inspired terms:

```text
Caging: restricts escape paths while allowing local movement.
Form closure: constrains local motion through geometry.
Force closure: resists disturbance through forces and contacts.
```

In agent systems, analogous mechanisms may appear as:

```text
Caging: restricts reachable task space.
Form-like closure: makes certain actions structurally impossible.
Force-like closure: uses verifiers, audits, and rollback to resist error propagation.
```

## 10. Closure coupling

Closure mechanisms are not isolated.

In physical systems, force may deform material and change geometry. In agent systems, an agent may attempt to bypass action restrictions by altering memory, verification, or task framing.

Therefore, Caging Engineering must consider **multi-domain closure coupling**:

```text
Specification constraints affect action reachability.
Knowledge trust affects planning reachability.
Memory writes affect future decision reachability.
Verifier integrity affects completion reachability.
Permission boundaries affect tool reachability.
```

A robust cage must protect not only actions, but also the structures that define which actions count as valid.
