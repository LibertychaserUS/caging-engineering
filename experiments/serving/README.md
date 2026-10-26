# Model serving for the experiments

The pod named in `PREREGISTRATION.md` §0.4 serves one open-weight checkpoint at a time with vLLM
behind an OpenAI-compatible endpoint; the harness reaches it over an SSH tunnel. The pod is started
and stopped by the project owner only; nothing here starts or stops it.

    experiments/serving/pod_setup.sh      # once per pod: vllm + model downloads into /workspace/hf
    experiments/serving/serve.sh <role>   # on the pod: role = agent_primary | agent_secondary | judge_primary | judge_exploratory
    experiments/serving/tunnel.sh         # local: forwards localhost:8000 to the pod's vLLM
    experiments/run_all.sh                # local: the whole preregistered sequence, resumable

The SSH alias (`runpod-a40`) lives in the owner's `~/.ssh/config`; no address appears in this repository.
Environment for the harness after the tunnel is up:

    export CE_LLM_BASE_URL=http://localhost:8000/v1 CE_LLM_MODEL=<served model id> CE_LLM_API_KEY=none
