# Watermark detection

This recipe checks the text written by recipes 1 and 2 for a watermark. Detection needs only the tokenizer and the key, not the model, so the servers run on CPU and need no GPU.

There are two servers, one per generation algorithm:

- `watermark_detection_server.py` uses `GumbelWatermarkDetector` and matches recipe 1 (`"algorithm": "gumbel"`).
- `watermark_detection_server_spec_decode.py` uses `DualKeyGumbelWatermarkDetector` and a `--alpha` argument (default 0.5). It matches recipe 2 (`"algorithm": "dual_key_gumbel"` with speculative decoding).

`--alpha` is the weight the detector gives to key B, which vLLM uses for rejection-recovery and bonus tokens (draft tokens use key A). For templated output such as JSON the best `--alpha` depends on the key; recipe 4 shows how to choose it and why to check false positives.

## Run it

Run recipes 1 and 2 first so that their `watermarked.txt` and `unwatermarked.txt` files exist. The commands below need `jq`.

Normal generation (recipe 1). From this folder, start the server in one terminal:

```bash
source ../../.venv/bin/activate
python watermark_detection_server.py --tokenizer Qwen/Qwen2.5-0.5B-Instruct --key 42
```

From this folder, in a second terminal, send the files:

```bash
jq -Rs '{text: .}' ../01_watermarked_generation/watermarked.txt | curl -s localhost:8000/detect -H 'Content-Type: application/json' -d @-; echo
jq -Rs '{text: .}' ../01_watermarked_generation/unwatermarked.txt | curl -s localhost:8000/detect -H 'Content-Type: application/json' -d @-; echo
```

Speculative decoding (recipe 2). Stop the first server, start this one, and send the recipe 2 files the same way:

```bash
python watermark_detection_server_spec_decode.py --tokenizer Qwen/Qwen2.5-0.5B-Instruct --key 42
```

```bash
jq -Rs '{text: .}' ../02_spec_decode_generation/watermarked.txt | curl -s localhost:8000/detect -H 'Content-Type: application/json' -d @-; echo
jq -Rs '{text: .}' ../02_spec_decode_generation/unwatermarked.txt | curl -s localhost:8000/detect -H 'Content-Type: application/json' -d @-; echo
```

## Expected output

Watermarked text will have a very small p-value (e.g., p < 1e-10) and `is_watermarked: true`. Unwatermarked text will have a large p-value (e.g., p > 0.1) and `is_watermarked: false`. Your exact numbers will depend on the model output.

## Things to know

**The detector must match generation.** `--tokenizer` must be the generating model's tokenizer. The key, algorithm, `context_width` and PRF must match the `watermark_config` used to generate; set them with `--key`, the choice of server, `--context-width` and `--prf`. If one differs, watermarked text looks unwatermarked.

**Reading the p-value.** The p-value is the probability of a score this high in text without the watermark. `is_watermarked` is true when it is at or below `--p-value-threshold` (default 0.01). Long text with varied wording gives very small p-values. Short or predictable text, such as JSON or code, gives larger ones, because only tokens where the model had a real choice carry the signal.

**Several keys.** If you rotate keys or serve several tenants with different keys, run one server per key, each with `--p-value-threshold 0.01/k` for k keys (Bonferroni correction). For example, with 5 keys pass `--p-value-threshold 0.002` to each server.
