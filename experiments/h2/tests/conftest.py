from __future__ import annotations

import pytest

from h2.llm import ChatResult


class FakeChat:
    """A ChatFn fake: answers from a queue or a function of the messages; records calls."""

    def __init__(self, answers=None, fn=None):
        self.answers = list(answers or [])
        self.fn = fn
        self.calls: list[dict] = []

    def __call__(self, messages, *, temperature, seed, max_tokens):
        self.calls.append({"messages": messages, "temperature": temperature, "seed": seed, "max_tokens": max_tokens})
        content = self.fn(messages) if self.fn else self.answers.pop(0)
        return ChatResult(content=content, finish_reason="stop", usage={"total_tokens": 1})


@pytest.fixture
def fake_chat():
    return FakeChat


def _try_load(dataset):
    try:
        from h2.data import load_problems
        return load_problems(dataset)
    except Exception as e:  # network or cache unavailable
        pytest.skip(f"EvalPlus {dataset} not available ({type(e).__name__}: {e})")


@pytest.fixture(scope="session")
def humaneval():
    return _try_load("humaneval")


@pytest.fixture(scope="session")
def mbpp():
    return _try_load("mbpp")
