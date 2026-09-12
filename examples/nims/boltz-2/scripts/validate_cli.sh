#!/usr/bin/env bash
# Exercise the installed console command through Bash against real services.
set -euo pipefail
bin="${BOLTZ2_BIN:-boltz2}"
python="${PYTHON:-python}"
url="${BOLTZ2_NIM_URL:-http://localhost:8000}"
out="${BOLTZ2_CLI_OUTPUT:-results/cli}"
mkdir -p "$out"
sequence=MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
kras=MTEYKLVVVGACGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQAQDLARSYGIPFIETSAKTRQGVDDAFYTLVREIRKHKE
"$python" - "$out" "$sequence" <<'PY'
import json, sys
from pathlib import Path
import yaml
out, sequence = Path(sys.argv[1]), sys.argv[2]
for chain in ('A', 'B'):
    (out / f'{chain}.a3m').write_text(f'>query\n{sequence}\n>syntax_example OX=9606\n{sequence}\n')
request = {'polymers': [{'id':'A','molecule_type':'protein','sequence':sequence}],
           'diffusion_samples':2,'max_parallel_samples':1,'sampling_steps':10,'recycling_steps':1}
(out / 'request.json').write_text(json.dumps(request))
(out / 'input.yaml').write_text(yaml.safe_dump({'version':1,'sequences':[
    {'protein':{'id':'A','sequence':sequence}}, {'ligand':{'id':'LIG','smiles':'CCO'}}]}))
(out / 'compounds.csv').write_text('name,smiles\nethanol,CCO\naspirin,CC(=O)Oc1ccccc1C(=O)O\n')
(out / 'invalid.csv').write_text('name,smiles\ninvalid,INVALID_SMILES\n')
PY
failures=0
run() {
    local name="$1"
    shift
    if "$bin" --base-url "$url" --timeout 1200 "$@" > "$out/$name.log" 2>&1; then
        echo "PASS $name"
    else
        echo "FAIL $name (see $out/$name.log)"
        failures=$((failures + 1))
    fi
}
run health health
run metadata metadata
run protein protein "$sequence" --sampling-steps 10 --diffusion-samples 2 --max-parallel-samples 1 --output-dir "$out/protein"
run protein_msa protein "$sequence" --msa-file "$out/A.a3m" a3m --sampling-steps 10 --output-dir "$out/protein_msa"
run pdb protein "$sequence" --sampling-steps 10 --output-format pdb --output-dir "$out/pdb"
run ligand ligand "$sequence" --smiles 'CC(=O)Oc1ccccc1C(=O)O' --predict-affinity --output-affinity-embedding --diffusion-samples-affinity 1 --sampling-steps-affinity 10 --sampling-steps 10 --output-dir "$out/ligand"
run ccd ligand "$sequence" --ccd ATP --sampling-steps 10 --output-dir "$out/ccd"
run pocket ligand "$sequence" --smiles CCO --pocket-residues 10,15 --sampling-steps 10 --output-dir "$out/pocket"
run covalent covalent "$kras" --ccd U4U --bond A:12:SG:LIG:C22 --sampling-steps 10 --output-dir "$out/covalent"
run dna dna-protein --protein-sequences "$sequence" --dna-sequences ATCGATCG --sampling-steps 10 --output-dir "$out/dna"
run advanced advanced --config-file "$out/request.json" --output-dir "$out/advanced"
run yaml yaml "$out/input.yaml" --sampling-steps 10 --output-dir "$out/yaml"
run convert convert-msa "$out/A.a3m" "$out/B.a3m" -c A,B -o "$out/converted"
run multimer multimer-msa "$out/A.a3m" "$out/B.a3m" -c A,B --sampling-steps 10 -o "$out/multimer.cif" --save-all
run multi --multi-endpoint protein "$sequence" --diffusion-samples 2 --max-parallel-samples 1 --sampling-steps 10 --output-dir "$out/multi"
run screening screen "$sequence" "$out/compounds.csv" --sampling-steps 10 --max-workers 2 --output-dir "$out/screening"
if [[ -n "${MSA_NIM_URL:-}" ]]; then
    run msa_search msa-search "$sequence" --endpoint "$MSA_NIM_URL" -d pdb70_220313 -o "$out/msa_search"
    run msa_predict msa-predict "$sequence" --endpoint "$MSA_NIM_URL" -d pdb70_220313 --sampling-steps 10 --output-dir "$out/msa_predict"
    run msa_ligand msa-ligand "$sequence" --endpoint "$MSA_NIM_URL" -d pdb70_220313 --smiles CCO --predict-affinity --diffusion-samples-affinity 1 --sampling-steps-affinity 10 --sampling-steps 10 --output-dir "$out/msa_ligand"
else
    echo 'SKIP MSA Search commands: MSA_NIM_URL is unset'
fi
if curl --fail-with-body --silent --show-error --max-time 1200 \
    "$url/biology/mit/boltz2/predict" -H 'Content-Type: application/json' \
    --data-binary "@$out/request.json" -o "$out/curl_response.json"; then
    echo 'PASS raw curl prediction'
else
    failures=$((failures + 1))
fi
for invalid in empty_url bad_sequence failed_screen; do
    if [[ "$invalid" == empty_url ]]; then
        args=(--base-url '' health)
    elif [[ "$invalid" == bad_sequence ]]; then
        args=(--base-url "$url" protein INVALID123 --no-save)
    else
        args=(--base-url "$url" screen "$sequence" "$out/invalid.csv" --no-affinity --output-dir "$out/failed_screen")
    fi
    if "$bin" "${args[@]}" > "$out/$invalid.log" 2>&1; then
        echo "FAIL $invalid was accepted"
        failures=$((failures + 1))
    else
        echo "PASS $invalid rejected"
    fi
done
"$python" - "$out" <<'PY'
import json, sys
from pathlib import Path
from Bio.PDB import MMCIFParser, PDBParser
import numpy as np
out = Path(sys.argv[1])
for name in ('protein','protein_msa','ligand','ccd','pocket','covalent','dna','advanced','yaml','multi'):
    response = json.loads((out / name / 'prediction_response.json').read_text())
    assert response['structures'] and np.isfinite(response['confidence_scores']).all(), name
for file in out.rglob('*.cif'):
    structure = MMCIFParser(QUIET=True).get_structure(file.stem, str(file))
    assert len(list(structure.get_atoms())) > 0, str(file)
for file in (out / 'pdb').glob('*.pdb'):
    assert len(list(PDBParser(QUIET=True).get_structure('pdb', str(file)).get_atoms())) > 0
assert list((out / 'pdb').glob('*.pdb')), 'No converted PDB file'
affinity = json.loads((out/'ligand/affinities.json').read_text())['LIG']
assert len(affinity['affinity_embedding'][0]) == 384
screen = json.loads((out/'screening/screening_metadata.json').read_text())
assert screen['successful_predictions'] == 2 and screen['failed_predictions'] == 0
assert json.loads((out/'failed_screen/screening_metadata.json').read_text())['failed_predictions'] == 1
assert len(json.loads((out/'curl_response.json').read_text())['structures']) == 2
print('PASS saved JSON, mmCIF, PDB, embeddings and screening results')
PY
exit "$failures"
