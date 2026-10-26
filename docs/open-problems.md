# Open Problems: Propositions to Carry Further, Objections, and What Is Not Claimed

The third theory document. `ontology.md` and `epistemology-and-method.md` built the position. This document does two things with it. Sections 1–4 collect the propositions that can be carried further: some already checked, some conjectures with a clear shape. Sections 5–10 record the strongest objections the authors can raise against the position, how far each reaches, and an explicit table of claims and non-claims so that the framework can be held to something. References of the form `v0.1 02_caging_taxonomy.md` point to the archive under `caging/caging-engineering/docs/`.

---

## Part I — Propositions

## 1. Composition: cages compose by intersection, and intersection can kill the goal

Two cages `C₁` and `C₂` applied together keep only the edges both allow:

```text
(C₁ ∧ C₂)(s, s') = C₁(s, s') ∧ C₂(s, s')
```

Three facts follow, and all three are checked in `formal/CagingCore.lean`:

1. **Composition shrinks reachability.** `R_{C₁∧C₂}(s0) ⊆ R_{C₁}(s0) ∩ R_{C₂}(s0)`. The inclusion is in general strict: a state can be reachable under each cage by different routes, and reachable under neither route once both cages apply at every step.
2. **Safety survives composition.** If either component keeps the reachable region out of `U`, so does the composite. More generally, tightening a cage never breaks safety.
3. **Goal reachability does not survive composition.** There is a three-state system with two routes to the goal, and two cages each of which keeps exactly one route; each cage reaches the goal, their conjunction reaches nothing but the start state. The file gives the example explicitly.

The asymmetry between (2) and (3) is the whole story of guardrail accretion. Safety properties are closed under adding restrictions; liveness-like properties are not. A designer who adds cages one at a time, each one checked for safety, is performing an operation that can only ever lose the goal and will never be told so by any of the individual checks.

**Proposition 1 (cage consistency check).** Given a finite abstraction of the task space, a goal predicate, and a set of cages, the question *is `G` still reachable under their conjunction* is a graph reachability problem on the abstraction and is therefore decidable in time linear in the abstraction's size. A caged runtime should run this check whenever a cage is added or tightened, and should refuse the change, or invoke the expansion protocol, when the answer is no.

*Next step.* Build the abstraction extractor for one concrete runtime (the candidate is the eight-cage executor in the Terra project, whose cages are predicates on commands) and run the check against its default cage set on a small task suite.

## 2. Memory ownership is a cage in time

The Memory Cage of `v0.1 02_caging_taxonomy.md` and the seven memory levels of `v0.1 04_memory_middleware.md` assign each level an owner and a write permission. Read through the ontology, these are not a separate mechanism from the Action Cage. They are the same kind of object applied to a different component of the state.

Decompose the state as `s = (w, m, p)`: the world, the memory stores, the held permissions. An action cage restricts edges by what they do to `w`. A memory cage restricts edges by what they do to `m`, and in particular by *who* is writing: an edge that writes level `k` of `m` survives only if its author holds the ownership of level `k`.

The two differ in which direction of time they face. A spatial cage limits where the agent can go *now*. An ownership rule limits what the agent can *become*: which future states are available because of what may be written into the memory that future decisions will read. Memory pollution is unreachable-later, not forbidden-now.

**Proposition 2.** Memory ownership and action caging are two projections of one restriction on the transition relation, distinguished only by the state component they constrain. A single formal treatment covers both, and the memory-promotion chain of `v0.1 04_memory_middleware.md` §4 is a sequence of ownership transfers, each of which is an edge that must itself be caged.

*Next step.* Extend `CagingCore.lean` with a product state and show that the ownership rule is expressible as a cage on the memory component; then state memory pollution as a reachability property on the product.

## 3. Reachability is time-dependent, and the cage should be too

The current formalisation is static: one transition relation, one cage, one reachable region. Real tasks are not. A goal may be reachable only in a window (a deployment freeze lifts; a reviewer is available; a dataset's embargo ends). A route may be safe at one time and unsafe at another (a shared resource is locked; a rate limit is in effect).

The natural extension is a time-indexed cage `C_t` over a timed transition system, where edges carry the time at which they may be taken. Goal reachability becomes *reachability within the horizon*; unsafe non-reachability becomes *at no time*. §6 below needs exactly this to state the tightening schedule for exploratory tasks: tightness becomes a function of time, piecewise monotone within phases.

**Proposition 3.** The monotonicity results of §1 lift pointwise to time-indexed cages: if `C_t ⊑ C'_t` for all `t`, then safety transfers from `C'` to `C` and goal reachability from `C` to `C'`. The composition counterexample also lifts, and gains a new form: two cages that each reach the goal *at some time* may, in conjunction, reach it at no time because their windows do not overlap.

*Next step.* The timed version is a modest extension of the Lean file. The substantive work is empirical: whether staged tightening beats fixed tightness on exploratory tasks, which §10 lists among the things that would count against the position.

## 4. The formal core, and what it lacks

The model in `formal/CagingCore.lean` is deliberately small. In prose: a **transition system** is a step relation on states with a distinguished initial state. A **cage** is a predicate on pairs of states. The **reachable region** `R_C(s0)` is the least set containing `s0` and closed under steps the cage allows. **Goal reachability** says some reachable state satisfies `G`; **unsafe non-reachability** says no reachable state satisfies `U`; a cage is **good** when both hold.

Checked facts:

| Name in file | Statement |
|---|---|
| `reach_mono` | A tighter cage reaches no more states. |
| `reach_and_sub` | The composite's reachable region lies inside the intersection of the components'. |
| `safe_and_of_left` | If one component is safe, the composite is safe. |
| `safe_of_le` | Tightening preserves safety. |
| `goal_of_le` | Loosening preserves goal reachability. |
| `and_not_reaches` | Two cages that each reach the goal, whose conjunction does not (explicit three-state witness). |

The file uses Lean 4 core only, with no external library, so the whole development can be checked with a single invocation of the compiler. That choice is itself an application of `epistemology-and-method.md`: the facts these documents lean on are handed to something that cannot be argued with.

What the core does **not** contain, and what the next version should:

- The **Meta-Cage** as a formal object: a distinguished component of the state holding `C` and `V`, with the rule that any edge modifying it is in `U` unless its source is the external authority. This is the formal shape of "a human merges".
- **Slack** and a **tightness** order on cages (`ontology.md` §4), and the statement that goodness is an interval under that order.
- **Refinement.** The claim that a concrete executor realises a cage is a refinement claim: the executor's actual reachable set is contained in the model's `R_C(s0)`. Stating this for the Terra executor would turn "Terra implements caging" from a description into something that can be false.
- The **timed** extension of §3 and the **product-state** extension of §2.

A TLA+ rendering would be a reasonable alternative for the refinement claim specifically, since model checking a small executor against a specification is TLA+'s home ground; the Lean development is better suited to the general propositions.

---

## Part II — Objections and limits

## 5. Unsafe non-reachability is undecidable in the open world

**Objection.** `R_C(s0) ∩ U = ∅` is a statement about a set `U`. In any task that touches the real world, `U` is not known; it is modelled. A guarantee about the modelled `U_model` says nothing about states the model did not anticipate, and those are typically the ones that matter.

**How far it reaches.** All the way. There is no version of Caging Engineering that guarantees safety against an unmodelled unsafe region, and none is claimed.

**What follows.** The modelling boundary of `U` is itself a claim and must be declared as one. A caged system should state two things, not one:

```text
(a) No state in R_C(s0) satisfies U_model.
(b) U_model covers the following classes of unsafe state: ...
    The following classes are outside the model: ...
```

Statement (b) belongs in the same table of permitted and forbidden claims that governs everything else the system reports. A system that reports (a) without (b) is overclaiming, whatever its verifier says. This is also the honest reading of the Semantic Cage Integrity requirement (`v0.1 01_core_definitions.md` §15): bypasses are, by definition, routes to `U` that the model of `U` did not include.

## 6. Over-caging has a cost, and the cost falls on exactly the tasks that need agents most

**Objection.** Research-type tasks, open-ended design, and diagnosis all require a large reachable region. `ontology.md` §4 defines slack as the resource that search consumes. A cage tight enough to be comfortable is one in which these tasks cannot be done.

**How far it reaches.** It is correct as stated against any *static* cage. The current formalisation is static: one cage, one reachable region.

**What follows.** The cage for an exploratory task must be *time-varying*, and the framework presently lacks a theory of the schedule. The shape of such a theory is visible, and it matches a working practice: open strategically, tighten tactically.

```text
tightness(t) is piecewise monotone:
  within a phase, the cage only tightens, and each tightening is justified
  by a recorded verdict (a hypothesis confirmed or eliminated);
  at a phase boundary, the cage may be reset looser for the next question.
```

Under this schedule the early reachable region is wide and the late one is narrow, and the path from wide to narrow is itself traceable. What is *not* yet available is any result about such schedules: whether a monotone-within-phase schedule dominates a fixed tightness for a given task class, how phase boundaries should be chosen, or how much slack a research task needs at its start. These are empirical questions and are listed as such in §10.

A separate warning falls out of the same analysis. Premature tightness is not a conservative error. It removes the states in which the goal would have been found, and because tightening never restores reachability (§1), the loss is silent: the system reports no failure, only an unreachable goal. Over-caging and under-caging fail differently, and only one of them announces itself.

## 7. The adjudicator itself errs

**Objection.** Tests are wrong. Specifications are wrong. A proof checker verifies that a proof matches a statement, not that the statement is the one that was meant. When the adjudicator is wrong, the verdict is wrong, and nothing inside the system can tell.

**How far it reaches.** Fully. The correctness of the criterion cannot be established by the adjudicator that applies it, and handing the criterion to a second adjudicator only moves the question to that adjudicator's criterion.

**What follows.** Two things.

First, this fixes the second of the irreducible human positions from `epistemology-and-method.md` §5. *Reading the specification* is not a step that can be delegated to the system that will be judged by it. Someone other than the proposer must have read the criterion and judged that it says what was intended, and that reading is a boundary act in the same sense as merging.

Second, there are partial mitigations, and they should be named as partial. Two independent adjudicators for the same property reduce the chance of a shared error but do not eliminate the regress. Mutation testing of the verifier (does it reject deliberately broken candidates?) catches vacuous criteria. Adversarial proposals aimed at the criterion rather than the task expose gaps before they are exploited. None of these closes the regress; each shortens it.

Together with the closure gap of `epistemology-and-method.md` §4, this gives the minimal irreducible human footprint in a caged system: **the one who changes the cage, and the one who reads the specification.** Everything else is, in principle, delegable.

## 8. Further limits, briefly

- **The transition relation of a learned policy is not known.** The cage is written against an abstraction of the system (commands, files, memory levels), not against the policy's actual state space. The abstraction gap is a standing source of unmodelled `U`, and every statement in Part I is a statement about the abstraction.
- **The cage's own sensors see reports.** `ontology.md` §5 applies to the enforcement layer as well as to the adjudicator. A cage that decides whether an edge is allowed by inspecting a path string is reasoning about a report of the file system, not the file system.
- **External verification has cost and latency.** A method that verifies every step externally may be slower than a method that verifies at the end; the trade-off between verification frequency and slack consumed is unexplored.
- **Composition is under-specified beyond conjunction.** §1 treats cages that compose by intersection. Cages that interact through shared state (one cage's enforcement writes memory that another cage reads) are not covered.
- **Nothing here is validated on tasks.** The repository's own motto, "define less, test more", applies to these documents. They are a position, with a small checked core, and no measurements.

## 9. What is claimed, and what is not

| | Claimed | Not claimed |
|---|---|---|
| **Framing** | Cages act on the transition relation, guardrails on individual actions; the distinction is definitional and has consequences under composition. | That any deployed system enforces a closure-level restriction exactly. |
| **Two conditions** | Goal reachability and unsafe non-reachability are independent, behave oppositely under tightening, and a safety-only framework has no notion of tightness. | That there is a canonical tightness measure. |
| **Verification** | An adjudicator counts as one only if it is non-persuadable, prior, and traceable. | That any adjudicator is correct; that the regress on its criterion can be closed. |
| **Humans** | Two positions are irreducible for structural reasons: changing the cage, reading the specification. | That these are the only places humans add value; that they are large amounts of work. |
| **Formal core** | The monotonicity and composition facts in `formal/CagingCore.lean` hold for the abstract transition-system model and are machine-checked. | That the model is faithful to any particular runtime; that its refinement by a real executor has been shown. |
| **Lineage** | The framework is a generalisation of supervisory control to a cognitive architecture, with knowledge, memory, and verification added as dimensions (`related-work.md`). | Priority or novelty over supervisory control, runtime enforcement, or barrier methods. |
| **Safety** | Guarantees are relative to a declared `U_model`. | Safety in the open world. |

## 10. What would count against the position

A framework that cannot say what would refute it is a vocabulary. The following observations, if made, would count against specific claims above. They are stated as observations, not as planned measurements; designing the measurements, with thresholds fixed before data, is the job of `experiments/PREREGISTRATION.md`.

- Systems built by accreting action-level guardrails do *not* show the predicted drift toward goal-unreachability; usefulness holds up as guardrails are added. (Against `ontology.md` §4 and the practical relevance of §1.)
- Composed cages that each individually reach the goal rarely or never fail to reach it in combination on realistic task sets. (Against the practical relevance of the composition result.)
- A persuadable judge with a frozen rubric produces unverified-completion rates no higher than a non-persuadable adjudicator on the same tasks. (Against `epistemology-and-method.md` §2.1 as a distinction that matters.)
- Fixed-tightness cages perform as well as staged-tightening cages on exploratory tasks, across the range of initial slack. (Against §6.)
- Retaining a failed-path index after convergence does not reduce re-entry into `U` on later tasks of the same kind, relative to discarding it. (Against the Convergence Cage's traceability rationale in `epistemology-and-method.md` §2.3.)
- Criteria that pass mutation testing and dual-adjudicator review still produce wrong verdicts at a rate indistinguishable from unreviewed criteria. (Against the mitigations in §7 being worth their cost; it would not touch the regress argument itself.)

None of these would refute the ontology, which is a choice of object rather than a hypothesis. All of them would bear on whether the choice is useful.

## 11. Status of the propositions

| # | Proposition | Status |
|---|---|---|
| 1 | Cage consistency under conjunction is decidable on a finite abstraction and should be a runtime check. | Composition facts checked; the check itself not built. |
| 2 | Memory ownership and action caging are projections of one restriction on different state components. | Argued; not formalised. |
| 3 | Monotonicity lifts to time-indexed cages; composition failure gains a window-overlap form. | Argued; the lift is a routine extension of the file. |
| 4 | A concrete executor realises a cage iff its reachable set refines the model's `R_C(s0)`. | Stated as the correct form of the claim; not shown for any executor. |
| 5 | Staged tightening dominates fixed tightness on exploratory tasks. | Conjecture; empirical. |
