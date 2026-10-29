# AI Text Watermarking with vLLM

Minimal recipes for text watermarking in vLLM, verified on `vllm/vllm-openai:v0.32.0`.

## Contents

| Path | What it shows |
|------|---------------|
| [`recipes/01_watermarked_generation`](recipes/01_watermarked_generation/RECIPE_watermarked_generation.md) | Watermarked generation with `gumbel`, and turning it off per request. |
| [`recipes/02_spec_decode_generation`](recipes/02_spec_decode_generation/RECIPE_spec_decode.md) | Watermarked generation under speculative decoding with `dual_key_gumbel`. |
| [`recipes/03_detection`](recipes/03_detection/RECIPE_detection.md) | Detecting the outputs of recipes 1 and 2 with a small detection server. |
| [`recipes/04_structured_data`](recipes/04_structured_data/RECIPE_structured_data.md) | Why templated JSON is harder to detect, and what to tune. |
| [`openshift/`](openshift/) | OpenShift AI deployment manifests for vLLM server and detection service. |

Each recipe folder has one or two short scripts and a `RECIPE_*.md` with the exact commands.

## Setup

### Option A: Deploy on OpenShift AI (recommended)

See [`openshift/`](openshift/) for ready-to-apply manifests. The container image is `vllm/vllm-openai:v0.32.0`. Quick start:

```bash
oc new-project watermark-test
oc apply -f openshift/vllm-watermark-deployment.yaml
oc apply -f openshift/watermark-detector-deployment.yaml
```

### Option B: Local development with venv

You need Linux with one CUDA GPU, [uv](https://docs.astral.sh/uv/), and `jq` and `curl` for recipe 3.

```bash
./setup.sh
```

This creates `.venv/` with vLLM 0.32.0.

The recipes use `Qwen/Qwen2.5-0.5B-Instruct`. Substitute any model supported by vLLM v0.32.0.

## Running the recipes

Run each recipe from its own folder with the commands in its `RECIPE_*.md`. They activate `.venv/` and run on one GPU.

Run recipes 1 and 2 before recipe 3, which detects their output files.

The detection servers in recipe 3 are minimal examples, not production endpoints. A public detection endpoint lets callers remove or forge the watermark without knowing the key, so keep detection behind access control.

## Quick-start on OpenShift AI

```bash
# 1. Deploy vLLM with watermarking and the detector
oc new-project watermark-test
oc apply -f openshift/vllm-watermark-deployment.yaml
oc apply -f openshift/watermark-detector-deployment.yaml
oc wait --for=condition=available deployment/vllm-watermark --timeout=600s
oc wait --for=condition=available deployment/watermark-detector --timeout=300s

# 2. Generate watermarked text
oc exec deployment/vllm-watermark -- curl -s http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-0.5B-Instruct","prompt":"Explain how AI watermarking works.","max_tokens":200,"temperature":0.7}'

# 3. Detect the watermark (send generated text to the detector)
oc exec deployment/watermark-detector -- curl -s http://localhost:8001/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "<paste generated text here>"}'
```

## Configuration reference

### Watermark config fields (`--watermark-config`)

| Field | Default | Description |
|-------|---------|-------------|
| `key` | *(required)* | Secret integer. Keep it private. |
| `algorithm` | `"gumbel"` | `"gumbel"` for standard generation. `"dual_key_gumbel"` for speculative decoding. |
| `context_width` | `4` | Number of preceding tokens used to seed each watermark decision. |
| `deduplicate_contexts` | `"single_turn"` | `"none"`, `"single_turn"`, or `"all"`. |

### Five things must match between generation and detection

1. **Tokenizer** — same model's tokenizer
2. **Key** — same secret integer
3. **Algorithm** — `gumbel` or `dual_key_gumbel`
4. **Context width** — same value (default 4)
5. **PRF** — same pseudorandom function (default `philox`)

## Important notes

- **Temperature must be > 0.** Greedy decoding (`temperature=0`) cannot be watermarked.
- **Short outputs carry a weaker signal.** Longer outputs give more confident detection.
- **Protect detector access.** Do not expose detection scores externally. Scores can help an adversary remove or forge the watermark.
- **Per-request opt-out must be controlled.** Requests can disable the watermark with `"watermarking": false`. Strip this field at the gateway for untrusted callers.
- **Several keys? Tighten the threshold.** Use `0.01/k` for k keys (Bonferroni correction).

## Reference links

- [vLLM watermarking documentation](https://docs.vllm.ai/en/latest/features/watermarking/)
- [Watermark detection server (upstream)](https://github.com/vllm-project/vllm/blob/main/examples/basic/online_serving/watermark_detection_server.py)
- [Gumbel-max implementation](https://github.com/vllm-project/vllm/blob/main/vllm/v1/watermarking/gumbel.py)
- [RFC #53916](https://github.com/vllm-project/vllm/issues/53916)
- [PR #54053 — Core watermarking](https://github.com/vllm-project/vllm/pull/54053)
- [PR #56122 — Dual-key + speculative decoding](https://github.com/vllm-project/vllm/pull/56122)

## Verified on

- **vLLM:** `vllm/vllm-openai:v0.32.0`
- **Model:** `Qwen/Qwen2.5-0.5B-Instruct`
- **GPU:** NVIDIA A10G (24 GB)
- **Result:** Watermarked text detected at p = 2.8e-18; unwatermarked text correctly not flagged (p = 0.903)
