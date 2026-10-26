"""The checker: breadth-first reachability under a conjunction of cages.

``check(abs, cages, goal, max_steps)`` computes the set of abstract states
reachable from ``abs.s0`` along edges that *every* cage allows (the
``Reach ts (Cage.and ...)`` of ``formal/CagingCore.lean``), optionally
restricted to paths of at most ``max_steps`` edges.  It returns

* ``REACHABLE`` with a **witness**: a shortest allowed path from ``s0`` to some
  state of the goal set (empty if ``s0`` is itself a goal state), or
* ``UNREACHABLE`` with the **frontier**: every edge of the abstraction whose
  source is reachable and which at least one cage cuts, annotated (``cut_by``)
  with the names of the cages that cut it.  This is where every route is cut.

With ``max_steps`` the reachable set is "reachable within ``max_steps``
allowed edges" (BFS by depth).  If the goal is unreachable only because of the
bound, no cage cuts anything on the boundary and the frontier is empty; an
empty frontier under ``UNREACHABLE`` therefore reads "the bound alone".
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .graph import Abstraction, Cage, Edge

Status = Literal["REACHABLE", "UNREACHABLE"]


@dataclass
class Verdict:
    status: Status
    witness: list[Edge] | None
    """Shortest allowed path ``s0 -> goal`` when REACHABLE, else ``None``."""
    frontier: list[Edge] | None
    """When UNREACHABLE: edges out of the reachable set cut by some cage (edge-list order); else ``None``."""
    reachable: frozenset[str]
    """States reachable from ``s0`` under the conjunction (within ``max_steps`` if given)."""
    cut_by: dict[Edge, tuple[str, ...]] | None
    """For each frontier edge, the names of the cages that cut it; ``None`` when REACHABLE."""
    goal: str
    max_steps: int | None

    def to_json(self) -> dict[str, Any]:
        """A JSON-serialisable view (edges as 3-lists, frontier with its annotations)."""
        frontier: list[dict[str, Any]] | None = None
        if self.frontier is not None:
            cut = self.cut_by or {}
            frontier = [{"edge": list(e), "cut_by": list(cut.get(e, ()))} for e in self.frontier]
        return {
            "status": self.status,
            "goal": self.goal,
            "max_steps": self.max_steps,
            "witness": None if self.witness is None else [list(e) for e in self.witness],
            "frontier": frontier,
            "reachable": sorted(self.reachable),
        }


def check(
    abs: Abstraction,
    cages: Sequence[Cage],
    goal: str,
    max_steps: int | None = None,
) -> Verdict:
    """Decide whether ``abs.goals[goal]`` is reachable under the conjunction of ``cages``."""
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be non-negative")
    goal_states = abs.goal_set(goal)
    cage_list = list(cages)

    # One pass over the explicit edge list: which cages cut each edge.
    cut: dict[Edge, tuple[str, ...]] = {}
    succ: dict[str, list[Edge]] = {s: [] for s in abs.states}
    for edge in abs.edges:
        if edge in cut:
            continue  # duplicate edge
        src, label, dst = edge
        names = tuple(c.name for c in cage_list if not c(src, label, dst))
        cut[edge] = names
        if not names:
            succ[src].append(edge)

    # BFS by depth from s0 over allowed edges.
    dist: dict[str, int] = {abs.s0: 0}
    parent: dict[str, Edge] = {}
    order: list[str] = [abs.s0]
    queue: deque[str] = deque([abs.s0])
    while queue:
        s = queue.popleft()
        d = dist[s]
        if max_steps is not None and d >= max_steps:
            continue
        for edge in succ[s]:
            t = edge[2]
            if t in dist:
                continue
            dist[t] = d + 1
            parent[t] = edge
            order.append(t)
            queue.append(t)

    reachable = frozenset(dist)
    hits = [s for s in order if s in goal_states]  # discovery order = non-decreasing depth
    if hits:
        target = hits[0]
        path: list[Edge] = []
        while target != abs.s0:
            edge = parent[target]
            path.append(edge)
            target = edge[0]
        path.reverse()
        return Verdict("REACHABLE", path, None, reachable, None, goal, max_steps)

    frontier: list[Edge] = []
    cut_by: dict[Edge, tuple[str, ...]] = {}
    for edge in abs.edges:
        if edge[0] in reachable and cut[edge] and edge not in cut_by:
            frontier.append(edge)
            cut_by[edge] = cut[edge]
    return Verdict("UNREACHABLE", None, frontier, reachable, cut_by, goal, max_steps)
