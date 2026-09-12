# Copyright (c) 2025-2026 NVIDIA Corporation.
import argparse
import os
from pathlib import Path
from boltz2_client import Boltz2SyncClient

parser = argparse.ArgumentParser(description="Predict from a Boltz YAML file.")
parser.add_argument("yaml_file", nargs="?", type=Path, default=Path(__file__).parent / "data/protein_ligand.yaml")
args = parser.parse_args()
client = Boltz2SyncClient(base_url=os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000"), timeout=1200)
result = client.predict_from_yaml_file(yaml_file=args.yaml_file, output_dir="results/examples/yaml")
print(result.confidence_scores)
