# Caging Engineering Manifesto

## 1. From prompt-driven agents to reachability-designed agents

The next stage of AI agent engineering should not be understood as simply writing better prompts or connecting more tools.

A reliable agent is not merely a model that can generate actions. It is a system whose reachable state space has been engineered.

The central question is:

> Under the current task, tools, knowledge, memory, permissions, and verification mechanisms, what states can the agent reach?

Caging Engineering begins from the claim that reliability is not only a property of the model. Reliability is a property of the **agentic system**.

## 2. Core principle

> Keep goals reachable, make unsafe states unreachable, and prune invalid paths after verification.

This principle has three parts:

1. **Goal reachability** — the cage must not overconstrain the agent so much that the task becomes impossible.
2. **Unsafe non-reachability** — dangerous, invalid, or unverifiable states should be made unreachable or require explicit escalation.
3. **Path convergence** — after a valid path is found, the system should preserve the accepted path and compress or demote failed and unused paths.

## 3. Caging is not mere restriction

A cage is not just a wall. A good cage is also a map.

It prevents escape into unsafe regions, but it also shapes the task space so that the agent can navigate toward the goal with lower uncertainty and lower cost.

Therefore:

```text
Bad cage: blocks everything.
Weak cage: lets the agent wander anywhere.
Good cage: preserves goal reachability while removing unsafe or invalid routes.
```

## 4. Agents as cognitive full-stack systems

An agentic system resembles a full-stack architecture:

```text
Task input
→ Specification layer
→ Core reasoning model
→ Planner / router
→ Memory middleware
→ Knowledge model / sources
→ Tool and action layer
→ External verifier layer
→ Path pruning and memory consolidation
→ Auditable output
```

The model is only one component. The system also needs:

- task specification;
- knowledge governance;
- memory middleware;
- action boundaries;
- external verification;
- audit trails;
- convergence mechanisms;
- cage integrity.

## 5. Why verification must be external

An agent should not rely only on self-reflection to judge correctness.

For many tasks, correctness is better determined by external tools:

```text
code → tests / type checker / linter
math → calculator / CAS / proof checker
documents → schema / layout / citation validator
data → parser / constraints / consistency checks
```

The model should learn when to call tools, when to verify, when to repair, and when to stop.

## 6. From external architecture to cognitive operators

In early systems, modules such as specification, memory, planning, verification, and caging may exist as explicit external components.

Over time, some of these modules can be converted into trainable cognitive operators:

```text
Specification Operator
Knowledge Operator
Memory Operator
Planning Operator
Caging Operator
Action Operator
Verification Operator
Pruning Operator
```

However, hard boundaries, audit logs, external verifiers, and permission systems should not be fully internalized into the model. Soft capabilities can be learned; hard safety and verification boundaries should remain externally enforceable.

## 7. The long-term vision

Caging Engineering aims to support reliable agents that are:

- goal-directed;
- bounded;
- auditable;
- memory-aware;
- verification-driven;
- able to learn from accepted and failed paths;
- able to request cage expansion when the current cage makes the goal unreachable.

The final goal is not a more verbose agent. The final goal is a more navigable task space.
