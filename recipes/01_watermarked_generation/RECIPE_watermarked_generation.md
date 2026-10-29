# Watermarked generation

This recipe turns on the Gumbel-max watermark in vLLM and generates one story with it and one without it. It writes the two stories to `watermarked.txt` and `unwatermarked.txt`, which recipe 3 then checks for the watermark.

## Run it

From this folder:

```bash
source ../../.venv/bin/activate
python generate.py
```

## Expected output

Both stories are 200 tokens and read like normal model output. The watermarked story is fixed by the key and the prompt: the watermark replaces the random draw, so changing `seed` does not change it. The unwatermarked story follows vLLM's default seed 0. Other GPU types or vLLM versions can change both.

You cannot tell the two apart by reading them. A detector with the same key can. Recipe 3 treats p ≤ 0.01 as watermarked and shows how to run the check.

## Configuration

The watermark is set once, when the engine starts:

```python
LLM("Qwen/Qwen2.5-0.5B-Instruct", watermark_config={"algorithm": "gumbel", "key": 42})
```

- `key` is the secret. Anyone with the key can detect the watermark, so keep it private.
- `algorithm` is `gumbel` by default. Use `dual_key_gumbel` with speculative decoding (recipe 2).
- `context_width` is how many previous tokens seed each watermark decision. The default is 4. Larger values make the watermark easier to break by editing the text.

The detector must use the same tokenizer, key, algorithm and `context_width`, or it will not find the watermark.

The server equivalent is:

```bash
vllm serve Qwen/Qwen2.5-0.5B-Instruct --watermark-config '{"algorithm":"gumbel","key":42}'
```

For OpenShift AI deployment, see the manifests in [`openshift/`](../../openshift/).

## Two ways to get unwatermarked text

Once the engine has a watermark config, every request is watermarked unless it opts out:

- `SamplingParams(watermarking=False)`, or `"watermarking": false` in an OpenAI-compatible request (with the `openai` Python client, pass `extra_body={"watermarking": False}`). If watermarking is mandatory for your deployment, strip this field from untrusted requests.
- Greedy decoding (`temperature=0`). The Gumbel-max watermark needs random sampling, so greedy requests skip it. vLLM logs a warning the first time this happens.
