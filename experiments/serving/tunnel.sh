#!/usr/bin/env bash
# Local. Forwards localhost:8000 to the pod's vLLM. Idempotent; prints the pid.
set -euo pipefail
alias_name=${POD_SSH_ALIAS:-runpod-a40}
if pgrep -f "ssh -N -L 8000:127.0.0.1:8000 $alias_name" >/dev/null; then echo "tunnel already up"; exit 0; fi
ssh -N -L 8000:127.0.0.1:8000 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 "$alias_name" &
echo "tunnel pid $!"
for i in $(seq 1 30); do curl -sf http://localhost:8000/v1/models >/dev/null 2>&1 && { echo ready; exit 0; }; sleep 2; done
echo "endpoint not reachable through the tunnel" >&2; exit 1
