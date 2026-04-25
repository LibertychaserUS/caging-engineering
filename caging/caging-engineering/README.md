# Caging Engineering

**Caging Engineering** is a reachability-oriented framework for reliable AI agent systems.

It treats an AI agent not as a single prompt-driven model, but as a full-stack cognitive architecture composed of task specification, knowledge access, memory middleware, action permissions, external verification, path pruning, and reachability control.

Core principle:

> **Keep goals reachable, make unsafe states unreachable, and prune invalid paths after verification.**

## Why this repository exists

Current AI agent systems are often described through prompts, tools, harnesses, guardrails, memory, or retrieval. These concepts are useful, but they do not fully capture the deeper engineering problem:

> How do we design the agent's reachable action space so that the target remains achievable while unsafe, irrelevant, or unverifiable states become unreachable or low-priority?

Caging Engineering proposes that reliable agents require not only better models, but also structured task spaces, explicit boundaries, verification mechanisms, memory discipline, and controlled knowledge access.

## Core idea

Given an initial agent state `s0`, a goal region `G`, an unsafe region `U`, and a cage `C`, the cage should shape the reachable region of the agent.

A good cage should satisfy two basic conditions:

```text
Goal reachability:      R_C(s0) intersects G
Unsafe non-reachability: R_C(s0) does not intersect U
```

In plain language:

```text
The agent must still be able to complete the task.
The agent must not be able to reach dangerous or invalid states.
```

This is not just restriction. It is navigation design.

## Core modules

Caging Engineering can be decomposed into several interacting cages:

1. **Specification Cage** — turns an ill-defined task into a well-defined task.
2. **Knowledge Cage** — controls what sources the agent can access, cite, trust, and use.
3. **Memory Cage** — separates working memory, project memory, accepted paths, failed paths, dormant ideas, and model-memory candidates.
4. **Action Cage** — controls tools, permissions, commands, edits, and executable actions.
5. **Verification Cage** — ensures outputs are checked by external, executable, or auditable validators.
6. **Convergence Cage** — prunes failed or irrelevant paths after success and preserves only useful traces.
7. **Parametric Memory Cage** — governs what knowledge may eventually be written into model-level memory or specialized knowledge models.
8. **Meta-Cage** — protects the cage itself from being silently modified by the agent.

## How this differs from related ideas

| Concept | Main role | Limitation addressed by Caging Engineering |
|---|---|---|
| Prompt engineering | Shapes model input | Does not define reachable state space or hard verification |
| Harness engineering | Connects model to tools and environment | Often focuses on apparatus, not reachability topology |
| Guardrails | Blocks certain outputs or actions | Usually local and reactive, not a full task-space design |
| Sandbox | Isolates execution environment | Does not guarantee goal reachability |
| RAG | Retrieves external information | Does not by itself define trust, memory, or verification policy |
| Agent frameworks | Orchestrate tools and steps | Often lack explicit cage integrity and path pruning |

## Repository status

This repository is an early public concept archive and research scaffold for **Caging Engineering v0.1.0**.

It publishes:

- core terminology;
- conceptual definitions;
- initial system architecture;
- an `.agent-template` directory for agentic task-space organization;
- open conceptual and implementation problems.

It does **not** publish private product implementations, private evaluation datasets, proprietary workflows, or application-specific verifier rules.

## Repository structure

```text
caging-engineering/
  README.md
  ROADMAP.md
  CITATION.cff
  LICENSE.md
  docs/
    00_manifesto.md
    01_core_definitions.md
    02_caging_taxonomy.md
    03_agentic_full_stack.md
    04_memory_middleware.md
    05_verifier_layer.md
    06_model_db_and_operator_graph.md
    07_research_trajectory.md
    08_open_questions.md
    09_implementation_issues.md
    10_appendix_suggestions.md
  figures/
    architecture_ascii.md
    operator_graph_ascii.md
  .agent-template/
    spec/
    knowledge/
    memory/
    action/
    verification/
    audit/
```

## Suggested citation

Please cite this work as:

```text
Zhang, Oliver. Caging Engineering: A Reachability-Oriented Framework for Reliable AI Agent Systems. Version 0.1.0, 2026.
```

See `CITATION.cff` for machine-readable citation metadata.
