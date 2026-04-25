# Core Definitions

This document fixes the initial terminology of Caging Engineering v0.1.0.

## 1. Agent

An **agent** is a system that receives a task, constructs or selects actions, uses tools or knowledge, updates state, and attempts to satisfy a goal under constraints.

An agent is not only a language model. It may include:

- a core reasoning model;
- planners;
- tools;
- memory systems;
- knowledge sources;
- external verifiers;
- audit logs;
- permission systems;
- routing policies.

## 2. State

A **state** is the relevant configuration of the agentic system at a given moment.

For an agentic coding or document task, state may include:

```text
task goal
known constraints
current hypothesis
files or sources inspected
current diff or output
available tools
memory entries
verification results
failed paths
accepted paths
permission level
```

A central challenge is deciding what belongs to the state model.

## 3. Goal Region

The **goal region** is the set of states in which the task is considered complete.

A task cannot support meaningful reachability analysis unless its goal region is sufficiently defined.

A vague task such as:

```text
Improve this project.
```

has an unclear goal region.

A better-defined task includes:

```text
Goal
Success predicate
Constraints
Allowed actions
Forbidden actions
Verification method
Stop condition
```

## 4. Unsafe Region

The **unsafe region** is the set of states that should not be reachable without explicit authorization.

Examples include:

```text
modifying protected tests
changing the task specification silently
using untrusted knowledge as authoritative
exposing secrets
deleting project files
polluting long-term memory
bypassing verification
claiming completion without validation
```

## 5. Reachable Region

The **reachable region** is the set of states an agent can reach from the initial state under a given cage.

Notation:

```text
R_C(s0)
```

Meaning:

```text
The set of states reachable from initial state s0 under cage C.
```

## 6. Cage

A **cage** is a set of constraints, permissions, tools, memory policies, verification rules, and routing rules that shape the reachable region of an agent.

A cage should not merely block actions. It should shape navigation.

## 7. Good Cage

A **good cage** should satisfy at least two conditions:

```text
Goal reachability:
R_C(s0) intersects G

Unsafe non-reachability:
R_C(s0) does not intersect U
```

In plain language:

```text
The agent can still reach the goal.
The agent cannot reach unsafe states.
```

## 8. Specification Cage

A **Specification Cage** turns an ill-defined task into a task with explicit goal, constraints, success predicate, and stop condition.

It answers:

```text
What exactly is the task?
What counts as success?
What is forbidden?
How will success be verified?
```

## 9. Knowledge Cage

A **Knowledge Cage** controls what the agent can access, cite, trust, and use as knowledge.

It includes:

```text
authority ranking
source provenance
version awareness
scope of applicability
conflict resolution
untrusted-source handling
```

## 10. Memory Cage

A **Memory Cage** controls how the agent writes, updates, reads, promotes, and forgets memory.

It separates:

```text
working memory
task memory
project memory
accepted paths
failed path index
dormant ideas
model memory candidates
```

## 11. Caged Memory Middleware

**Caged Memory Middleware** is a memory layer between the core model and long-term knowledge or parametric memory.

It behaves partly like Redis and partly like Git:

```text
Redis-like: fast working state, task-local cache
Git-like: versioned, auditable, branchable, reviewable memory history
```

It prevents raw, unverified thoughts from directly becoming long-term model memory.

## 12. Action Cage

An **Action Cage** controls what the agent can do.

It includes:

```text
allowed tools
forbidden tools
file permissions
command permissions
edit scope
network access
execution limits
human approval requirements
```

## 13. Verification Cage

A **Verification Cage** controls how completion is checked.

It requires external, auditable, or executable validation whenever possible.

Examples:

```text
tests
linters
type checkers
schemas
calculators
layout checkers
citation validators
human review
```

## 14. Cage Integrity

**Cage Integrity** means the agent cannot silently modify the cage itself.

Protected elements may include:

```text
task specification
verification rules
authority rules
memory promotion rules
forbidden actions
permission boundaries
external tests
```

## 15. Semantic Cage Integrity

**Semantic Cage Integrity** means the agent cannot bypass a rule through an equivalent indirect action.

Example:

```text
Rule: Do not delete tests.
Bypass: Clear test file contents, skip test execution, or modify test helpers to hide failures.
```

The rule must apply to the semantic effect, not merely the literal action name.

## 16. Cage Expansion Protocol

A **Cage Expansion Protocol** is used when the goal is not reachable under the current cage.

The agent should report:

```text
why the goal appears unreachable
which boundary blocks progress
what minimal expansion is needed
what risks the expansion introduces
whether human approval is required
```

## 17. Path Pruning

**Path Pruning** is the process of compressing the search history after success.

Accepted paths are preserved. Failed paths are compressed into a negative index. Dormant ideas are archived with low priority.

## 18. Accepted Path

An **Accepted Path** is a verified route from task specification to completion.

It should include:

```text
key steps
why they were selected
what evidence supported them
what verifier accepted them
what final state was reached
```

## 19. Failed Path Index

A **Failed Path Index** stores compressed records of invalid or unproductive paths.

It prevents repeated mistakes without polluting main memory with excessive detail.

## 20. Dormant Idea

A **Dormant Idea** is a non-adopted idea that is not currently part of the accepted path but may be useful in the future.

Dormant ideas should not pollute the active task state.

## 21. Parametric Knowledge Model

A **Parametric Knowledge Model** is a specialized model that acts as a model-level knowledge store.

It differs from a traditional external database because knowledge is represented in model parameters, adapters, or specialized neural memory modules.

## 22. Model-as-Database

**Model-as-Database** refers to treating a model as a queryable, partially editable, and potentially updatable knowledge structure.

It is not equivalent to SQL CRUD. Model memory is distributed, approximate, and difficult to delete precisely.

## 23. Parametric Memory Cage

A **Parametric Memory Cage** controls what may be written into model-level memory.

It should prevent unverified, temporary, or task-local information from becoming permanent model knowledge.

## 24. Cognitive Operator Graph

A **Cognitive Operator Graph** represents agent behavior as a composition of cognitive operators:

```text
Specification
Knowledge
Memory
Planning
Caging
Action
Verification
Pruning
```

The long-term vision is that some external agentic modules may become trainable cognitive operators, while hard verifiers and hard boundaries remain external.
