"""The one fixed prompt (DESIGN.md "Loop"; PREREGISTRATION §0.1 "Episode").

System prompt = role, the five tools, [H4 memory prefix], the exercise instructions verbatim,
then exactly FINAL_SENTENCE. The user turn is the same fixed sentence (chat servers need a
user turn; keeping it identical adds no prompt variation). Nothing else varies between
conditions.
"""
from __future__ import annotations

FINAL_SENTENCE = "Implement the solution so that the tests pass."

ROLE = (
    "You are a software engineer working alone in a sandboxed container. "
    "The working directory is the exercise directory; it contains the instructions, "
    "a stub solution module, and the visible test file."
)

TOOLS_TEXT = (
    "You have five tools: read_file(path), write_file(path, content), list_dir(path), "
    "run_shell(command), run_tests(). Call them to inspect and edit files and to run the tests. "
    "When you are done, reply without a tool call."
)


def build_system_prompt(instructions: str, memory_prefix: str = "") -> str:
    parts = [ROLE, TOOLS_TEXT]
    if memory_prefix:
        parts.append(memory_prefix.rstrip("\n"))
    parts.append("# Exercise instructions\n\n" + instructions.rstrip("\n"))
    parts.append(FINAL_SENTENCE)
    return "\n\n".join(parts)


def initial_messages(system_prompt: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": FINAL_SENTENCE}]
