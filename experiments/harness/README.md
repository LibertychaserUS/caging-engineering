# Harness

Reference implementation of the agent harness for H1/H3/H4 (`DESIGN.md`; `../PREREGISTRATION.md` §0).
Python 3.12, `httpx` only; Docker CLI for the sandbox; no agent framework.

## Setup

    cd experiments/harness
    uv sync --extra dev                      # or: uv run --python 3.12 --with pytest --with httpx <cmd>
    docker build -t ce-harness:py312 experiments/harness/docker   # from the repository root

Environment variables (names only; never written to disk or to the repository):
`CE_LLM_BASE_URL`, `CE_LLM_MODEL`, `CE_LLM_API_KEY` (endpoint), `CE_IMAGE` (default `ce-harness:py312`),
`CE_EXERCISM_DIR` (checkout of exercism/python at the pinned commit; or pass `--exercism-dir`).

## Tests (no Docker, no model)

    uv run --python 3.12 --with pytest --with httpx pytest -q

## Container smoke check (needs the image)

    uv run --python 3.12 --with httpx python scripts/smoke_container.py

## Runs

Plan only: add `--dry-run` to any command below (exit 2 if a manifest field is still null).

    python -m harness.runner --hypothesis h1 --model primary   --seeds 1 2 3 --out results/h1 --parallel 4
    python -m harness.runner --hypothesis h1 --model secondary --seeds 1     --out results/h1-secondary --parallel 4
    python -m harness.runner --hypothesis h3 --model primary   --seeds 1     --out results/h3 --parallel 4
    python -m harness.runner --hypothesis h4 --model primary   --seeds 1     --out results/h4 --parallel 4

Smoke episodes only: append `--exercises hello-world leap` (the manifest's smoke exercises are
excluded from every analysis). Output: `episodes.jsonl` (one `EpisodeRecord` per line), `audit/`,
`diff/`, `final/`, `run.json`. Re-running the same command resumes; a harness error is retried once,
then recorded with `harness_error` and appended to the manifest's `harness_failures`.
