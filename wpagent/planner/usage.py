"""Track Claude API spend: printed after every call and appended to runs/usage.jsonl with a running total."""
from __future__ import annotations

import json
import time

from ..config import ROOT

USAGE_FILE = ROOT / "runs" / "usage.jsonl"

# USD per million tokens (Anthropic first-party pricing, Oct 2026).
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00},
}


def cost_usd(model: str, usage) -> float:
    p = PRICES[model]
    return (
        (usage.input_tokens or 0) * p["input"]
        + (usage.output_tokens or 0) * p["output"]
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * p["cache_read"]
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * p["cache_write"]
    ) / 1_000_000


def total_usd() -> float:
    if not USAGE_FILE.exists():
        return 0.0
    return sum(json.loads(line)["usd"] for line in USAGE_FILE.read_text(encoding="utf-8").splitlines() if line.strip())


def record(model: str, usage, purpose: str, run_dir: str | None = None) -> dict:
    entry = {
        "t": round(time.time(), 3), "model": model, "purpose": purpose, "run_dir": run_dir,
        "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "usd": round(cost_usd(model, usage), 4),
    }
    USAGE_FILE.parent.mkdir(exist_ok=True)
    with USAGE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[usage] {purpose}: {entry['input_tokens']:,} in / {entry['output_tokens']:,} out tokens "
          f"= ${entry['usd']:.4f}  | running total ${total_usd():.4f}")
    return entry
