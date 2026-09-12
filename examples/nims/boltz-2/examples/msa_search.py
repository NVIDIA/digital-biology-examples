# Copyright (c) 2025-2026 NVIDIA Corporation.
import os
from boltz2_client import Boltz2SyncClient

client = Boltz2SyncClient(base_url=os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000"), timeout=1200)
sequence = 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG'
# MSA Search is a separate service; only installed databases can be selected.
client.configure_msa_search(msa_endpoint_url=os.environ["MSA_NIM_URL"], timeout=1200)
result = client.predict_with_msa_search(
    sequence=sequence, databases=[os.getenv("MSA_DATABASE", "pdb70_220313")],
    output_dir="results/examples/msa",
)
print(result.confidence_scores)
