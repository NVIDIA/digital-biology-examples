# Copyright (c) 2025-2026 NVIDIA Corporation.
import argparse
import os
from pathlib import Path
from boltz2_client import (
    Boltz2SyncClient, Polymer, PredictionRequest,
    convert_a3m_to_multimer_csv, create_paired_msa_per_chain,
)

parser = argparse.ArgumentParser(description="Predict a two-chain complex from supplied A3M files.")
parser.add_argument("chain_a", type=Path)
parser.add_argument("chain_b", type=Path)
args = parser.parse_args()
conversion = convert_a3m_to_multimer_csv(a3m_files={"A": args.chain_a, "B": args.chain_b})
msa = create_paired_msa_per_chain(conversion)
request = PredictionRequest(polymers=[
    Polymer(id=chain, molecule_type="protein", sequence=seq, msa=msa[chain])
    for chain, seq in conversion.query_sequences.items()
])
client = Boltz2SyncClient(base_url=os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000"), timeout=1200)
result = client.predict(request, output_dir="results/examples/paired")
print(result.iptm_scores)
