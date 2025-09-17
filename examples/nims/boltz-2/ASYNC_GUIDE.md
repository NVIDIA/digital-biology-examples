# Async Programming Guide for Boltz-2 Python Client

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

This guide demonstrates how to efficiently perform asynchronous protein structure predictions using the Boltz-2 Python client. Async programming allows you to process multiple protein sequences concurrently, dramatically improving throughput for batch operations.

## Table of Contents

1. [Basic Async Concepts](#basic-async-concepts)
2. [Simple Async Example](#simple-async-example)
3. [Batch Processing with Rate Limiting](#batch-processing-with-rate-limiting)
4. [Advanced Patterns](#advanced-patterns)
5. [Performance Optimization](#performance-optimization)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)

## Basic Async Concepts

### Why Use Async?

- **Concurrency**: Process multiple proteins simultaneously
- **Efficiency**: Better resource utilization during I/O operations
- **Scalability**: Handle large batches without blocking
- **Throughput**: Significantly faster than sequential processing

### Key Components

```python
import asyncio
from boltz2_client import Boltz2Client, EndpointType

# Create async client
client = Boltz2Client(
    base_url="http://localhost:8000",
    endpoint_type=EndpointType.LOCAL
)

# Async function
async def fold_protein(sequence: str):
    response = await client.predict_protein_structure(
        sequence=sequence,
        recycling_steps=1,
        sampling_steps=20,
        save_structures=False
    )
    return response

# Run async function
result = asyncio.run(fold_protein("MKTVRQERLK..."))
```

## Simple Async Example

### Single Protein (Async)

```python
import asyncio
from boltz2_client import Boltz2Client

async def predict_single():
    client = Boltz2Client("http://localhost:8000")
    
    response = await client.predict_protein_structure(
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        recycling_steps=3,
        sampling_steps=50
    )
    
    print(f"Confidence: {response.confidence_scores[0]:.3f}")
    return response

# Run it
result = asyncio.run(predict_single())
```

### Multiple Proteins (Concurrent)

```python
import asyncio
from boltz2_client import Boltz2Client

async def predict_multiple():
    client = Boltz2Client("http://localhost:8000")
    
    sequences = [
        "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        "MKLLVVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLV",
        "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"
    ]
    
    # Create tasks for concurrent execution
    tasks = [
        client.predict_protein_structure(
            sequence=seq,
            recycling_steps=1,
            sampling_steps=20,
            save_structures=False
        )
        for seq in sequences
    ]
    
    # Wait for all to complete
    results = await asyncio.gather(*tasks)
    
    for i, result in enumerate(results):
        confidence = result.confidence_scores[0] if result.confidence_scores else 0
        print(f"Protein {i+1}: confidence={confidence:.3f}")
    
    return results

# Run it
results = asyncio.run(predict_multiple())
```

## Batch Processing with Rate Limiting

### Using Semaphore for Rate Limiting

```python
import asyncio
from boltz2_client import Boltz2Client

class RateLimitedFolder:
    def __init__(self, max_concurrent=5):
        self.client = Boltz2Client("http://localhost:8000")
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fold_with_limit(self, sequence: str, protein_id: str):
        async with self.semaphore:  # Rate limiting
            try:
                response = await self.client.predict_protein_structure(
                    sequence=sequence,
                    recycling_steps=1,
                    sampling_steps=20,
                    save_structures=False
                )
                confidence = response.confidence_scores[0] if response.confidence_scores else 0
                print(f"✅ {protein_id}: confidence={confidence:.3f}")
                return {"id": protein_id, "success": True, "confidence": confidence}
            except Exception as e:
                print(f"❌ {protein_id}: {e}")
                return {"id": protein_id, "success": False, "error": str(e)}

async def batch_fold():
    folder = RateLimitedFolder(max_concurrent=3)
    
    # Your protein sequences
    proteins = [
        ("protein_1", "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"),
        ("protein_2", "MKLLVVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLVLV"),
        # ... more proteins
    ]
    
    tasks = [
        folder.fold_with_limit(sequence, protein_id)
        for protein_id, sequence in proteins
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# Run batch folding
results = asyncio.run(batch_fold())
```

## Advanced Patterns

### Progress Tracking with asyncio.as_completed

```python
import asyncio
import time
from boltz2_client import Boltz2Client

async def fold_with_progress(sequences):
    client = Boltz2Client("http://localhost:8000")
    
    # Create tasks
    tasks = [
        client.predict_protein_structure(
            sequence=seq,
            recycling_steps=1,
            sampling_steps=20,
            save_structures=False
        )
        for seq in sequences
    ]
    
    results = []
    completed = 0
    total = len(tasks)
    
    # Process as they complete
    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            confidence = result.confidence_scores[0] if result.confidence_scores else 0
            results.append(result)
            completed += 1
            
            print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%) - Latest confidence: {confidence:.3f}")
            
        except Exception as e:
            print(f"Error: {e}")
            completed += 1
    
    return results
```

### Retry Logic with Exponential Backoff

```python
import asyncio
import random
from boltz2_client import Boltz2Client

async def fold_with_retry(client, sequence, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await client.predict_protein_structure(
                sequence=sequence,
                recycling_steps=1,
                sampling_steps=20,
                save_structures=False
            )
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                delay = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
                print(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                await asyncio.sleep(delay)
            else:
                print(f"All {max_retries} attempts failed: {e}")
                raise
```

### Chunked Processing for Large Batches

```python
import asyncio
from boltz2_client import Boltz2Client

async def process_in_chunks(sequences, chunk_size=10):
    client = Boltz2Client("http://localhost:8000")
    all_results = []
    
    # Process sequences in chunks
    for i in range(0, len(sequences), chunk_size):
        chunk = sequences[i:i + chunk_size]
        print(f"Processing chunk {i//chunk_size + 1}/{(len(sequences)-1)//chunk_size + 1}")
        
        # Process chunk concurrently
        tasks = [
            client.predict_protein_structure(
                sequence=seq,
                recycling_steps=1,
                sampling_steps=20,
                save_structures=False
            )
            for seq in chunk
        ]
        
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        all_results.extend(chunk_results)
        
        # Brief pause between chunks
        await asyncio.sleep(1)
    
    return all_results
```

## Performance Optimization

### Multi-Endpoint for Maximum Throughput

For the highest throughput, use multiple Boltz-2 endpoints with load balancing:

```python
from boltz2_client import MultiEndpointClient, LoadBalanceStrategy

# Configure multiple endpoints
multi_client = MultiEndpointClient(
    endpoints=[
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",
    ],
    strategy=LoadBalanceStrategy.LEAST_LOADED,
    is_async=True
)

# Use with async batch processing
async def multi_endpoint_batch(sequences):
    tasks = []
    for seq in sequences:
        request = PredictionRequest(
            polymers=[Polymer(id="A", molecule_type="protein", sequence=seq)],
            recycling_steps=1,
            sampling_steps=20
        )
        tasks.append(multi_client.predict(request))
    
    results = await asyncio.gather(*tasks)
    return results
```

See [MULTI_ENDPOINT_GUIDE.md](MULTI_ENDPOINT_GUIDE.md) for detailed setup instructions.

### Optimal Concurrency Settings

```python
# Local endpoint - adjust based on GPU memory
MAX_CONCURRENT_LOCAL = 3-5

# NVIDIA hosted endpoint - respect rate limits
MAX_CONCURRENT_HOSTED = 10-20

# Fast settings for batch processing
FAST_SETTINGS = {
    "recycling_steps": 1,
    "sampling_steps": 20,
    "save_structures": False
}

# High-quality settings for important predictions
QUALITY_SETTINGS = {
    "recycling_steps": 3,
    "sampling_steps": 50,
    "save_structures": True
}
```

### Memory Management

```python
import asyncio
import gc
from boltz2_client import Boltz2Client

async def memory_efficient_batch(sequences, batch_size=50):
    client = Boltz2Client("http://localhost:8000")
    
    for i in range(0, len(sequences), batch_size):
        batch = sequences[i:i + batch_size]
        
        # Process batch
        results = await asyncio.gather(*[
            client.predict_protein_structure(
                sequence=seq,
                recycling_steps=1,
                sampling_steps=20,
                save_structures=False
            )
            for seq in batch
        ])
        
        # Process results immediately
        for result in results:
            # Save or process result
            pass
        
        # Clean up memory
        del results
        gc.collect()
        
        print(f"Completed batch {i//batch_size + 1}")
```

## Error Handling

### Comprehensive Error Handling

```python
import asyncio
from boltz2_client import Boltz2Client
from boltz2_client.exceptions import (
    Boltz2APIError,
    Boltz2TimeoutError,
    Boltz2ConnectionError,
    Boltz2ValidationError
)

async def robust_fold(client, sequence, protein_id):
    try:
        response = await client.predict_protein_structure(
            sequence=sequence,
            recycling_steps=1,
            sampling_steps=20,
            save_structures=False
        )
        return {"id": protein_id, "success": True, "result": response}
        
    except Boltz2ValidationError as e:
        return {"id": protein_id, "success": False, "error": "validation", "message": str(e)}
    except Boltz2TimeoutError as e:
        return {"id": protein_id, "success": False, "error": "timeout", "message": str(e)}
    except Boltz2ConnectionError as e:
        return {"id": protein_id, "success": False, "error": "connection", "message": str(e)}
    except Boltz2APIError as e:
        return {"id": protein_id, "success": False, "error": "api", "message": str(e)}
    except Exception as e:
        return {"id": protein_id, "success": False, "error": "unknown", "message": str(e)}
```

## Best Practices

### 1. Choose Appropriate Concurrency

```python
# Local endpoint: Limited by GPU memory
local_concurrent = 3-5

# NVIDIA hosted: Limited by rate limits
hosted_concurrent = 10-20

# Start conservative and increase gradually
```

### 2. Use Fast Settings for Batch Processing

```python
# For batch processing, use minimal settings
batch_settings = {
    "recycling_steps": 1,
    "sampling_steps": 20,
    "save_structures": False
}

# For important predictions, use quality settings
quality_settings = {
    "recycling_steps": 3,
    "sampling_steps": 50,
    "save_structures": True
}
```

### 3. Implement Proper Error Handling

```python
# Always handle exceptions gracefully
# Use retry logic for transient errors
# Log errors for debugging
# Continue processing other sequences on individual failures
```

### 4. Monitor Resource Usage

```python
import psutil
import time

async def monitor_resources():
    while True:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        print(f"CPU: {cpu}%, Memory: {memory}%")
        await asyncio.sleep(10)

# Run monitoring in background
asyncio.create_task(monitor_resources())
```

### 5. Save Results Incrementally

```python
import json
from datetime import datetime

async def save_results_incrementally(results, filename=None):
    if not filename:
        filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {filename}")
```


## Troubleshooting

### Common Issues

1. **Too many concurrent requests**: Reduce `max_concurrent`
2. **Memory issues**: Use chunked processing
3. **Timeout errors**: Increase timeout or reduce complexity
4. **Rate limiting**: Add delays between requests
5. **Connection errors**: Implement retry logic

### Debugging Tips

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Add timing information
import time
start = time.time()
# ... your async code ...
print(f"Total time: {time.time() - start:.2f}s")
```

This guide provides a comprehensive foundation for async protein folding with the Boltz-2 Python client. Start with the simple examples and gradually implement more advanced patterns as needed.
---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
