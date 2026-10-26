# Epistemology and Method: The Authority of a Verifier Comes from Its Inability to Be Persuaded

The second theory document. `ontology.md` fixed what exists: states, cages, and an adjudicator outside the agent's writable space. This document asks what it means, inside such a system, to *know* that a goal has been reached, and derives a method from the answer. References of the form `v0.1 05_verifier_layer.md` point to the archive under `caging/caging-engineering/docs/`.

## 1. The compressed claim

Caging Engineering's epistemology can be stated in one sentence:

> To know is to have been confirmed by something that cannot talk back.

`v0.1 05_verifier_layer.md` §1 already says that self-reflection stays inside the model's own generative space and that external feedback is needed. This document takes that observation seriously enough to ask *what property* of the external thing makes its feedback count as confirmation. The answer is not accuracy, and not independence in the statistical sense. It is three structural requirements on the adjudicator.

## 2. Three hard requirements on the adjudicator

### 2.1 Non-persuadability

The adjudicator has no natural-language interface.

A proof checker's kernel, a continuous-integration gate, a sealed data label, an append-only ledger: what these share is that there is no way to *explain* anything to them. They accept an object and return a verdict determined by the object alone.

The reason this matters is logical rather than practical. An adjudicator that can be persuaded is one whose verdict depends on the proposer's description of the proposal. Its verdict is then a function of the proposer's output, which makes it, formally, a component of the proposer. Verification by a persuadable adjudicator is self-report with an extra step.

A corollary worth stating explicitly, because current practice runs against it: a language model used as a judge is a proposer-side instrument unless its criterion is frozen in advance and its inputs are sealed from the proposer's commentary. Under those conditions it can *rank* candidates. It cannot *adjudicate*, because the thing it is judging can address it.

### 2.2 Priority

The criterion is fixed, and frozen, before the proposal exists.

This is the epistemic location of the rule "thresholds before data". A criterion that is settled after the result is visible is not a test of the result; it is a description of it. The requirement is the same one that preregistration imposes on empirical studies and that falsifiability imposes on hypotheses: the conditions under which the claim would fail must be written down before anyone knows whether it does.

Inside a caged system, priority has a concrete form. The success predicate in the Specification Cage, the test suite, the schema, the acceptance thresholds: all of these are committed to an append-only store *before* the agent begins, and the Meta-Cage makes the edges that would modify them unreachable. A specification the agent can still edit is not prior; it is a draft.

### 2.3 Traceability

Every verdict is written to a place from which it cannot be removed.

The usual justification for audit logs is accountability. That is not the justification here. The reason verdicts must persist is that the unsafe region `U` is, for most real tasks, known only empirically. Every negative verdict is one more observed point in `U`. A system that discards its failures is discarding its only map of the region it is supposed to keep the agent out of.

Traceability is therefore what allows the estimate of `U` to accumulate across tasks, and it is what makes the Failed Path Index (`v0.1 01_core_definitions.md` §19) an epistemic object rather than a convenience.

## 3. The method that follows

From the ontology and the three requirements, a method falls out. It is a pipeline rather than a set of components; the eight cages of `v0.1 02_caging_taxonomy.md` are the parts, and this is the order in which they bind.

```text
1. Specify     turn the ill-defined task into a well-defined one (Specification Cage):
               goal, success predicate, constraints, stop condition.
2. Freeze      write down the criteria and thresholds for G and U, and commit them
               somewhere the agent cannot reach (priority).
3. Construct   build C such that R_C(s0) meets G and misses U.
               If this cannot be done, the task is not yet caged; go back to 1
               or invoke the expansion protocol.
4. Run         let the policy walk the surviving edges.
5. Adjudicate  V, outside the writable space, returns a verdict (non-persuadability).
6. Record      the verdict, positive or negative, enters the append-only store
               (traceability).
7. Converge    on success, prune: keep the accepted path, compress the failed ones,
               archive the dormant ones (Convergence Cage).
8. Protect     any change to C, V, or the frozen criteria originates outside the cage
               (Meta-Cage).
```

Two remarks on the pipeline.

Step 3 can fail. When no cage satisfies both conditions, the correct output is not a looser cage chosen silently but a *report*: which boundary blocks the goal, what the minimal expansion would be, what it would newly make reachable. `v0.1 01_core_definitions.md` §16 already specifies the Cage Expansion Protocol; its place in the method is here, as the failure branch of construction.

Step 8 is not a step the agent performs. It is a constraint on who may perform the other steps' maintenance. That asymmetry is the subject of the next section.

## 4. The Meta-Cage and the closure gap

A cage cannot establish its own completeness by means available inside it. Whatever checks the cage can run on itself are edges in its own transition relation, and the question whether those edges suffice is exactly the question at issue. The structure is the familiar one from logic: a system strong enough to describe its own rules cannot, from inside, certify that those rules are enough. This is an analogy, not a theorem about agents; but the practical conclusion does not depend on the analogy being exact.

The practical conclusion is that the authority to modify the cage must come from outside it. In current systems, "outside" means one of two things: a human, or a kernel that is itself outside the agent's writable space and whose rules the human has read.

This gives a theoretical position to a practice that is usually defended as mere process: *a human merges*. It is not a habit, and it is not distrust of the model. It is the one gap in the system's closure that cannot be filled from within, and the Meta-Cage is the rule that only something outside the system may fill it.

## 5. The irreducible human positions

Two consequences of this document bear on what humans are for in a caged system, and they are stated here so that `open-problems.md` can build on them.

- **The one who changes the cage.** Because of the closure gap (§4), modifications to `C`, `V`, and the frozen criteria originate outside. This is a role, not a quantity of work; it may be rare.
- **The one who reads the specification.** Because priority (§2.2) requires the criterion to be fixed before the proposal, and because the adjudicator cannot check its own criterion (`open-problems.md` §7), someone who is not the proposer must have read the specification and judged that it says what was meant.

Everything else in the pipeline can, in principle, be delegated. These two cannot, not because of present model limitations but because of where they sit relative to the cage's boundary.

## 6. Where this diverges from common practice

The three requirements give a way to classify techniques that are often grouped together as "verification".

| Technique | Non-persuadable | Prior | Traceable | Status under this document |
|---|:-:|:-:|:-:|---|
| Self-critique / reflection loop | no | no | rarely | Search heuristic inside the proposer. Useful; not verification. |
| Language model as judge, free-form rubric | no | no | sometimes | Proposer-side ranking instrument. |
| Language model as judge, frozen rubric, sealed inputs | partly | yes | yes | Can rank; cannot adjudicate; verdicts should be audited against a non-persuadable check. |
| Unit / integration tests pinned outside the sandbox | yes | yes | if logged | Adjudicator. |
| Type checker, schema validator, linter | yes | yes | if logged | Adjudicator for the properties they cover. |
| Proof checker kernel | yes | yes | if logged | Adjudicator; the specification remains a human-read object. |
| Human review | partly | depends | depends | Adjudicator only when the reviewer reads the artefact, not the agent's account of it. |

The last row deserves emphasis. A human who approves on the basis of the agent's summary has been addressed by the proposer, and the approval inherits the problem of §2.1. The human positions of §5 are positions *at the boundary*, and they are only held by someone who looks at the thing itself.

## 7. One-line summary

Confirmation comes from what cannot be argued with, was fixed in advance, and leaves a trace; the method is the order in which those three are secured; and the gap the method cannot close from inside is where the human stands.
