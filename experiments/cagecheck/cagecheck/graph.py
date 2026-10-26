"""Data types shared by the checker and the brute-force validator.

An :class:`Abstraction` is a finite labelled transition system with an initial
state and one or more *named* goal sets.  A :class:`Cage` is an edge predicate
``(src, label, dst) -> bool`` (``True`` = the edge stays available) carrying a
``name`` so that a frontier can say which cage cut which edge.  ``conj`` is the
conjunction of cages of ``formal/CagingCore.lean`` (``Cage.and``): an edge
survives only if every component allows it.

Nothing algorithmic lives here; ``checker.py`` and ``bruteforce.py`` share
only these definitions.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

Edge = tuple[str, str, str]
"""``(src, label, dst)``.  Labels are action classes (see ``t1.py``) or arbitrary strings."""


@runtime_checkable
class Cage(Protocol):
    """An edge predicate with a name."""

    name: str

    def __call__(self, src: str, label: str, dst: str) -> bool: ...


@dataclass(frozen=True)
class NamedCage:
    """A cage built from a plain callable."""

    name: str
    allow: Callable[[str, str, str], bool]

    def __call__(self, src: str, label: str, dst: str) -> bool:
        return bool(self.allow(src, label, dst))

    def __repr__(self) -> str:
        return f"NamedCage({self.name!r})"


def conj(*cages: Cage) -> NamedCage:
    """Conjunction: an edge is allowed iff every component cage allows it.

    With no arguments this is the trivial cage that allows everything.
    """
    parts = tuple(cages)
    if not parts:
        return allow_all()
    name = "∧".join(c.name for c in parts)

    def allow(src: str, label: str, dst: str) -> bool:
        return all(c(src, label, dst) for c in parts)

    return NamedCage(name, allow)


def allow_all(name: str = "⊤") -> NamedCage:
    """The cage that cuts nothing."""
    return NamedCage(name, lambda src, label, dst: True)


def block_labels(name: str, labels: Iterable[str]) -> NamedCage:
    """A cage that cuts every edge whose label is in ``labels`` (any src/dst)."""
    blocked = frozenset(labels)
    return NamedCage(name, lambda src, label, dst: label not in blocked)


def block_edges(name: str, edges: Iterable[Edge]) -> NamedCage:
    """A cage that cuts exactly the listed explicit edges."""
    blocked = frozenset(edges)
    return NamedCage(name, lambda src, label, dst: (src, label, dst) not in blocked)


@dataclass(frozen=True)
class Abstraction:
    """A finite labelled transition system with named goal sets.

    ``states`` must be unique; ``s0`` and every edge endpoint must be a state;
    every goal set must be a subset of ``states``.  Duplicate edges are
    tolerated (they do not change reachability).
    """

    states: list[str]
    s0: str
    edges: list[Edge]
    goals: dict[str, frozenset[str]]

    def __post_init__(self) -> None:
        state_set = set(self.states)
        if len(state_set) != len(self.states):
            raise ValueError("states must be unique")
        if self.s0 not in state_set:
            raise ValueError(f"s0 {self.s0!r} is not a state")
        for src, label, dst in self.edges:
            if src not in state_set or dst not in state_set:
                raise ValueError(f"edge {(src, label, dst)!r} has an endpoint that is not a state")
        for gname, gset in self.goals.items():
            if not gset <= state_set:
                raise ValueError(f"goal set {gname!r} contains non-states: {sorted(gset - state_set)}")

    def goal_set(self, goal: str) -> frozenset[str]:
        try:
            return self.goals[goal]
        except KeyError:
            raise KeyError(f"unknown goal set {goal!r}; known: {sorted(self.goals)}") from None
