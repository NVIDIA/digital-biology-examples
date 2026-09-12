# Copyright (c) 2025-2026 NVIDIA Corporation.
import os
from boltz2_client import Boltz2SyncClient

client = Boltz2SyncClient(base_url=os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000"), timeout=1200)
sequence = 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG'
result = client.predict_protein_structure(sequence=sequence, output_dir="results/examples/protein")
print(result.confidence_scores)
