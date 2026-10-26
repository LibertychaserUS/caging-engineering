"""cagecheck: reachability of a goal set on a finite abstraction under a conjunction of cages.

Modules
-------
graph       data types: Abstraction, Edge, Cage, NamedCage, conj
checker     BFS checker returning a Verdict (witness or annotated frontier)
bruteforce  independent naive enumeration used only for validation
t1          the H3 Part B abstraction of a T1 episode and the cage library K1-K6
"""

from .graph import Abstraction, Cage, Edge, NamedCage, allow_all, block_edges, block_labels, conj
from .checker import Verdict, check

__all__ = [
    "Abstraction",
    "Cage",
    "Edge",
    "NamedCage",
    "Verdict",
    "allow_all",
    "block_edges",
    "block_labels",
    "check",
    "conj",
]
