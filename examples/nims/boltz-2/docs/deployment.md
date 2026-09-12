# Local NIM 1.9.0 deployment

Check the current [support matrix](https://docs.nvidia.com/nim/bionemo/boltz2/latest/support-matrix.html)
and [NVIDIA startup guide](https://docs.nvidia.com/nim/bionemo/boltz2/latest/getting-started.html)
for your GPU and driver. Verify `nvidia-smi` works on the host and GPU passthrough
works with NVIDIA Container Toolkit before downloading models. CPU-only inference
is not supported by this deployment workflow.

The [startup script](../scripts/start_local_nim.sh) pins
`nvcr.io/nim/mit/boltz2:1.9.0`, uses the caller's UID/GID for private writable mounts,
binds port 8000 to localhost, and waits on `/v1/health/ready`. It will not replace
an existing container with the same name. Set `BOLTZ2_CONTAINER_NAME` and
`BOLTZ2_PORT` to run a separate instance. Use `docker logs <name>` for startup
progress; cold starts download model assets and take longer than warm starts.

Set the credential in the process environment without putting it in a script or
repository. `NGC_API_KEY` takes precedence over `NVIDIA_API_KEY`.

```bash
export LOCAL_NIM_CACHE="$HOME/.cache/nim/boltz2"
export LOCAL_NIM_OUTPUT="$HOME/boltz2-output"
bash scripts/start_local_nim.sh
curl --fail http://localhost:8000/v1/health/ready
boltz2 --base-url http://localhost:8000 health
```

NIM 1.9 uses a unified optimized backend; do not copy TensorRT backend switches
or older per-GPU profile hashes into the command. Mount model assets at
`/opt/nim/.cache` and prediction artifacts at `/opt/nim/output`. Full matrix
artifacts need the request flags as described in [outputs](outputs.md).

Stop the server when finished with `docker stop boltz2-nim-1-9`. Cache and output
files persist on the host. Inspect and remove the stopped container explicitly
before reusing its name.

## Existing SageMaker endpoint

Install `python -m pip install -e ".[sagemaker]"`, configure AWS credentials, and
set `SAGEMAKER_ENDPOINT_NAME` and `SAGEMAKER_REGION` for your existing endpoint.
This connection example replaces the standalone SageMaker notebook. It uses
the synchronous client so it can run as a Python script:

```python
import os
from boltz2_client import Boltz2SyncClient

client = Boltz2SyncClient(
    endpoint_type="sagemaker",
    sagemaker_endpoint_name=os.environ["SAGEMAKER_ENDPOINT_NAME"],
    sagemaker_region=os.environ["SAGEMAKER_REGION"],
    timeout=1200,
)
print(client.health_check().status)
result = client.predict_protein_structure(
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    output_dir="results/sagemaker",
)
print(result.confidence_scores)
```

In Jupyter, use `Boltz2Client` and await both calls. Supported NIM features depend
on the deployed Marketplace package; use its documentation for provisioning.
Full PAE/PDE files remain on the server and are not downloaded by this client.
SageMaker inference was not live-tested in this refresh.
