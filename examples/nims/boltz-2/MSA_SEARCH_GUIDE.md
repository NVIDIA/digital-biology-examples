# MSA Search NIM Integration Guide

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

This guide explains how to use NVIDIA's GPU-accelerated MSA Search NIM with the Boltz-2 Python Client for enhanced protein structure predictions.

## Overview

The MSA Search NIM integration provides:
- GPU-accelerated sequence similarity search across multiple databases
- Automatic MSA generation from protein sequences
- Multiple output format support (A3M, FASTA, CSV, Stockholm)
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

# Save as Stockholm (for conservation analysis)
sto_path = await msa_integration.search_and_save(
    sequence="YOUR_PROTEIN_SEQUENCE",
    output_path="protein_msa.sto",
    output_format="sto",
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

## Available Databases

The MSA Search NIM supports multiple sequence databases:

- **Uniref30_2302**: UniRef clusters at 30% identity (updated 2023-02)
- **uniref50**: UniRef clusters at 50% identity  
- **uniref30**: UniRef clusters at 30% identity
- **colabfold_envdb_202108**: ColabFold environmental database (2021-08)
- **bfd**: Big Fantastic Database
- **uniclust30**: UniClust clusters at 30% identity
- **pdb70**: PDB sequences clustered at 70% identity
- **pfam**: Pfam protein families
- **envdb**: Environmental sequence database

Check available databases:
```python
databases = await client.get_msa_databases()
print(f"Available: {databases}")
```

## Parameters

### MSA Search Parameters

- **sequence** (str): Query protein sequence
- **databases** (List[str]): Databases to search (default: ["Uniref30_2302", "colabfold_envdb_202108"])
- **max_msa_sequences** (int): Maximum number of sequences to return (1-10001, default: 500)
- **e_value** (float): E-value threshold for hits (default: 0.0001)

### Output Formats

- **a3m**: A3M format with metadata (recommended for structure prediction)
- **fasta**: Standard FASTA format
- **csv**: CSV with hit statistics and sequences
- **sto**: Stockholm format with alignment metadata

## Advanced Usage

### Custom MSA Search Client

```python
from boltz2_client import MSASearchClient, MSAFormatConverter

# Create standalone MSA search client
msa_client = MSASearchClient(
    endpoint_url="https://health.api.nvidia.com/v1/biology/nvidia/msa-search",
    api_key="your_api_key",
    timeout=300,
    max_retries=3
)

# Search
response = await msa_client.search(
    sequence="YOUR_SEQUENCE",
    databases=["Uniref30_2302"],
    max_msa_sequences=1000
)

# Convert to desired format
a3m_content = MSAFormatConverter.extract_alignment(response, "a3m")
fasta_content = MSAFormatConverter.extract_alignment(response, "fasta")
sto_content = MSAFormatConverter.extract_alignment(response, "sto")
```

### MSA Search Response Structure

```python
# Response contains:
response.alignments     # Dict[database][format] -> AlignmentFileRecord
response.templates      # Optional template hits
response.metrics        # Optional search metrics

# Each AlignmentFileRecord contains:
record.alignment    # The alignment content (A3M/FASTA/STO format)
record.format       # The format type ("a3m", "fasta", "sto")
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
   - Use Uniref30_2302 for general proteins
   - Add colabfold_envdb_202108 for environmental sequences
   - Use pdb70 when structural homologs are important

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
   - Check available databases with get_msa_databases()
   - Use only supported database names

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
- `-f, --output-format`: Output format (a3m, fasta, sto)
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
- `--recycling-steps`: Number of recycling steps (1-6)
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

- [NVIDIA MSA Search NIM Documentation](https://docs.nvidia.com/nim/bionemo/msa-search/latest/index.html)
- [Boltz-2 Python Client](https://github.com/NVIDIA/digital-biology-examples/tree/main/examples/nims/boltz-2)
- [A3M Format Specification](http://soeding.genzentrum.lmu.de/software/hhsuite/)

---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
