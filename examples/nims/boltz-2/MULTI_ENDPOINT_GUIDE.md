# Multi-Endpoint Virtual Screening Guide

This guide explains how to use multiple Boltz-2 NIM endpoints for parallelized virtual screening with the boltz2-python-client.

## Overview

The `MultiEndpointClient` allows you to distribute prediction requests across multiple Boltz-2 NIM endpoints, enabling:

- **True parallelization**: Utilize multiple GPU servers simultaneously
- **Load balancing**: Distribute work evenly across endpoints
- **Fault tolerance**: Automatic failover if an endpoint becomes unavailable
- **Better throughput**: Scale linearly with the number of endpoints

## 🚀 **Complete Multi-Endpoint Support**

The `MultiEndpointClient` now supports **ALL** Boltz2 NIM functionalities with load balancing:

### **✅ Core Structure Prediction**
- `predict_protein_structure()` - Protein structure prediction
- `predict_protein_ligand_complex()` - Protein-ligand complex prediction  
- `predict_covalent_complex()` - Covalent complex prediction
- `predict_dna_protein_complex()` - DNA-protein complex prediction
- `predict_with_advanced_parameters()` - Advanced parameter prediction
- `predict_from_yaml_config()` - YAML-based prediction
- `predict_from_yaml_file()` - File-based YAML prediction

### **✅ Virtual Screening**
- `VirtualScreening` class with multi-endpoint support
- Compound library management
- High-throughput screening across multiple endpoints

### **✅ Utility Functions**
- `health_check()` - Multi-endpoint health monitoring
- `get_service_metadata()` - Service information from healthy endpoints

### **✅ Load Balancing Strategies**
- Round Robin, Random, Least Loaded, and Weighted distribution
- Automatic failover and health checking
- Support for both sync and async operations

## Key Features

### Load Balancing Strategies

1. **Round Robin** (`LoadBalanceStrategy.ROUND_ROBIN`)
   - Distributes requests evenly in circular order
   - Best for endpoints with similar performance

2. **Random** (`LoadBalanceStrategy.RANDOM`)
   - Randomly selects an endpoint for each request
   - Good for simple load distribution

3. **Least Loaded** (`LoadBalanceStrategy.LEAST_LOADED`)
   - Routes requests to the endpoint with fewest active requests
   - Optimal for maximizing throughput

4. **Weighted** (`LoadBalanceStrategy.WEIGHTED`)
   - Distributes based on assigned weights
   - Useful when endpoints have different capabilities

### Health Checking

- Automatic periodic health checks
- Unhealthy endpoints are temporarily excluded
- Automatic recovery when endpoints come back online

## Quick Start

### Basic Setup

```python
from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
    VirtualScreening
)

# Configure multiple endpoints
endpoints = [
    # Simple URL strings
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",
    
    # Or use EndpointConfig for more control
    EndpointConfig(
        base_url="http://gpu-server-1:8000",
        weight=2.0  # This server gets 2x more requests
    ),
]

# Create multi-endpoint client
multi_client = MultiEndpointClient(
    endpoints=endpoints,
    strategy=LoadBalanceStrategy.LEAST_LOADED,
    health_check_interval=30.0,  # Check health every 30 seconds
)

# Use with virtual screening
vs = VirtualScreening(client=multi_client)
```

### Running Multiple Local NIM Instances

To run multiple Boltz-2 NIM instances on different ports:

```bash
# Terminal 1 - First instance on port 8000
docker run --rm --gpus device=0 -p 8000:8000 \
  nvcr.io/nim/mit/boltz-2:latest

# Terminal 2 - Second instance on port 8001  
docker run --rm --gpus device=1 -p 8001:8000 \
  nvcr.io/nim/mit/boltz-2:latest

# Terminal 3 - Third instance on port 8002
docker run --rm --gpus device=2 -p 8002:8000 \
  nvcr.io/nim/mit/boltz-2:latest
```

## 🧬 **Complete Functionality Examples**

### **1. Multi-Endpoint Protein Structure Prediction**

```python
import asyncio
from boltz2_client import MultiEndpointClient, LoadBalanceStrategy

async def predict_protein_multi_endpoint():
    # Setup multi-endpoint client
    multi_client = MultiEndpointClient(
        endpoints=[
            "http://localhost:8000",
            "http://localhost:8001",
            "http://localhost:8002",
        ],
        strategy=LoadBalanceStrategy.LEAST_LOADED,
        is_async=True
    )
    
    # Predict protein structure with load balancing
    result = await multi_client.predict_protein_structure(
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        recycling_steps=3,
        sampling_steps=50,
        diffusion_samples=1
    )
    
    print(f"Generated {len(result.structures)} structures")
    await multi_client.close()

# Run
asyncio.run(predict_protein_multi_endpoint())
```

### **2. Multi-Endpoint Protein-Ligand Complex Prediction**

```python
async def predict_protein_ligand_multi_endpoint():
    multi_client = MultiEndpointClient(
        endpoints=["http://localhost:8000", "http://localhost:8001"],
        strategy=LoadBalanceStrategy.ROUND_ROBIN,
        is_async=True
    )
    
    # Predict protein-ligand complex with affinity
    result = await multi_client.predict_protein_ligand_complex(
        protein_sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        smiles="CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
        predict_affinity=True,
        sampling_steps_affinity=200,
        diffusion_samples_affinity=5,
        pocket_residues=[10, 11, 12, 13, 14],
        pocket_radius=8.0
    )
    
    print(f"Complex prediction completed with {len(result.structures)} structures")
    await multi_client.close()
```

### **3. Multi-Endpoint Covalent Complex Prediction**

```python
async def predict_covalent_multi_endpoint():
    multi_client = MultiEndpointClient(
        endpoints=["http://localhost:8000", "http://localhost:8001"],
        strategy=LoadBalanceStrategy.WEIGHTED,
        is_async=True
    )
    
    # Predict covalent complex
    result = await multi_client.predict_covalent_complex(
        protein_sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        ccd="ASP",  # Aspirin CCD code
        predict_affinity=True,
        pocket_residues=[10, 11, 12, 13, 14],
        pocket_radius=8.0
    )
    
    print(f"Covalent complex prediction completed")
    await multi_client.close()
```

### **4. Multi-Endpoint DNA-Protein Complex Prediction**

```python
async def predict_dna_protein_multi_endpoint():
    multi_client = MultiEndpointClient(
        endpoints=["http://localhost:8000", "http://localhost:8001"],
        strategy=LoadBalanceStrategy.LEAST_LOADED,
        is_async=True
    )
    
    # Predict DNA-protein complex
    result = await multi_client.predict_dna_protein_complex(
        protein_sequences=["MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"],
        dna_sequences=["ATCGATCGATCGATCG"],
        protein_ids=["A"],
        dna_ids=["D"]
    )
    
    print(f"DNA-protein complex prediction completed")
    await multi_client.close()
```

### **5. Multi-Endpoint YAML-Based Prediction**

```python
async def predict_yaml_multi_endpoint():
    multi_client = MultiEndpointClient(
        endpoints=["http://localhost:8000", "http://localhost:8001"],
        strategy=LoadBalanceStrategy.RANDOM,
        is_async=True
    )
    
    # YAML config for prediction
    config = {
        "polymers": [
            {
                "id": "A",
                "molecule_type": "protein",
                "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            }
        ],
        "recycling_steps": 3,
        "sampling_steps": 50,
        "diffusion_samples": 1
    }
    
    # Predict from YAML config
    result = await multi_client.predict_from_yaml_config(config=config)
    
    print(f"YAML-based prediction completed")
    await multi_client.close()
```

### **6. Multi-Endpoint Virtual Screening**

```python
import asyncio
from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    VirtualScreening,
    CompoundLibrary
)

async def run_screening():
    # Setup multi-endpoint client
    multi_client = MultiEndpointClient(
        endpoints=[
            "http://localhost:8000",
            "http://localhost:8001",
            "http://localhost:8002",
        ],
        strategy=LoadBalanceStrategy.LEAST_LOADED,
        is_async=True
    )
    
    # Create screening instance
    vs = VirtualScreening(client=multi_client)
    
    # Define compounds
    compounds = [
        {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
        {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
        # ... more compounds
    ]
    
    # Run screening
    result = await vs.screen(
        target_sequence="YOUR_PROTEIN_SEQUENCE",
        compound_library=compounds,
        predict_affinity=True,
        recycling_steps=2,
        sampling_steps=30,
    )
    
    # Print endpoint statistics
    multi_client.print_status()
    
    # Clean up
    await multi_client.close()

# Run
asyncio.run(run_screening())
```

### **7. Multi-Endpoint Health Monitoring**

```python
async def monitor_health():
    multi_client = MultiEndpointClient(
        endpoints=["http://localhost:8000", "http://localhost:8001"],
        is_async=True
    )
    
    # Check overall health
    health_status = await multi_client.health_check()
    print(f"Overall Status: {health_status.status}")
    print(f"Details: {health_status.details}")
    
    # Get detailed status
    status = multi_client.get_status()
    print(f"Strategy: {status['strategy']}")
    
    # Print pretty status table
    multi_client.print_status()
    
    await multi_client.close()
```

## Advanced Configuration

### Mixed Endpoint Types

You can combine local and cloud endpoints:

```python
endpoints = [
    # Local GPU servers
    EndpointConfig(
        base_url="http://gpu-1:8000",
        weight=2.0,
        max_concurrent_requests=10
    ),
    
    # NVIDIA hosted endpoint as backup
    EndpointConfig(
        base_url="https://health.api.nvidia.com",
        api_key="your_api_key",
        endpoint_type="nvidia_hosted",
        weight=0.5  # Use less frequently
    ),
]
```

### Custom Health Check Settings

```python
multi_client = MultiEndpointClient(
    endpoints=endpoints,
    health_check_interval=60.0,  # Check every minute
    timeout=300.0,  # 5 minute timeout for predictions
    max_retries=3,  # Retry failed requests up to 3 times
)
```

### Monitoring Performance

```python
# Get detailed status
status = multi_client.get_status()
print(f"Strategy: {status['strategy']}")
for endpoint in status['endpoints']:
    print(f"  {endpoint['url']}: {endpoint['total_requests']} requests, "
          f"avg {endpoint['avg_response_time']}s")

# Or use the built-in pretty printer
multi_client.print_status()
```

## Performance Tips

1. **Use Least Loaded Strategy**: Generally provides best throughput
2. **Set Appropriate Weights**: Assign higher weights to more powerful servers
3. **Monitor Health**: Adjust health check intervals based on your needs
4. **Batch Size**: Consider using smaller batch sizes to distribute work better

## Deployment Patterns

### Single Machine, Multiple GPUs

```python
# Run one NIM instance per GPU
endpoints = [
    f"http://localhost:800{i}" for i in range(num_gpus)
]
```

### Multiple Machines

```python
# Distribute across multiple servers
endpoints = [
    "http://gpu-server-1:8000",
    "http://gpu-server-2:8000",
    "http://gpu-server-3:8000",
]
```

### Hybrid Cloud

```python
# Mix on-premise and cloud resources
endpoints = [
    # On-premise GPUs for primary workload
    *[f"http://local-gpu-{i}:8000" for i in range(4)],
    
    # Cloud endpoints for burst capacity
    EndpointConfig(
        base_url="https://cloud-endpoint.com",
        api_key="api_key",
        weight=0.5  # Use less frequently due to cost
    ),
]
```

## Troubleshooting

### All Endpoints Failing

If all endpoints fail, the client will raise a `Boltz2APIError`. Check:

1. Endpoints are running and accessible
2. Network connectivity
3. GPU memory availability
4. Docker container status

### Uneven Load Distribution

If load is not distributed evenly:

1. Check endpoint weights
2. Verify all endpoints are healthy
3. Consider using `LEAST_LOADED` strategy
4. Monitor `current_requests` in status

### Performance Issues

1. Increase number of endpoints
2. Use more powerful GPUs
3. Reduce model parameters (sampling steps, etc.)
4. Check network latency between client and endpoints

## Complete Example

See `examples/comprehensive_multi_endpoint_demo.py` for a complete working example demonstrating ALL Boltz2 NIM functionalities with multi-endpoint support.

## 🎯 **What This Enables**

- **High-Throughput Everything**: All Boltz2 NIM prediction types now scale across multiple GPUs
- **Resource Optimization**: Better utilization of available computational resources  
- **Production Ready**: Robust error handling and monitoring for enterprise use
- **Flexible Deployment**: Mix local, cloud, and hybrid resources seamlessly
- **True Parallelization**: Multiple prediction types can run simultaneously across endpoints

This implementation transforms the Boltz2 client into a **distributed, load-balanced, production-ready system** that can efficiently utilize multiple Boltz2 NIM endpoints for **ALL** available functionalities, not just virtual screening.
---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
