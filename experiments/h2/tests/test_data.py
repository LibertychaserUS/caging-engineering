from h2.data import (Example, Problem, compose_solution, extract_examples, parse_assert_examples,
                     parse_doctest_examples, prompt_imports)

HE_IDS = ["HumanEval/0", "HumanEval/23", "HumanEval/108"]
MBPP_IDS = ["Mbpp/2", "Mbpp/3", "Mbpp/4"]


def test_real_humaneval_prompts(humaneval):
    ex0 = extract_examples(humaneval["HumanEval/0"])
    assert [e.as_tuple() for e in ex0] == [
        ("has_close_elements([1.0, 2.0, 3.0], 0.5)", "False"),
        ("has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)", "True"),
    ]
    ex23 = extract_examples(humaneval["HumanEval/23"])
    assert [e.as_tuple() for e in ex23] == [("strlen('')", "0"), ("strlen('abc')", "3")]
    # HumanEval/108 writes its examples as `f(x) == y` with no expected output
    ex108 = extract_examples(humaneval["HumanEval/108"])
    assert ex108 and all(e.want == "" and "==" in e.source for e in ex108)
    # a prompt without doctest lines yields None (excluded from E and criterion 1)
    without = [tid for tid, p in humaneval.items() if ">>>" not in p.prompt]
    assert without and all(extract_examples(humaneval[t]) is None for t in without)
    assert all(extract_examples(humaneval[t]) for t in HE_IDS)


def test_real_mbpp_prompts(mbpp):
    for tid in MBPP_IDS:
        ex = extract_examples(mbpp[tid])
        assert ex and all(e.kind == "assert" and e.source.startswith("assert ") for e in ex)
    assert extract_examples(mbpp["Mbpp/3"])[0].as_tuple() == "assert is_not_prime(2) == False"
    assert sum(1 for p in mbpp.values() if extract_examples(p) is None) == 0


def test_doctest_parser_synthetic():
    text = '''
    Examples:
    >>> f(1)
    [1,
     2]
    >>> f(2)

    >>> g(1) == 3
    >>> h("ab
    cd")
    'x'
    >>> k(
    ...   3)
    9
    '''
    ex = parse_doctest_examples(text)
    assert [e.as_tuple() for e in ex] == [
        ("f(1)", "[1,\n2]"), ("f(2)", ""), ("g(1) == 3", ""), ("k(\n  3)", "9")]  # malformed h(...) dropped


def test_no_examples_is_none():
    p = Problem("X/1", "humaneval", 'def f(x):\n    """Return x. Example: f(1) ==> 1"""\n', "f")
    assert extract_examples(p) is None
    assert parse_assert_examples("no asserts here\nassertion failed\n") == []
    assert parse_assert_examples("  assert f(1) == 2\nassert (\n") == [Example("assert", "assert f(1) == 2", None)]


def test_compose_solution_full_definition_gets_missing_imports():
    p = Problem("X/2", "humaneval", 'from typing import List\n\n\ndef f(xs: List[int]) -> int:\n    """doc"""\n', "f")
    sol = compose_solution(p, "def f(xs: List[int]) -> int:\n    return len(xs)")
    assert sol.startswith("from typing import List\n")
    assert sol.count("def f(") == 1
    assert prompt_imports(p.prompt) == ["from typing import List"]
    # already imported: not duplicated
    sol2 = compose_solution(p, "from typing import List\ndef f(xs: List[int]) -> int:\n    return 1")
    assert sol2.count("from typing import List") == 1


def test_compose_solution_completion_is_appended():
    p = Problem("X/3", "humaneval", 'def f(x):\n    """doc"""\n', "f")
    assert compose_solution(p, "    return x") == 'def f(x):\n    """doc"""\n    return x\n'
