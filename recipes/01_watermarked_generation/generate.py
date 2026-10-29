from pathlib import Path

from vllm import LLM, SamplingParams


def main():
    llm = LLM("Qwen/Qwen2.5-0.5B-Instruct", watermark_config={"algorithm": "gumbel", "key": 42})
    messages = [{"role": "user", "content": "Write a short story about a lighthouse keeper."}]

    here = Path(__file__).parent
    for name, watermarking in [("watermarked", True), ("unwatermarked", False)]:
        # temperature must be above 0: greedy requests are never watermarked.
        params = SamplingParams(temperature=1.0, max_tokens=200, watermarking=watermarking)
        text = llm.chat(messages, params)[0].outputs[0].text
        print(f"=== {name} ===\n{text}\n")
        (here / f"{name}.txt").write_text(text)


if __name__ == "__main__":
    main()
