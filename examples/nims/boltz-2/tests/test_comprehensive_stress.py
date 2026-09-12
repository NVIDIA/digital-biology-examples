"""Real load tests: 50 proteins and 147 affinity requests; every request must pass."""
import asyncio
import itertools
import json
import os
from pathlib import Path
import time

import pytest
from boltz2_client import MultiEndpointClient, LoadBalanceStrategy

pytestmark = [pytest.mark.real_endpoint, pytest.mark.performance, pytest.mark.slow]

PROTEIN_SEQUENCES = [
    'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG',
    'MNIFEMLRIDEGLRLKIYKDTEGYYTIGIGHLLTKSPSLNAAKSELDKAIGRNTNGVITKDEAEKLFNQDVDAAVRGILRNAKLKPVYDSLDAVRRCALINMVFQMGETGVAGFTNSLRMLQQKRWDEAAVNLAKSRWYNQTPNRAKRVITTFRTGTWDAYKNL',
    'MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKT',
    'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVDDGTLLDNYKVPRLQLLKYV',
    'MKLFDSLTVIGAVGNKIGLLYCFLHTSRGKPAIGIDMDRLETKLTLKGCQK',
    'MKLFDSLTVIGAVGNKIGLLYCFLHTSRGKPAIGIDMDRLETKLTLKGCQK',
    'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVDDGTLLDNYKVPRLQLLKYV',
    'MNIFEMLRIDEGLRLKIYKDTEGYYTIGIGHLLTKSPSLNAAKSELDKAIGRNTNGVITKDEAEKLFNQDVDAAVRGILRNAKLKPVYDSLDAVRRCALINMVFQMGETGVAGFTNSLRMLQQKRWDEAAVNLAKSRWYNQTPNRAKRVITTFRTGTWDAYKNL',
    'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG',
    'MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKT',
]
LIGANDS = [
    'CC(C)(C)OC(=O)N[C@@H](CC1=CC=CC=C1)C(=O)O',
    'CC(C)CC[C@H](NC(=O)OCc1ccccc1)C(=O)O',
    'O=C(O)[C@@H]1CCCN1C(=O)OC(C)(C)C',
    'CC(=O)Nc1ccc(O)cc1',
    'CC(C)Cc1ccc(C(C)C(=O)O)cc1',
    'O=C(O)Cc1ccccc1',
    'CC(=O)OC1C(Sc2ccccc2)=C(C(=O)O)N2C(=O)CC2C1(C)C',
    'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',
    'CC(=O)Oc1ccccc1C(=O)O',
    'CN(C)c1ccc(C(=C2C=CC(=[N+](C)C)C=C2)c2ccccc2)cc1',
    'Cc1ccc(C(C)C)cc1',
    'COc1ccc(CC(C)=O)cc1',
    'O=C1CC(c2ccccc2)Oc2ccccc21',
    'O=C(Cc1ccccc1)Nc1ccccc1',
    'Cc1ccccc1C(=O)O',
    'O=C(O)c1ccc(O)c(O)c1',
    'CC(C)(C)c1ccc(O)cc1',
    'O=C(O)C=Cc1ccccc1',
    'c1ccc2c(c1)OCO2',
    'O=C(O)c1cccnc1',
    'COc1ccccc1',
    'CC(C)=O',
    'CCO',
    'CC(C)O',
    'c1ccccc1',
    'Cc1ccccc1',
    'CC(=O)O',
    'O=C=O',
    'O',
    'CCCCCl',
    'O=C(O)CCc1ccccc1',
    'COc1ccc(C=O)cc1',
    'Cc1ccc(C)cc1',
    'O=Cc1ccccc1',
    'O=C(c1ccccc1)c1ccccc1',
    'CC(=O)c1ccccc1',
    'COC(=O)c1ccccc1',
    'CCOc1ccccc1',
    'c1ccc(Cl)cc1',
    'CC(C)(C)O',
    'CCN(CC)CC',
    'C1CCCCC1',
    'C1CCOC1',
    'CN(C)C=O',
    'CC#N',
    'CS(C)=O',
    'ClCCl',
    'ClC(Cl)Cl',
    'ClC(Cl)(Cl)Cl',
]
TEST_PROTEINS = [
    'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG',
    'MNIFEMLRIDEGLRLKIYKDTEGYYTIGIGHLLTKSPSLNAAKSELDKAIGRNTNGVITKDEAEKLFNQDVDAAVRGILRNAKLKPVYDSLDAVRRCALINMVFQMGETGVAGFTNSLRMLQQKRWDEAAVNLAKSRWYNQTPNRAKRVITTFRTGTWDAYKNL',
    'MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKT',
]


async def run_requests(cases, output):
    output.mkdir(parents=True, exist_ok=True)
    client = MultiEndpointClient(
        endpoints=os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000").split(","),
        strategy=LoadBalanceStrategy.LEAST_LOADED, timeout=1200, max_retries=1,
    )
    semaphore = asyncio.Semaphore(int(os.getenv("BOLTZ2_TEST_CONCURRENCY", "2")))

    async def run(index, sequence, smiles):
        start = time.monotonic()
        async with semaphore:
            try:
                kwargs = dict(recycling_steps=1, sampling_steps=10, diffusion_samples=1,
                              output_dir=output / str(index))
                if smiles:
                    result = await client.predict_protein_ligand_complex(
                        protein_sequence=sequence, ligand_smiles=smiles,
                        predict_affinity=True, sampling_steps_affinity=50,
                        diffusion_samples_affinity=3, **kwargs)
                    assert result.affinities
                    assert all(a.affinity_pic50 for a in result.affinities.values())
                else:
                    result = await client.predict_protein_structure(sequence=sequence, **kwargs)
                assert result.structures and result.confidence_scores
                assert all(s.structure.startswith("data_") for s in result.structures)
                assert (output / str(index) / "prediction_response.json").exists()
                return dict(index=index, passed=True, seconds=time.monotonic() - start)
            except Exception as error:
                return dict(index=index, passed=False, error=str(error))

    report = await asyncio.gather(*(run(i, *case) for i, case in enumerate(cases)))
    (output / "validation.json").write_text(json.dumps(report, indent=2))
    failures = [row for row in report if not row["passed"]]
    assert len(report) == len(cases)
    assert not failures, json.dumps(failures, indent=2)


async def test_50_protein_sequences():
    sequences = []
    for i, sequence in enumerate(PROTEIN_SEQUENCES * 5):
        if i % 2 == 0:
            sequence += "A"
        if i % 3 == 0:
            sequence = sequence[:-1]
        sequences.append((sequence, None))
    await run_requests(sequences, Path("results/stress/proteins"))


async def test_protein_ligand_complexes():
    cases = list(itertools.product(TEST_PROTEINS, LIGANDS))
    await run_requests(cases, Path("results/stress/affinity"))
