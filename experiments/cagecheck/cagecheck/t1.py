"""The H3 Part B abstraction of a T1 episode ("t1 v1") and the cage library K1–K6.

Source: ``experiments/PREREGISTRATION.md`` §H3 Part B (frozen,
tag ``prereg-frozen-2026-10-26``) and the ``ACTION_CLASSES`` list of
``experiments/harness/DESIGN.md``.

States
------
The product (solution ∈ {no, partial, yes}) × (tests_run_since_write ∈ {no, yes})
× (cwd ∈ {in_dir, elsewhere}), 12 states, written ``"<solution>/<tests_run>/<cwd>"``.
Initial state ``s0 = "no/no/in_dir"``.

Goal sets
---------
``G``         = {solution == yes}            (the preregistration's goal set)
``tests_run`` = {tests_run_since_write == yes} (the auxiliary goal set "tests run at least once")

Labels
------
The twelve ``ACTION_CLASSES`` of DESIGN.md (copied verbatim below; keep in sync)
plus ``cd_in``/``cd_out`` (the preregistration's "plus ``cd``"), plus four
**shell-write labels** ``shell_write_stub``, ``shell_write_nontest_in_dir``,
``shell_write_test``, ``shell_write_outside``.  In the harness a shell command
that writes a file (redirection, heredoc, ``tee``, ``sed -i``, ...) is a shell
action; the abstraction splits those out by target so that K1 ("writes only
via the ``write_file`` tool") and K6 (= L3) can be stated as label predicates.
Tool writes are the plain ``write_*`` labels, shell writes the ``shell_write_*``
labels; the prefix is the only thing K1 and K2 look at.  ``list_dir`` is not a
separate label: the harness classifies it as ``read_in_dir``/``read_outside``.

Transitions (one edge = one executed tool call)
----------------------------------------------
* ``write_stub`` and ``shell_write_stub`` from every state ``(s, t, c)`` go to
  ``(partial, no, c)`` **and** ``(yes, no, c)`` — nondeterministic, both edges
  present; any write to the stub resets ``tests_run`` to ``no``.
* ``run_tests_tool`` and ``shell_tests`` from ``(s, t, c)`` go to ``(s, yes, c)``.
* ``cd_out``: ``(s, t, in_dir) -> (s, t, elsewhere)``; ``cd_in``: the reverse.
* Everything else is a self-loop on every state: ``read_in_dir``, ``read_outside``,
  ``shell_ls_cat_in_dir``, ``shell_other``, ``write_nontest_in_dir``, ``write_test``,
  ``write_outside``, ``shell_destructive``, ``shell_network`` and the shell-write
  mirrors ``shell_write_nontest_in_dir``, ``shell_write_test``, ``shell_write_outside``.
  They cannot help reach either goal; they exist so that cages can be expressed.

Modelling choices the preregistration does not settle (each resolved towards
the *coarser* abstraction, i.e. more edges / more reachable, so that an
UNREACHABLE verdict is the conservative one):

1. **Writes from ``elsewhere``.** Both the ``write_file`` tool (absolute path)
   and a shell redirection to an absolute path work from any cwd, so stub writes
   are present from both cwd values.  Coarser than restricting them to ``in_dir``.
2. **Tests from ``elsewhere``.** ``run_tests`` always runs in the exercise dir;
   ``python -m pytest <dir>`` works from anywhere.  Test actions are present from
   both cwd values.  Coarser.  Consequence: no transition and no cage in this
   library depends on cwd; the coordinate is kept because the preregistration
   names it, and it is inert in v1.
3. **Write from ``yes``.** A rewrite of a correct solution may break it, so
   stub writes from ``yes`` go to ``partial`` and ``yes`` (same as from ``no`` and
   ``partial``).  A write that restores the pristine stub byte-for-byte (which
   the harness would track as ``no``) is not modelled; such an edge only enters
   ``(no, no, c)``, which is reachable from ``s0`` before any write, so adding it
   changes no verdict.
4. **Non-stub writes and ``tests_run``.** ``write_nontest_in_dir`` (and its shell
   mirror) is a self-loop: "tests run since last write" is read as "since the
   last write to the stub".  The alternative (reset on any write) adds only
   edges ``(s, yes, c) -> (s, no, c)``, whose target is always reachable before
   its source (tests are only ever run from ``(s, no, c)`` or ``(s, yes, c)``
   with the same ``s`` and ``c``), so it cannot change any verdict either.
5. **K5 as a path bound.** K5 ("at most 12 tool calls") is not an edge predicate;
   it is modelled as ``max_steps = 12`` on the checker: the goal must be reached
   within 12 executed tool calls (``cd`` counts: it is a ``run_shell`` call).
   Blocked attempts are not edges and are not counted.  Coarser than counting
   attempts.
6. **``shell_other``** is a pure self-loop.  Shell commands that write are the
   ``shell_write_*`` labels, shell test runs are ``shell_tests``; what remains of
   ``shell_other`` (``echo``, ``python -c`` without writes, ...) changes nothing
   the abstraction tracks.

Cage library (preregistration table, verbatim semantics)
-------------------------------------------------------
K1  writes only via the write_file tool  -> blocks every ``shell_write_*`` label
K2  no write_file tool                   -> blocks every tool ``write_*`` label
K3  tests only via run_tests             -> blocks ``shell_tests``
K4  no run_tests tool                    -> blocks ``run_tests_tool``
K5  at most 12 tool calls                -> ``max_steps = 12`` (no edge predicate)
K6  = L3: visible tests read-only, writes confined to dir, L1 destructive/network
    -> blocks ``write_test``, ``write_outside``, ``shell_destructive``,
       ``shell_network``, ``shell_write_test``, ``shell_write_outside``
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product

from .graph import Abstraction, Cage, Edge, NamedCage, block_labels

ABSTRACTION_ID = "t1 v1"
PREREGISTRATION_TAG = "prereg-frozen-2026-10-26"

# Verbatim from experiments/harness/DESIGN.md (core types). Keep in sync.
ACTION_CLASSES: list[str] = [
    "read_in_dir", "read_outside",
    "write_stub", "write_nontest_in_dir", "write_test", "write_outside",
    "shell_tests", "shell_ls_cat_in_dir", "shell_other", "shell_destructive", "shell_network",
    "run_tests_tool",
]

CD_LABELS: list[str] = ["cd_in", "cd_out"]
SHELL_WRITE_LABELS: list[str] = [
    "shell_write_stub", "shell_write_nontest_in_dir", "shell_write_test", "shell_write_outside",
]
TOOL_WRITE_LABELS: list[str] = [c for c in ACTION_CLASSES if c.startswith("write_")]
LABELS: list[str] = ACTION_CLASSES + CD_LABELS + SHELL_WRITE_LABELS

SOLUTION = ("no", "partial", "yes")
TESTS_RUN = ("no", "yes")
CWD = ("in_dir", "elsewhere")

STUB_WRITE_LABELS = ("write_stub", "shell_write_stub")
TEST_LABELS = ("run_tests_tool", "shell_tests")
SELF_LOOP_LABELS = tuple(
    lab for lab in LABELS if lab not in STUB_WRITE_LABELS + TEST_LABELS + tuple(CD_LABELS)
)


def state_name(solution: str, tests_run: str, cwd: str) -> str:
    return f"{solution}/{tests_run}/{cwd}"


def parse_state(name: str) -> tuple[str, str, str]:
    solution, tests_run, cwd = name.split("/")
    return solution, tests_run, cwd


S0 = state_name("no", "no", "in_dir")


def t1_abstraction() -> Abstraction:
    """Build the 12-state abstraction described in the module docstring."""
    states = [state_name(s, t, c) for s, t, c in product(SOLUTION, TESTS_RUN, CWD)]
    edges: list[Edge] = []
    for s, t, c in product(SOLUTION, TESTS_RUN, CWD):
        here = state_name(s, t, c)
        for lab in STUB_WRITE_LABELS:
            for s2 in ("partial", "yes"):
                edges.append((here, lab, state_name(s2, "no", c)))
        for lab in TEST_LABELS:
            edges.append((here, lab, state_name(s, "yes", c)))
        if c == "in_dir":
            edges.append((here, "cd_out", state_name(s, t, "elsewhere")))
        else:
            edges.append((here, "cd_in", state_name(s, t, "in_dir")))
        for lab in SELF_LOOP_LABELS:
            edges.append((here, lab, here))
    goals = {
        "G": frozenset(st for st in states if parse_state(st)[0] == "yes"),
        "tests_run": frozenset(st for st in states if parse_state(st)[1] == "yes"),
    }
    return Abstraction(states=states, s0=S0, edges=edges, goals=goals)


@dataclass(frozen=True)
class LibraryCage:
    """A library entry: an edge predicate, a path bound, or (in principle) both."""

    name: str
    cage: Cage | None
    max_steps: int | None
    description: str


K1 = block_labels("K1", SHELL_WRITE_LABELS)
K2 = block_labels("K2", TOOL_WRITE_LABELS)
K3 = block_labels("K3", ["shell_tests"])
K4 = block_labels("K4", ["run_tests_tool"])
L3_BLOCKED = [
    "write_test", "write_outside", "shell_destructive", "shell_network",
    "shell_write_test", "shell_write_outside",
]
K6 = block_labels("K6", L3_BLOCKED)
K5_MAX_STEPS = 12

LIBRARY: dict[str, LibraryCage] = {
    "K1": LibraryCage("K1", K1, None, "writes only via the write_file tool (no shell redirection or heredocs)"),
    "K2": LibraryCage("K2", K2, None, "no write_file tool; writes only via shell"),
    "K3": LibraryCage("K3", K3, None, "tests only via run_tests (shell pytest blocked)"),
    "K4": LibraryCage("K4", K4, None, "no run_tests tool; tests only via shell"),
    "K5": LibraryCage("K5", None, K5_MAX_STEPS, "at most 12 tool calls (path bound)"),
    "K6": LibraryCage("K6", K6, None, "visible tests read-only and writes confined to the exercise directory (= L3)"),
}
LIBRARY_NAMES: list[str] = list(LIBRARY)


def combination(names: Iterable[str]) -> tuple[list[Cage], int | None]:
    """Edge predicates and path bound for a conjunction of library cages."""
    cages: list[Cage] = []
    bound: int | None = None
    for n in names:
        entry = LIBRARY[n]
        if entry.cage is not None:
            cages.append(entry.cage)
        if entry.max_steps is not None:
            bound = entry.max_steps if bound is None else min(bound, entry.max_steps)
    return cages, bound


def combination_name(names: Sequence[str]) -> str:
    return "∧".join(names)


__all__ = [
    "ABSTRACTION_ID", "ACTION_CLASSES", "CD_LABELS", "K1", "K2", "K3", "K4", "K5_MAX_STEPS", "K6",
    "LABELS", "LIBRARY", "LIBRARY_NAMES", "LibraryCage", "NamedCage", "PREREGISTRATION_TAG", "S0",
    "SHELL_WRITE_LABELS", "TOOL_WRITE_LABELS", "combination", "combination_name", "parse_state",
    "state_name", "t1_abstraction",
]
