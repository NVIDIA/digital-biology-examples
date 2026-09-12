# Copyright (c) 2025-2026 NVIDIA Corporation.
import os
from boltz2_client import Boltz2SyncClient

client = Boltz2SyncClient(base_url=os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000"), timeout=1200)
sequence = 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG'
from uuid import uuid4
from boltz2_client import Polymer, Ligand, PredictionRequest

request = PredictionRequest(
    polymers=[Polymer(id="A", molecule_type="protein", sequence=sequence)],
    ligands=[Ligand(id="LIG", smiles="CCO", predict_affinity=True, output_affinity_embedding=True)],
    diffusion_samples=2, max_parallel_samples=1, diffusion_samples_affinity=1,
    complex_id="example_" + uuid4().hex[:12], write_full_pae=True, write_full_pde=True,
)
result = client.predict(request, output_dir="results/examples/nim_1_9")
print("Confidence:", result.confidence_scores)
print("Affinity embedding dimensions:", len(result.affinities["LIG"].affinity_embedding[0]))
print("Server matrix directory:", request.complex_id)
