import argparse
import json
import random
import statistics

from vllm import LLM, SamplingParams
from vllm.v1.watermarking import DualKeyGumbelWatermarkDetector, GumbelWatermarkDetector

SENSORS = [
    "temperature", "pressure", "humidity", "voltage", "current", "wind speed",
    "rainfall", "altitude", "heart rate", "blood pressure", "stock price",
    "exchange rate", "CPU load", "memory usage", "latency", "throughput",
]
KEY = 42


def make_prompt(sensor, station):
    rng = random.Random(f"{sensor}{station}")
    rows = [
        {"id": i, "sensor": f"{sensor} {station}", "value": round(rng.uniform(10, 99), 2)}
        for i in range(1, 16)
    ]
    return (
        f"Here are {sensor} readings:\n{json.dumps(rows, indent=2)}\n"
        "Continue the list with 20 more readings in exactly the same format. Output only JSON."
    )


def report(name, outputs, detector):
    results = [detector.detect(ids) for ids in outputs]
    detected = sum(r.is_watermarked for r in results)  # p_value <= 0.01
    median_p = statistics.median(r.p_value for r in results)
    print(f"{name}: detected {detected}/{len(results)}, median p = {median_p:.1e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", action="store_true", help="use MTP speculative decoding")
    spec = parser.parse_args().spec

    if spec:
        llm = LLM(
            "Qwen/Qwen2.5-0.5B-Instruct",
            watermark_config={"algorithm": "dual_key_gumbel", "key": KEY},
            speculative_config={
                "method": "mtp",
                "num_speculative_tokens": 3,
                "draft_sample_method": "probabilistic",
            },
        )
        detectors = {
            f"alpha={a}": DualKeyGumbelWatermarkDetector(key=KEY, alpha=a) for a in (0.5, 0.2)
        }
    else:
        llm = LLM("Qwen/Qwen2.5-0.5B-Instruct", watermark_config={"algorithm": "gumbel", "key": KEY})
        detectors = {"gumbel": GumbelWatermarkDetector(key=KEY)}

    prompts = [make_prompt(s, st) for s in SENSORS for st in "AB"]
    messages = [[{"role": "user", "content": p}] for p in prompts * 4]

    outputs = {}
    for name, watermarking in [("watermarked", True), ("unwatermarked", False)]:
        params = SamplingParams(temperature=1.0, max_tokens=400, watermarking=watermarking)
        outputs[name] = [list(o.outputs[0].token_ids) for o in llm.chat(messages, params)]

    for label, detector in detectors.items():
        print(f"=== {label} ===")
        for name, token_ids in outputs.items():
            report(name, token_ids, detector)


if __name__ == "__main__":
    main()
