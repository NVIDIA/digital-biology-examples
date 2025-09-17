# Virtual Screening Guide

The Boltz-2 Python client provides a powerful high-level API for virtual screening campaigns, enabling drug discovery workflows with minimal code.

## Overview

Virtual screening allows you to:
- Screen compound libraries against protein targets
- Predict binding affinities and poses
- Parallelize predictions for high throughput
- Analyze and rank results automatically
- Export structures and results for further analysis

## Quick Start

### Minimal Example

```python
from boltz2_client import quick_screen

# Define compounds
compounds = [
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"}
]

# Run screening
result = quick_screen(
    target_sequence="MKTVRQERLKSIVRILERSKEPVSGAQ...",
    compounds=compounds,
    target_name="My Protein",
    output_dir="screening_results"
)

# View top hits
print(result.get_top_hits(n=5))
```

### CLI Usage

```bash
# Screen compounds from CSV file
boltz2 screen "PROTEIN_SEQUENCE" compounds.csv -o results/

# Screen with pocket constraints
boltz2 screen target.fasta library.csv --pocket-residues "10,15,20,25" --pocket-radius 12.0

# Disable affinity prediction for faster screening
boltz2 screen "SEQUENCE" compounds.json --no-affinity -o fast_screen/

# Use multiple endpoints for parallel screening (NEW)
boltz2 --multi-endpoint "http://localhost:8000,http://localhost:8001,http://localhost:8002" \
  screen "PROTEIN_SEQUENCE" compounds.csv -o multi_results/

# Multi-endpoint with load balancing strategy
boltz2 --multi-endpoint "http://localhost:8000,http://localhost:8001" \
  --load-balance-strategy least-loaded \
  screen target.fasta large_library.csv --predict-affinity
```

## Compound Libraries

### From Python Lists

```python
compounds = [
    {
        "name": "Compound1",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "metadata": {
            "type": "inhibitor",
            "known_ic50": 100.5,
            "source": "literature"
        }
    },
    # ... more compounds
]
```

### From CSV Files

Create a CSV file with compound information:

```csv
name,smiles,type,known_ic50
Aspirin,CC(=O)OC1=CC=CC=C1C(=O)O,NSAID,1000
Ibuprofen,CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,NSAID,5000
```

Load and use:

```python
from boltz2_client import CompoundLibrary

library = CompoundLibrary.from_csv("compounds.csv")
```

### From JSON Files

```json
[
    {
        "name": "Aspirin",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "metadata": {"type": "NSAID"}
    }
]
```

## Advanced Usage

### With Pocket Constraints

```python
from boltz2_client import VirtualScreening

screener = VirtualScreening()

# Define binding pocket residues (0-indexed)
pocket_residues = [45, 50, 55, 60, 65, 70, 75]

result = screener.screen(
    target_sequence=sequence,
    compound_library=compounds,
    pocket_residues=pocket_residues,
    pocket_radius=10.0,  # Angstroms
    predict_affinity=True
)
```

### Parallel Processing Control

```python
# Control parallelization
screener = VirtualScreening(max_workers=8)

# Process in batches
result = screener.screen(
    target_sequence=sequence,
    compound_library=large_library,
    batch_size=10,  # Process 10 compounds at a time
    progress_callback=lambda done, total: print(f"{done}/{total}")
)
```

### Custom Parameters

```python
result = screener.screen(
    target_sequence=sequence,
    compound_library=compounds,
    # Structure prediction parameters
    recycling_steps=3,
    sampling_steps=50,
    diffusion_samples=2,
    # Affinity prediction parameters
    sampling_steps_affinity=200,
    diffusion_samples_affinity=5,
    affinity_mw_correction=True
)
```

## Analyzing Results

### Basic Analysis

```python
# Get summary statistics
print(f"Success rate: {result.success_rate:.1%}")
print(f"Duration: {result.duration_seconds:.1f} seconds")

# Get top compounds by pIC50
top_hits = result.get_top_hits(n=10, by="predicted_pic50")
print(top_hits[["compound_name", "predicted_pic50", "predicted_ic50_nm"]])

# Convert to pandas DataFrame
df = result.to_dataframe()
```

### Group Analysis

```python
# Analyze by compound type
stats = result.get_statistics_by_group(group_by="compound_type")
print(stats)
```

### Saving Results

```python
# Save all results and structures
saved_files = result.save_results(
    output_dir="screening_campaign", 
    save_structures=True  # Save CIF files
)

# Files created:
# - screening_results.csv: All compound results
# - screening_metadata.json: Campaign metadata
# - structures/: Directory with CIF files
```

## Performance Tips

1. **Use Multi-Endpoint Client for Parallel Processing** (NEW)
   ```python
   from boltz2_client import MultiEndpointClient, LoadBalanceStrategy
   
   # Configure multiple endpoints for better throughput
   multi_client = MultiEndpointClient(
       endpoints=[
           "http://localhost:8000",
           "http://localhost:8001",
           "http://localhost:8002",
       ],
       strategy=LoadBalanceStrategy.LEAST_LOADED,
       is_async=True
   )
   screener = VirtualScreening(client=multi_client, max_workers=8)
   ```
   See [MULTI_ENDPOINT_GUIDE.md](MULTI_ENDPOINT_GUIDE.md) for detailed setup.

2. **Use Async Client for Large Libraries**
   ```python
   from boltz2_client import Boltz2Client
   
   client = Boltz2Client()  # Async client
   screener = VirtualScreening(client=client, max_workers=8)
   ```

3. **Adjust Sampling for Speed vs Accuracy**
   - For initial screening: `sampling_steps=20, sampling_steps_affinity=50`
   - For final hits: `sampling_steps=100, sampling_steps_affinity=200`

4. **Batch Processing for Memory Management**
   ```python
   # For libraries with 1000+ compounds
   result = screener.screen(
       target_sequence=sequence,
       compound_library=huge_library,
       batch_size=50,
       max_workers=4
   )
   ```

5. **Disable Affinity for Structure-Only Screening**
   ```python
   result = screener.screen(
       target_sequence=sequence,
       compound_library=compounds,
       predict_affinity=False  # 2-3x faster
   )
   ```

## Example Workflow

```python
from boltz2_client import VirtualScreening, CompoundLibrary
import pandas as pd

# 1. Load compound library
library = CompoundLibrary.from_csv("fda_approved_drugs.csv")

# 2. Define target
target_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQ..."  # Your target

# 3. Run screening with progress
screener = VirtualScreening(max_workers=6)

def show_progress(done, total):
    print(f"\rScreening: {done}/{total} ({done/total:.1%})", end="")

result = screener.screen(
    target_sequence=target_sequence,
    compound_library=library,
    target_name="Kinase Target",
    recycling_steps=2,
    sampling_steps=30,
    progress_callback=show_progress
)

# 4. Analyze results
print(f"\n\nSuccess rate: {result.success_rate:.1%}")
top_10 = result.get_top_hits(n=10)

# 5. Save for further analysis
result.save_results("kinase_screening_results")

# 6. Export to Excel for sharing
df = result.to_dataframe()
df.to_excel("screening_results.xlsx", index=False)
```

## Troubleshooting

### Out of Memory Errors
- Reduce `max_workers` 
- Enable batching with `batch_size`
- Use shorter protein sequences for initial screening

### Slow Performance
- Disable affinity prediction for initial screening
- Reduce sampling steps
- Use async client with more workers

### Failed Predictions
- Check SMILES validity
- Ensure protein sequence has valid amino acids
- Verify service is running and healthy

## Best Practices

1. **Start Simple**: Run initial screens with reduced parameters
2. **Validate Hits**: Re-run top compounds with higher sampling
3. **Use Metadata**: Track compound sources and known activities
4. **Save Everything**: Keep raw results for reanalysis
5. **Monitor Progress**: Use callbacks for long campaigns

## API Reference

See the [API documentation](API_REFERENCE.md) for detailed parameter descriptions.
---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
