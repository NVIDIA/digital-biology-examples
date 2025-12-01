# Converting ColabFold A3M Files to Boltz2 Multimer Format

This guide explains how to convert ColabFold-generated A3M monomer MSA files into the paired CSV format required by Boltz2 for multimer structure predictions.

## Overview

When predicting protein complex structures with Boltz2, providing Multiple Sequence Alignments (MSAs) significantly improves prediction quality by capturing co-evolutionary signals between interacting proteins. ColabFold generates individual A3M MSA files for each protein chain, but Boltz2 expects paired MSAs where sequences from the same organism are matched across chains.

This package provides tools to automatically convert ColabFold A3M files to Boltz2's multimer format.

## Quick Start

### One-Command Prediction (Recommended)

The fastest way to predict a complex from A3M files:

```bash
# Predict complex structure directly from A3M files (all-in-one)
boltz2 --base-url http://localhost:8002 multimer-msa \
    chain_A.a3m chain_B.a3m \
    -c A,B \
    -o complex.cif

# With custom settings
boltz2 --base-url http://localhost:8002 multimer-msa \
    chain_A.a3m chain_B.a3m \
    -c A,B \
    -o complex.cif \
    --sampling-steps 400 \
    --pairing-mode uniref
```

### CLI: Convert Only

If you just want to convert A3M files to CSV without prediction:

```bash
# Default: auto-detect pairing mode (like ColabFold)
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv

# Force UniRef ID pairing (works with all ColabFold output)
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --pairing-mode uniref

# Force TaxID pairing (requires taxonomy annotations)
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --pairing-mode taxid
```

### Python API

```python
from boltz2_client import (
    convert_a3m_to_multimer_csv,
    create_paired_msa_per_chain,
    save_prediction_outputs,
    get_prediction_summary
)
from pathlib import Path

# Convert A3M files (auto-detect pairing mode)
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': Path('chain_A.a3m'), 'B': Path('chain_B.a3m')}
)

print(f"Created {result.num_pairs} paired sequences")

# Get per-chain MSA structures for Boltz2
msa_per_chain = create_paired_msa_per_chain(result)

# After prediction, save all outputs with one call
paths = save_prediction_outputs(
    response=response,
    output_dir=Path("results"),
    base_name="complex",
    save_scores=True,      # Save confidence scores JSON
    save_csv=True,         # Save paired CSVs
    conversion_result=result
)

# Get prediction quality summary
summary = get_prediction_summary(response)
print(f"Confidence: {summary['confidence']:.2f}")
print(f"Quality: {summary['quality_assessment']}")
```

## CLI Commands Reference

### `boltz2 multimer-msa` - One-Step Prediction

Converts A3M files and runs prediction in a single command.

```bash
boltz2 [--base-url URL] multimer-msa [OPTIONS] A3M_FILES...
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --chain-ids` | (required) | Comma-separated chain IDs (e.g., "A,B") |
| `-o, --output` | `complex.cif` | Output CIF file path |
| `--save-csv` | false | Save paired CSV files alongside CIF |
| `--save-all` | false | Save all outputs: CIF + scores JSON |
| `--max-pairs` | None | Maximum paired sequences to include |
| `--pairing-mode` | `auto` | Pairing mode: `auto`, `taxid`, or `uniref` |
| `--recycling-steps` | 3 | Number of recycling steps |
| `--sampling-steps` | 200 | Number of diffusion sampling steps |
| `--diffusion-samples` | 1 | Number of output structures |

**Examples:**

```bash
# Basic heterodimer
boltz2 --base-url http://localhost:8002 multimer-msa \
    chain_A.a3m chain_B.a3m -c A,B

# Trimer with higher quality
boltz2 --base-url http://localhost:8002 multimer-msa \
    a.a3m b.a3m c.a3m -c A,B,C \
    --sampling-steps 400

# Multiple structure predictions
boltz2 --base-url http://localhost:8002 multimer-msa \
    chain_A.a3m chain_B.a3m -c A,B \
    --diffusion-samples 5 \
    -o complex.cif

# Fast prediction with limited MSA depth
boltz2 --base-url http://localhost:8002 multimer-msa \
    chain_A.a3m chain_B.a3m -c A,B \
    --max-pairs 100 \
    --sampling-steps 50

# Save all outputs (structure + scores + CSVs)
boltz2 --base-url http://localhost:8002 multimer-msa \
    chain_A.a3m chain_B.a3m -c A,B \
    -o results/complex.cif \
    --save-all --save-csv
```

**Output files with `--save-all --save-csv`:**
```
results/
├── complex.cif              # 3D structure (mmCIF format)
├── complex.scores.json      # All confidence scores and metrics
├── complex_chain_A.csv      # Paired MSA for chain A
└── complex_chain_B.csv      # Paired MSA for chain B
```

**Scores JSON contains:**
```json
{
  "confidence_scores": [0.85],
  "ptm_scores": [0.82],
  "iptm_scores": [0.78],
  "complex_plddt_scores": [0.88],
  "complex_iplddt_scores": [0.85],
  "pair_chains_iptm_scores": [...],
  "metrics": {"total_time_seconds": 5.2, ...}
}
```

### Multi-Endpoint Load Balancing

For high-throughput workflows, use multiple Boltz2 NIMs with load balancing:

```bash
# Use 4 Boltz2 NIM endpoints with automatic load balancing
boltz2 --multi-endpoint \
    --base-url "http://localhost:8000,http://localhost:8001,http://localhost:8002,http://localhost:8003" \
    multimer-msa chain_A.a3m chain_B.a3m -c A,B -o complex.cif

# Specify load balancing strategy
boltz2 --multi-endpoint \
    --base-url "http://gpu1:8000,http://gpu2:8000" \
    --load-balance-strategy round_robin \
    multimer-msa chain_A.a3m chain_B.a3m -c A,B

# Available strategies: round_robin, least_loaded (default), random
```

### `boltz2 convert-msa` - Convert Only

Converts A3M files to paired CSV format without running prediction.

```bash
boltz2 convert-msa [OPTIONS] A3M_FILES...
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --chain-ids` | (required) | Comma-separated chain IDs |
| `-o, --output` | (required) | Output CSV file path |
| `--max-pairs` | None | Maximum paired sequences |
| `--pairing-strategy` | `greedy` | Strategy: `greedy` or `complete` |
| `--pairing-mode` | `auto` | Mode: `auto`, `taxid`, or `uniref` |

## How It Works

### The Pairing Problem

For multimer predictions, we need to identify which sequences in different MSAs come from the same organism. This "pairing" allows Boltz2 to learn co-evolutionary patterns between interacting proteins.

```
Chain A MSA:           Chain B MSA:           Paired Result:
>Human_ProteinA        >Human_ProteinB        key=1: HumanA + HumanB
MKTVRQ...              MVTPEG...              (same organism)

>Mouse_ProteinA        >Mouse_ProteinB        key=2: MouseA + MouseB  
MKTIRQ...              MVSPEG...              (same organism)

>Rat_ProteinA          >Chicken_ProteinB      No pair
MKTLRQ...              MVTPDG...              (different organisms)
```

### Pairing Strategies

#### 1. Auto-Detect (Default, ColabFold-style)

The converter automatically detects the best pairing mode based on your A3M files:

- If >50% of sequences have TaxIDs → **TaxID pairing**
- If ≤50% have TaxIDs → **UniRef ID pairing**

```python
# Auto-detect (recommended)
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'}
    # use_tax_id=None (default) triggers auto-detection
)
```

#### 2. UniRef ID Pairing

Pairs sequences that share the same UniRef100 cluster ID. Works with **all** ColabFold output.

```python
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'},
    use_tax_id=False  # Force UniRef ID pairing
)
```

#### 3. TaxID Pairing

Pairs sequences from the same species using NCBI Taxonomic IDs. Requires A3M files with taxonomy annotations (OX= fields or species codes like `_HUMAN`).

```python
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'},
    use_tax_id=True  # Force TaxID pairing
)
```

### Greedy vs Complete Pairing

- **Greedy** (default): Pairs sequences if they match in at least 2 chains
- **Complete**: Only pairs if ALL chains have a matching sequence

```python
# Greedy pairing (default, like ColabFold)
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'a.a3m', 'B': 'b.a3m', 'C': 'c.a3m'},
    pairing_strategy='greedy'
)

# Complete pairing (stricter)
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'a.a3m', 'B': 'b.a3m', 'C': 'c.a3m'},
    pairing_strategy='complete'
)
```

## A3M Header Formats

The converter recognizes multiple header formats:

| Format | Example | TaxID Source |
|--------|---------|--------------|
| UniProt with species | `>tr\|P12345\|NAME_HUMAN` | Species code → TaxID |
| Explicit OX field | `>... OX=9606 ...` | OX= field |
| NCBI with species | `>gi\|123\| [Homo sapiens]` | Species name lookup |
| UniRef100 only | `>UniRef100_A0A2N5EEG3 340 0.99` | UniRef ID (fallback) |

## End-to-End Example

```python
import asyncio
from pathlib import Path
from boltz2_client import (
    Boltz2Client,
    Polymer,
    PredictionRequest,
    convert_a3m_to_multimer_csv,
    create_paired_msa_per_chain
)

async def predict_complex_with_msa():
    # 1. Convert A3M files to paired MSA
    result = convert_a3m_to_multimer_csv(
        a3m_files={
            'A': Path('chain_A.a3m'),
            'B': Path('chain_B.a3m')
        }
    )
    print(f"Paired sequences: {result.num_pairs}")
    
    # 2. Create per-chain MSA structures
    msa_per_chain = create_paired_msa_per_chain(result)
    
    # 3. Create polymers with MSA
    protein_A = Polymer(
        id="A",
        molecule_type="protein",
        sequence=result.query_sequences['A'],
        msa=msa_per_chain['A']
    )
    
    protein_B = Polymer(
        id="B",
        molecule_type="protein",
        sequence=result.query_sequences['B'],
        msa=msa_per_chain['B']
    )
    
    # 4. Submit prediction
    client = Boltz2Client(base_url="http://localhost:8002")
    
    request = PredictionRequest(
        polymers=[protein_A, protein_B],
        recycling_steps=3,
        sampling_steps=200,
        diffusion_samples=1
    )
    
    response = await client.predict(request)
    
    # 5. Save structure
    if response.structures:
        with open("complex.cif", "w") as f:
            f.write(response.structures[0].cif_data)
        print("Structure saved to complex.cif")

# Run
asyncio.run(predict_complex_with_msa())
```

## Species to TaxID Mapping

The converter includes multiple methods to resolve species codes to TaxIDs:

1. **Built-in mapping**: 54 common species (instant)
2. **Bundled speclist.txt**: 27,836 species from UniProt (instant)
3. **UniProt API**: Online lookup for any species code
4. **Biopython Entrez**: NCBI Taxonomy lookup for scientific names

```python
from boltz2_client import SpeciesMapper

# Built-in lookup
tax_id = SpeciesMapper.get_tax_id("HUMAN")  # "9606"

# Smart lookup (tries all methods)
tax_id = SpeciesMapper.smart_lookup("Homo sapiens")  # "9606"

# Check available mappings
stats = SpeciesMapper.get_mapping_stats()
print(f"Total species available: {stats['total']}")  # ~27,890
```

## Troubleshooting

### "Only query sequence paired"

This happens when no common identifiers are found across chains. Solutions:

1. Use `--pairing-mode uniref` if your files have UniRef IDs
2. Add taxonomy annotations to your A3M files
3. Check if your A3M files have overlapping organisms

### "No TaxIDs found"

Standard ColabFold output uses UniRef100 IDs without TaxIDs. Use:

```bash
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o out.csv --pairing-mode uniref
```

### Getting TaxID-annotated A3M files

1. Run ColabFold with `--use-env-template` flag
2. Use MMseqs2 to add taxonomy: `mmseqs taxonomy queryDB uniref30 taxDB tmp`

## Output Format

The converter produces CSV files with columns `key` and `sequence`:

```csv
key,sequence
1,MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG
2,MKTIRQERLKSIIRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG
3,MKTLRQERLKSIVRILERSKDPVSGAQLAEELSVSRQVIVQDIAYLRSLG
```

For Boltz2, each chain gets its own CSV file. Sequences with the same `key` value across chain CSVs are treated as paired (from the same organism).

## References

- [ColabFold](https://github.com/sokrypton/ColabFold) - Fast MSA generation
- [Boltz2](https://github.com/jwohlwend/boltz) - Protein structure prediction
- [UniProt speclist.txt](https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/speclist.txt) - Species code to TaxID mapping

