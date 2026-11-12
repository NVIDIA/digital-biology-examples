# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""CLI complex_id handling. No GPU or network needed."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from boltz2_client.cli import cli
from boltz2_client.models import PredictionResponse


SEQUENCE = "ACDEFGHIKLMNPQRSTVWY"


@pytest.fixture
def response():
    return PredictionResponse.model_validate({
        "structures": [{"format": "mmcif", "structure": "data_test\n#\n"}],
        "confidence_scores": [0.8],
        "metrics": {"test": "data"},
    })


@pytest.fixture
def a3m_files(tmp_path):
    files = []
    for name, sequence in {"A": "ACDE", "B": "FGHI"}.items():
        path = tmp_path / f"{name}.a3m"
        path.write_text(f">query\n{sequence}\n>UniRef100_SHARED\n{sequence}\n")
        files.append(path)
    return files


class CapturingClient:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.helper_kwargs = []

    async def health_check(self):
        return SimpleNamespace(status="healthy")

    async def predict(self, request, *args, **kwargs):
        self.requests.append(request.model_dump(exclude_none=True))
        return self.response

    async def predict_with_msa_search(self, *args, **kwargs):
        self.helper_kwargs.append(kwargs)
        return self.response

    async def predict_ligand_with_msa_search(self, *args, **kwargs):
        self.helper_kwargs.append(kwargs)
        return self.response

    async def predict_protein_ligand_complex(self, *args, **kwargs):
        self.helper_kwargs.append(kwargs)
        return self.response

    async def predict_with_advanced_parameters(self, *args, **kwargs):
        self.helper_kwargs.append(kwargs)
        return self.response

    async def predict_dna_protein_complex(self, *args, **kwargs):
        self.helper_kwargs.append(kwargs)
        return self.response

    async def search_msa(self, *args, **kwargs):
        save_path = kwargs.get("save_path")
        if save_path:
            save_path.write_text(">query\nACD\n")
        return save_path

    def configure_msa_search(self, *args, **kwargs):
        return None


def run_with_client(args, client):
    with (
        patch("boltz2_client.cli.create_client", return_value=client),
        patch("boltz2_client.cli.msa.Boltz2Client", return_value=client),
    ):
        return CliRunner().invoke(cli, args)


def test_multimer_msa_complex_id_is_sent(a3m_files, response, tmp_path):
    client = CapturingClient(response)
    result = run_with_client([
        "multimer-msa", str(a3m_files[0]), str(a3m_files[1]),
        "-c", "A,B",
        "--complex-id", "ABC_1-x",
        "--output", str(tmp_path / "complex.cif"),
    ], client)

    assert result.exit_code == 0, result.output
    assert client.requests[0]["complex_id"] == "ABC_1-x"


def test_multimer_msa_omits_complex_id_when_unset(a3m_files, response, tmp_path):
    client = CapturingClient(response)
    result = run_with_client([
        "multimer-msa", str(a3m_files[0]), str(a3m_files[1]),
        "-c", "A,B",
        "--output", str(tmp_path / "complex.cif"),
    ], client)

    assert result.exit_code == 0, result.output
    assert "complex_id" not in client.requests[0]


@pytest.mark.parametrize("bad_id", ["bad id", "", "a" * 65])
def test_invalid_complex_id_fails_before_msa_conversion(a3m_files, bad_id):
    def fail_conversion(*args, **kwargs):
        raise AssertionError("MSA conversion should not run for invalid complex_id")

    args = [
        "multimer-msa", str(a3m_files[0]), str(a3m_files[1]),
        "-c", "A,B",
        "--complex-id", bad_id,
    ]

    with patch("boltz2_client.a3m.convert_a3m_to_multimer_csv", fail_conversion):
        result = CliRunner().invoke(cli, args)

    assert result.exit_code == 2
    assert "Invalid value for '--complex-id'" in result.output


def test_protein_complex_id_is_sent(response):
    client = CapturingClient(response)
    result = run_with_client([
        "protein", SEQUENCE,
        "--complex-id", "protein_1",
        "--no-save",
    ], client)

    assert result.exit_code == 0, result.output
    assert client.requests[0]["complex_id"] == "protein_1"


def test_yaml_complex_id_is_sent(response, tmp_path):
    config = tmp_path / "complex.yaml"
    config.write_text(
        "version: 1\n"
        "sequences:\n"
        "  - protein:\n"
        "      id: A\n"
        f"      sequence: {SEQUENCE}\n"
    )
    client = CapturingClient(response)

    result = run_with_client([
        "yaml", str(config),
        "--complex-id", "yaml_1",
        "--no-save",
    ], client)

    assert result.exit_code == 0, result.output
    assert client.requests[0]["complex_id"] == "yaml_1"


def test_multimer_msa_complex_id_works_with_multi_endpoint(a3m_files, response, tmp_path):
    client = CapturingClient(response)
    with patch("boltz2_client.cli.create_client", return_value=client):
        result = CliRunner().invoke(cli, [
            "--multi-endpoint",
            "--base-url", "http://localhost:8010",
            "multimer-msa", str(a3m_files[0]), str(a3m_files[1]),
            "-c", "A,B",
            "--complex-id", "multi_1",
            "--output", str(tmp_path / "complex.cif"),
        ])

    assert result.exit_code == 0, result.output
    assert client.requests[0]["complex_id"] == "multi_1"


@pytest.mark.parametrize("command", [
    "protein", "ligand", "covalent", "dna-protein", "yaml",
    "msa-predict", "msa-ligand", "multimer-msa",
])
def test_prediction_command_help_lists_complex_id(command):
    result = CliRunner().invoke(cli, [command, "--help"])

    assert result.exit_code == 0
    assert "--complex-id" in result.output


@pytest.mark.parametrize(("command", "args"), [
    ("ligand", [SEQUENCE, "--smiles", "CC", "--no-save"]),
    ("covalent", [SEQUENCE, "--ccd", "ATP", "--bond", "A:1:CA:LIG:C1", "--no-save"]),
    ("dna-protein", ["--protein-sequences", SEQUENCE, "--dna-sequences", "ATCG", "--no-save"]),
    ("msa-predict", [SEQUENCE, "--no-save-msa"]),
    ("msa-ligand", [SEQUENCE, "--smiles", "CC"]),
])
def test_helper_commands_forward_complex_id(command, args, response, tmp_path):
    client = CapturingClient(response)
    result = run_with_client([
        command, *args,
        "--complex-id", "helper_1",
        "--output-dir", str(tmp_path),
    ], client)

    assert result.exit_code == 0, result.output
    assert client.helper_kwargs[0]["complex_id"] == "helper_1"
