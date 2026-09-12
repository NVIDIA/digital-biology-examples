"""Exercise NIM 1.9 against a real GPU endpoint and retain validation evidence."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from boltz2_client import Boltz2Client, Ligand, Polymer, PredictionRequest


async def validate(args):
    client = Boltz2Client(base_url=args.base_url, timeout=args.timeout)
    health = await client.health_check()
    metadata = await client.get_service_metadata()
    if not metadata.version.startswith("1.9"):
        raise RuntimeError(f"Expected NIM 1.9, got {metadata.version}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "service_metadata.json").write_text(metadata.model_dump_json(indent=2))
    complex_id = "client_validation_" + uuid4().hex[:12]
    protein = Polymer(id="A", molecule_type="protein", sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG")
    request = PredictionRequest(polymers=[protein], complex_id=complex_id,
                                diffusion_samples=2, max_parallel_samples=1,
                                write_full_pae=True, write_full_pde=True)
    result = await client.predict(request, output_dir=args.output_dir / "protein")
    assert len(result.structures) == 2
    assert all("data_" in structure.structure for structure in result.structures)
    assert result.pae is None and result.pde is None
    assert result.complex_pde_scores and result.complex_ipde_scores
    # This pair exercises API behavior; it is not an accuracy benchmark.
    affinity_request = PredictionRequest(
        polymers=[protein], ligands=[Ligand(id="LIG", smiles="CC(=O)Oc1ccccc1C(=O)O",
                                           predict_affinity=True, output_affinity_embedding=True)],
        diffusion_samples_affinity=1,
    )
    affinity_result = await client.predict(affinity_request, output_dir=args.output_dir / "affinity")
    affinity = affinity_result.affinities["LIG"]
    assert affinity.affinity_embedding and all(len(row) == 384 for row in affinity.affinity_embedding)
    matrices = []
    if args.server_output_dir:
        import numpy as np
        for kind in ("pae", "pde"):
            files = list((args.server_output_dir / complex_id / kind).glob("*.npz"))
            assert len(files) == 2, f"Expected two {kind} files under {complex_id}"
            for file in files:
                with np.load(file, allow_pickle=False) as data:
                    matrix = data[kind]
                    assert matrix.ndim == 2 and matrix.shape[0] == matrix.shape[1]
                    assert np.isfinite(matrix).all()
                matrices.append(str(file))
    report = {"health": health.status, "nim_version": metadata.version,
              "complex_id": complex_id, "structures": len(result.structures),
              "embedding_dimension": len(affinity.affinity_embedding[0]),
              "verified_matrix_files": matrices,
              "matrix_files_checked": bool(args.server_output_dir)}
    (args.output_dir / "validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--output-dir", type=Path, default=Path("results/live"))
    parser.add_argument("--server-output-dir", type=Path)
    asyncio.run(validate(parser.parse_args()))
