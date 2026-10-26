# Ontology: The Agent as a Trajectory in a Reachable Space

This is the first of four theory documents that extend the v0.1.0 concept archive. It fixes what Caging Engineering takes to exist, and what it refuses to treat as primary. The other three cover the epistemology and method (`epistemology-and-method.md`), the propositions, objections and limits (`open-problems.md`), and the placement among prior work (`related-work.md`). References of the form `v0.1 01_core_definitions.md` point to the archive under `caging/caging-engineering/docs/`.

## 1. A change of object

Most current writing about agents treats the agent as a *mind that is instructed*. The engineering that follows from that picture revolves around how one speaks to it: prompts, system instructions, personas, few-shot examples, tone.

Caging Engineering changes the object of study. An agent is a *motion through a state space*. What is worth studying is not what it thinks, but where it can go.

This is not a claim that models do not reason. It is a decision about what the engineering discipline should quantify over. Prompts, tools, and models remain in the picture, but as derived notions:

```text
a tool      = a family of edges added to the transition relation
a prompt    = a prior over which available edges the agent tends to take
a model     = the policy that chooses among available edges
a cage      = a restriction on which edges exist at all
```

Only the last of these is the subject of this framework.

## 2. Three primitives

Once the object is the reachable space, the world contains three kinds of thing.

**State, `s`.** Everything the task outcome depends on and that the system can in principle observe: the file tree, the memory stores at every level, the permission set currently held, and the observable part of the external world (a running service, a remote repository, a mailbox). What is admitted into the state is a modelling decision; `v0.1 08_open_questions.md` lists it as the first unresolved question, and that remains true.

**Cage, `C`.** A cage is *not* a prohibition on actions. It is a restriction on the transition relation: a statement about which edges `s → s'` exist. Formally a cage is a predicate on pairs of states, and the reachable region under it is the closure of the initial state under the surviving edges:

```text
R_C(s0) = the least set containing s0 and closed under { s → s' : step(s, s') ∧ C(s, s') }
```

**Adjudicator, `V`.** A function that decides whether a state lies in the goal region `G` or the unsafe region `U`. Its single defining property is that it sits *outside the agent's writable space*. An adjudicator the agent can edit is not an adjudicator; it is part of the proposal. The epistemic consequences of this are the subject of `epistemology-and-method.md`.

Everything in the v0.1.0 taxonomy (`v0.1 02_caging_taxonomy.md`) can be read back onto these three. The Specification Cage fixes `G`. The Action, Knowledge, and Memory Cages are restrictions on different components of the transition relation. The Verification Cage is `V`. The Meta-Cage is the rule that edges modifying `C` or `V` lie in `U`. The Convergence Cage acts after adjudication, on what is retained of the trajectory.

## 3. The level at which a cage acts

The decisive difference between a cage and a guardrail is the level at which each acts.

A guardrail acts at the **action level**. It is a predicate on individual actions or outputs: this command is forbidden, this string may not appear, this file may not be opened.

A cage acts at the **reachability level**. It is a restriction on the transition relation, and therefore on the closure `R_C(s0)`.

The difference shows up under composition. An action-level prohibition can be routed around: the forbidden effect is produced by a sequence of permitted actions. `v0.1 01_core_definitions.md` §15 calls this a semantic bypass and gives the standard example (do not delete the tests; so empty them, or skip them, or edit the helper that reports them). A reachability-level restriction has no such gap by construction: a bypass *is* a reachable path to a state in `U`, and a cage is precisely a statement that no such path exists.

This is a definitional distinction, not an implementation guarantee. Any running system enforces its cage through some finite set of checks on some abstraction of the state, and the gap between the abstraction and the system is where bypasses live. `open-problems.md` §8 returns to this. The point here is which object the design is *about*: a guardrail is about actions; a cage is about the closure.

## 4. Two independent conditions

The core principle has two parts that are logically independent:

```text
Goal reachability:        R_C(s0) ∩ G ≠ ∅     (a liveness-like condition)
Unsafe non-reachability:  R_C(s0) ∩ U = ∅     (a safety condition)
```

The two behave differently under the operations a designer actually performs. Tightening a cage (removing edges) can never break safety and can never restore reachability. Loosening a cage can never break reachability and can never restore safety. Composing two cages (keeping only edges both allow) preserves safety if either component was safe, and may destroy reachability even when both components reached the goal. These facts are elementary; `formal/CagingCore.lean` states and checks them.

They explain a failure mode that practitioners recognise. A system built from safety alone drifts toward blocking `G`: every added guardrail shrinks the reachable region, nothing ever enlarges it, and after enough additions the agent is safe and useless. Caging Engineering requires both conditions at once, which is why it has a quantity that a safety-only framework cannot define.

### Tightness and slack

Let `N(G)` be the set of states lying on at least one surviving path from `s0` into `G`. The **slack** of a cage is what the reachable region contains beyond that:

```text
slack(C) = R_C(s0) \ N(G)
```

A cage with zero slack admits only states that lie on a route to the goal. **Tightness** is any monotone measure of how small the slack is.

Tightness is not to be maximised. Zero slack means there is no exploration: the goal path must already be known when the cage is written, which is the one situation where an agent is unnecessary. Slack is the resource that search consumes. The design question is how much slack a task needs, and when; `open-problems.md` §6 argues that for research-type tasks the answer changes over the course of the task.

What tightness does is put *safety* and *usefulness* on a single scale. The space of good cages is an interval: any cage at least as loose as some single route to `G`, and at least as tight as the complement of `U`. Design happens inside that interval.

## 5. The world is reports, not ground truth

The second ontological commitment is borrowed from a neighbouring project and is stated here because it changes what an adjudicator can be.

The adjudicator does not see the world. It sees *reports*: the exit code of a test runner, a directory listing, a log line, a hash. The agent also sees reports. No layer of the system sees ground truth.

The consequence is structural rather than practical. If no single layer can be trusted to be correct, authority cannot come from any layer's correctness. It can only come from the *relations between layers* being tamper-evident: an append-only ledger whose hash is held elsewhere, a verdict that is signed by a key the proposer does not hold, a test suite whose checksum is pinned outside the sandbox. Adjudication is therefore necessarily layered, and the audit log is itself an object that must be auditable.

`v0.1 05_verifier_layer.md` §6 lists verifier integrity as a requirement. This document gives the reason it cannot be dropped: it is not that tampering is likely, it is that without tamper-evidence between layers there is nothing in the ontology that authority could attach to.

## 6. What the ontology commits to, and what it does not

Commits to:

- The object of design is the transition relation, not the policy that walks it.
- A cage is a region of the transition relation, not a wall around the agent. The boundary is drawn first; the agent's freedom is what remains inside.
- Goal reachability and unsafe non-reachability are independent requirements, and a framework that states only one of them has no notion of tightness.
- Adjudication is external to the agent's writable space and layered, because every layer sees reports.

Does not commit to:

- Any particular choice of state model. That remains an open question and is almost certainly task-dependent.
- Any claim that a running system realises the closure-level restriction exactly. Implementations approximate it on an abstraction.
- Any claim about the inner workings of the policy. The framework is agnostic about how the model chooses among the edges it is given.

## 7. One-line summary

An agent is not a mind to be instructed but a space to be shaped. The cage is the geometry of what can happen next, and a good cage is one in which the goal is still inside, the unsafe region is outside, and there is enough room left between them to search.
