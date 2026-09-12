# Copyright (c) 2025-2026 NVIDIA Corporation.
import asyncio
import os
from boltz2_client import MultiEndpointClient

async def main():
    endpoints = os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000").split(",")
    async with MultiEndpointClient(endpoints=endpoints, timeout=1200) as client:
        result = await client.predict_protein_structure(
            sequence='MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG', diffusion_samples=2, max_parallel_samples=1,
            output_dir="results/examples/multi",
        )
        print(result.confidence_scores)

asyncio.run(main())
