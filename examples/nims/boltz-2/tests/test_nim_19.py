"""NIM 1.9 request, transport, and output regressions. No GPU or network needed."""
import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from boltz2_client import (
    AlignmentFileRecord, Atom, Boltz2Client, Boltz2SyncClient, Ligand,
    Polymer, PredictionRequest, PredictionResponse, save_prediction_outputs,
)
from boltz2_client.cli import cli
from boltz2_client.exceptions import Boltz2APIError, Boltz2TimeoutError
from boltz2_client.models import YAMLConfig


@contextmanager
def mock_http(transport):
    http = httpx.AsyncClient(transport=transport)
    with patch("boltz2_client.client.httpx.AsyncClient", return_value=http):
        yield http


@pytest.fixture
def response_payload():
    # Synthetic schema fixture, not measured model output.
    return {
        "structures": [{"format": "mmcif", "structure": "data_test\n#\n"}],
        "confidence_scores": [0.8], "ptm_scores": [0.7],
        "complex_pde_scores": [1.2], "complex_ipde_scores": [1.5],
        "pae": None, "pde": None,
        "affinities": {"L1": {
            "affinity_pic50": [6.0], "affinity_pred_value": [0.0],
            "affinity_probability_binary": [0.8],
            "model_1_affinity_pred_value": [0.1],
            "model_1_affinity_probability_binary": [0.7],
            "model_2_affinity_pred_value": [-0.1],
            "model_2_affinity_probability_binary": [0.9],
            "affinity_embedding": [[0.1] * 384],
            "model_1_affinity_embedding": [[0.2] * 384],
            "model_2_affinity_embedding": [[0.0] * 384],
        }},
        "metrics": {"total_time_seconds": 1.0},
        "future_score": [0.9],
    }


def request(**kwargs):
    return PredictionRequest(polymers=[Polymer(id="A", molecule_type="protein", sequence="ACDX")], **kwargs)


@pytest.mark.parametrize("ligand", [{}, {"smiles": "CC", "ccd": "ATP"}, {"smiles": "CC", "output_affinity_embedding": True}])
def test_invalid_ligands(ligand):
    with pytest.raises(ValidationError):
        Ligand(**ligand)


@pytest.mark.parametrize("count", [0, 26])
def test_parallel_sample_limits(count):
    with pytest.raises(ValidationError):
        request(max_parallel_samples=count)


def test_schema_features_and_typos():
    assert request(max_parallel_samples=25).max_parallel_samples == 25
    assert request().max_parallel_samples is None
    assert Atom(id="LIG", residue_index=1, atom_name="C1").id == "LIG"
    with pytest.raises(ValidationError):
        request(max_paralell_samples=2)
    with pytest.raises(ValidationError):
        Polymer(molecule_type="protein", sequence="")
    with pytest.raises(ValidationError):
        request().sampling_steps = 1
    with pytest.raises(ValidationError):
        AlignmentFileRecord(data=">query\nACD", format="a3m")


def test_msa_validation():
    msa = {"db": {"a3m": AlignmentFileRecord(alignment=">query\nACD", format="a3m")}}
    with pytest.raises(ValidationError):
        Polymer(molecule_type="dna", sequence="ACG", msa=msa)
    with pytest.raises(ValidationError):
        Polymer(molecule_type="protein", sequence="ACD", msa={"db": {"csv": msa["db"]["a3m"]}})
    with pytest.raises(ValidationError):
        request(ligands=[Ligand(ccd="ATP", predict_affinity=True), Ligand(ccd="ATP")])


def test_hosted_default_and_local_no_auth(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    assert Boltz2Client(endpoint_type="nvidia_hosted").predict_url == "https://health.api.nvidia.com/v1/biology/mit/boltz2/predict"
    assert Boltz2SyncClient(endpoint_type="nvidia_hosted").base_url == "https://health.api.nvidia.com"
    assert "Authorization" not in Boltz2Client()._get_headers()
    monkeypatch.delenv("NVIDIA_API_KEY")
    monkeypatch.setenv("NGC_API_KEY", "test-ngc-key")
    assert Boltz2Client(endpoint_type="nvidia_hosted").api_key == "test-ngc-key"


async def test_wire_request_and_complete_output(tmp_path, response_payload):
    captured = []
    def handle(req):
        captured.append(json.loads(req.content))
        assert str(req.url) == "http://localhost:8000/biology/mit/boltz2/predict"
        assert "authorization" not in req.headers
        return httpx.Response(200, json=response_payload)
    transport = httpx.MockTransport(handle)
    with mock_http(transport):
        result = await Boltz2Client().predict_protein_ligand_complex(
            protein_sequence="ACDX", ligand_smiles="CC", ligand_id="L1",
            predict_affinity=True, output_affinity_embedding=True,
            max_parallel_samples=2, diffusion_samples=2,
            write_full_pae=True, write_full_pde=True, output_dir=str(tmp_path),
        )
    assert captured[0]["max_parallel_samples"] == 2
    assert captured[0]["ligands"][0]["output_affinity_embedding"] is True
    assert result.pae is None
    assert len(result.affinities["L1"].affinity_embedding[0]) == 384
    saved = json.loads((tmp_path / "prediction_response.json").read_text())
    assert saved["future_score"] == [0.9]
    assert saved["affinities"] == response_payload["affinities"]
    assert json.loads((tmp_path / "prediction_metadata.json").read_text())["complex_pde_scores"] == [1.2]
    paths = save_prediction_outputs(result, tmp_path / "export")
    assert json.loads(paths["scores"].read_text())["affinities"] == response_payload["affinities"]


async def test_legacy_requests_omit_new_flags(response_payload):
    def handle(req):
        payload = json.loads(req.content)
        assert "max_parallel_samples" not in payload
        assert "output_affinity_embedding" not in payload["ligands"][0]
        return httpx.Response(200, json=response_payload)
    with mock_http(httpx.MockTransport(handle)):
        await Boltz2Client().predict(request(ligands=[Ligand(smiles="CC")]), save_structures=False)


@pytest.mark.parametrize("status,payload", [(422, {"error": "Invalid sequence"}), (503, {"detail": "Unavailable"})])
async def test_nim_errors_preserve_status(status, payload):
    with mock_http(httpx.MockTransport(lambda req: httpx.Response(status, json=payload))):
        with pytest.raises(Boltz2APIError) as error:
            await Boltz2Client().predict(request(), save_structures=False)
    assert error.value.status_code == status
    assert error.value.response_data == payload


async def test_polling_success(response_payload):
    calls = []
    def handle(req):
        calls.append(req.method)
        if req.method == "POST":
            return httpx.Response(202, headers={"nvcf-reqid": "test-task"})
        assert str(req.url).endswith("/status/test-task")
        return httpx.Response(200, json=response_payload)
    with mock_http(httpx.MockTransport(handle)):
        result = await Boltz2Client(endpoint_type="nvidia_hosted", api_key="test", poll_seconds=0.001).predict(request(), save_structures=False)
    assert result.structures
    assert calls == ["POST", "GET"]


async def test_polling_has_deadline_and_no_resubmission():
    calls = []
    def handle(req):
        calls.append(req.method)
        return httpx.Response(202, headers={"nvcf-reqid": "test-task"})
    with mock_http(httpx.MockTransport(handle)):
        with pytest.raises(Boltz2TimeoutError):
            await Boltz2Client(endpoint_type="nvidia_hosted", api_key="test", timeout=0.02, poll_seconds=0.001).predict(request(), save_structures=False)
    assert calls.count("POST") == 1


@pytest.mark.parametrize("status", [403, 429, 502])
async def test_polling_terminal_error(status):
    http = AsyncMock()
    http.get.return_value = httpx.Response(status, json={"error": "failed"})
    client = Boltz2Client(endpoint_type="nvidia_hosted", api_key="test", poll_seconds=0.001)
    with pytest.raises(Boltz2APIError) as error:
        await client._handle_nvidia_polling(http, httpx.Response(202, headers={"nvcf-reqid": "task"}))
    assert error.value.status_code == status


@pytest.mark.parametrize("as_list", [True, False])
def test_yaml_affinity_is_not_dropped(as_list):
    properties = {"affinity": {"binder": "L1"}}
    config = YAMLConfig.model_validate({"version": 1, "sequences": [
        {"protein": {"id": "A", "sequence": "ACD"}},
        {"ligand": {"id": "L1", "smiles": "CC"}},
    ], "properties": [properties] if as_list else properties})
    assert config.to_prediction_request().ligands[0].predict_affinity


def test_cli_new_options(response_payload):
    result = PredictionResponse.model_validate(response_payload)
    client = AsyncMock()
    client.predict.return_value = result
    client.predict_protein_ligand_complex.return_value = result
    with patch("boltz2_client.cli.create_client", return_value=client):
        run = CliRunner().invoke(cli, ["protein", "ACDX", "--max-parallel-samples", "2", "--write-full-pae", "--no-save"])
        assert run.exit_code == 0, run.output
        assert "NIM_OUTPUT_PATH" in run.output
        assert client.predict.call_args.args[0].max_parallel_samples == 2
        run = CliRunner().invoke(cli, ["ligand", "ACD", "--smiles", "CC", "--predict-affinity", "--output-affinity-embedding", "--no-save"])
        assert run.exit_code == 0, run.output
        assert client.predict_protein_ligand_complex.call_args.kwargs["output_affinity_embedding"]


async def test_msa_search_does_not_receive_prediction_options():
    client = Boltz2Client()
    client._msa_search_client = AsyncMock()
    client._msa_search_integration = AsyncMock()
    client._msa_search_integration.search_and_prepare_for_boltz.return_value = {
        "msa_search": {"a3m": AlignmentFileRecord(alignment=">query\nACD\n", format="a3m")}
    }
    with patch.object(client, "predict", new_callable=AsyncMock) as predict:
        await client.predict_with_msa_search("ACD", save_structures=False, max_parallel_samples=2)
        search_args = client._msa_search_integration.search_and_prepare_for_boltz.call_args.kwargs
        assert "save_structures" not in search_args
        assert "max_parallel_samples" not in search_args
        assert predict.call_args.kwargs["max_parallel_samples"] == 2


async def test_missing_yaml_msa_fails_before_inference(tmp_path):
    config = tmp_path / "complex.yaml"
    config.write_text("version: 1\nsequences:\n  - protein:\n      id: A\n      sequence: ACD\n      msa: missing.a3m\n")
    from boltz2_client.exceptions import Boltz2ValidationError
    client = Boltz2Client()
    with patch.object(client, "predict", new_callable=AsyncMock) as predict:
        with pytest.raises(Boltz2ValidationError, match="MSA file not found"):
            await client.predict_from_yaml_file(config)
        predict.assert_not_called()


@pytest.mark.parametrize("complex_id", ["../escape", "a/b", "", "a" * 65])
def test_complex_id_path_validation(complex_id):
    with pytest.raises(ValidationError):
        request(complex_id=complex_id)


async def test_invalid_response_is_not_reported_as_input_error():
    from boltz2_client.exceptions import Boltz2InvalidResponseError
    with mock_http(httpx.MockTransport(lambda req: httpx.Response(200, json={"structures": []}))):
        with pytest.raises(Boltz2InvalidResponseError):
            await Boltz2Client().predict(request(), save_structures=False)
