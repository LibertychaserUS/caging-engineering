/-
Caging Engineering — formal core.

A minimal transition-system model of a cage, with the handful of facts the
theory essays rely on. Checked with Lean 4 core only (no Mathlib).

  * `Reach ts C`           reachable region R_C(s0)
  * `GoalReachable`        R_C(s0) ∩ G ≠ ∅        (liveness-like)
  * `UnsafeUnreachable`    R_C(s0) ∩ U = ∅        (safety)
  * `Good`                 both at once

Facts proved here:
  * reachability is monotone in the cage            (`reach_mono`)
  * composing cages shrinks reachability            (`reach_and_sub`)
  * safety survives composition and tightening      (`safe_and_of_left`, `safe_of_le`)
  * goal reachability survives loosening            (`goal_of_le`)
  * goal reachability does NOT survive composition  (`and_not_reaches`, a 3-state counterexample)
-/

namespace Caging

universe u
variable {S : Type u}

/-- A transition system: a step relation and an initial state. -/
structure TS (S : Type u) where
  step : S → S → Prop
  s0   : S

/-- A cage is a predicate on transitions: which edges remain available. -/
def Cage (S : Type u) := S → S → Prop

/-- Conjunction of cages: an edge survives only if both cages allow it. -/
def Cage.and (C₁ C₂ : Cage S) : Cage S := fun s s' => C₁ s s' ∧ C₂ s s'

/-- Cage refinement: `C₁` allows no edge that `C₂` forbids (C₁ is tighter). -/
def Cage.le (C₁ C₂ : Cage S) : Prop := ∀ s s', C₁ s s' → C₂ s s'

/-- The reachable region from `ts.s0` under cage `C`. -/
inductive Reach (ts : TS S) (C : Cage S) : S → Prop
  | base : Reach ts C ts.s0
  | step {s s' : S} : Reach ts C s → ts.step s s' → C s s' → Reach ts C s'

def GoalReachable (ts : TS S) (C : Cage S) (G : S → Prop) : Prop :=
  ∃ s, Reach ts C s ∧ G s

def UnsafeUnreachable (ts : TS S) (C : Cage S) (U : S → Prop) : Prop :=
  ∀ s, Reach ts C s → ¬ U s

def Good (ts : TS S) (C : Cage S) (G U : S → Prop) : Prop :=
  GoalReachable ts C G ∧ UnsafeUnreachable ts C U

/-- Reachability is monotone in the cage. -/
theorem reach_mono {ts : TS S} {C₁ C₂ : Cage S} (h : Cage.le C₁ C₂) :
    ∀ s, Reach ts C₁ s → Reach ts C₂ s := by
  intro s hs
  induction hs with
  | base => exact Reach.base
  | step _ hstep hc ih => exact Reach.step ih hstep (h _ _ hc)

theorem and_le_left (C₁ C₂ : Cage S) : Cage.le (Cage.and C₁ C₂) C₁ :=
  fun _ _ h => h.1

theorem and_le_right (C₁ C₂ : Cage S) : Cage.le (Cage.and C₁ C₂) C₂ :=
  fun _ _ h => h.2

/-- Composition shrinks reachability: R_{C₁∧C₂} ⊆ R_{C₁} ∩ R_{C₂}. -/
theorem reach_and_sub {ts : TS S} {C₁ C₂ : Cage S} :
    ∀ s, Reach ts (Cage.and C₁ C₂) s → Reach ts C₁ s ∧ Reach ts C₂ s :=
  fun s h => ⟨reach_mono (and_le_left C₁ C₂) s h, reach_mono (and_le_right C₁ C₂) s h⟩

/-- Safety survives composition: one safe component is enough. -/
theorem safe_and_of_left {ts : TS S} {C₁ C₂ : Cage S} {U : S → Prop}
    (h : UnsafeUnreachable ts C₁ U) : UnsafeUnreachable ts (Cage.and C₁ C₂) U :=
  fun s hs => h s (reach_mono (and_le_left C₁ C₂) s hs)

/-- Safety survives tightening. -/
theorem safe_of_le {ts : TS S} {C₁ C₂ : Cage S} {U : S → Prop}
    (hle : Cage.le C₁ C₂) (h : UnsafeUnreachable ts C₂ U) : UnsafeUnreachable ts C₁ U :=
  fun s hs => h s (reach_mono hle s hs)

/-- Goal reachability survives loosening. -/
theorem goal_of_le {ts : TS S} {C₁ C₂ : Cage S} {G : S → Prop}
    (hle : Cage.le C₁ C₂) (h : GoalReachable ts C₁ G) : GoalReachable ts C₂ G :=
  let ⟨s, hs, hg⟩ := h
  ⟨s, reach_mono hle s hs, hg⟩

/-! ### Goal reachability does not survive composition

Three states: `a` (start), `b`, `g` (goal). Two routes to the goal:
`a → g` directly, or `a → b → g`. Cage `C₁` keeps only the direct edge, cage
`C₂` keeps only the two-step route. Each cage alone reaches the goal; their
conjunction keeps no edge at all. -/

inductive Three
  | a | b | g
  deriving DecidableEq

open Three

def diamond : TS Three :=
  ⟨fun s s' => (s = a ∧ s' = g) ∨ (s = a ∧ s' = b) ∨ (s = b ∧ s' = g), a⟩

def C₁ : Cage Three := fun s s' => s = a ∧ s' = g
def C₂ : Cage Three := fun s s' => (s = a ∧ s' = b) ∨ (s = b ∧ s' = g)
def isGoal : Three → Prop := fun s => s = g

theorem c1_reaches : GoalReachable diamond C₁ isGoal :=
  ⟨g, Reach.step Reach.base (Or.inl ⟨rfl, rfl⟩) ⟨rfl, rfl⟩, rfl⟩

theorem c2_reaches : GoalReachable diamond C₂ isGoal :=
  ⟨g,
    Reach.step
      (Reach.step Reach.base (Or.inr (Or.inl ⟨rfl, rfl⟩)) (Or.inl ⟨rfl, rfl⟩))
      (Or.inr (Or.inr ⟨rfl, rfl⟩)) (Or.inr ⟨rfl, rfl⟩),
    rfl⟩

theorem and_reach_only_start : ∀ s, Reach diamond (Cage.and C₁ C₂) s → s = a := by
  intro s h
  induction h with
  | base => rfl
  | step _ _ hc _ =>
    match hc with
    | ⟨⟨_, h2⟩, Or.inl ⟨_, h5⟩⟩ => subst h2; cases h5
    | ⟨⟨h1, _⟩, Or.inr ⟨h4, _⟩⟩ => subst h1; cases h4

theorem and_not_reaches : ¬ GoalReachable diamond (Cage.and C₁ C₂) isGoal := by
  intro ⟨s, hs, hg⟩
  have hsa := and_reach_only_start s hs
  subst hsa
  cases hg

end Caging
