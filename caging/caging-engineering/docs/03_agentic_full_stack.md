# Agentic Full-Stack Architecture

Caging Engineering treats an AI agent as a full-stack cognitive system.

## 1. Traditional full-stack analogy

A traditional software system may include:

```text
Frontend
API gateway
Backend services
Cache
Database
Workers
Logging
Monitoring
CI/CD
Permissions
```

An agentic system has analogous layers, but they operate over goals, knowledge, actions, verification, and memory.

## 2. Agentic full stack

```text
User task
→ Specification Cage
→ Core Reasoning Model
→ Planner / Router
→ Caged Memory Middleware
→ Knowledge Model / External Sources
→ Tool and Action Layer
→ External Verifier Layer
→ Path Pruning and Memory Consolidation
→ Auditable final output
```

## 3. Layer responsibilities

### User Task

The raw task from the user. It may be vague, incomplete, or contradictory.

### Specification Cage

Transforms the raw task into a well-defined task object.

### Core Reasoning Model

Acts as the cognitive core. It reasons, plans, compares options, and makes decisions.

### Planner / Router

Selects candidate paths, tools, experts, knowledge sources, and verification methods.

### Caged Memory Middleware

Maintains current state, task memory, project memory, accepted paths, failed paths, and dormant ideas.

### Knowledge Model / External Sources

Provides relevant knowledge, references, historical cases, and domain-specific information.

### Tool and Action Layer

Executes actions such as editing files, running commands, calling APIs, generating artifacts, or querying systems.

### External Verifier Layer

Checks whether outputs satisfy explicit criteria.

### Path Pruning and Memory Consolidation

After success, preserves accepted paths and compresses failed or unused paths.

## 4. Caging Layer as an overlay

The Caging Layer surrounds the full stack.

It controls:

```text
task definition
knowledge access
memory writes
action permissions
verification integrity
path pruning
cage expansion
semantic bypass prevention
```

## 5. Why this matters

A weak model inside a well-designed task space may complete tasks more reliably than a strong model in an unconstrained space.

Reliability comes from the system:

```text
model intelligence
+ task specification
+ knowledge access
+ memory discipline
+ action boundaries
+ verification
+ path pruning
```

Caging Engineering is the discipline of designing this combined reachable space.
