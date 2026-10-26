from __future__ import annotations

import pytest

from harness.tools import ClassifyContext

EXERCISE_DIR = "/work/leap"
TEST_FILE = "/work/leap/leap_test.py"
STUB_FILE = "/work/leap/leap.py"


@pytest.fixture
def ctx() -> ClassifyContext:
    return ClassifyContext(EXERCISE_DIR, (TEST_FILE,), (STUB_FILE,), EXERCISE_DIR)
