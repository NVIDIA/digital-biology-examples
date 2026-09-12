# Pair A3M alignments for a multimer

Each A3M file must start with its chain's query sequence. Pairing joins homologs
by taxonomy or UniRef identifiers and produces Boltz2 CSV records per chain.
Unrelated alignments do not establish co-evolution or binding.

```python
from pathlib import Path
from boltz2_client import (
    Boltz2Client, Polymer, PredictionRequest,
    convert_a3m_to_multimer_csv, create_paired_msa_per_chain,
)

conversion = convert_a3m_to_multimer_csv(
    a3m_files={"A": Path("chain_A.a3m"), "B": Path("chain_B.a3m")},
    pairing_strategy="greedy",
)
msa = create_paired_msa_per_chain(conversion)
request = PredictionRequest(polymers=[
    Polymer(id=chain, molecule_type="protein", sequence=sequence, msa=msa[chain])
    for chain, sequence in conversion.query_sequences.items()
])
result = await Boltz2Client(timeout=1200).predict(request, output_dir="results/multimer")
```

```bash
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o results/paired
boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B \
  -o results/multimer.cif --save-all
```

Use `--pairing-mode taxid` for taxonomic headers, `uniref` for UniRef-based
matching, or `auto` to detect the header style. `--include-unpaired` retains
unpaired rows. `--max-pairs` limits paired depth.

The [runnable notebook](../examples/notebooks/02_protein_complexes.ipynb)
accepts existing per-chain A3M files through `MULTIMER_A3M_A` and
`MULTIMER_A3M_B`, checks their query sequences, and supplies the paired CSV to
the same complex prediction workflow. Without files it runs without an MSA.
