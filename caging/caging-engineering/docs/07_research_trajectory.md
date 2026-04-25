# Research Trajectory

This document records the conceptual path that led to Caging Engineering v0.1.0.

## 1. Hand degrees of freedom

The discussion began with the idea that a human hand cannot be described only by the number of degrees of freedom.

A hand has:

```text
multiple joint variables
continuous angle ranges
coupled motion
soft tissue deformation
tactile feedback
force constraints
```

This led to the notion of a high-dimensional continuous action or configuration space.

## 2. From configuration space to task feasibility

A more useful question emerged:

> Given a goal, can this hand complete the action?

This shifted the focus from motion capacity to task-oriented feasibility.

Relevant ideas:

```text
configuration space
action feasibility
manipulation feasibility
goal-oriented dexterity
```

## 3. From task feasibility to reachability

The central static formulation became:

```text
The task is feasible if the goal region intersects the reachable region.
```

This reframed action as a reachability problem.

Instead of asking only how to perform a process dynamically, the static view asks:

```text
Is the target located inside the reachable structure of the system?
```

## 4. Topology and locking

The idea of objects being trapped, locked, or impossible to remove led to a topological interpretation.

Key insight:

```text
An object is locked if its current feasible connected region does not connect to the escape region.
```

This connected the discussion to robotics-inspired notions such as caging, form closure, and force closure.

## 5. From robotics caging to agent caging

The term **caging** was then generalized from robotics to AI agents.

In robotics:

```text
Caging restricts an object's escape paths.
```

In agent systems:

```text
Caging restricts the agent's reachable task space.
```

This produced the idea of **Caging Engineering**.

## 6. From harness engineering to caging engineering

Harness engineering connects a model to tools and external systems.

Caging Engineering goes deeper:

```text
Harness connects the agent to the world.
Caging shapes what parts of the world the agent can reach.
```

The focus shifted from tool attachment to reachable-space design.

## 7. Agentic coding as navigation

Agentic coding was interpreted as a navigation problem:

```text
current project state
→ actions
→ new state
→ verification
→ repair
→ goal state
```

This made reachability, path cost, verification, and path pruning central.

## 8. Knowledge and memory reachability

The discussion then expanded from action reachability to knowledge reachability.

An agent may fail not because it cannot act, but because it cannot access the right knowledge.

This led to:

```text
Knowledge Cage
Memory Cage
Caged Memory Middleware
```

## 9. Model-as-Database

The idea then moved beyond external DBs.

Instead of only giving the model a database, one can imagine specialized models acting as knowledge stores.

This produced:

```text
Parametric Knowledge Model
Model-as-Database
Parametric Memory Cage
```

## 10. Agentic full stack and cognitive operators

Finally, the agent was reframed as a full-stack architecture that may later be compressed into trainable cognitive operators.

The final conceptual direction:

```text
Agentic full-stack architecture
→ Cognitive operator graph
→ System-to-model distillation
→ Caged hybrid agentic architecture
```

## 11. Current summary

Caging Engineering now refers to:

> A reachability-oriented engineering framework for AI agents that designs task spaces where goals remain reachable, unsafe states become unreachable, knowledge and memory are controlled, verification is externalized, and invalid paths are pruned after success.
