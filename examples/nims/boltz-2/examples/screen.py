# Copyright (c) 2025-2026 NVIDIA Corporation.
import os
from boltz2_client import Boltz2SyncClient

client = Boltz2SyncClient(base_url=os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000"), timeout=1200)
sequence = 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG'
from boltz2_client import VirtualScreening

# Small API example, not a validated binding pair or screening benchmark.
screener = VirtualScreening(client=client, max_workers=2)
result = screener.screen(target_sequence=sequence, compound_library=[
    {"name": "aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O"},
    {"name": "ethanol", "smiles": "CCO"},
], diffusion_samples_affinity=1)
result.save_results("results/examples/screening")
if result.failed_results:
    raise RuntimeError(result.failed_results)
print(result.get_top_hits(n=2))
