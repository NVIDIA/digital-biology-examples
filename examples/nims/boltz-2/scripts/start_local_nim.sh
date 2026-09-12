#!/usr/bin/env bash
# Start a pinned NIM with persistent model and prediction outputs.
set -euo pipefail
if [[ -z "${NGC_API_KEY:-}" && -n "${NVIDIA_API_KEY:-}" ]]; then
  export NGC_API_KEY="$NVIDIA_API_KEY"
fi
: "${NGC_API_KEY:?Set NGC_API_KEY or NVIDIA_API_KEY in the process environment}"
: "${LOCAL_NIM_CACHE:?Set LOCAL_NIM_CACHE}"
: "${LOCAL_NIM_OUTPUT:?Set LOCAL_NIM_OUTPUT}"

nvidia-smi >/dev/null
install -d -m 0700 "$LOCAL_NIM_CACHE" "$LOCAL_NIM_OUTPUT"
printf '%s' "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin

docker run -d --name "${BOLTZ2_CONTAINER_NAME:-boltz2-nim-1-9}" \
  --gpus all --shm-size=16G --user "$(id -u):$(id -g)" \
  -e NGC_API_KEY -e NIM_OUTPUT_PATH=/opt/nim/output \
  -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" \
  -v "$LOCAL_NIM_OUTPUT:/opt/nim/output" \
  -p "127.0.0.1:${BOLTZ2_PORT:-8000}:8000" \
  nvcr.io/nim/mit/boltz2:1.9.0

for attempt in $(seq 1 720); do
  if curl -fsS "http://localhost:${BOLTZ2_PORT:-8000}/v1/health/ready" >/dev/null; then
    echo "Boltz-2 NIM is ready."
    exit 0
  fi
  if [[ "$(docker inspect -f '{{.State.Running}}' "${BOLTZ2_CONTAINER_NAME:-boltz2-nim-1-9}")" != true ]]; then
    echo "Container exited; inspect its logs with docker logs." >&2
    exit 1
  fi
  sleep 5
done
echo "NIM did not become ready within 60 minutes; inspect container logs." >&2
exit 1
