# MSA Search NIM Integration Guide

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.

This guide explains how to use NVIDIA's GPU-accelerated MSA Search NIM (v2.3.0+) with the Boltz-2 Python Client for enhanced protein structure predictions.

Reference: [MSA Search NIM docs](https://docs.nvidia.com/nim/bionemo/msa-search/2.3.0/overview.html)

## Overview

The MSA Search NIM integration provides:
- **Monomer MSA Search** -- GPU-accelerated sequence similarity search
- **Paired MSA Search** (v2.1.0+) -- species-based pairing for protein complexes
- **Structural Template Search** (v2.2.0+) -- find homologous PDB structures
- Output formats: A3M, FASTA
- Seamless integration with Boltz-2 structure prediction
- Batch processing capabilities for multiple sequences

## Quick Start

### 1. Configure MSA Search

```python
from boltz2_client import Boltz2Client

# Initialize Boltz-2 client
client = Boltz2Client(base_url="http://localhost:8000")

# Configure MSA Search NIM
# For NVIDIA-hosted endpoint:
client.configure_msa_search(
    msa_endpoint_url="https://health.api.nvidia.com/v1/biology/nvidia/msa-search",
    api_key="your_nvidia_api_key"  # Or set NVIDIA_API_KEY env var
)

# For local deployment:
client.configure_msa_search(
    msa_endpoint_url="http://localhost:8001"
)
```

### 2. Search MSA and Predict Structure

```python
# One-step MSA search + structure prediction
result = await client.predict_with_msa_search(
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    databases=["Uniref30_2302", "colabfold_envdb_202108"],
    max_msa_sequences=1000,
    e_value=10.0
)

print(f"Confidence: {result.confidence_scores[0]:.3f}")
```

## Detailed Usage

### MSA Search Only

```python
# Search and get results as object
response = await client.search_msa(
    sequence="YOUR_PROTEIN_SEQUENCE",
    databases=["Uniref30_2302", "colabfold_envdb_202108"],
    max_msa_sequences=1000,
    e_value=10.0
)

print(f"MSA search completed for {len(response.alignments)} databases")
```

### Save MSA in Different Formats

```python
# Search and save MSA in different formats
from boltz2_client import MSASearchIntegration

# Configure MSA integration
msa_integration = MSASearchIntegration(client._msa_search_client)

# Save as A3M (for structure prediction)
a3m_path = await msa_integration.search_and_save(
    sequence="YOUR_PROTEIN_SEQUENCE",
    output_path="protein_msa.a3m",
    output_format="a3m",
    databases=["Uniref30_2302"],
    max_msa_sequences=500
)

# Save as FASTA (for alignment viewers)
fasta_path = await msa_integration.search_and_save(
    sequence="YOUR_PROTEIN_SEQUENCE",
    output_path="protein_msa.fasta",
    output_format="fasta",
    databases=["Uniref30_2302"],
    max_msa_sequences=500
)

```

### Batch MSA Search

```python
# Define multiple sequences
sequences = {
    "Protein1": "MKTVRQERLKSIVRILERSKEPVSGAQ...",
    "Protein2": "MQIFVKTLTGKTITLEVEPSDTIENVK...",
    "Protein3": "KVFERCELARTLKRLGMDGYRGISLAN..."
}

# Batch search
msa_paths = await client.batch_msa_search(
    sequences=sequences,
    output_dir="batch_msa_results",
    output_format="a3m",
    databases=["Uniref30_2302"],
    max_msa_sequences=500
)

for seq_id, path in msa_paths.items():
    print(f"{seq_id}: {path}")
```

## Paired MSA Search (Multimers)

For protein complexes, paired search finds homologs per chain and pairs them by
species -- essential for AlphaFold-Multimer and Boltz-2 multimer predictions.

```python
from boltz2_client import MSASearchClient

msa_client = MSASearchClient(endpoint_url="http://localhost:8001")

# Two-chain hemoglobin example
response = await msa_client.paired_search(
    sequences={
        "A": "VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH",
        "B": "MHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPYTQRFFESFGDLST",
    },
    pairing_strategy="greedy",   # or "complete" (all chains required)
    databases=["uniref30_2302"],
)

for chain_id, dbs in response.alignments_by_chain.items():
    for db, fmts in dbs.items():
        print(f"Chain {chain_id} / {db}: {len(fmts['a3m'].alignment)} chars")
```

Pairing strategies (only differ for 3+ chains):
- **greedy** -- maximise rows, allow gaps where a species lacks a chain
- **complete** -- only include species with hits for *all* chains

## Structural Template Search

Find homologous PDB structures and retrieve mmCIF files in one request.

```python
response = await msa_client.template_search(
    sequence="VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH",
    structural_template_databases=["pdb70_220313"],
    max_structures=10,
)

# Template hits
for pdb_id, tpl in response.structures.items():
    print(f"{pdb_id}: {tpl.format}, {len(tpl.structure)} chars")

# MSA alignments (same as monomer search)
a3m = response.alignments["uniref30_2302"]["a3m"].alignment
```

## Available Databases

The default ColabFold databases shipped with MSA Search NIM v2.0+ (GPU-Server
enabled by default):

- **uniref30_2302** -- UniRef clusters at 30 % identity (2023-02)
- **colabfold_envdb_202108** -- ColabFold environmental database (2021-08)
- **pdb70_220313** -- PDB sequences clustered at 70 % identity (for templates)

> Database names are **case-insensitive** since v2.2.0.

Check available databases:
```python
metadata = await msa_client.get_metadata()    # preferred (v2.2.0+)
# or (deprecated):
# configs = await msa_client.get_databases()
```

## Parameters

### Monomer Search

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sequence` | str | *required* | Query protein sequence (1-4096 chars, accepts `X`) |
| `databases` | list[str] | `["all"]` | Databases to search (case-insensitive) |
| `max_msa_sequences` | int | 500 | Max sequences per database (`NIM_GLOBAL_MAX_MSA_DEPTH`) |
| `e_value` | float | 0.0001 | E-value threshold (0.0-1.0) |
| `output_alignment_formats` | list[str] | `["a3m"]` | `"a3m"` and/or `"fasta"` |
| `search_type` | str | `"colabfold"` | `"colabfold"` (cascaded) or `"alphafold2"` (single-pass) |

### Paired Search

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sequences` | list or dict | *required* | One sequence per chain (min 2) |
| `pairing_strategy` | str | `"greedy"` | `"greedy"` or `"complete"` |
| `unpack` | bool | `True` | Per-chain output vs raw combined |
| `databases` / `e_value` / `max_msa_sequences` | | | Same as monomer |

### Structural Template Search

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sequence` | str | *required* | Query protein sequence |
| `structural_template_databases` | list[str] | `["pdb70_220313"]` | PDB databases for templates |
| `msa_databases` | list[str] | `["all"]` | Databases for MSA generation |
| `max_structures` | int | 20 | Max PDB structures to return |
| `e_value` / `max_msa_sequences` | | | Same as monomer |

### Output Formats

- **a3m** -- A3M format with metadata (recommended for structure prediction)
- **fasta** -- Standard FASTA format

## Advanced Usage

### Custom MSA Search Client

```python
from boltz2_client import MSASearchClient, MSAFormatConverter

msa_client = MSASearchClient(
    endpoint_url="http://localhost:8001",
    timeout=300,
    max_retries=3,
)

# Monomer search
response = await msa_client.search(
    sequence="YOUR_SEQUENCE",
    databases=["uniref30_2302"],
    max_msa_sequences=500,
)
a3m_content = MSAFormatConverter.extract_alignment(response, "a3m")
fasta_content = MSAFormatConverter.extract_alignment(response, "fasta")

# Paired search for a multimer
paired = await msa_client.paired_search(
    sequences=["SEQ_CHAIN_A", "SEQ_CHAIN_B"],
    pairing_strategy="greedy",
)

# Structural template search
templates = await msa_client.template_search(
    sequence="YOUR_SEQUENCE",
    structural_template_databases=["pdb70_220313"],
    max_structures=10,
)
```

### Response Structures

```python
# Monomer MSASearchResponse:
response.alignments     # Dict[database][format] -> AlignmentFileRecord
response.metrics        # Optional search metrics

# Paired PairedMSASearchResponse:
response.alignments_by_chain   # Dict[chain_id][database][format] -> AlignmentFileRecord

# Template StructuralTemplateResponse:
response.alignments     # MSA alignments (same as monomer)
response.search_hits    # Dict[database][format] -> SearchHitRecord (M8 format)
response.structures     # Dict[pdb_id] -> StructuralTemplate (mmCIF)

# Each AlignmentFileRecord contains:
record.alignment    # The alignment content (A3M or FASTA format)
record.format       # The format type ("a3m" or "fasta")
```

## Integration with YAML Configs

You can reference MSA files generated by MSA Search in YAML configurations:

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: "MKTVRQERLKSIVRILERSKEPVSGAQ..."
      msa: "protein_A_msa.a3m"  # Generated by MSA Search
```

## Best Practices

1. **Database Selection**
   - Use `uniref30_2302` for general proteins
   - Add `colabfold_envdb_202108` for environmental sequences
   - Use `pdb70_220313` for structural template search

2. **Parameter Tuning**
  - Increase max_msa_sequences for proteins with many homologs
  - Lower e_value for more stringent matches
   - Balance search time vs. MSA quality

3. **Performance Optimization**
   - Use batch search for multiple sequences
   - Cache MSA results for repeated predictions
   - Adjust timeout based on sequence length

4. **Error Handling**
   ```python
   try:
       result = await client.predict_with_msa_search(sequence)
   except Exception as e:
       print(f"MSA search failed: {e}")
       # Fall back to prediction without MSA
       result = await client.predict_protein_structure(sequence)
   ```

## Troubleshooting

### Common Issues

1. **MSA Search not configured**
   - Error: "MSA Search not configured. Call configure_msa_search() first."
   - Solution: Configure MSA search before using MSA methods

2. **Timeout errors**
   - Increase timeout in configure_msa_search()
   - Reduce max_msa_sequences for faster searches

3. **API key issues**
   - Set NVIDIA_API_KEY environment variable
   - Or pass api_key to configure_msa_search()

4. **Database not available**
   - Check available databases with `msa_client.get_metadata()`
   - Use only supported database names (case-insensitive since v2.2.0)

## Example Scripts

See `examples/10_msa_search_integration.py` for comprehensive examples including:
- Basic MSA search and export
- Automated MSA + structure prediction
- Comparison with/without MSA
- Batch processing
- Multiple output formats

## Performance Tips

- MSA search typically takes 30-300 seconds depending on:
  - Sequence length
  - Number of databases searched
  - max_msa_sequences parameter
  - Network latency (for hosted endpoints)

- For production use:
  - Use NVIDIA-hosted endpoints for scalability
  - Implement caching for frequently searched sequences
  - Consider batch processing for multiple proteins

## CLI Usage

The MSA Search functionality is also available through the command-line interface:

### MSA Search Command

Search for homologous sequences and save the alignment:

```bash
# Basic MSA search
boltz2 msa-search "MKTVRQERLKSIVRILERSKEPVSGAQ..." -o output.a3m

# Search specific databases with custom parameters
boltz2 msa-search "SEQUENCE" -d Uniref30_2302 -d PDB70_220313 --max-sequences 1000 -o output.a3m

# Export in different format
boltz2 msa-search "SEQUENCE" -f fasta -o output.fasta

# Use custom endpoint
boltz2 msa-search "SEQUENCE" --endpoint http://your-msa-nim:8000 -o output.a3m
```

Options:
- `--endpoint`: MSA Search NIM endpoint URL
- `-d, --databases`: Databases to search (can specify multiple)
- `--max-sequences`: Maximum sequences to return
- `--e-value`: E-value threshold
- `-f, --output-format`: Output format (a3m, fasta)
- `-o, --output`: Output file path (required)

### MSA-Guided Prediction Command

Perform MSA search and structure prediction in one step:

```bash
# Basic MSA-guided prediction
boltz2 msa-predict "MKTVRQERLKSIVRILERSKEPVSGAQ..."

# Custom parameters
boltz2 msa-predict "SEQUENCE" --max-sequences 1000 --recycling-steps 5

# Save to specific directory
boltz2 msa-predict "SEQUENCE" --output-dir results/

# Don't save MSA separately
boltz2 msa-predict "SEQUENCE" --no-save-msa
```

Options:
- `--endpoint`: MSA Search NIM endpoint URL
- `-d, --databases`: Databases to search
- `--max-sequences`: Maximum sequences for MSA
- `--e-value`: E-value threshold
- `--recycling-steps`: Number of recycling steps (1-10)
- `--sampling-steps`: Number of sampling steps (10-1000)
- `--output-dir`: Directory to save output files
- `--no-save-msa`: Don't save the MSA file separately

### Example Workflow

```bash
# 1. Search MSA for your protein
boltz2 msa-search "MKTVRQERLKSIVRILERSKEPVSGAQ..." -o my_protein.a3m

# 2. Use the MSA for structure prediction
boltz2 protein "MKTVRQERLKSIVRILERSKEPVSGAQ..." --msa-file my_protein.a3m a3m

# Or do both in one step
boltz2 msa-predict "MKTVRQERLKSIVRILERSKEPVSGAQ..." --output-dir results/
```

## References

- [NVIDIA MSA Search NIM v2.3.0 Documentation](https://docs.nvidia.com/nim/bionemo/msa-search/2.3.0/overview.html)
- [Boltz-2 Python Client](https://github.com/NVIDIA/digital-biology-examples/tree/main/examples/nims/boltz-2)
- [A3M Format Specification](http://soeding.genzentrum.lmu.de/software/hhsuite/)

---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
