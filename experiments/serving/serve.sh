#!/usr/bin/env bash
# Run ON the pod. Serves one role's checkpoint with vLLM on port 8000 (A40 48 GB, bf16).
set -euo pipefail
role=${1:?role: agent_primary | agent_secondary | judge_primary | judge_exploratory}
case "$role" in
  agent_primary)     model=Qwen/Qwen2.5-Coder-14B-Instruct ;;
  agent_secondary)   model=Qwen/Qwen2.5-Coder-7B-Instruct ;;
  judge_primary)     model=meta-llama/Llama-3.1-8B-Instruct ;;
  judge_exploratory) model=Qwen/Qwen2.5-14B-Instruct ;;
  *) echo "unknown role $role" >&2; exit 2 ;;
esac
export HF_HOME=/workspace/hf
pkill -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true
sleep 2
mkdir -p /workspace/logs
nohup python3 -m vllm.entrypoints.openai.api_server \
  --model "$model" --served-model-name "$model" \
  --dtype bfloat16 --max-model-len 16384 --gpu-memory-utilization 0.90 \
  --enable-prefix-caching --enable-auto-tool-choice --tool-call-parser hermes \
  --port 8000 --host 127.0.0.1 > "/workspace/logs/vllm-$role.log" 2>&1 &
echo "serving $model as role $role; log /workspace/logs/vllm-$role.log"
for i in $(seq 1 120); do
  if curl -sf http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then echo ready; exit 0; fi
  sleep 5
done
echo "vLLM did not become ready in 10 min; see the log" >&2; tail -20 "/workspace/logs/vllm-$role.log" >&2; exit 1
