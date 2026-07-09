#!/usr/bin/env bash
# Copyright (c) 2026, NVIDIA CORPORATION. Licensed under the Apache License, Version 2.0 (the "License") you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
#
# Brev Launchable setup script (VM Mode, Ubuntu 22.04+, 1x A100 80GB) for the de novo protein binder
# design workflow using NVIDIA Proteina-Complexa + Boltz-2 (local NIM). Idempotent + phase-marked.
#
# Builds everything (Complexa + weights + AF2 params + Boltz-2 NIM cache) on the LARGEST writable
# volume, because cloud GPU instances often have a tiny root disk (e.g. 97 GB) plus a big scratch
# volume (e.g. /ephemeral). Override the location with PBD_WORK=/path.
#
# Secrets (set in the pasted startup script / your shell):
#   NGC_API_KEY   required for the local Boltz-2 NIM (image pull + weights).
#                 (Proteina-Complexa + AF2 weights are public; no key needed.)
#
# Produces ~/.complexa_env, registers a "Python (Complexa)" Jupyter kernel, and serves a
# widget-capable JupyterLab on :8888. Logs to ~/complexa_setup.log.
set -uo pipefail
LOG="$HOME/complexa_setup.log"
exec > >(tee -a "$LOG") 2>&1
mark() { echo "=== [$(date +%H:%M:%S)] $* ==="; }
SETUP_FAIL=0
fail() { echo "!!! ERROR: $*"; SETUP_FAIL=1; }
export DEBIAN_FRONTEND=noninteractive
export PATH="$HOME/.local/bin:$PATH"

AGENT_TOOLKIT_REPO="${AGENT_TOOLKIT_REPO:-https://github.com/NVIDIA-BioNeMo/bionemo-agent-toolkit}"
COMPLEXA_GIT="${COMPLEXA_GIT:-https://github.com/NVIDIA-Digital-Bio/Proteina-Complexa}"
BOLTZ2_IMAGE="${BOLTZ2_IMAGE:-nvcr.io/nim/mit/boltz2:latest}"
MIN_FREE_GB="${PBD_MIN_FREE_GB:-90}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "$HOME")"

# --- pick a work dir on the largest writable volume (root disks are often tiny) -------------------
pick_workdir() {
    local best="$HOME" bestkb=0 d kb
    for d in "${PBD_WORK:-}" /ephemeral /raid /scratch /workspace /data /mnt/* "$HOME"; do
        [ -n "$d" ] && [ -d "$d" ] || continue
        mkdir -p "$d/.pbd_wtest" 2>/dev/null || continue
        rmdir "$d/.pbd_wtest" 2>/dev/null || true
        kb=$(df -Pk "$d" 2>/dev/null | awk 'NR==2{print $4}')
        [ -n "$kb" ] || continue
        if [ "$kb" -gt "$bestkb" ]; then bestkb=$kb; best=$d; fi
    done
    printf '%s' "$best"
}
WORK="$(pick_workdir)/complexa-binder-design"
if ! mkdir -p "$WORK" 2>/dev/null; then WORK="$HOME/complexa-binder-design"; mkdir -p "$WORK"; fi
COMPLEXA_REPO="$WORK/Proteina-Complexa"
SKILL_ROOT="$WORK/bionemo-agent-toolkit"
SKILL="$SKILL_ROOT/workflows/generative_protein_binder_design/complexa-binder-design"
NIMCACHE="$WORK/nimcache_boltz2"
AF2_DIR="$SKILL/community_models/ckpts/AF2"
FREE_GB=$(( $(df -Pk "$WORK" 2>/dev/null | awk 'NR==2{print $4}') / 1024 / 1024 ))

# Keep build/download caches + temp off the (often tiny) root disk too.
export UV_CACHE_DIR="$WORK/.uv-cache" PIP_CACHE_DIR="$WORK/.pip-cache" \
       XDG_CACHE_HOME="$WORK/.cache" HF_HOME="$WORK/.hf" TMPDIR="$WORK/.tmp"
mkdir -p "$UV_CACHE_DIR" "$PIP_CACHE_DIR" "$XDG_CACHE_HOME" "$HF_HOME" "$TMPDIR" 2>/dev/null || true

# ---------------------------------------------------------------------------
mark "Phase 0: base packages + uv  (work dir: $WORK — ${FREE_GB} GB free)"
if [ "$FREE_GB" -lt "$MIN_FREE_GB" ]; then
    echo "!!! WARNING: only ${FREE_GB} GB free on $WORK (need ~${MIN_FREE_GB} GB)."
    echo "!!! Set PBD_WORK to a larger volume, or deploy with a bigger disk. Continuing anyway..."
fi
sudo apt-get update -y >/dev/null 2>&1 || true
sudo apt-get install -y git curl wget unzip build-essential >/dev/null 2>&1 || true
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version || fail "uv install failed"

# ---------------------------------------------------------------------------
mark "Phase 1: clone + build Proteina-Complexa (uv env, weights) on $WORK"
[ -d "$COMPLEXA_REPO/.git" ] || git clone --depth 1 "$COMPLEXA_GIT" "$COMPLEXA_REPO"
cd "$COMPLEXA_REPO"
[ -d "$COMPLEXA_REPO/.venv" ] || ./env/build_uv_env.sh   # FULL build (JAX/colabdesign for generation)
# shellcheck disable=SC1091
source "$COMPLEXA_REPO/.venv/bin/activate"
# emits env.sh (needed by the CLI: target list, generate). The first attempt right after the venv
# build can fail transiently, so retry until env.sh appears.
for _a in 1 2 3; do
    complexa init uv 2>&1 | tail -6 || true
    [ -s "$COMPLEXA_REPO/env.sh" ] && { echo "complexa init ok (attempt $_a)"; break; }
    echo "complexa init (attempt $_a) produced no env.sh; retrying in 8s..."; sleep 8
done
if [ ! -s "$COMPLEXA_REPO/env.sh" ]; then
    fail "complexa init did not create env.sh after retries (see output above; check disk on $WORK)."
fi
# shellcheck disable=SC1091
source "$COMPLEXA_REPO/env.sh" 2>/dev/null || true
[ -f "$COMPLEXA_REPO/ckpts/complexa.ckpt" ] || complexa download --complexa-all || fail "complexa download failed"

# ---------------------------------------------------------------------------
mark "Phase 2: skill scripts (agent-toolkit) + ipSAE + python deps + Jupyter kernel"
[ -d "$SKILL_ROOT/.git" ] || git clone --depth 1 "$AGENT_TOOLKIT_REPO" "$SKILL_ROOT"
uv pip install numpy gemmi pyyaml pandas matplotlib requests \
    jupyterlab ipywidgets ipymolstar py3Dmol 2>&1 | tail -2 || \
    pip install numpy gemmi pyyaml pandas matplotlib requests jupyterlab ipywidgets ipymolstar py3Dmol 2>&1 | tail -2
( cd "$SKILL" && bash scripts/fetch_ipsae.sh ) || echo "ipSAE fetch failed (non-fatal)"

# Register the Complexa venv as a selectable Jupyter kernel (with env) so it works in Brev's JupyterLab
# (the default 'Python 3' kernel is a *different* env and fails with 'No module named numpy').
python -m ipykernel install --user --name complexa --display-name "Python (Complexa)" 2>/dev/null || true
KJ="$HOME/.local/share/jupyter/kernels/complexa/kernel.json"
if [ -f "$KJ" ]; then
    python - "$KJ" "$COMPLEXA_REPO" "$SKILL" "$AF2_DIR" <<'PYK'
import json, os, sys
kj, repo, skill, af2 = sys.argv[1:5]
d = json.load(open(kj))
d["env"] = {
    "COMPLEXA_REPO": repo,
    "COMPLEXA_SKILL": skill,
    "AF2_DIR": af2,
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
mark "Phase 3: AF2-Multimer params (~5 GB public; only for reward-guided best-of-n + AF2)"
AF2_TAR_URL="${AF2_TAR_URL:-https://storage.googleapis.com/alphafold/alphafold_params_2022-12-06.tar}"
if [ "${PBD_SETUP_AF2:-1}" = "0" ]; then
    echo "PBD_SETUP_AF2=0 -> skipping AF2 params (add later with scripts/setup_af2_params.sh)."
elif ls "$AF2_DIR"/params/params_model_1_multimer_v3.npz >/dev/null 2>&1; then
    echo "AF2 params already present at $AF2_DIR/params"
else
    mkdir -p "$AF2_DIR"
    # Resumable (-c), retried ~5 GB download straight into the notebook's AF2_DIR. (The skill
    # script's default landed under COMPLEXA_REPO, mismatching AF2_DIR -> "params present: False";
    # and its single wget under `set -e` aborts on any transient drop.)
    if ! ls "$AF2_DIR"/params_model_*_multimer_v3.npz >/dev/null 2>&1; then
        for a in 1 2 3; do
            echo "AF2 params download attempt $a (~5 GB, resumable) ..."
            wget -c -q --tries=3 --timeout=60 -O "$AF2_DIR/af2.tar" "$AF2_TAR_URL" && break
            echo "  attempt $a failed; retrying in 10s"; sleep 10
        done
        tar -xf "$AF2_DIR/af2.tar" -C "$AF2_DIR" 2>/dev/null && rm -f "$AF2_DIR/af2.tar" \
            || echo "AF2 tar extract failed (partial download?)"
    fi
    # Build the params/ symlink layout colabdesign expects (+ verify), pinned to AF2_DIR.
    ( cd "$SKILL" && bash scripts/setup_af2_params.sh "$AF2_DIR" ) >/dev/null 2>&1 || true
    if ls "$AF2_DIR"/params/params_model_1_multimer_v3.npz >/dev/null 2>&1; then
        echo "AF2 params ready at $AF2_DIR/params"
    else
        echo "AF2 params NOT installed (optional — the default single-pass workflow does not need them)."
        echo "  Add later:  source ~/.complexa_env && bash '$SKILL/scripts/setup_af2_params.sh' \"\$AF2_DIR\""
    fi
fi

# ---------------------------------------------------------------------------
mark "Phase 4: local Boltz-2 NIM (:8000), cache on $NIMCACHE"
if [ -n "${NGC_API_KEY:-}" ]; then
    printf '%s' "$NGC_API_KEY" | sudo docker login nvcr.io -u '$oauthtoken' --password-stdin >/dev/null 2>&1 \
        && echo "nvcr login ok" || fail "nvcr login failed (check NGC_API_KEY)"
    mkdir -p "$NIMCACHE"; chmod 777 "$NIMCACHE"
    if ! sudo docker ps --format '{{.Names}}' | grep -q '^boltz2$'; then
        sudo docker rm -f boltz2 >/dev/null 2>&1 || true
        sudo docker run -d --name boltz2 --gpus all --shm-size=8g \
            -e NGC_API_KEY="$NGC_API_KEY" -v "$NIMCACHE:/opt/nim/.cache" \
            -p 8000:8000 "$BOLTZ2_IMAGE" || fail "failed to start Boltz-2 NIM"
        echo "Boltz-2 NIM starting (first run downloads weights + builds engines)."
    fi
    # Background self-heal: the model download can fail transiently ("error decoding response
    # body") and exit the container. Poll health for ~30 min and restart the container if it is
    # not running yet -- the same manual restart that reliably recovers it. Detached so it
    # survives this script exiting.
    setsid bash -c '
      tries=0
      for _w in $(seq 1 60); do
        sleep 30
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8000/v1/health/ready 2>/dev/null)
        [ "$code" = "200" ] && { echo "[watchdog $(date +%H:%M:%S)] Boltz-2 healthy"; break; }
        st=$(sudo docker inspect -f "{{.State.Status}}" boltz2 2>/dev/null || echo missing)
        if [ "$st" != "running" ] && [ "$tries" -lt 4 ]; then
          tries=$((tries+1)); echo "[watchdog $(date +%H:%M:%S)] Boltz-2 $st -> restart #$tries"
          sudo docker start boltz2 >/dev/null 2>&1 || sudo docker restart boltz2 >/dev/null 2>&1 || true
        fi
      done ' >> "$LOG" 2>&1 &
    echo "Boltz-2 health watchdog started (self-heals transient download failures)."
else
    echo "NGC_API_KEY not set -> skipping local Boltz-2 NIM. Set it and re-run this script."
    fail "NGC_API_KEY missing"
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
# Serve from the launchable folder so users land right on the notebook (not the home dir).
NBDIR="$SCRIPT_DIR"
if [ ! -f "$NBDIR/Complexa_Binder_Design.ipynb" ]; then
    FOUND="$(find "$HOME" "$WORK" -maxdepth 7 -name 'Complexa_Binder_Design.ipynb' 2>/dev/null | head -1)"
    [ -n "$FOUND" ] && NBDIR="$(dirname "$FOUND")"
fi
echo "JupyterLab root dir: $NBDIR"
sudo systemctl stop jupyter.service 2>/dev/null || true
fuser -k 8888/tcp 2>/dev/null || true
sleep 2
( cd "$NBDIR" && setsid nohup jupyter lab --ip 0.0.0.0 --port 8888 --no-browser \
    --ServerApp.token= --ServerApp.password= --ServerApp.allow_remote_access=True \
    --ServerApp.root_dir="$NBDIR" --ServerApp.default_url="/lab/tree/Complexa_Binder_Design.ipynb" \
    </dev/null >"$HOME/jupyter.log" 2>&1 & ) || true
sleep 6
ss -ltn 2>/dev/null | grep -q ':8888' && echo "Complexa JupyterLab serving on :8888 (open via Brev; hard-refresh)." \
    || echo "WARN: JupyterLab not on :8888 yet; start it manually (see README)."

# ---------------------------------------------------------------------------
if [ "$SETUP_FAIL" = "1" ]; then
    mark "SETUP FINISHED WITH ERRORS — see the '!!!' lines above (common cause: disk full → set PBD_WORK)"
else
    mark "SETUP COMPLETE"
fi
echo "COMPLEXA_SETUP_DONE (fail=$SETUP_FAIL)"
