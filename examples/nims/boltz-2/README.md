# Boltz-2 Python Client

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

[![PyPI version](https://badge.fury.io/py/boltz2-python-client.svg)](https://badge.fury.io/py/boltz2-python-client)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Python client for NVIDIA's Boltz-2 biomolecular structure prediction service. This package provides both synchronous and asynchronous interfaces, a rich CLI, and built-in 3D visualization capabilities.

## 🚀 **Features**

- ✅ **Full API Coverage** - Complete Boltz-2 API support
- ✅ **Async & Sync Clients** - Choose your preferred programming style
- ✅ **Rich CLI Interface** - Beautiful command-line tools with progress bars
- ✅ **3D Visualization** - Built-in py3Dmol integration for structure viewing
- ✅ **Flexible Endpoints** - Support for both local and NVIDIA hosted services
- ✅ **Type Safety** - Full Pydantic model validation
- ✅ **YAML Configuration** - Official Boltz format support
- ✅ **Affinity Prediction** - Predict binding affinity (IC50) for protein-ligand complexes
- ✅ **Virtual Screening** - High-level API for drug discovery campaigns
- ✅ **MSA Search Integration** - GPU-accelerated MSA generation with NVIDIA MSA Search NIM
- ✅ **A3M to Multimer MSA** - Convert ColabFold A3M files to paired multimer format (NEW)
- ✅ **Multi-Endpoint Load Balancing** - Distribute predictions across multiple NIMs
- ✅ **Comprehensive Examples** - Ready-to-use code samples

## 📦 **Installation**

### From PyPI (Recommended)
```bash
pip install boltz2-python-client
```

### From TestPyPI (Latest Development)
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ boltz2-python-client
```

### From Source
```bash
git clone https://github.com/NVIDIA/digital-biology-examples.git
cd digital-biology-examples/examples/nims/boltz-2
pip install -e .
```

## 🎯 **Quick Start**

### Python API

```python
import asyncio
from boltz2_client import Boltz2Client

async def quick_prediction():
    client = Boltz2Client(base_url="http://localhost:8000")
    seq = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"

    # --- BASIC (no MSA) --------------------------------------------
    basic = await client.predict_protein_structure(sequence=seq)
    print("basic confidence", basic.confidence_scores[0])

    # --- MSA-GUIDED --------------------------------------------------
    msa_path = "msa-kras-g12c_combined.a3m"  # any *.a3m/*.sto/*.fasta file
    msa   = [(msa_path, "a3m")]

    msa_res = await client.predict_protein_structure(
        sequence=seq,
        msa_files=msa,            # NEW helper will auto-convert ➜ nested-dict
        sampling_steps=50,
        recycling_steps=3,
    )
    print("msa confidence", msa_res.confidence_scores[0])

if __name__ == "__main__":
    asyncio.run(quick_prediction())
```

### CLI Usage

```bash
# Health check
boltz2 health

# Protein structure prediction
boltz2 protein "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"

# Protein-ligand complex
boltz2 ligand "PROTEIN_SEQUENCE" --smiles "CC(=O)OC1=CC=CC=C1C(=O)O"

# Protein-ligand with affinity prediction
boltz2 ligand "PROTEIN_SEQUENCE" --smiles "CC(=O)OC1=CC=CC=C1C(=O)O" --predict-affinity

# Covalent complex with bond constraints
boltz2 covalent "SEQUENCE" --ccd U4U --bond A:11:SG:L:C22

# Virtual screening campaign
boltz2 screen "TARGET_SEQUENCE" compounds.csv -o screening_results/

# MSA search
boltz2 msa-search "PROTEIN_SEQUENCE" --databases Uniref30_2302 colabfold_envdb_202108 --output msa.a3m

# MSA search + structure prediction
boltz2 msa-predict "PROTEIN_SEQUENCE" --databases Uniref30_2302 --max-sequences 1000

# MSA search + ligand affinity
boltz2 msa-ligand "PROTEIN_SEQUENCE" --smiles "LIGAND_SMILES" --predict-affinity

# Convert ColabFold A3M files to paired multimer CSV
boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv

# One-command multimer prediction from A3M files (NEW)
boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B -o complex.cif

# Multi-endpoint multimer prediction
boltz2 --multi-endpoint --base-url "http://gpu1:8000,http://gpu2:8000" \
    multimer-msa chain_A.a3m chain_B.a3m -c A,B -o complex.cif
```

### Affinity Prediction

```python
from boltz2_client import Boltz2Client, Polymer, Ligand, PredictionRequest

client = Boltz2Client()

# Create protein and ligand with affinity prediction
protein = Polymer(id="A", molecule_type="protein", sequence="YOUR_SEQUENCE")
ligand = Ligand(id="LIG", smiles="CC(=O)OC1=CC=CC=C1C(=O)O", predict_affinity=True)

request = PredictionRequest(
    polymers=[protein],
    ligands=[ligand],
    sampling_steps_affinity=200,  # Affinity-specific parameters
    diffusion_samples_affinity=5
)

result = await client.predict(request)

# Access affinity results
if result.affinities and "LIG" in result.affinities:
    affinity = result.affinities["LIG"]
    print(f"pIC50: {affinity.affinity_pic50[0]:.2f}")
    print(f"IC50: {10**(-affinity.affinity_pic50[0])*1e9:.1f} nM")
    print(f"Binding probability: {affinity.affinity_probability_binary[0]:.1%}")
```

### MSA Search Integration (NEW)

Integrate GPU-accelerated MSA Search NIM for enhanced protein structure predictions:

```python
from boltz2_client import Boltz2Client

# Initialize and configure MSA Search
client = Boltz2Client()
client.configure_msa_search(
    msa_endpoint_url="https://health.api.nvidia.com/v1/biology/nvidia/msa-search",
    api_key="your_nvidia_api_key"  # Or set NVIDIA_API_KEY env var
)

# One-step MSA search + structure prediction
result = await client.predict_with_msa_search(
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    databases=["Uniref30_2302", "PDB70_220313"],
    max_msa_sequences=1000,
    e_value=0.0001
)

print(f"Confidence: {result.confidence_scores[0]:.3f}")

# Or just search MSA and save in different formats
msa_path = await client.search_msa(
    sequence="YOUR_PROTEIN_SEQUENCE",
    output_format="a3m",  # Options: a3m, fasta, csv, sto
    save_path="protein_msa.a3m"
)
```

See the [MSA Search Guide](MSA_SEARCH_GUIDE.md) for detailed usage and parameters.

### A3M to Multimer MSA Conversion (NEW)

Convert ColabFold-generated A3M monomer MSA files to paired multimer format for Boltz2:

```python
from boltz2_client import (
    Boltz2Client,
    convert_a3m_to_multimer_csv,
    create_paired_msa_per_chain,
    Polymer, PredictionRequest
)

# Convert A3M files to paired MSA (auto-detects pairing mode)
result = convert_a3m_to_multimer_csv(
    a3m_files={'A': 'chain_A.a3m', 'B': 'chain_B.a3m'}
)
print(f"Paired {result.num_pairs} sequences")

# Create per-chain MSA structures for Boltz2
msa_per_chain = create_paired_msa_per_chain(result)

# Create polymers with paired MSA
protein_A = Polymer(id="A", molecule_type="protein", 
                    sequence=result.query_sequences['A'],
                    msa=msa_per_chain['A'])
protein_B = Polymer(id="B", molecule_type="protein",
                    sequence=result.query_sequences['B'],
                    msa=msa_per_chain['B'])

# Predict complex structure
client = Boltz2Client(base_url="http://localhost:8000")
response = await client.predict(PredictionRequest(
    polymers=[protein_A, protein_B],
    recycling_steps=3,
    sampling_steps=200
))
```

#### CLI One-Command Prediction
```bash
# Predict directly from A3M files (converts + predicts in one step)
boltz2 --base-url http://localhost:8000 multimer-msa \
    chain_A.a3m chain_B.a3m \
    -c A,B \
    -o complex.cif

# Save all outputs: structure, paired CSVs, and confidence scores
boltz2 --base-url http://localhost:8000 multimer-msa \
    chain_A.a3m chain_B.a3m \
    -c A,B \
    -o complex.cif \
    --save-csv \    # Save paired CSV files
    --save-all      # Save scores JSON (confidence, pLDDT, pTM, etc.)

# With multi-endpoint load balancing
boltz2 --multi-endpoint \
    --base-url "http://gpu1:8000,http://gpu2:8000,http://gpu3:8000" \
    multimer-msa chain_A.a3m chain_B.a3m -c A,B -o complex.cif --save-all
```

**Output files with `--save-all --save-csv`:**
```
output/
├── complex.cif              # 3D structure (mmCIF)
├── complex.scores.json      # Confidence scores, pLDDT, pTM, metrics
├── complex_chain_A.csv      # Paired MSA for chain A
└── complex_chain_B.csv      # Paired MSA for chain B
```

#### Save All Outputs (Python API)
```python
from boltz2_client import save_prediction_outputs, get_prediction_summary

# Save all outputs with one function call
paths = save_prediction_outputs(
    response=response,
    output_dir=Path("results"),
    base_name="my_complex",
    save_structure=True,   # Save CIF file(s)
    save_scores=True,      # Save scores JSON
    save_csv=True,         # Save paired CSVs
    conversion_result=result  # From convert_a3m_to_multimer_csv
)
print(paths)
# {'structure': Path('results/my_complex.cif'),
#  'scores': Path('results/my_complex.scores.json'),
#  'csv_A': Path('results/my_complex_chain_A.csv'),
#  'csv_B': Path('results/my_complex_chain_B.csv')}

# Get a quick summary of prediction quality
summary = get_prediction_summary(response)
print(f"Confidence: {summary['confidence']:.2f}")
print(f"Quality: {summary['quality_assessment']}")  # Very High/High/Medium/Low
```

See the [A3M to Multimer MSA Guide](examples/A3M_TO_MULTIMER_MSA.md) for detailed usage.

### Virtual Screening

```python
from boltz2_client import quick_screen

# Minimal virtual screening
compounds = [
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"}
]

result = quick_screen(
    target_sequence="YOUR_PROTEIN_SEQUENCE",
    compounds=compounds,
    target_name="My Target",
    output_dir="screening_results"
)

# Show top hits
print(result.get_top_hits(n=5))
```

### Multi-Endpoint Virtual Screening (NEW)

Parallelize screening across multiple Boltz-2 NIM endpoints for better throughput:

```python
from boltz2_client import MultiEndpointClient, LoadBalanceStrategy, VirtualScreening

# Configure multiple endpoints
multi_client = MultiEndpointClient(
    endpoints=[
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",
    ],
    strategy=LoadBalanceStrategy.LEAST_LOADED
)

# Use with virtual screening
vs = VirtualScreening(client=multi_client)
result = await vs.screen(
    target_sequence="YOUR_PROTEIN_SEQUENCE",
    compound_library=compounds,
    predict_affinity=True
)

# View endpoint statistics
multi_client.print_status()
```

See [MULTI_ENDPOINT_GUIDE.md](MULTI_ENDPOINT_GUIDE.md) for detailed setup instructions.

### 3D Visualization

```python
import py3Dmol
from boltz2_client import Boltz2Client

client = Boltz2Client()
result = await client.predict_protein_structure(sequence="YOUR_SEQUENCE", recycling_steps=6, sampling_steps=50 )

# Create 3D visualization
view = py3Dmol.view(width=800, height=600)
view.addModel(result.structures[0].structure, 'cif')
view.setStyle({'cartoon': {'color': 'spectrum'}})
view.zoomTo()
view.show()
```

## 🔧 **Configuration**

### Local Endpoint (Default)
```python
client = Boltz2Client(base_url="http://localhost:8000")
```

### NVIDIA Hosted Endpoint
```python
client = Boltz2Client(
    base_url="https://health.api.nvidia.com",
    api_key="your_api_key",
    endpoint_type="nvidia_hosted"
)
```

### Environment Variables
```bash
export NVIDIA_API_KEY="your_api_key"
export BOLTZ2_BASE_URL="http://localhost:8000"
```

## 🐳 **Local Deployment Setup**

To run Boltz-2 locally using NVIDIA's NIM (NVIDIA Inference Microservice) container, follow these steps:

### Prerequisites
- **NVIDIA GPU** with sufficient VRAM (recommended: 24GB+)
- **Docker** with NVIDIA Container Runtime
- **NGC Account** with API key

### Step 1: Generate NGC API Key
1. Go to [NGC (NVIDIA GPU Cloud)](https://ngc.nvidia.com/)
2. Sign in or create an account
3. Navigate to **Setup → Generate API Key**
4. Copy your personal API key

### Step 2: Docker Login
```bash
# Login to NVIDIA Container Registry
docker login nvcr.io
Username: $oauthtoken
Password: <PASTE_API_KEY_HERE>
```

### Step 3: Set Up Environment
```bash
# Export your NGC API key
export NGC_API_KEY=<your_personal_NGC_key>

# Create local cache directory (recommended for model reuse)
export LOCAL_NIM_CACHE=~/.cache/nim
mkdir -p $LOCAL_NIM_CACHE
chmod -R 777 $LOCAL_NIM_CACHE
```

### Step 4: Run Boltz-2 NIM Container

#### Option A: Use All Available GPUs (Default)
```bash
docker run -it \
    --runtime=nvidia \
    -p 8000:8000 \
    -e NGC_API_KEY \
    -v "$LOCAL_NIM_CACHE":/opt/nim/.cache \
    nvcr.io/nim/mit/boltz2:1.0.0
```

#### Option B: Use Specific GPU (e.g., GPU 0)
```bash
docker run -it \
    --runtime=nvidia \
    --gpus='"device=0"' \
    -p 8000:8000 \
    -e NGC_API_KEY \
    -v "$LOCAL_NIM_CACHE":/opt/nim/.cache \
    nvcr.io/nim/mit/boltz2:1.0.0
```

### Step 5: Verify Installation
Once the container is running, test the service:

```bash
# Health check
curl http://localhost:8000/v1/health/live

# Or using the Python client
python -c "
import asyncio
from boltz2_client import Boltz2Client

async def test():
    client = Boltz2Client(base_url='http://localhost:8000')
    health = await client.health_check()
    print(f'Service status: {health.status}')

asyncio.run(test())
"
```

### 🚨 **Important Notes**

- **First Run**: The container will automatically download models (~several GB), which may take time
- **Cache Directory**: Using `LOCAL_NIM_CACHE` saves bandwidth and time for subsequent runs
- **GPU Memory**: Ensure sufficient GPU memory for your prediction workloads
- **Port 8000**: Make sure port 8000 is available and not blocked by firewall
- **Network**: Container needs internet access for initial model downloads

### 🔧 **Troubleshooting**

**Container fails to start:**
```bash
# Check GPU availability
nvidia-smi

# Check Docker NVIDIA runtime
docker run --rm --runtime=nvidia nvidia/cuda:11.0-base nvidia-smi
```

**Permission issues:**
```bash
# Fix cache directory permissions
sudo chown -R $USER:$USER $LOCAL_NIM_CACHE
chmod -R 755 $LOCAL_NIM_CACHE
```

**Memory issues:**
```bash
# Monitor GPU memory usage
watch -n 1 nvidia-smi

# Use specific GPU with more memory
docker run --gpus='"device=1"' ...  # Use GPU 1 instead
```

## 📚 **Examples**

The `examples/` directory contains comprehensive examples:

- **01_basic_protein_folding.py** - Simple protein structure prediction
- **02_protein_structure_prediction_with_msa.py** - MSA-guided predictions with comparison
- **03_protein_ligand_complex.py** - Protein-ligand complexes
- **04_covalent_bonding.py** - Covalent bond constraints
- **05_dna_protein_complex.py** - DNA-protein interactions
- **06_yaml_configurations.py** - YAML config files
- **07_advanced_parameters.py** - Advanced API parameters
- **08_affinity_prediction.py** - Binding affinity prediction (IC50/pIC50)
- **15_a3m_to_multimer_csv.py** - A3M to multimer MSA conversion
- **16_colabfold_a3m_to_multimer.ipynb** - Interactive notebook for multimer MSA (NEW)
- **A3M_TO_MULTIMER_MSA.md** - Comprehensive guide for A3M conversion (NEW)

## 🧪 **Supported Prediction Types**

| Type | Description | CLI Command | Python Method |
|------|-------------|-------------|---------------|
| **Protein** | Single protein folding | `protein` | `predict_protein_structure()` |
| **Ligand Complex** | Protein-ligand binding | `ligand` | `predict_protein_ligand_complex()` |
| **Covalent Complex** | Covalent bonds | `covalent` | `predict_covalent_complex()` |
| **DNA-Protein** | Nucleic acid complexes | `dna-protein` | `predict_dna_protein_complex()` |
| **Advanced** | Custom parameters | `advanced` | `predict_with_advanced_parameters()` |
| **YAML** | Configuration files | `yaml` | `predict_from_yaml_config()` |

## 🔬 **Advanced Features**

### Batch Processing
```python
from boltz2_client import Boltz2Client
import asyncio

async def batch_predictions():
    client = Boltz2Client()
    sequences = ["SEQ1", "SEQ2", "SEQ3"]
    
    # Process multiple sequences concurrently
    tasks = [client.predict_protein_structure(seq) for seq in sequences]
    results = await asyncio.gather(*tasks)
    
    for i, result in enumerate(results):
        print(f"Sequence {i+1}: Confidence {result.confidence:.3f}")
```

### MSA-Guided Predictions
```python
# With MSA file
result = await client.predict_protein_structure(
    sequence="YOUR_SEQUENCE",
    msa_files=[("path/to/alignment.a3m", "a3m")]
)
```

### Custom Parameters
```python
result = await client.predict_with_advanced_parameters(
    polymers=[{"id": "A", "sequence": "SEQUENCE"}],
    recycling_steps=3,
    sampling_steps=200,
    diffusion_samples=1
)
```

### 🆕 Affinity Prediction
Predict binding affinity (IC50/pIC50) for protein-ligand complexes:

```python
from boltz2_client import Boltz2Client, Polymer, Ligand, PredictionRequest

# Create protein and ligand
protein = Polymer(id="A", molecule_type="protein", sequence="YOUR_SEQUENCE")
ligand = Ligand(id="LIG", smiles="CC(=O)OC1=CC=CC=C1C(=O)O", predict_affinity=True)

# Create request with affinity parameters
request = PredictionRequest(
    polymers=[protein],
    ligands=[ligand],
    sampling_steps_affinity=200,  # Default: 200
    diffusion_samples_affinity=5,  # Default: 5
    affinity_mw_correction=False   # Default: False
)

# Predict structure and affinity
result = await client.predict(request)

# Access affinity results
if result.affinities and "LIG" in result.affinities:
    affinity = result.affinities["LIG"]
    print(f"pIC50: {affinity.affinity_pic50[0]:.3f}")
    print(f"Binding probability: {affinity.affinity_probability_binary[0]:.3f}")
```

#### 🧬 MSA-Guided Affinity Prediction
Combine MSA search with affinity prediction for improved accuracy:

```python
# Configure MSA Search
client.configure_msa_search("http://your-msa-nim:8000")

# Predict with MSA + affinity in one call
result = await client.predict_ligand_with_msa_search(
    protein_sequence="YOUR_SEQUENCE",
    ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
    predict_affinity=True,
    databases=["Uniref30_2302", "PDB70_220313"],
    max_msa_sequences=1000,
    sampling_steps_affinity=300
)

# Or use existing MSA file
result = await client.predict_protein_ligand_complex(
    protein_sequence="YOUR_SEQUENCE",
    ligand_smiles="LIGAND_SMILES",
    msa_files=[("alignment.a3m", "a3m")],
    predict_affinity=True
)
```

#### CLI Usage
```bash
# Basic affinity prediction
boltz2 ligand "PROTEIN_SEQUENCE" --smiles "LIGAND_SMILES" --predict-affinity

# With custom parameters
boltz2 ligand "PROTEIN_SEQUENCE" --ccd Y7W \
    --predict-affinity \
    --sampling-steps-affinity 100 \
    --diffusion-samples-affinity 3 \
    --affinity-mw-correction
```

**Note:** Only ONE ligand per request can have affinity prediction enabled.

## 🛠 **Development**

### Setup Development Environment
```bash
git clone https://github.com/NVIDIA/digital-biology-examples.git
cd digital-biology-examples/examples/nims/boltz-2
pip install -e ".[dev]"
```

### Run Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black boltz2_client/
isort boltz2_client/
```

### Type Checking
```bash
mypy boltz2_client/
```

## 📋 **Requirements**

- **Python**: 3.8+
- **Dependencies**:
  - `httpx>=0.24.0` - HTTP client
  - `pydantic>=2.0.0` - Data validation
  - `rich>=13.0.0` - CLI formatting
  - `aiofiles>=23.0.0` - Async file operations
  - `click>=8.0.0` - CLI framework
  - `PyYAML>=6.0.0` - YAML support
  - `py3Dmol>=2.0.0` - 3D visualization

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Merge Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Third-party dependencies are licensed under their respective licenses - see the [licenses/](licenses/) directory for details.

## 📚 **Documentation**

### Guides
- **[MSA Search Guide](MSA_SEARCH_GUIDE.md)** - GPU-accelerated MSA generation with NVIDIA MSA Search NIM
- **[A3M to Multimer MSA Guide](examples/A3M_TO_MULTIMER_MSA.md)** - Convert ColabFold A3M files to paired multimer format (NEW)
- **[Affinity Prediction Guide](AFFINITY_PREDICTION_GUIDE.md)** - Comprehensive guide for binding affinity prediction
- **[YAML Configuration Guide](YAML_GUIDE.md)** - Working with YAML configuration files
- **[Async Programming Guide](ASYNC_GUIDE.md)** - Best practices for async operations
- **[Covalent Complex Guide](COVALENT_COMPLEX_GUIDE.md)** - Predicting covalent bonds
- **[Multi-Endpoint Guide](MULTI_ENDPOINT_GUIDE.md)** - Load balancing across multiple NIMs
- **[Parameters Guide](PARAMETERS.md)** - Detailed parameter documentation

## 🔗 **Links**

- **TestPyPI**: https://test.pypi.org/project/boltz2-python-client/
- **NVIDIA BioNeMo**: https://www.nvidia.com/en-us/clara/bionemo/
- **Boltz-2 Paper**: [Link to Boltz-2 paper](https://cdn.prod.website-files.com/68404fd075dba49e58331ad9/6842ee1285b9af247ac5a122_boltz2.pdf)


## 🏆 **Acknowledgments**

- NVIDIA BioNeMo Team for the Boltz-2 service
- Contributors and testers
- Open source community

---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.

---

**Made with ❤️ for the computational biology community** 