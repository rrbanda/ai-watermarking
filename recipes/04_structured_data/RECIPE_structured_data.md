# Structured data

This recipe shows how well watermarked JSON is detected with and without speculative decoding, and why to check false positives on your own template.

`detect_json.py` builds 32 few-shot prompts, each holding 15 JSON sensor records and asking for 20 more. It sends each prompt 4 times watermarked and 4 times with `watermarking=False`, which gives 128 outputs per set. It uses key 42.

Without `--spec` it uses recipe 1's setup: `Qwen/Qwen2.5-0.5B-Instruct`, `gumbel` and the plain detector. With `--spec` it uses recipe 2's setup (`dual_key_gumbel`, MTP, 3 draft tokens per step, probabilistic drafting) and runs the dual-key detector at `alpha=0.5` and at `alpha=0.2`.

## Why structured data is hard

Only tokens where the model has a real choice carry the watermark. In JSON most tokens are forced: brackets, quotes, key names and the next `id`.

JSON also repeats the same short contexts many times within one output. The detector scores a repeated context only once, so this repetition adds no false evidence.

During normal generation, vLLM samples a repeated context without the watermark (the default `single_turn` deduplication), which prevents repetition bias in the generated text.

Repetition across outputs does matter. Every output of one template has the same forced tokens after the same contexts. With a fixed key, each of those tokens gets the same score in every output, watermarked or not. So each key starts every output of the template with its own offset, up or down. That key's false-positive rate on that template is then no longer the p-value threshold.

## Normal generation

Without spec decode, use `gumbel` as in recipe 1. It has no `alpha` to tune.

## Speculative decoding

The detector's `alpha` is the weight it gives to key B. The `alpha` in the watermark config is ignored under spec decode, so the detector's value is the one to tune.

Because of the per-key offset, no formula gives the best value for a template. Compare values on your own outputs with your own key.

## Run it

From this folder:

```bash
source ../../.venv/bin/activate
python detect_json.py
python detect_json.py --spec
```

## Things to know

**Check false positives on your template.** Generate a few hundred `watermarking=False` outputs of your template and count how many are flagged. If too many are, lower the threshold (`--p-value-threshold` on the server, `p_value_threshold` on the detector).

**JSON stays weaker than prose.** Structured output will always have higher (weaker) p-values than free-form prose of the same length, because fewer tokens carry signal.
