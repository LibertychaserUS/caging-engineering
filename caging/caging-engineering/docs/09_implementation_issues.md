# Implementation Issues

This document lists practical implementation challenges.

## 1. State tracking

The system must track task state without exploding context length.

Possible solution:

```text
short working memory
structured state files
compressed history
accepted path summaries
failed path index
```

## 2. Tool routing

The agent must learn when to use tools rather than reasoning in natural language.

Potential issue:

```text
overuse of tools wastes time
underuse of tools increases hallucination
wrong tool selection creates false confidence
```

## 3. Verifier selection

Different tasks require different verifiers.

The system needs a verifier routing policy:

```text
code → tests / type checker / linter
math → calculator / proof checker
data → schema / consistency validator
text → rubric / citation / style validator
security → scanner / policy checker
```

## 4. Memory write policy

The agent should not write everything into long-term memory.

Suggested rule:

```text
Only verified conclusions and compressed failure records should be promoted.
```

## 5. Authority conflict resolution

Knowledge sources may conflict.

The system needs an authority ranking.

Example pattern:

```text
current runtime evidence
> locked project configuration
> source code
> official docs for the exact version
> project notes
> external blog posts
> model prior
```

## 6. Cage expansion

A cage that is too small may make the task impossible.

Implementation should support:

```text
blocked-goal detection
minimal expansion request
risk statement
human approval
expanded scope logging
```

## 7. Semantic bypass detection

Rules must apply to effects, not merely action names.

Example:

```text
Do not modify tests.
```

Bypasses may include:

```text
skip tests
change test runner config
modify test helper
clear test contents
alter expected output indirectly
```

## 8. External hard boundaries

Some boundaries should remain outside the model.

Examples:

```text
permission system
audit log
verifier execution
protected files
release gates
human approval checkpoints
```

## 9. Context and token budget

The system should avoid sending the full memory repository into the model every time.

Possible solution:

```text
retrieve only current task state
retrieve accepted path summaries
retrieve relevant failed path index
retrieve authoritative snippets
keep raw logs outside context
```

## 10. Evaluation harness

A minimal evaluation harness should compare:

```text
baseline agent without cage
agent with specification cage only
agent with specification + memory cage
agent with full caging + verifier layer
```

Possible metrics:

```text
success rate
verification pass rate
unsafe action attempts
irrelevant action count
repeat failure count
memory pollution rate
total cost
human correction time
```
