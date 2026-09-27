"""Generate one spec synchronously and print what it actually produced."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.config import load_config  # noqa: E402
from engine.spec import FALLBACK_MARKER, load_cluster_items, load_idea, generate_spec  # noqa: E402
from engine.store.db import init_db  # noqa: E402

idea_id = int(sys.argv[1]) if len(sys.argv) > 1 else 16

conn = init_db()
idea = load_idea(conn, idea_id)
if not idea:
    print(f"idea {idea_id} not found")
    raise SystemExit(1)
items = load_cluster_items(conn, idea_id)
print(f"idea {idea_id}: {idea['title'][:60]}", flush=True)
print(f"cluster items: {len(items)}", flush=True)

cfg = load_config()
cfg.setdefault("models", {}).setdefault("max_tokens_by_stage", {})["expensive"] = 3000
import engine.providers as providers  # noqa: E402
providers._registry = None
reg = providers.get_provider(cfg)
reg.start_budget("spec")

spec = generate_spec(idea, items)
print(f"\nFALLBACK_MARKER present: {FALLBACK_MARKER in spec}", flush=True)
for heading in (
    "## Problem", "## Solution", "## Target User", "## Key Features",
    "## Tech Stack & Architecture", "## Data Model", "## API / Interfaces",
    "## UI/UX Requirements", "## Monetization", "## Risks & Mitigation",
    "## Launch Checklist", "## Cited Sources",
):
    print(f"  {'OK ' if heading in spec else 'MISS'} {heading}", flush=True)
print(f"\nchars: {len(spec)}  llm minutes: {reg.budget_report()}", flush=True)
print("\n--- first 1200 chars of body ---\n", flush=True)
print(spec[spec.find("## Metadata"):][:1200], flush=True)
reg.close()
