# Caged Memory Middleware

## 1. Why a memory middleware is needed

Future agent systems may include:

```text
Core reasoning model
Parametric knowledge model
External knowledge sources
Working memory
Project memory
Verification logs
```

The core model should not directly write into the parametric knowledge model or authoritative knowledge sources.

A middle layer is needed to buffer, audit, version, prune, and promote memory.

## 2. Redis-like and Git-like properties

Caged Memory Middleware combines two ideas.

### Redis-like working memory

Fast, task-local, mutable state:

```text
current goal
current hypothesis
inspected files or sources
current plan
test results
runtime errors
next action
```

### Git-like memory repository

Versioned, auditable, reviewable memory:

```text
accepted paths
failed path index
project memory
dormant ideas
decision logs
model memory candidates
```

## 3. Memory levels

### Level 0: Authoritative sources

Examples:

```text
official specifications
project contracts
source code
locked tests
schemas
formal requirements
```

Recommended permission:

```text
Read-only or externally governed.
```

### Level 1: Project memory

Stable project-level knowledge:

```text
architecture notes
known constraints
known fragile areas
historical decisions
common commands
```

Recommended permission:

```text
Append-only or proposal-based update.
```

### Level 2: Task memory

Current task state:

```text
hypotheses
attempts
observations
current errors
temporary plans
```

Recommended permission:

```text
Writable and resettable.
```

### Level 3: Accepted path memory

Verified successful paths:

```text
what worked
why it worked
what verifier accepted it
what constraints were preserved
```

Recommended permission:

```text
Append with verification evidence.
```

### Level 4: Failed path index

Compressed failed paths:

```text
what did not work
why it failed
what should not be repeated
```

Recommended permission:

```text
Append compressed entries.
```

### Level 5: Dormant ideas

Ideas not adopted for the current task but potentially useful later.

Recommended permission:

```text
Archive, low-priority retrieval.
```

### Level 6: Model memory candidates

Repeated, verified patterns that may be candidates for parametric memory updates.

Recommended permission:

```text
Human or high-trust review before promotion.
```

## 4. Memory promotion chain

A safe promotion chain:

```text
Raw thought
→ Task memory
→ Verified observation
→ Accepted path
→ Project memory
→ Repeated verified pattern
→ Model memory candidate
→ Parametric knowledge update
```

The key rule:

> Temporary task-local information must not directly become permanent model memory.

## 5. Path pruning

After successful completion:

```text
Accepted path enters main memory.
Failed paths enter compressed negative memory.
Dormant ideas enter low-priority archive.
Noise is removed.
```

This prevents agents from carrying an entire exploration forest into future tasks.

## 6. Memory integrity risks

Potential failures:

```text
wrong facts promoted
old knowledge kept forever
failed paths forgotten and repeated
temporary assumptions treated as truth
model memory polluted
source provenance lost
```

Memory Caging exists to prevent these failures.
