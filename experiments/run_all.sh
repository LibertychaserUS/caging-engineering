#!/usr/bin/env bash
# The whole preregistered sequence, in the order the paper needs the data; every step is resumable.
# Local machine runs containers; the pod serves models (experiments/serving/). Nothing here starts or
# stops the pod. Phases (each skipped if already complete):
#   0 smoke on the pinned agent model (manifest smoke exercises; never analysed)
#   1 H1 primary (L0-L6 x 137 x seeds 1 2 3)      agent_primary
#   2 H3 (41 combinations)                        agent_primary
#   3 H4 (12 sequences)                           agent_primary
#   4 H2 proposals + self-report + arguments      agent_primary   (then truth + gate E locally)
#   5 H1 secondary (1 seed)                       agent_secondary; H2 proposals for the secondary proposer
#   6 H2 judge gates                              judge_primary, then judge_exploratory
set -euo pipefail
cd "$(dirname "$0")"
alias_name=${POD_SSH_ALIAS:-runpod-a40}
RESULTS=${CE_RESULTS:-$HOME/Projects/_shared/caging-data/results}
export CE_EXERCISM_DIR=${CE_EXERCISM_DIR:-$HOME/Projects/_shared/caging-data/exercism-python}
export CE_LLM_BASE_URL=http://localhost:8000/v1 CE_LLM_API_KEY=none
export CE_JUDGE_BASE_URL=http://localhost:8000/v1 CE_JUDGE_API_KEY=none
UV="uv run -q --python 3.12 --with httpx"

serve() {  # role -> sets CE_LLM_MODEL to the served id
  ssh "$alias_name" "bash -s $1" < serving/serve.sh
  serving/tunnel.sh
  export CE_LLM_MODEL=$(curl -sf http://localhost:8000/v1/models | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"][0]["id"])')
  export CE_JUDGE_MODEL=$CE_LLM_MODEL
  echo "== serving $CE_LLM_MODEL ($1)"
}
h() { (cd harness && $UV python -m harness.runner "$@"); }

serve agent_primary
h --hypothesis h1 --model primary --seeds 1 --exercises leap two-fer --out "$RESULTS/smoke-pinned" --parallel 2
h --hypothesis h1 --model primary --seeds 1 2 3 --out "$RESULTS/h1" --parallel "${CE_PARALLEL:-4}"
h --hypothesis h3 --model primary --seeds 1       --out "$RESULTS/h3" --parallel "${CE_PARALLEL:-4}"
h --hypothesis h4 --model primary --seeds 1       --out "$RESULTS/h4" --parallel "${CE_PARALLEL:-4}"
(cd h2 && $UV --with evalplus==0.3.1 python run.py propose --dataset both --out "$RESULTS/h2/primary")
(cd h2 && $UV --with evalplus==0.3.1 python run.py truth   --dataset both --out "$RESULTS/h2/primary")
(cd h2 && $UV --with evalplus==0.3.1 python run.py gates --skip-judge --dataset both --out "$RESULTS/h2/primary")

serve agent_secondary
h --hypothesis h1 --model secondary --seeds 1 --out "$RESULTS/h1-secondary" --parallel "${CE_PARALLEL:-4}"
(cd h2 && $UV --with evalplus==0.3.1 python run.py propose --dataset both --out "$RESULTS/h2/secondary")
(cd h2 && $UV --with evalplus==0.3.1 python run.py truth   --dataset both --out "$RESULTS/h2/secondary")

serve judge_primary
for p in primary secondary; do (cd h2 && $UV --with evalplus==0.3.1 python run.py gates --skip-e --judge-tag primary --dataset both --out "$RESULTS/h2/$p"); done
serve judge_exploratory
for p in primary secondary; do (cd h2 && $UV --with evalplus==0.3.1 python run.py gates --skip-e --judge-tag exploratory --dataset both --out "$RESULTS/h2/$p"); done
for p in primary secondary; do (cd h2 && $UV --with evalplus==0.3.1 python run.py analyze --out "$RESULTS/h2/$p"); done
echo "all phases complete; results under $RESULTS"
