# Open Conceptual Questions

This document lists unresolved conceptual questions in Caging Engineering v0.1.0.

## 1. What exactly is the state space?

A rigorous theory requires a clear state model.

Open questions:

```text
What belongs to the agent state?
How do we represent memory state?
How do we represent knowledge access?
How do we represent verification status?
How do we represent tool permissions?
```

## 2. How should goal regions be defined?

Reachability requires a goal region.

For ill-defined tasks, the goal region may not exist.

Open questions:

```text
How can natural language tasks be transformed into success predicates?
When should the agent ask for clarification?
When can the agent infer missing constraints?
How do we avoid over-specification?
```

## 3. How should unsafe regions be defined?

Unsafe states may include obvious security violations, but also subtle states such as memory pollution or verifier manipulation.

Open questions:

```text
What counts as unsafe?
Who defines unsafe regions?
Can unsafe regions be task-dependent?
How can semantic bypasses be detected?
```

## 4. How can we measure reachability?

Reachability may be binary or graded.

Possible approaches:

```text
binary feasibility
success probability
cost-to-go
risk-adjusted reachability
verification-distance-to-go
knowledge availability score
```

## 5. How do we avoid over-caging?

A cage can be too restrictive.

Open questions:

```text
How can the agent detect that the current cage makes the goal unreachable?
How should cage expansion be requested?
What is the minimum safe expansion?
Who approves expansion?
```

## 6. How should path cost be defined?

The best path is not always the shortest path.

Possible cost components:

```text
time
tokens
risk
edit scope
verification cost
rollback difficulty
knowledge uncertainty
permission cost
long-term maintainability
```

## 7. How should memory be forgotten?

Memory accumulation may cause pollution.

Open questions:

```text
When should memory decay?
When should memory be deprecated?
How should old project facts be invalidated?
How should failed paths be compressed?
How should dormant ideas be recalled?
```

## 8. How should model-level memory be updated?

Parametric memory is powerful but risky.

Open questions:

```text
What qualifies as a model memory candidate?
How many times must a pattern be verified before promotion?
How can parametric memory be rolled back?
How can model unlearning be tested?
How can contamination be detected?
```

## 9. How can external verifiers be protected?

The agent may try to modify the verifier or route around it.

Open questions:

```text
Which verifiers are immutable?
Which verifiers are editable by proposal only?
How do we detect verifier bypass?
How do we audit verification history?
```

## 10. How do we prove this framework is useful?

A theory needs evaluation.

Possible evaluation targets:

```text
task success rate
unsafe action rate
unverified completion rate
number of irrelevant edits
failure repetition rate
memory pollution rate
average repair cycles
human correction time
```
