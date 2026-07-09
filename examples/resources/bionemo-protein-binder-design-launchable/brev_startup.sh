#!/usr/bin/env bash
# Copyright (c) 2026, NVIDIA CORPORATION. Licensed under the Apache License, Version 2.0 (the "License") you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
#
# Brev Launchable bootstrap (VM Mode) for the Proteina-Complexa + Boltz-2 binder-design example.
# Paste this as the Launchable *startup script*. It clones this repo (if not already present) and
# runs setup.sh, which builds Proteina-Complexa, fetches weights + AF2 params, starts a local
# Boltz-2 NIM, and serves a widget-capable JupyterLab on :8888.
#
# Provide these in the Launchable environment / secrets:
#   NGC_API_KEY    required   nvapi-... for the local Boltz-2 NIM (image pull + weight download).
#                             For an event, use a short-lived, scoped key and revoke it afterwards.
#   GITHUB_TOKEN   optional   only if you point this at a private mirror (used just for the clone).
#
# Optional overrides:
#   PBD_REPO_URL   (default: NVIDIA/digital-biology-examples)   PBD_REPO_BRANCH (default: main)
#   PBD_REPO_DIR   (default: $HOME/digital-biology-examples)
set -uo pipefail

REPO_URL="${PBD_REPO_URL:-https://github.com/NVIDIA/digital-biology-examples.git}"
REPO_BRANCH="${PBD_REPO_BRANCH:-main}"
REPO_DIR="${PBD_REPO_DIR:-$HOME/digital-biology-examples}"
SUBDIR="examples/resources/bionemo-protein-binder-design-launchable"
export PATH="$HOME/.local/bin:$PATH"

# --- NGC_API_KEY (required for the local Boltz-2 NIM) ---------------------------------------------
# Brev Launchables have no separate "secret" field — provide the key HERE, in this pasted script.
#   Option A (embed, so attendees need no key): uncomment the line below and paste an event key.
#     The key is readable on each VM while valid, so use a SHORT-LIVED, SCOPED key and revoke it
#     right after the event.
# export NGC_API_KEY='nvapi-...'
#   Option B (bring-your-own-key): leave it commented; each user exports NGC_API_KEY in the Brev
#     terminal and re-runs this script, or enters it in the notebook's first cell.
# -------------------------------------------------------------------------------------------------

echo "=== [brev_startup] $(date +%H:%M:%S) clone $REPO_URL ($REPO_BRANCH) ==="
if [ ! -d "$REPO_DIR/.git" ]; then
    url="$REPO_URL"
    if [ -n "${GITHUB_TOKEN:-}" ]; then          # private mirror: inject token just for the clone
        url="https://${GITHUB_TOKEN}@${REPO_URL#https://}"
    fi
    git clone --branch "$REPO_BRANCH" --depth 1 "$url" "$REPO_DIR" \
        || git clone "$url" "$REPO_DIR"           # fall back to default branch (checked below)
    git -C "$REPO_DIR" remote set-url origin "$REPO_URL" 2>/dev/null || true  # scrub any token from disk
else
    echo "repo already present at $REPO_DIR — updating"
    git -C "$REPO_DIR" fetch --depth 1 origin "$REPO_BRANCH" 2>/dev/null \
        && git -C "$REPO_DIR" checkout "$REPO_BRANCH" 2>/dev/null || true
fi

SETUP="$REPO_DIR/$SUBDIR/setup.sh"
if [ ! -f "$SETUP" ]; then
    echo "ERROR: setup.sh not found at $SETUP — check PBD_REPO_BRANCH ($REPO_BRANCH)."
    exit 1
fi

if [ -z "${NGC_API_KEY:-}" ]; then
    echo "WARNING: NGC_API_KEY not set — the local Boltz-2 NIM will be skipped."
    echo "         Set NGC_API_KEY (nvapi-...) in the Launchable environment and re-run this script."
fi

echo "=== [brev_startup] running setup.sh ==="
bash "$SETUP"
echo "=== [brev_startup] done — open JupyterLab (port 8888) and run"
echo "    $SUBDIR/Complexa_Binder_Design.ipynb ==="
