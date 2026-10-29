from pathlib import Path

from vllm import LLM, SamplingParams


def main():
    llm = LLM(
        "Qwen/Qwen2.5-0.5B-Instruct",
        watermark_config={"algorithm": "dual_key_gumbel", "key": 42},
        speculative_config={
            "method": "mtp",
            "num_speculative_tokens": 3,
            "draft_sample_method": "probabilistic",
        },
        disable_log_stats=False,  # needed for llm.get_metrics()
    )
    messages = [{"role": "user", "content": "Write a short story about a lighthouse keeper."}]

    here = Path(__file__).parent
    for name, watermarking in [("watermarked", True), ("unwatermarked", False)]:
        # temperature must be above 0: greedy requests are never watermarked.
        params = SamplingParams(temperature=1.0, max_tokens=200, watermarking=watermarking)
        text = llm.chat(messages, params)[0].outputs[0].text
        print(f"=== {name} ===\n{text}\n")
        (here / f"{name}.txt").write_text(text)

    metrics = {m.name: m for m in llm.get_metrics()}
    accepted = metrics["vllm:spec_decode_num_accepted_tokens"].value
    drafted = metrics["vllm:spec_decode_num_draft_tokens"].value
    print(f"Accepted {accepted} of {drafted} draft tokens ({accepted / drafted:.1%})")


if __name__ == "__main__":
    main()
