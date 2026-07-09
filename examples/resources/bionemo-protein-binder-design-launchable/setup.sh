#!/usr/bin/env bash
# Copyright (c) 2026, NVIDIA CORPORATION. Licensed under the Apache License, Version 2.0 (the "License") you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
#
# Brev Launchable setup script (VM Mode, Ubuntu 22.04+, 1x A100 80GB) for the
# de novo protein binder design workflow using NVIDIA Proteina-Complexa +
# Boltz-2 (local NIM). Idempotent + phase-marked; safe to re-run.
#
# Secrets (set in the Brev deploy env / your shell):
#   NGC_API_KEY   required for the local Boltz-2 NIM (image pull + weights).
#                 (Proteina-Complexa + AF2 weights are public; no key needed.)
#
# Produces ~/.complexa_env (source it before running the notebook) and leaves a
# local Boltz-2 NIM on :8000. Logs to ~/complexa_setup.log.
set -uo pipefail
LOG="$HOME/complexa_setup.log"
exec > >(tee -a "$LOG") 2>&1
mark() { echo "=== [$(date +%H:%M:%S)] $* ==="; }
export DEBIAN_FRONTEND=noninteractive
export PATH="$HOME/.local/bin:$PATH"

AGENT_TOOLKIT_REPO="${AGENT_TOOLKIT_REPO:-https://github.com/NVIDIA-BioNeMo/bionemo-agent-toolkit}"
COMPLEXA_GIT="${COMPLEXA_GIT:-https://github.com/NVIDIA-Digital-Bio/Proteina-Complexa}"
BOLTZ2_IMAGE="${BOLTZ2_IMAGE:-nvcr.io/nim/mit/boltz2:latest}"
WORK="$HOME"
COMPLEXA_REPO="$WORK/Proteina-Complexa"
SKILL_ROOT="$WORK/bionemo-agent-toolkit"
SKILL="$SKILL_ROOT/workflows/generative_protein_binder_design/complexa-binder-design"

# ---------------------------------------------------------------------------
mark "Phase 0: base packages + uv"
sudo apt-get update -y >/dev/null 2>&1 || true
sudo apt-get install -y git curl wget unzip build-essential >/dev/null 2>&1 || true
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version || { echo "uv install failed"; }

# ---------------------------------------------------------------------------
mark "Phase 1: clone + build Proteina-Complexa (uv env, weights)"
if [ ! -d "$COMPLEXA_REPO" ]; then
    git clone --depth 1 "$COMPLEXA_GIT" "$COMPLEXA_REPO"
fi
cd "$COMPLEXA_REPO"
if [ ! -d "$COMPLEXA_REPO/.venv" ]; then
    ./env/build_uv_env.sh          # FULL build (JAX/colabdesign needed for generation)
fi
# shellcheck disable=SC1091
source "$COMPLEXA_REPO/.venv/bin/activate"
complexa init uv || true            # emits env.sh (needed for the CLI: target list, generate)
# shellcheck disable=SC1091
source "$COMPLEXA_REPO/env.sh" 2>/dev/null || true
if [ ! -f "$COMPLEXA_REPO/ckpts/complexa.ckpt" ]; then
    complexa download --complexa-all   # public NGC weights (no key)
fi

# ---------------------------------------------------------------------------
mark "Phase 2: skill scripts (agent-toolkit) + ipSAE + python deps"
if [ ! -d "$SKILL_ROOT" ]; then
    git clone --depth 1 "$AGENT_TOOLKIT_REPO" "$SKILL_ROOT"
fi
# skill Stage-1/validation deps + notebook viz, into the Complexa venv
uv pip install numpy gemmi pyyaml pandas matplotlib requests \
    jupyterlab ipywidgets ipymolstar py3Dmol 2>&1 | tail -2 || \
    pip install numpy gemmi pyyaml pandas matplotlib requests jupyterlab ipywidgets ipymolstar py3Dmol 2>&1 | tail -2
( cd "$SKILL" && bash scripts/fetch_ipsae.sh ) || echo "ipSAE fetch failed (non-fatal)"

# Register the Complexa venv as a selectable Jupyter kernel so it works in Brev's JupyterLab
# (the default 'Python 3' kernel is a *different* env and fails with 'No module named numpy').
python -m ipykernel install --user --name complexa --display-name "Python (Complexa)" 2>/dev/null || true
KJ="$HOME/.local/share/jupyter/kernels/complexa/kernel.json"
if [ -f "$KJ" ]; then
    python - "$KJ" "$COMPLEXA_REPO" "$SKILL" <<'PYK'
import json, os, sys
kj, repo, skill = sys.argv[1:4]
d = json.load(open(kj))
d["env"] = {
    "COMPLEXA_REPO": repo,
    "COMPLEXA_SKILL": skill,
    "AF2_DIR": skill + "/community_models/ckpts/AF2",
    "BOLTZ2_URL": "http://localhost:8000/biology/mit/boltz2/predict",
    "XLA_PYTHON_CLIENT_PREALLOCATE": "false",
    "XLA_PYTHON_CLIENT_MEM_FRACTION": "0.7",
    "PATH": os.path.dirname(sys.executable) + ":" + os.path.expanduser("~/.local/bin")
            + ":/usr/local/bin:/usr/bin:/bin",
}
json.dump(d, open(kj, "w"), indent=1)
print("registered 'Python (Complexa)' Jupyter kernel")
PYK
fi

# ---------------------------------------------------------------------------
mark "Phase 3: AF2-Multimer params (public; for reward-guided best-of-n)"
# setup_af2_params.sh writes params under the skill dir (its CWD).
AF2_DIR="$SKILL/community_models/ckpts/AF2"
if [ ! -d "$AF2_DIR/params" ]; then
    ( cd "$SKILL" && bash scripts/setup_af2_params.sh ) || echo "AF2 params setup failed (bypass still works)"
fi

# ---------------------------------------------------------------------------
mark "Phase 4: local Boltz-2 NIM (:8000)"
if [ -n "${NGC_API_KEY:-}" ]; then
    printf '%s' "$NGC_API_KEY" | sudo docker login nvcr.io -u '$oauthtoken' --password-stdin >/dev/null 2>&1 \
        && echo "nvcr login ok" || echo "nvcr login failed"
    mkdir -p "$HOME/nimcache_boltz2"; chmod 777 "$HOME/nimcache_boltz2"
    if ! sudo docker ps --format '{{.Names}}' | grep -q '^boltz2$'; then
        sudo docker rm -f boltz2 >/dev/null 2>&1 || true
        sudo docker run -d --name boltz2 --gpus all --shm-size=8g \
            -e NGC_API_KEY="$NGC_API_KEY" -v "$HOME/nimcache_boltz2:/opt/nim/.cache" \
            -p 8000:8000 "$BOLTZ2_IMAGE"
        echo "Boltz-2 NIM starting (first run downloads weights + builds engines)."
    fi
else
    echo "NGC_API_KEY not set -> skipping local Boltz-2 NIM. Use hosted Boltz-2"
    echo "(export NVIDIA_API_KEY and set --endpoint hosted) or re-run with NGC_API_KEY."
fi

# ---------------------------------------------------------------------------
mark "Phase 5: write ~/.complexa_env"
cat > "$HOME/.complexa_env" <<EOF
export PATH="\$HOME/.local/bin:\$PATH"
export COMPLEXA_REPO="$COMPLEXA_REPO"
export COMPLEXA_BIN="$COMPLEXA_REPO/.venv/bin/complexa"
export COMPLEXA_SKILL="$SKILL"
export AF2_DIR="$AF2_DIR"
export BOLTZ2_URL="http://localhost:8000/biology/mit/boltz2/predict"
# keep JAX/AF2 from grabbing the whole GPU so reward-guided generation coexists with the Boltz-2 NIM
export XLA_PYTHON_CLIENT_PREALLOCATE=false
export XLA_PYTHON_CLIENT_MEM_FRACTION=0.7
# activate the Complexa venv + Hydra env (env.sh) for the CLI + skill scripts:
source "$COMPLEXA_REPO/.venv/bin/activate"
source "$COMPLEXA_REPO/env.sh" 2>/dev/null || true
EOF
echo "Wrote $HOME/.complexa_env"

# ---------------------------------------------------------------------------
mark "Phase 6: serve widget-capable JupyterLab from the Complexa venv on :8888"
# Brev's stock jupyter.service lacks the anywidget/ipywidgets front-end extensions, so the embedded
# Mol* views won't render there. Replace it, on the port Brev exposes, with the Complexa venv's
# JupyterLab (which has the extensions). Mirrors Brev's no-token/remote-access config.
NB="$(find "$HOME" -maxdepth 4 -name 'Complexa_Binder_Design.ipynb' 2>/dev/null | head -1)"
[ -n "$NB" ] && cp -f "$NB" "$HOME/Complexa_Binder_Design.ipynb" 2>/dev/null || true
sudo systemctl stop jupyter.service 2>/dev/null || true
fuser -k 8888/tcp 2>/dev/null || true
sleep 2
( cd "$HOME" && setsid nohup jupyter lab --ip 0.0.0.0 --port 8888 --no-browser \
    --ServerApp.token= --ServerApp.password= --ServerApp.allow_remote_access=True \
    --ServerApp.notebook_dir="$HOME" </dev/null >"$HOME/jupyter.log" 2>&1 & ) || true
sleep 6
if ss -ltn 2>/dev/null | grep -q ':8888'; then
    echo "Complexa JupyterLab serving on :8888 (open it via Brev; hard-refresh the browser)."
else
    echo "WARN: JupyterLab not on :8888 yet; start it manually (see README 'Seeing the 3D Mol* widgets')."
fi

mark "SETUP COMPLETE"
echo "COMPLEXA_SETUP_DONE"
