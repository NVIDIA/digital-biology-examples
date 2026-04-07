# A3M to Multimer MSA Conversion Guide

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.

This guide explains how to convert ColabFold-generated A3M monomer MSA files into the paired CSV format required by Boltz2 for multimer structure predictions.

## Table of Contents

1. [Overview](#overview)
2. [Understanding the Problem](#understanding-the-problem)
3. [How Pairing Works](#how-pairing-works)
4. [Input: A3M File Format](#input-a3m-file-format)
5. [Output: Paired CSV Format](#output-paired-csv-format)
6. [Pairing Strategies](#pairing-strategies)
7. [Include Unpaired Sequences](#include-unpaired-sequences)
8. [Usage](#usage)
   - [Python API](#python-api)
   - [Command Line Interface](#command-line-interface)
9. [Configuration Options](#configuration-options)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Overview

When predicting multimer (protein complex) structures, Boltz2 benefits from **paired MSAs** that capture co-evolutionary signals between interacting proteins. This feature converts separate monomer A3M files from ColabFold into the paired CSV format that Boltz2 understands.

```
┌─────────────────┐     ┌─────────────────┐
│  Chain A A3M    │     │  Chain B A3M    │
│  (monomer MSA)  │     │  (monomer MSA)  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   Pairing   │
              │   Engine    │
              └──────┬──────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼────────┐     ┌────────▼────────┐
│  Chain A CSV    │     │  Chain B CSV    │
│  (paired MSA)   │     │  (paired MSA)   │
└─────────────────┘     └─────────────────┘
```

---

## Understanding the Problem

### Why Pairing Matters

Proteins that interact often co-evolve—when one protein changes, its binding partner may compensate with a corresponding change. This co-evolutionary signal is captured in MSAs when sequences from the **same organism** are aligned together.

**Example**: If human protein A interacts with human protein B, and mouse protein A interacts with mouse protein B, pairing the human sequences together (and mouse sequences together) reveals correlated mutations that indicate interaction.

### The Challenge

ColabFold generates **separate** A3M files for each protein chain. These files contain homologous sequences from various organisms, but they're not aligned to each other. The challenge is to:

1. Identify which sequences come from the same organism
2. Pair them together in a format Boltz2 understands
3. Handle cases where organisms don't have sequences in all chains

---

## How Pairing Works

### Step 1: Parse A3M Files

Each A3M file is parsed to extract:
- **Sequence**: The amino acid sequence
- **Identifier**: UniRef cluster ID or UniProt accession
- **Organism ID**: Used for matching (TaxID or UniRef ID)

### Step 2: Extract Pairing Keys

For each sequence, a "key" is extracted for matching:

| Mode | Key Source | Example |
|------|------------|---------|
| **TaxID** | NCBI Taxonomic ID | `9606` (human) |
| **UniRef** | UniRef cluster ID | `A0A2N5EEG3` |

### Step 3: Match Across Chains

Sequences with the **same key** across different chains are paired:

```
Chain A MSA:                    Chain B MSA:
┌─────────────────────┐         ┌─────────────────────┐
│ Query (human)       │ ←─────→ │ Query (human)       │
│ Seq1 (TaxID: 9606)  │ ←─────→ │ SeqX (TaxID: 9606)  │  ✓ Paired
│ Seq2 (TaxID: 10090) │ ←─────→ │ SeqY (TaxID: 10090) │  ✓ Paired
│ Seq3 (TaxID: 7955)  │         │                     │  ✗ No match
│                     │         │ SeqZ (TaxID: 562)   │  ✗ No match
└─────────────────────┘         └─────────────────────┘
```

### Step 4: Generate Paired CSV

Each chain gets its own CSV file with matching keys:

```
Chain A CSV:              Chain B CSV:
key,sequence              key,sequence
1,MKTVRQ...               1,MVTPEG...    ← Same key = paired
2,MKTVRQ...               2,MVTPEG...    ← Same key = paired
```

---

## Input: A3M File Format

A3M is a variant of FASTA format used by HHblits/ColabFold. Each sequence has a header line starting with `>` followed by the sequence.

### Supported Header Formats

The converter supports multiple header formats:

#### 1. UniRef Format (ColabFold default)
```
>UniRef100_A0A2N5EEG3    340    0.994
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQ
```

#### 2. UniProt Format
```
>tr|A0A0B4J2F2|A0A0B4J2F2_HUMAN
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQ
```
- Species code `HUMAN` is mapped to TaxID `9606`

#### 3. With Explicit TaxID (OX field)
```
>UniRef100_ABC123 OX=9606 n=5 Tax=Homo sapiens
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQ
```

#### 4. NCBI Format
```
>gi|123|ref|NP_001.1| protein [Homo sapiens]
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQ
```

---

## Output: Paired CSV Format

Boltz2 expects a simple CSV format with two columns:

| Column | Description |
|--------|-------------|
| `key` | Pairing identifier (rows with same key are paired) |
| `sequence` | Amino acid sequence |

### Example Output

**Chain A CSV** (`paired_chain_A.csv`):
```csv
key,sequence
1,MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
2,MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
3,MKTVRQERLKSIVRILERSKDPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
```

**Chain B CSV** (`paired_chain_B.csv`):
```csv
key,sequence
1,MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD
2,MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD
3,MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAERPAD
```

**Key insight**: Row 1 in Chain A and Row 1 in Chain B have the same key (`1`), so Boltz2 treats them as paired sequences from the same organism.

---

## Pairing Strategies

### Greedy Strategy (Default)

The **greedy** strategy is the default and matches ColabFold's behavior since June 2023.

- Takes the **first** matching sequence for each organism
- Fast and produces good results for most cases
- Recommended for general use

```python
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'},
    pairing_strategy='greedy'  # Default
)
```

### Complete Strategy

The **complete** strategy creates all possible pair combinations for each organism.

- If organism X has 3 sequences in Chain A and 2 in Chain B, creates 3×2 = 6 pairs
- Results in larger MSAs
- May improve predictions for difficult targets

```python
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'},
    pairing_strategy='complete'
)
```

---

## Include Unpaired Sequences

By default, only sequences with matches across **all chains** are included. The `include_unpaired` option adds sequences that exist in only some chains using a **block-diagonal format**.

### What is Block-Diagonal Format?

Unpaired sequences are included with gap characters (`-`) for chains where they don't exist:

```
Without include_unpaired:          With include_unpaired:
                                   
Chain A    Chain B                 Chain A    Chain B
───────    ───────                 ───────    ───────
MKTVRQ     MVTPEG  ← paired        MKTVRQ     MVTPEG  ← paired
MKTVRQ     MVTPEG  ← paired        MKTVRQ     MVTPEG  ← paired
                                   MKAAYQ     ------  ← A only (block-diagonal)
                                   ------     MSXYZQ  ← B only (block-diagonal)
```

### When to Use

| Scenario | Recommendation |
|----------|----------------|
| Standard multimer prediction | `include_unpaired=False` (default) |
| Low sequence coverage | `include_unpaired=True` |
| Chains from different kingdoms | `include_unpaired=True` |
| Maximum MSA depth needed | `include_unpaired=True` |

### Usage

```python
# Python API
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'},
    include_unpaired=True
)

# CLI
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --include-unpaired
```

### Detailed Example

Given:
- **Chain A**: Query + organisms {Human, Mouse, Zebrafish, **Yeast**}
- **Chain B**: Query + organisms {Human, Mouse, Zebrafish, **E.coli**}

**Without `include_unpaired`** (4 rows):
```
key  Chain A              Chain B
───  ───────              ───────
1    Query                Query
2    Human seq            Human seq
3    Mouse seq            Mouse seq
4    Zebrafish seq        Zebrafish seq
```

**With `include_unpaired`** (6 rows):
```
key  Chain A              Chain B
───  ───────              ───────
1    Query                Query
2    Human seq            Human seq
3    Mouse seq            Mouse seq
4    Zebrafish seq        Zebrafish seq
5    Yeast seq            -----------    ← Block-diagonal
6    -----------          E.coli seq     ← Block-diagonal
```

---

## Usage

### Python API

#### Basic Conversion

```python
from boltz2_client import convert_a3m_to_multimer_csv, create_paired_msa_per_chain

# Convert A3M files to paired CSV
result = convert_a3m_to_multimer_csv(
    a3m_files={
        'A': 'chain_A.a3m',
        'B': 'chain_B.a3m'
    },
    output_path='paired.csv'  # Optional: save to file
)

print(f"Created {result.num_pairs} paired sequences")
print(f"Query sequences: {result.query_sequences}")
```

#### Full Prediction Workflow

```python
from boltz2_client import (
    Boltz2Client,
    Polymer,
    PredictionRequest,
    convert_a3m_to_multimer_csv,
    create_paired_msa_per_chain,
    save_prediction_outputs,
    get_prediction_summary,
)

# Step 1: Convert A3M to paired CSV
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'},
    include_unpaired=True  # Include all sequences
)

# Step 2: Create MSA data structures for each chain
msa_per_chain = create_paired_msa_per_chain(result)

# Step 3: Build prediction request
protein_A = Polymer(
    id='A',
    molecule_type='protein',
    sequence=result.query_sequences['A'],
    msa=msa_per_chain['A']
)

protein_B = Polymer(
    id='B',
    molecule_type='protein',
    sequence=result.query_sequences['B'],
    msa=msa_per_chain['B']
)

request = PredictionRequest(
    polymers=[protein_A, protein_B],
    recycling_steps=3,
    sampling_steps=200
)

# Step 4: Run prediction
client = Boltz2Client(base_url="http://localhost:8000")
response = await client.predict(request)

# Step 5: Save all outputs
saved = save_prediction_outputs(
    response=response,
    output_dir="results/",
    base_name="my_complex",
    save_structure=True,
    save_scores=True,
    save_csv=True,
    conversion_result=result
)

# Step 6: Get summary
summary = get_prediction_summary(response)
print(f"Confidence: {summary['confidence']:.2f}")
print(f"Quality: {summary['quality_assessment']}")
```

#### Advanced: Custom Pairing Strategy

```python
from boltz2_client.a3m_to_csv_converter import (
    A3MToCSVConverter,
    GreedyPairingStrategy,
    CompletePairingStrategy,
)

# Use complete pairing with TaxID matching
strategy = CompletePairingStrategy(use_tax_id=True)
converter = A3MToCSVConverter(
    pairing_strategy=strategy,
    include_unpaired=True,
    max_pairs=1000
)

result = converter.convert_files(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'}
)
```

### Command Line Interface

#### Convert A3M to CSV Only

```bash
# Basic conversion
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv

# With unpaired sequences
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --include-unpaired

# Limit number of pairs
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --max-pairs 500

# Force TaxID or UniRef pairing mode
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --pairing-mode taxid
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --pairing-mode uniref
```

#### End-to-End Prediction

```bash
# Basic prediction
boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B

# With custom output and all files saved
boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B \
    -o my_complex.cif \
    --save-all \
    --save-csv

# Include unpaired sequences
boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B --include-unpaired

# Three-chain complex
boltz2 multimer-msa a.a3m b.a3m c.a3m -c A,B,C -o trimer.cif

# Higher quality prediction
boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B \
    --sampling-steps 400 \
    --diffusion-samples 3
```

---

## Configuration Options

### Pairing Mode (`--pairing-mode` / `use_tax_id`)

| Mode | Description | When to Use |
|------|-------------|-------------|
| `auto` | Auto-detect based on A3M content | Default, recommended |
| `taxid` | Force TaxID-based pairing | A3M has OX= fields or species codes |
| `uniref` | Force UniRef ID pairing | Standard ColabFold output |

### Pairing Strategy (`--pairing-strategy` / `pairing_strategy`)

| Strategy | Description |
|----------|-------------|
| `greedy` | First match per organism (default, ColabFold-style) |
| `complete` | All combinations per organism |
| `taxonomy` | Alias for greedy + taxid mode |

### Other Options

| Option | Description | Default |
|--------|-------------|---------|
| `include_unpaired` | Include unmatched sequences with gaps | `False` |
| `max_pairs` | Limit number of paired rows | None (unlimited) |
| `save_csv` | Save intermediate CSV files | `False` |
| `save_all` | Save structure, scores, and CSVs | `False` |

---

## Best Practices

### 1. Use Auto-Detection

Let the converter auto-detect the pairing mode:

```python
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'a.a3m', 'B': 'b.a3m'},
    use_tax_id=None  # Auto-detect (default)
)
```

### 2. Check Pairing Quality

Verify you have enough paired sequences:

```python
result = convert_a3m_to_multimer_csv(...)

print(f"Paired sequences: {result.num_pairs}")
if result.num_pairs < 10:
    print("Warning: Low pairing count. Consider using --include-unpaired")
```

### 3. Use Include Unpaired for Low Coverage

If your proteins are from different organisms or have low sequence identity:

```python
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'a.a3m', 'B': 'b.a3m'},
    include_unpaired=True
)
```

### 4. Limit Pairs for Large MSAs

For very large MSAs, limit pairs to improve performance:

```python
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'a.a3m', 'B': 'b.a3m'},
    max_pairs=1000
)
```

### 5. Save All Outputs for Analysis

Use `save_prediction_outputs()` to save everything:

```python
saved = save_prediction_outputs(
    response=response,
    output_dir="results/",
    save_structure=True,
    save_scores=True,
    save_csv=True,
    conversion_result=result
)
```

---

## Troubleshooting

### No Paired Sequences Found

**Problem**: `num_pairs = 1` (only query)

**Solutions**:
1. Check if A3M files have TaxID annotations
2. Try `--pairing-mode uniref` for standard ColabFold output
3. Use `--include-unpaired` to include all sequences

```bash
# Check A3M headers
head -20 chain_A.a3m

# Try UniRef mode
boltz2 convert-msa a.a3m b.a3m -c A,B -o out.csv --pairing-mode uniref
```

### Sequence Mismatch Error

**Problem**: `First sequence in CSV alignment paired does not match input sequence`

**Solution**: Ensure the query sequence in Boltz2 request matches the first sequence in your A3M file:

```python
# Use query sequences from conversion result
protein_A = Polymer(
    id='A',
    sequence=result.query_sequences['A'],  # Use this!
    msa=msa_per_chain['A']
)
```

### Species Code Not Found

**Problem**: Warning about unknown species code

**Solution**: The converter includes a comprehensive species mapping. For rare species:
1. Use explicit `OX=` field in A3M headers
2. The converter will attempt online lookup if enabled

### Large MSA Performance

**Problem**: Conversion is slow for large MSAs

**Solutions**:
1. Limit pairs: `--max-pairs 1000`
2. Use default (no `--include-unpaired`) to reduce rows
3. Pre-filter A3M files to remove redundant sequences

---

## Summary

The A3M to Multimer MSA converter enables seamless transition from ColabFold monomer searches to Boltz2 multimer predictions by:

1. **Parsing** various A3M header formats
2. **Pairing** sequences by organism (TaxID or UniRef ID)
3. **Generating** per-chain CSVs with matching keys
4. **Optionally including** unpaired sequences in block-diagonal format

This provides Boltz2 with the co-evolutionary signal needed for accurate multimer structure prediction.

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
