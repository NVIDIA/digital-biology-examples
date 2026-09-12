"""Verify public Python methods and Bash entry points against actual NIM outputs."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from Bio.PDB import MMCIFParser
import pytest

from boltz2_client import (
    Boltz2Client, Boltz2SyncClient, MultiEndpointClient,
    Polymer, Ligand, PredictionRequest, AlignmentFileRecord, StructuralTemplate,
)
from boltz2_client.models import Modification, Atom, BondConstraint

pytestmark = pytest.mark.real_endpoint
ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000")
SEQUENCE = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
KRAS = "MTEYKLVVVGACGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQAQDLARSYGIPFIETSAKTRQGVDDAFYTLVREIRKHKE"


def assert_outputs(result, output):
    assert result.structures and result.confidence_scores
    assert np.isfinite(result.confidence_scores).all()
    saved = json.loads((output / "prediction_response.json").read_text())
    assert len(saved["structures"]) == len(result.structures)
    for file in output.glob("*.cif"):
        structure = MMCIFParser(QUIET=True).get_structure(file.stem, str(file))
        coords = np.array([atom.coord for atom in structure.get_atoms()])
        assert coords.size and np.isfinite(coords).all()
    assert list(output.glob("*.cif"))


def case(name, tmp_path):
    polymer = Polymer(id="A", molecule_type="protein", sequence=SEQUENCE)
    if name == "protein":
        return "predict_protein_structure", dict(sequence=SEQUENCE, diffusion_samples=2, max_parallel_samples=1)
    if name in {"smiles", "ccd", "pocket"}:
        kwargs = dict(protein_sequence=SEQUENCE)
        if name == "ccd":
            kwargs["ligand_ccd"] = "ATP"
        else:
            kwargs.update(ligand_smiles="CC(=O)Oc1ccccc1C(=O)O", predict_affinity=True,
                          output_affinity_embedding=True, diffusion_samples_affinity=1,
                          sampling_steps_affinity=10)
        if name == "pocket":
            kwargs["pocket_residues"] = [10, 15]
        return "predict_protein_ligand_complex", kwargs
    if name == "covalent":
        return "predict_covalent_complex", dict(protein_sequence=KRAS, ligand_ccd="U4U",
                                               covalent_bonds=[(12, "SG", "C22")])
    if name == "dna":
        return "predict_dna_protein_complex", dict(protein_sequences=[SEQUENCE], dna_sequences=["ATCGATCG"])
    if name == "msa":
        msa = {"custom": {"a3m": AlignmentFileRecord(alignment=f">query\n{SEQUENCE}\n", format="a3m", rank=0)}}
        return "predict_protein_structure", dict(sequence=SEQUENCE, msa=msa)
    if name == "advanced":
        return "predict_with_advanced_parameters", dict(polymers=[polymer], max_parallel_samples=1,
                                                        diffusion_samples=2, without_potentials=True)
    if name == "yaml":
        path = tmp_path / "input.yaml"
        path.write_text(f"version: 1\nsequences:\n  - protein:\n      id: A\n      sequence: {SEQUENCE}\n")
        return "predict_from_yaml_file", dict(yaml_file=path)
    if name == "rna":
        request = PredictionRequest(polymers=[polymer, Polymer(id="B", molecule_type="rna", sequence="AUGCAUGC")])
    elif name == "modified":
        request = PredictionRequest(polymers=[Polymer(id="A", molecule_type="protein", sequence="ASTYACDEFGHIKLMNPQRST",
                                    modifications=[Modification(ccd="SEP", position=2)])])
    elif name == "cyclic":
        request = PredictionRequest(polymers=[Polymer(id="A", molecule_type="protein", sequence="ACDEFGHIKL", cyclic=True)])
    elif name == "disulfide":
        request = PredictionRequest(polymers=[Polymer(id="A", molecule_type="protein", sequence="ACDEFGHIKLMNCQRSTVWY")],
                    constraints=[BondConstraint(atoms=[Atom(id="A", residue_index=i, atom_name="SG") for i in (2, 13)])])
    else:
        raise ValueError(name)
    return "predict", dict(request=request)


@pytest.mark.parametrize("mode", ["async", "sync"])
@pytest.mark.parametrize("name", ["protein", "smiles", "ccd", "pocket", "covalent", "dna", "msa", "advanced", "yaml", "rna", "modified", "cyclic", "disulfide"])
async def test_python_methods(mode, name, tmp_path):
    client = (Boltz2Client if mode == "async" else Boltz2SyncClient)(base_url=URL, timeout=1200)
    method, kwargs = case(name, tmp_path)
    output = tmp_path / "output"
    kwargs.update(output_dir=output, recycling_steps=1, sampling_steps=10)
    function = getattr(client, method)
    result = await function(**kwargs) if mode == "async" else await asyncio.to_thread(function, **kwargs)
    assert_outputs(result, output)
    if name in {"protein", "advanced"}:
        assert len(result.structures) == 2
    if name in {"smiles", "pocket"}:
        affinity = result.affinities["LIG"]
        for key in ("affinity_embedding", "model_1_affinity_embedding", "model_2_affinity_embedding"):
            values = np.asarray(getattr(affinity, key))
            assert values.shape == (1, 384) and np.isfinite(values).all()


@pytest.mark.parametrize("mode", ["async", "sync"])
async def test_template_method(mode, tmp_path):
    async_client = Boltz2Client(base_url=URL, timeout=1200)
    base = await async_client.predict_protein_structure(sequence=SEQUENCE, sampling_steps=10, save_structures=False)
    template = StructuralTemplate(structure=base.structures[0].structure, format="cif", chain_id="A")
    kwargs = dict(sequence=SEQUENCE, templates=[template], sampling_steps=10, output_dir=tmp_path)
    if mode == "async":
        result = await async_client.predict_with_templates(**kwargs)
    else:
        client = Boltz2SyncClient(base_url=URL, timeout=1200)
        result = await asyncio.to_thread(client.predict_with_templates, **kwargs)
    assert_outputs(result, tmp_path)


@pytest.mark.parametrize("mode", ["async", "sync"])
async def test_multi_endpoint_new_parameters(mode, tmp_path):
    kwargs = dict(protein_sequence=SEQUENCE, ligand_smiles="CCO", predict_affinity=True,
                  output_affinity_embedding=True, diffusion_samples=2, max_parallel_samples=1,
                  sampling_steps=10, sampling_steps_affinity=10, diffusion_samples_affinity=1,
                  output_dir=tmp_path)
    if mode == "async":
        async with MultiEndpointClient(endpoints=[URL], timeout=1200) as client:
            result = await client.predict_protein_ligand_complex(**kwargs)
    else:
        with MultiEndpointClient(endpoints=[URL], timeout=1200, is_async=False) as client:
            result = await asyncio.to_thread(client.predict_protein_ligand_complex_sync, **kwargs)
    assert len(result.structures) == 2
    assert result.affinities["LIG"].affinity_embedding
    assert_outputs(result, tmp_path)


def test_bash_cli():
    env = dict(os.environ, BOLTZ2_BIN=str(Path(sys.executable).parent / "boltz2"), PYTHON=sys.executable)
    output = ROOT / "results/cli"
    output.mkdir(parents=True, exist_ok=True)
    with (output / "validation.log").open("w") as log:
        result = subprocess.run(["bash", "scripts/validate_cli.sh"], cwd=ROOT, env=env,
                                stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    assert result.returncode == 0, (output / "validation.log").read_text()


@pytest.mark.parametrize("mode", ["async", "sync"])
def test_multi_endpoint_screening(mode, tmp_path):
    from boltz2_client import VirtualScreening
    client = MultiEndpointClient(endpoints=[URL], timeout=1200, is_async=mode == "async")
    result = VirtualScreening(client=client, max_workers=2).screen(
        target_sequence=SEQUENCE, compound_library=[{"name":"ethanol", "smiles":"CCO"}],
        sampling_steps=10, sampling_steps_affinity=10, diffusion_samples_affinity=1,
    )
    assert len(result.successful_results) == 1 and not result.failed_results
    assert np.isfinite(result.successful_results[0]["predicted_pic50"])
    result.save_results(tmp_path)
    assert json.loads((tmp_path / "screening_metadata.json").read_text())["failed_predictions"] == 0
