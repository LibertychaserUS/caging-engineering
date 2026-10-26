# Related Work: Where Caging Engineering Sits

The fourth theory document. An honest account places the framework among its relatives rather than apart from them. The v0.1.0 `README.md` compares Caging Engineering with prompt engineering, harness engineering, guardrails, sandboxes, retrieval, and agent frameworks; those are its neighbours in current agent practice. This document adds the neighbours in theory, which are older, and the neighbours in the memory-governance literature, which are newer. For each lineage it states what is inherited and what is different. Bibliographic details are given to the level that is stable (authors, venue, year); exact page numbers belong in the paper's bibliography.

## 1. Supervisory control of discrete-event systems

**Lineage.** Ramadge and Wonham, *Supervisory control of a class of discrete event processes* (SIAM J. Control and Optimization, 1987) and *The control of discrete event systems* (Proc. IEEE, 1989), with the textbook treatment in Cassandras and Lafortune, *Introduction to Discrete Event Systems*. A plant generates a language of event sequences. A supervisor observes the plant and disables a subset of *controllable* events, so that the closed-loop language stays within a specification. The two central notions are **controllability** (the specification can be enforced by disabling only controllable events) and **non-blocking** (every closed-loop behaviour can still be extended to a *marked* state, i.e. a completed task).

**What is inherited.** Almost the entire two-condition structure. Non-blocking *is* goal reachability. The safety specification *is* unsafe non-reachability. The supervisor *is* the cage, and the distinction between controllable and uncontrollable events is the distinction between edges a cage can remove and edges it cannot (the external world's moves). The supremal controllable sublanguage, the loosest supervisor that still meets the specification, is the supervisory-control name for the loosest good cage. The composition result of `open-problems.md` §1 is a special case of the known fact that the conjunction of non-blocking supervisors need not be non-blocking, which is why modular and decentralised supervisory control treat non-conflict as a separate property to be checked.

**What is different.** Three things, and they are the content of the framework rather than decoration.

1. *The plant is a learned policy whose transition relation is not given.* Supervisory control assumes a finite automaton model of the plant. A language-model agent's actual transition structure is unknown and is approximated by an abstraction (commands, files, memory levels). Every guarantee is relative to that abstraction, which `open-problems.md` §5 and §8 treat as a declared boundary.
2. *The state includes knowledge and memory.* Supervisory control models the plant's events; it has no notion of what the plant knows or remembers, and therefore no analogue of the Knowledge, Memory, or Parametric Memory Cages. Memory ownership as a cage in time (`open-problems.md` §2) has no counterpart in the classical theory.
3. *The adjudicator is given its own requirements.* In supervisory control the marked states are observable by definition. For an agent task, whether a state is in `G` is not observable without a verifier, and `epistemology-and-method.md` argues that the verifier's authority depends on structural properties (non-persuadability, priority, traceability) that the classical theory never needed to state.

Caging Engineering is therefore best described as supervisory control carried over to a cognitive architecture, with the plant model, the state, and the observer each generalised. A reader from control theory should recognise it at once.

## 2. Runtime enforcement, security automata, and shielding

**Lineage.** Schneider, *Enforceable security policies* (ACM TISSEC, 2000): execution monitors that observe a system step by step and halt it before a violation. The paper's central result is that monitors of this kind can enforce exactly the **safety properties** in the Alpern–Schneider sense, and cannot enforce liveness. Ligatti, Bauer, and Walker, *Edit automata* (2005), extend the monitor's powers (suppress, insert) and enlarge the enforceable class somewhat, but the safety/liveness boundary remains the organising fact. In reactive synthesis, Bloem et al., *Shield synthesis* (TACAS, 2015) construct a minimal-interference monitor from a temporal specification; Alshiekh et al., *Safe reinforcement learning via shielding* (AAAI, 2018) apply the construction to learning agents.

**What is inherited.** The enforcement mechanism of any real cage is a monitor of this kind: a check on each proposed transition. The Action Cage of a runtime such as Terra is, implementation-wise, a security automaton over commands.

**What is different.** The classical result is, read through `ontology.md` §4, the formal reason that guardrails accrete toward uselessness: an execution monitor cannot see the goal, so a design discipline built only from monitors has no way to notice when the goal has been lost. Shields are additionally *per-step*: they decide about the next transition, where a cage is a statement about the closure. Caging Engineering keeps the monitor as the enforcement layer and adds the goal-side condition that the monitor cannot express, together with a design step (`epistemology-and-method.md` §3, step 3) at which goal reachability is checked before the monitor is deployed.

## 3. Control barrier functions and set invariance

**Lineage.** For continuous-time systems, a **control barrier function** is a function whose zero-superlevel set is rendered forward-invariant by constraining the control input (Ames, Xu, Grizzle, Tabuada, *Control barrier function based quadratic programs for safety critical systems*, IEEE TAC, 2017; Ames et al., survey, ECC 2019). Control Lyapunov functions supply the dual, goal-directed condition, and the combined CLF–CBF quadratic program trades the two off at each instant. The older root is Nagumo's theorem on set invariance and the viability theory of Aubin.

**What is inherited.** The pairing. A barrier function alone is unsafe non-reachability for continuous dynamics, with the same one-sidedness as a security automaton; the CLF–CBF pairing is the continuous analogue of the two-condition requirement, and the slack between the barrier and the Lyapunov descent direction is the continuous analogue of tightness.

**What is different.** The state space is discrete and partly symbolic, the dynamics are not differentiable, and the "controller" is a learned policy that is not being synthesised but constrained. The useful import is conceptual: that safety and goal-directedness are two constraints solved jointly, not one applied after the other.

## 4. Barrier analysis and defence in depth in safety engineering

**Lineage.** Haddon's energy-barrier model (*Energy damage and the ten countermeasure strategies*, 1973), the hazard-barrier-target framework used in process-safety analysis, Reason's model of accident causation with layered, imperfect defences (*Human Error*, 1990), and the defence-in-depth doctrine of the nuclear industry. Leveson's STAMP/STPA (*Engineering a Safer World*, 2011) reframes safety as a control problem over a sociotechnical system, with accidents arising from inadequate control rather than component failure.

**What is inherited.** The word "cage" is borrowed in spirit from this tradition, and so is its central empirical lesson: barriers fail *in combination*, through interactions the designer of each individual barrier did not consider. `open-problems.md` §1 is that lesson in the vocabulary of transition relations. Leveson's move, treating safety as control rather than as component reliability, is the same move `ontology.md` §1 makes from the model to the system.

**What is different.** Safety engineering's barriers are physical or procedural and its hazards are energy flows; it has no goal-side condition (a plant that is safely shut down is a success). Caging Engineering's insistence on the goal condition is what distinguishes it from a pure safety discipline.

## 5. Agent-side practice: guardrails, sandboxes, permissions, specifications

**Lineage.** Output and action guardrails (content filters, tool allow-lists, command deny-lists); sandboxes and containers for execution isolation; capability- and permission-based tool access; constitutional and rule-based steering of model behaviour; and task-specification practices such as explicit success criteria and stop conditions.

**What is inherited.** Each is an implementation of one cage. Guardrails and allow-lists are Action Cages at the action level; sandboxes are Action Cages at the environment level; permission systems are the `p` component of the state in `open-problems.md` §2; specification practices are the Specification Cage.

**What is different.** None of these, individually or as a list, states a goal condition, and none has a notion of tightness. The v0.1.0 `README.md` table already records this. What the present documents add is the explanation of *why* a list of such mechanisms tends to produce a safe and useless agent (`ontology.md` §4; §2 above), and the classification of common verification practices by the three adjudicator requirements (`epistemology-and-method.md` §6).

## 6. Agent memory governance and memory security

This lineage is recent and fast-moving; the works below are those the authors have examined, not a survey.

**Memory systems.** MemGPT (Packer et al., 2023) introduced the operating-system analogy for context management. Mem0 (Chhikara et al., 2025), Zep/Graphiti (Rasmussen et al., 2025), and A-MEM (Xu et al., NeurIPS 2025) are retrieval-centred memory layers; Zep's bitemporal "invalidate, do not delete" rule is a precedent for traceability at the memory level. MemOS (Li et al., 2025) declares memory a first-class system resource with access-control, lifespan, and versioning metadata on each unit; EverMemOS (ACL 2026) organises a memory lifecycle from episodic traces to consolidated semantics.

**Memory attacks.** AgentPoison (Chen et al., NeurIPS 2024) poisons long-term memory or knowledge bases through optimised triggers; MINJA (Dong et al., NeurIPS 2025) injects malicious reasoning into an agent's memory through ordinary queries alone, with no system access. Both attack the default assumption that *whatever is written to memory is true*, which is exactly the assumption the Memory Cage and the promotion chain of `v0.1 04_memory_middleware.md` reject.

**Memory governance.** MemLineage (2026) attaches writer principal, source hash, trust level, and a lineage graph to each write and enforces policy on derived reads; Collaborative Memory (Accenture, 2025) applies dynamic multi-user access control to shared agent memory; MAPLE-Guard (2026) gates write, retrieval, promotion, and cross-agent transfer with deterministic provenance; A-MemGuard (ICML 2026) is a runtime detector that cross-checks reasoning paths and distils failures into "lessons".

**What is inherited.** Provenance, versioning, and policy-aware retention are now widely argued to be necessary at storage time rather than retrieval time. The Failed Path Index and the append-only verdict store of `epistemology-and-method.md` §2.3 are in this spirit.

**What is different.** The governance works above are access-control and provenance layers: they decide *who may write* by identity and trust label. `open-problems.md` §2 proposes something stronger and narrower: that memory ownership is a *cage on the transition relation*, so that memory pollution is a reachability property that can be stated and, on an abstraction, checked, rather than a policy violation to be detected after the fact. The detectors (A-MemGuard, taint-tracking approaches) are the natural comparison group for that claim: a constructive guarantee on an abstraction against a detector with a false-negative rate on the real system.

## 7. Verification, preregistration, and falsifiability

**Lineage.** Popper's demarcation by falsifiability; the preregistration movement in the empirical sciences (Nosek et al., *The preregistration revolution*, PNAS 2018); registered reports; and, on the engineering side, test-driven development's rule that the test is written before the code it tests.

**What is inherited.** The *priority* requirement of `epistemology-and-method.md` §2.2 is the same requirement in each of these: the criterion is fixed before the result is visible. The framework does not add to this tradition; it imports it into the design of an agent's adjudicator and observes that the Meta-Cage is what makes priority enforceable rather than aspirational.

## 8. Formal methods: proof assistants, model checking, refinement

**Lineage.** Interactive theorem proving in Lean 4 (de Moura and Ullrich, 2021) and the general method of handing a claim to a kernel that checks it; model checking of specifications in TLA+ (Lamport, 2002) and the refinement relation between a specification and an implementation (Abadi and Lamport, *The existence of refinement mappings*, 1991).

**What is inherited.** The posture. `formal/CagingCore.lean` is small, and its facts are elementary, but the decision to state them in a checked form rather than in prose is the framework's own epistemology applied to itself. The refinement relation is the correct form of the claim "runtime X implements caging" (`open-problems.md` §4), and TLA+ is the natural tool for checking it against a small executor.

**What is different.** Nothing is claimed to be new here. The point of listing it is to make the standard explicit: a statement about the framework that could be checked and has not been is, by the framework's own lights, a draft.

## 9. Summary table

| Lineage | Gives Caging Engineering | Lacks, from Caging Engineering's point of view |
|---|---|---|
| Supervisory control (Ramadge–Wonham) | The two-condition structure, controllability, non-blocking, modular non-conflict | A plant whose model is unknown; knowledge and memory in the state; requirements on the observer |
| Runtime enforcement / shielding | The enforcement mechanism; the safety-only theorem that explains guardrail accretion | Any goal-side condition; closure-level rather than per-step view |
| Control barrier functions | Joint safety/goal constraint; slack as a continuous quantity | Discrete, symbolic, non-differentiable state |
| Safety-engineering barrier analysis | Barriers fail in combination; safety as control | A goal condition |
| Agent-side guardrails, sandboxes, permissions | Implementations of individual cages | A goal condition; tightness; adjudicator requirements |
| Memory governance and security | Storage-time provenance and policy; the attack models | Memory as a cage on the transition relation; constructive rather than detective guarantees |
| Preregistration / falsifiability | The priority requirement | — (imported unchanged) |
| Proof assistants, model checking, refinement | The checked-core posture; the refinement form of implementation claims | — (imported unchanged) |

What Caging Engineering adds to these lineages is not a new mathematical object. It is the insistence that the same two-condition requirement be applied across the whole cognitive stack (specification, knowledge, memory, action, verification), that the adjudicator be given structural requirements rather than assumed correct, and that the human positions be derived rather than assumed. Whether that insistence pays for itself is an empirical question, and `experiments/PREREGISTRATION.md` is where it is to be asked.
