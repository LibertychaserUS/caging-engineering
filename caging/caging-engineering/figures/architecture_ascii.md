# Architecture Diagram

```text
                         ┌─────────────────────┐
                         │      User Task      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Specification Cage │
                         │  goal / constraints │
                         │  success predicate  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Core Reasoning Model│
                         │ planning / decision │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
     ┌────────────────┐    ┌───────────────────┐   ┌────────────────┐
     │ Planner/Router │    │ Caged Memory      │   │ Tool/Action    │
     │ path selection │    │ Middleware        │   │ Layer          │
     └───────┬────────┘    └─────────┬─────────┘   └───────┬────────┘
             │                       │                     │
             │                       ▼                     │
             │              ┌───────────────────┐          │
             │              │ Knowledge Model / │          │
             │              │ External Sources  │          │
             │              └─────────┬─────────┘          │
             │                        │                    │
             └────────────────────────┼────────────────────┘
                                      │
                                      ▼
                         ┌─────────────────────┐
                         │ External Verifier   │
                         │ tests / checks      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Path Pruning &      │
                         │ Memory Consolidation│
                         └─────────────────────┘
```

The Caging Layer surrounds the whole system and controls:

```text
specification boundaries
knowledge access
memory writes
action permissions
verifier integrity
path pruning
cage expansion
semantic bypass prevention
```
