#!/usr/bin/env bash
# Run ON the pod once. Installs vLLM and pre-downloads the pinned checkpoints into /workspace/hf.
# Llama-3.1-8B-Instruct is gated: HF_TOKEN must be set on the pod by the project owner (never stored here).
set -euo pipefail
export HF_HOME=/workspace/hf
mkdir -p "$HF_HOME"
python3 -m pip install -q --upgrade pip
python3 -m pip install -q "vllm>=0.6,<0.9" "huggingface_hub[cli]"
for m in Qwen/Qwen2.5-Coder-14B-Instruct Qwen/Qwen2.5-Coder-7B-Instruct meta-llama/Llama-3.1-8B-Instruct Qwen/Qwen2.5-14B-Instruct; do
  echo "== $m"; huggingface-cli download "$m" --quiet >/dev/null && echo ok || echo "FAILED (gated? set HF_TOKEN)"
done
# Record the resolved revisions so they can be copied into experiments/manifest.json.
python3 - <<'PY'
import json, os, pathlib
root = pathlib.Path(os.environ["HF_HOME"]) / "hub"
out = {}
for d in root.glob("models--*"):
    ref = d / "refs" / "main"
    if ref.exists():
        out[d.name.replace("models--", "").replace("--", "/")] = ref.read_text().strip()
print(json.dumps(out, indent=2))
PY
