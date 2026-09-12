"""Execute local notebook workflows with synthetic responses and the NIM schema.

This checks Python flow and submitted payloads, not GPU inference or browser rendering.
Real notebook execution is handled by scripts/validate_notebooks.py.
"""
import ast
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jsonschema
import nbformat
import pytest

from boltz2_client import Boltz2Client, PredictionRequest, PredictionResponse

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "examples/notebooks").glob("*.ipynb"))
SCHEMA = json.loads((ROOT / "tests/fixtures/nim_1_9_request_schema.json").read_text())


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_format_and_python(path):
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            assert cell.outputs == []
            assert cell.execution_count is None
            compile(cell.source, f"{path.name}:{index}", "exec", ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
async def test_notebook_workflow(path, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in ("BOLTZ2_SERVER_OUTPUT_DIR", "MULTIMER_A3M_A", "MULTIMER_A3M_B",
                "CDK4_MSA_PATH", "MSA_NIM_URL", "MSA_DATABASE", "BOLTZ2_NIM_URL"):
        monkeypatch.delenv(key, raising=False)
    payloads = []

    async def predict(self, request, **kwargs):
        output_dir = kwargs.get("output_dir")
        for key in ("save_structures", "output_dir", "progress_callback"):
            kwargs.pop(key, None)
        data = request.model_dump(exclude_none=True)
        data.update(kwargs)
        validated = PredictionRequest.model_validate(data)
        data = validated.model_dump(exclude_none=True)
        jsonschema.validate(data, SCHEMA)
        payloads.append(data)
        affinities = {}
        for ligand in request.ligands or []:
            if ligand.predict_affinity:
                values = {key: [0.5] for key in (
                    "affinity_pic50", "affinity_pred_value", "affinity_probability_binary",
                    "model_1_affinity_pred_value", "model_1_affinity_probability_binary",
                    "model_2_affinity_pred_value", "model_2_affinity_probability_binary",
                )}
                if ligand.output_affinity_embedding:
                    for field in ("affinity_embedding", "model_1_affinity_embedding", "model_2_affinity_embedding"):
                        values[field] = [[0.0] * 384]
                affinities[ligand.id] = values
        response = PredictionResponse(
            structures=[{"format": "mmcif", "structure": "data_synthetic_test\n#\n"}] * request.diffusion_samples,
            confidence_scores=[0.5] * request.diffusion_samples,
            iptm_scores=[0.4], complex_pde_scores=[2.0], affinities=affinities,
        )
        if output_dir:
            await self._save_structures(response, output_dir)
        return response

    async def metadata(self):
        return SimpleNamespace(version="1.9.0")

    namespace = {"__name__": "__main__"}
    with patch.object(Boltz2Client, "predict", predict), patch.object(Boltz2Client, "get_service_metadata", metadata):
        for index, cell in enumerate(nbformat.read(path, as_version=4).cells):
            if cell.cell_type != "code":
                continue
            value = eval(compile(cell.source, f"{path.name}:{index}", "exec", ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), namespace)
            if inspect.isawaitable(value):
                await value
    assert payloads
    assert list(tmp_path.rglob("*.cif"))
    if os.getenv("BOLTZ2_CONTRACT_OUTPUT"):
        output = Path(os.environ["BOLTZ2_CONTRACT_OUTPUT"])
        output.mkdir(parents=True, exist_ok=True)
        (output / (path.stem + ".json")).write_text(json.dumps(payloads))


def test_all_request_fields_match_image_schema():
    assert set(PredictionRequest.model_fields) == set(SCHEMA["properties"])
