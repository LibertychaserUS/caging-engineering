"""Independent brute-force reachability, used only to validate ``checker.py``.

Two deliberately naive algorithms that share nothing with the checker except
the data types in ``graph.py``:

* unbounded: Kleene fixpoint iteration over the explicit edge list — keep
  sweeping the whole list, adding ``dst`` whenever ``src`` is already in the
  set and the edge survives every cage, until a full sweep adds nothing;
* bounded (``max_steps``): enumerate *every* path of at most ``max_steps``
  surviving edges as an explicit list of edges (cycles included), and collect
  the endpoints.  This is exponential, so it runs only when a crude upper bound
  on the number of paths fits ``path_budget``; in every bounded case a second
  naive method also runs — depth-layered iteration (``S_0 = {s0}``,
  ``S_{i+1} = post(S_i)``, no visited set, union of the layers) — and when both
  ran they must agree or ``brute`` raises.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .graph import Abstraction, Cage, Edge


@dataclass(frozen=True)
class BruteResult:
    reached: bool
    reachable: frozenset[str]
    min_depth: dict[str, int] | None
    """Shortest path length per reachable state; only computed in the bounded mode."""


def surviving_edges(abs: Abstraction, cages: Sequence[Cage]) -> list[Edge]:
    """The explicit edges that no cage cuts (filtering done here, independently)."""
    kept: list[Edge] = []
    for src, label, dst in abs.edges:
        cut = False
        for cage in cages:
            if not cage(src, label, dst):
                cut = True
                break
        if not cut:
            kept.append((src, label, dst))
    return kept


def reachable_fixpoint(abs: Abstraction, cages: Sequence[Cage]) -> frozenset[str]:
    kept = surviving_edges(abs, cages)
    region: set[str] = {abs.s0}
    while True:
        before = len(region)
        for src, _label, dst in kept:
            if src in region:
                region.add(dst)
        if len(region) == before:
            return frozenset(region)


def reachable_paths(
    abs: Abstraction, cages: Sequence[Cage], max_steps: int
) -> tuple[frozenset[str], dict[str, int]]:
    """Endpoints of all paths of length <= max_steps, by explicit path enumeration."""
    kept = surviving_edges(abs, cages)
    by_src: dict[str, list[Edge]] = {}
    for edge in kept:
        by_src.setdefault(edge[0], []).append(edge)

    min_depth: dict[str, int] = {abs.s0: 0}
    stack: list[list[Edge]] = [[]]  # every partial path is materialised
    while stack:
        path = stack.pop()
        if len(path) >= max_steps:
            continue
        end = path[-1][2] if path else abs.s0
        for edge in by_src.get(end, ()):
            longer = path + [edge]
            dst = edge[2]
            if dst not in min_depth or min_depth[dst] > len(longer):
                min_depth[dst] = len(longer)
            stack.append(longer)
    return frozenset(min_depth), min_depth


def reachable_layers(
    abs: Abstraction, cages: Sequence[Cage], max_steps: int
) -> tuple[frozenset[str], dict[str, int]]:
    """Depth-layered iteration without a visited set: layer i = endpoints of all length-i paths."""
    kept = surviving_edges(abs, cages)
    min_depth: dict[str, int] = {abs.s0: 0}
    layer: set[str] = {abs.s0}
    for i in range(1, max_steps + 1):
        nxt: set[str] = set()
        for src, _label, dst in kept:
            if src in layer:
                nxt.add(dst)
        for s in nxt:
            min_depth.setdefault(s, i)
        layer = nxt
    return frozenset(min_depth), min_depth


def path_count_bound(abs: Abstraction, cages: Sequence[Cage], max_steps: int) -> int:
    """Crude upper bound on the number of paths of length <= max_steps: sum of d_max**i."""
    degree: dict[str, int] = {}
    for src, _label, _dst in surviving_edges(abs, cages):
        degree[src] = degree.get(src, 0) + 1
    d = max(degree.values(), default=0)
    return sum(d**i for i in range(max_steps + 1))


def brute(
    abs: Abstraction,
    cages: Sequence[Cage],
    goal: str,
    max_steps: int | None = None,
    path_budget: int = 200_000,
) -> BruteResult:
    goal_states = abs.goal_set(goal)
    if max_steps is None:
        region = reachable_fixpoint(abs, cages)
        depth: dict[str, int] | None = None
    else:
        region, depth = reachable_layers(abs, cages, max_steps)
        if path_count_bound(abs, cages, max_steps) <= path_budget:
            region2, depth2 = reachable_paths(abs, cages, max_steps)
            if region2 != region or depth2 != depth:
                raise AssertionError("bounded brute-force methods disagree (path enumeration vs layers)")
    reached = any(s in goal_states for s in region)
    return BruteResult(reached, region, depth)
