# Covalent complexes

Use a CCD ligand and a bond constraint. Atom names must exist in the selected
CCD definition and protein residue; residue indices are 1-based. NIM validates
the chemistry. SMILES ligands are not used for the named-atom CCD workflow.

```python
from boltz2_client import Boltz2Client

client = Boltz2Client(timeout=1200)
# KRAS G12C fragment: residue 12 is cysteine. See the full construct in the notebook.
sequence = "MTEYKLVVVGACGVGKSALTIQLIQNHFVDEYDPT"
result = await client.predict_covalent_complex(
    protein_sequence=sequence, ligand_ccd="U4U",
    covalent_bonds=[(12, "SG", "C22")],
    output_dir="results/covalent",
)
```

```bash
boltz2 covalent "$KRAS_G12C_SEQUENCE" --ccd U4U \
  --bond A:12:SG:LIG:C22 --output-dir results/covalent
```

The CLI bond format has five fields:
`PROTEIN_ID:RESIDUE_INDEX:PROTEIN_ATOM:LIGAND_ID:LIGAND_ATOM`.
For a protein disulfide, use `--disulfide A:12:A:45` with actual cysteines at
those positions. A constraint is an input assumption, not proof of a bond.

[Full KRAS example and visualization](../examples/notebooks/05_covalent_ligand.ipynb).
