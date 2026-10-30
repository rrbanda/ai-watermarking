# Disconnected Environment Deployment

Deploy vLLM watermarking in a cluster with no outbound internet access.

Three things need to be pre-staged:

1. **Container image** — mirror `vllm/vllm-openai:v0.32.0` to your internal registry
2. **Model files** — copy model weights + tokenizer to a PVC
3. **Watermark key** — stored in an OpenShift Secret (same as connected)

## Step 1: Mirror the container image

On a machine with internet access:

```bash
# Pull from Docker Hub
podman pull vllm/vllm-openai:v0.32.0

# Tag for your internal registry
podman tag vllm/vllm-openai:v0.32.0 <REGISTRY>/vllm-openai:v0.32.0

# Push to your internal registry
podman push <REGISTRY>/vllm-openai:v0.32.0
```

Replace `<REGISTRY>` with your internal registry URL (e.g. `registry.example.com/ai`).

## Step 2: Download model files to a local machine

On a machine with internet access:

```bash
pip install huggingface_hub
python -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen2.5-0.5B-Instruct', local_dir='./Qwen2.5-0.5B-Instruct')
"
```

This downloads ~1 GB (model weights + tokenizer). Transfer the `Qwen2.5-0.5B-Instruct/` directory to a location accessible from the cluster.

## Step 3: Create the PVC and copy model files

```bash
oc new-project watermark-test

# Create the PVC
oc apply -f model-pvc.yaml

# Start a temporary pod to copy files into the PVC
oc run model-loader --image=registry.access.redhat.com/ubi9/ubi-minimal \
  --restart=Never \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "model-loader",
        "image": "registry.access.redhat.com/ubi9/ubi-minimal",
        "command": ["sleep", "3600"],
        "volumeMounts": [{"name": "model", "mountPath": "/mnt/models"}]
      }],
      "volumes": [{
        "name": "model",
        "persistentVolumeClaim": {"claimName": "watermark-model"}
      }]
    }
  }'

oc wait --for=condition=ready pod/model-loader --timeout=120s

# Copy the model files into the PVC
oc cp ./Qwen2.5-0.5B-Instruct model-loader:/mnt/models/Qwen2.5-0.5B-Instruct

# Verify
oc exec model-loader -- ls /mnt/models/Qwen2.5-0.5B-Instruct

# Clean up the loader pod
oc delete pod model-loader
```

## Step 4: Deploy

```bash
# Create the watermark key Secret
oc apply -f ../watermark-secret.yaml

# Deploy vLLM server (GPU) and detector (CPU)
oc apply -f vllm-watermark-disconnected.yaml
oc apply -f watermark-detector-disconnected.yaml

# Wait for readiness
oc wait --for=condition=available deployment/vllm-watermark --timeout=600s
oc wait --for=condition=available deployment/watermark-detector --timeout=300s
```

## Step 5: Test

```bash
# Generate watermarked text
oc exec deployment/vllm-watermark -- curl -s http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/mnt/models/Qwen2.5-0.5B-Instruct","prompt":"Write a short story about a lighthouse keeper.","max_tokens":200,"temperature":0.7}'

# Detect watermark
oc exec deployment/watermark-detector -- curl -s http://localhost:8001/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "<paste generated text here>"}'
```

Note: In disconnected mode the model name in API requests is the **local path** (`/mnt/models/Qwen2.5-0.5B-Instruct`), not the Hugging Face name.

## Alternative: OCI model image

Instead of `oc cp`, you can package the model as an OCI image and use an init container to load it. See the [Red Hat AI Inference disconnected deployment guide](https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.4/html/deploy_the_standalone_red_hat_ai_inference_container_in_a_disconnected_environment/) for that pattern.
