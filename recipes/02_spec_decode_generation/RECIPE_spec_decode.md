# Watermarked generation with speculative decoding

This recipe generates watermarked text while speculative decoding is on.

The script runs one prompt twice: once watermarked, once with `watermarking=False`. It writes `watermarked.txt` and `unwatermarked.txt` next to itself and prints the draft acceptance rate.

**Note:** This recipe requires a model with a built-in MTP draft head. `Qwen/Qwen2.5-0.5B-Instruct` may not ship one. If speculative decoding fails to initialize, use a model that includes an MTP head (such as models in the Qwen3 family once supported by your vLLM version), or switch to a different speculative method supported by your model.

## Run it

From this folder:

```bash
source ../../.venv/bin/activate
python generate_spec_decode.py
```

The equivalent server:

```bash
vllm serve <your-model> \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3,"draft_sample_method":"probabilistic"}' \
  --watermark-config '{"algorithm":"dual_key_gumbel","key":42}'
```

## Things to know

**Use `dual_key_gumbel`.** Draft tokens are sampled with key A, and rejection-recovery and bonus tokens with key B. The accept/reject test uses the unwatermarked probabilities, so watermarking does not lower the acceptance rate. Detection must use the dual-key detector, which scores every token against both keys. The plain gumbel detector gives p around 0.7 on this text.

**For prose, set the detector's `alpha` to key B's share.** The `alpha` field of the watermark config has no effect here: the speculative protocol picks the key for each token. On the detector side, `alpha` weights the two keys. Each verification step emits exactly one key-B token (recovery or bonus) after its accepted drafts, so with k draft tokens per step key B's share is 1/(1 + k × acceptance), where acceptance is the rate the script prints.

**Spec decode settings are restricted.** The method must be `mtp`, `eagle`, `eagle3` or `dspark`; every other method is rejected, including ngram and a separate `draft_model`. Parallel drafting works only with `dspark`. `draft_sample_method` defaults to `"greedy"`, so the config sets `"probabilistic"` explicitly, and `rejection_sample_method` must stay at its default `"standard"`.

**Plain `gumbel` works only with an opt-in, and gives a weaker signal.** Add `"allow_target_only_watermarking": true` to a `gumbel` config, and detect with the normal (gumbel) server from recipe 3. Accepted draft tokens are then not watermarked at all, so the signal shrinks with the acceptance rate.
