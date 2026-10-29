# OpenShift AI Deployment

Deploy vLLM with watermarking and the detection server on OpenShift AI.

These manifests were tested on OpenShift 4.20 with RHOAI 3.5 and vLLM v0.32.0 on an NVIDIA A10G GPU.

## Quick start

```bash
# Create a project
oc new-project watermark-test

# Deploy the vLLM server with watermarking (requires a GPU node)
oc apply -f vllm-watermark-deployment.yaml

# Wait for the server to be ready (~3-5 min for image pull + model download)
oc wait --for=condition=available deployment/vllm-watermark --timeout=600s

# Deploy the detection server (CPU only, no GPU)
oc apply -f watermark-detector-deployment.yaml
oc wait --for=condition=available deployment/watermark-detector --timeout=300s
```

## Test end-to-end

```bash
# Generate watermarked text
TEXT=$(oc exec deployment/vllm-watermark -- curl -s http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-0.5B-Instruct","prompt":"Write a short story about a lighthouse keeper.","max_tokens":200,"temperature":1.0}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['text'])")

# Detect watermark
oc exec deployment/watermark-detector -- curl -s http://localhost:8001/detect \
  -H "Content-Type: application/json" \
  -d "{\"text\": $(echo "$TEXT" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")}"
```

## OpenShift-specific notes

### Writable cache directories

The upstream `vllm/vllm-openai` image expects a writable home directory. Under OpenShift's restricted SCC the container runs as a random UID that cannot write to `/`. The manifests set `HOME`, `HF_HOME`, `XDG_CACHE_HOME`, `FLASHINFER_WORKSPACE_DIR`, and `TRITON_CACHE_DIR` to subdirectories under `/tmp`, backed by an `emptyDir` volume. **Without these env vars, the container will crash with `PermissionError: [Errno 13] Permission denied: '/.cache'`.**

### Shared memory

vLLM uses `/dev/shm` for inter-process communication. The manifests mount a `Memory`-backed `emptyDir` at `/dev/shm` with a 4Gi limit.

### GPU scheduling

The vLLM deployment uses `nodeSelector: nvidia.com/gpu.present: "true"` to land on GPU nodes. Ensure the NVIDIA GPU Operator and Node Feature Discovery (NFD) are installed.

## Customization

- Replace `Qwen/Qwen2.5-0.5B-Instruct` with your model in **both** deployments
- Replace the key (`98765`) with your secret key — **must be the same in both**
- For production, store the key in an OpenShift Secret and reference via `env.valueFrom.secretKeyRef`
- Adjust `--max-model-len` based on your GPU memory and model size

## Cleanup

```bash
oc delete project watermark-test
```
