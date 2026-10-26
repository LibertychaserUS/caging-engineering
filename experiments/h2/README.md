# H2 — persuadability of the adjudicator

Implements `experiments/PREREGISTRATION.md` §H2 (frozen). Python 3.12; deps `httpx`, `evalplus==0.3.1`.

Run from this directory, in this order (each step is resumable; `--dataset humaneval|mbpp|both`):

```
uv run --python 3.12 --with httpx --with evalplus==0.3.1 python run.py propose --out results/h2/<proposer-tag>/
uv run --python 3.12 --with httpx --with evalplus==0.3.1 python run.py truth   --out results/h2/<proposer-tag>/ --parallel 4
uv run --python 3.12 --with httpx --with evalplus==0.3.1 python run.py gates   --out results/h2/<proposer-tag>/ --judge-tag primary
uv run --python 3.12 --with httpx --with evalplus==0.3.1 python run.py analyze --out results/h2/<proposer-tag>/ --primary-judge primary
```

`truth` runs `python -m evalplus.evaluate --dataset <ds> --samples <out>/samples_<ds>.jsonl --parallel <n>`
(EvalPlus's own sandbox, on the host) and needs every proposal present. `gates` runs gate E in
`docker run --rm -i --network none --memory 512m --cpus 1 ce-harness:py312 python -` (image from
`experiments/harness/docker/`), then gates B/C/D on the judge endpoint. Run `gates` once per judge
with a distinct `--judge-tag`; `analyze` reports every tag and applies the decision rule to each.

Environment (names only; values are never printed or written):
proposer `CE_LLM_BASE_URL`, `CE_LLM_MODEL`, `CE_LLM_API_KEY`; judge `CE_JUDGE_BASE_URL`, `CE_JUDGE_MODEL`, `CE_JUDGE_API_KEY`.

Outputs in `--out`: `proposals.jsonl`, `self_report.jsonl` (gate A), `arguments.jsonl`, `samples_*.jsonl` +
`*_eval_results.json` (EvalPlus), `truth.jsonl`, `gate_e.jsonl`, `gates_<judge-tag>.jsonl`, `results.json`, `results.md`.

Running the proposer or judge against a hosted endpoint instead of the project's own server is an
infrastructure deviation: log it in `experiments/DEVIATIONS.md` before the run. `--limit N` exists for
pipeline checks only; never analyse a limited run.

Tests (fakes only, no model calls): `uv run --python 3.12 --with pytest --with httpx --with evalplus==0.3.1 pytest -q`
