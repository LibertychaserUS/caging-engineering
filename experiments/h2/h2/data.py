"""EvalPlus data access and extraction of the executable examples in a prompt.

HumanEval+: the examples are doctest lines inside the function docstring
(``>>> expr`` followed by the expected-output lines).  MBPP+: the examples
are the ``assert ...`` lines inside the prompt docstring.  A problem whose
prompt contains neither yields ``None`` and is excluded from gate E and from
criterion 1 (preregistration H2).
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, asdict
from typing import Iterable

DATASETS = ("humaneval", "mbpp")


@dataclass(frozen=True)
class Problem:
    task_id: str
    dataset: str  # "humaneval" | "mbpp"
    prompt: str
    entry_point: str


@dataclass(frozen=True)
class Example:
    kind: str          # "doctest" | "assert"
    source: str        # the expression (doctest) or the full assert statement
    want: str | None   # expected output text for doctest; None for assert

    def as_tuple(self):
        return (self.source, self.want) if self.kind == "doctest" else self.source


def load_problems(dataset: str) -> dict[str, Problem]:
    """Load HumanEval+ or MBPP+ through the pinned evalplus package (v0.3.1)."""
    if dataset == "humaneval":
        from evalplus.data import get_human_eval_plus
        raw = get_human_eval_plus()
    elif dataset == "mbpp":
        from evalplus.data import get_mbpp_plus
        raw = get_mbpp_plus()
    else:
        raise ValueError(f"unknown dataset {dataset!r}; expected one of {DATASETS}")
    return {
        tid: Problem(task_id=tid, dataset=dataset, prompt=p["prompt"], entry_point=p["entry_point"])
        for tid, p in raw.items()
    }


def datasets_for(arg: str) -> list[str]:
    if arg == "both":
        return list(DATASETS)
    if arg in DATASETS:
        return [arg]
    raise ValueError(f"--dataset must be humaneval, mbpp or both (got {arg!r})")


# ---------------------------------------------------------------- docstrings

def _docstrings(prompt: str) -> list[str]:
    """All docstrings in the prompt (module and function level), via ast.

    Falls back to a regex over triple-quoted blocks when the prompt does not
    parse (it always should for EvalPlus prompts; the fallback is defensive).
    """
    try:
        tree = ast.parse(prompt)
    except SyntaxError:
        return [m.group(2) for m in re.finditer(r'("""|\'\'\')(.*?)\1', prompt, re.S)]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                out.append(doc)
    return out


# ------------------------------------------------------------------ doctest

_PS1 = re.compile(r"^(?P<indent>[ \t]*)>>>(?: (?P<src>.*)|$)")
_PS2 = re.compile(r"^(?P<indent>[ \t]*)\.\.\.(?: (?P<src>.*)|$)")


def parse_doctest_examples(text: str) -> list[Example]:
    """Tolerant doctest parser: ``>>>``/``...`` source lines followed by want lines.

    The want block ends at a blank line, at the next ``>>>`` line, or at the
    end of the text.  Unlike ``doctest.DocTestParser`` it does not raise on
    inconsistent indentation (several HumanEval docstrings have it).
    Examples with no want are kept with ``want=""`` (doctest semantics: the
    expression must produce no output).
    """
    lines = text.splitlines()
    examples: list[Example] = []
    i = 0
    while i < len(lines):
        m = _PS1.match(lines[i])
        if not m:
            i += 1
            continue
        src_lines = [m.group("src") or ""]
        i += 1
        while i < len(lines):
            m2 = _PS2.match(lines[i])
            if not m2:
                break
            src_lines.append(m2.group("src") or "")
            i += 1
        want_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and not _PS1.match(lines[i]):
            want_lines.append(lines[i].strip())
            i += 1
        source = "\n".join(src_lines).strip()
        if source and _parses(source):
            examples.append(Example("doctest", source, "\n".join(want_lines)))
    return examples


def _parses(source: str) -> bool:
    """True when the source is a valid expression or statement.

    A few HumanEval doctest lines are malformed (a string literal broken
    across lines, a missing ``==``); they cannot be executed and are dropped,
    exactly like an ``assert`` line that does not parse.
    """
    for mode in ("eval", "exec"):
        try:
            ast.parse(source, mode=mode)
            return True
        except SyntaxError:
            continue
    return False


# ------------------------------------------------------------------- assert

_ASSERT = re.compile(r"^[ \t]*(assert\b.*)$")


def parse_assert_examples(text: str) -> list[Example]:
    """``assert ...`` lines; only those that parse as a Python statement are kept."""
    out = []
    for line in text.splitlines():
        m = _ASSERT.match(line)
        if not m:
            continue
        stmt = m.group(1).strip()
        try:
            ast.parse(stmt)
        except SyntaxError:
            continue
        out.append(Example("assert", stmt, None))
    return out


# ------------------------------------------------------------------- public

def extract_examples(problem: Problem) -> list[Example] | None:
    """Executable examples of a problem, or None when the prompt has none."""
    docs = _docstrings(problem.prompt)
    if problem.dataset == "humaneval":
        found = [e for d in docs for e in parse_doctest_examples(d)]
    elif problem.dataset == "mbpp":
        found = [e for d in docs for e in parse_assert_examples(d)]
        if not found:  # defensive: asserts outside a docstring
            found = parse_assert_examples(problem.prompt)
    else:
        raise ValueError(problem.dataset)
    return found or None


def examples_to_json(examples: list[Example] | None) -> list[dict] | None:
    return None if examples is None else [asdict(e) for e in examples]


def examples_from_json(items: Iterable[dict] | None) -> list[Example] | None:
    return None if items is None else [Example(**d) for d in items]


# ------------------------------------------------------- solution assembly

_IMPORT_LINE = re.compile(r"^(?:import\s+\S.*|from\s+\S+\s+import\s+.*)$")


def prompt_imports(prompt: str) -> list[str]:
    """Top-level import lines of a prompt, in order."""
    return [ln for ln in prompt.splitlines() if _IMPORT_LINE.match(ln.strip()) and not ln.startswith((" ", "\t"))]


def compose_solution(problem: Problem, code: str) -> str:
    """The executable artefact that ground truth and gates B–E see.

    If the proposer returned a full definition of the entry point, that is
    the solution, with any prompt import lines it omitted prepended (so a
    missing ``from typing import List`` does not count as a hidden failure
    that no reader could see).  Otherwise the code is treated as a completion
    of the prompt, HumanEval style, and appended to it.
    """
    code = code.rstrip() + "\n"
    if re.search(rf"^[ \t]*def\s+{re.escape(problem.entry_point)}\s*\(", code, re.M):
        missing = [ln for ln in prompt_imports(problem.prompt) if ln.strip() not in code]
        return ("\n".join(missing) + "\n\n" if missing else "") + code
    return problem.prompt.rstrip("\n") + "\n" + code
