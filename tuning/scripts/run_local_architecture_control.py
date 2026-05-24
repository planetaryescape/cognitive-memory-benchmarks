#!/usr/bin/env python3
"""Run the local LoCoMo architecture-control campaign.

The campaign uses a local OpenAI-compatible chat endpoint for extraction,
reranking, and answer generation while keeping the benchmark harness and
OpenAI embeddings unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "tuning" / "runs" / "phase12-local-architecture-control"
DATA_PATH = "tuning/splits/peer_review_20260511/locomo_test.json"
MODEL = "openai/gpt-oss-120b"
ENDPOINT = "http://localhost:1234/v1"


@dataclass(frozen=True)
class Row:
    name: str
    label: str
    phase_suffix: str
    adapter: str
    config: str | None
    cognitive_flags: bool


ROWS = [
    Row(
        name="full",
        label="Full tuned",
        phase_suffix="full_split_full_tuned",
        adapter="cognitive_memory",
        config="tuning/spaces/peer_review/locomo_dev_tuned_frozen.json",
        cognitive_flags=True,
    ),
    Row(
        name="vector_only",
        label="Vector-only",
        phase_suffix="full_split_vector_only",
        adapter="naive_rag",
        config=None,
        cognitive_flags=False,
    ),
    Row(
        name="heuristic_default",
        label="Heuristic default",
        phase_suffix="full_split_heuristic_default",
        adapter="cognitive_memory",
        config="tuning/spaces/peer_review/heuristic_default.json",
        cognitive_flags=True,
    ),
    Row(
        name="no_reinforcement",
        label="No reinforcement",
        phase_suffix="full_split_no_reinforcement",
        adapter="cognitive_memory",
        config="tuning/spaces/peer_review/frozen_ablations/no_reinforcement.json",
        cognitive_flags=True,
    ),
    Row(
        name="no_associative_graph",
        label="No associative graph",
        phase_suffix="full_split_no_associative_graph",
        adapter="cognitive_memory",
        config="tuning/spaces/peer_review/frozen_ablations/no_associative_graph.json",
        cognitive_flags=True,
    ),
    Row(
        name="no_consolidation_deep_recall",
        label="No consolidation/deep recall",
        phase_suffix="full_split_no_consolidation_deep_recall",
        adapter="cognitive_memory",
        config="tuning/spaces/peer_review/frozen_ablations/no_consolidation_deep_recall.json",
        cognitive_flags=True,
    ),
    Row(
        name="no_core_promotion",
        label="No core promotion",
        phase_suffix="full_split_no_core_promotion",
        adapter="cognitive_memory",
        config="tuning/spaces/peer_review/frozen_ablations/no_core_promotion.json",
        cognitive_flags=True,
    ),
    Row(
        name="no_retention_weighting",
        label="No retention weighting",
        phase_suffix="full_split_no_retention_weighting",
        adapter="cognitive_memory",
        config="tuning/spaces/peer_review/frozen_ablations/no_retention_weighting.json",
        cognitive_flags=True,
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(event, default=str, sort_keys=True) + "\n")


def check_endpoint(endpoint: str, model: str, timeout: float) -> dict[str, Any]:
    url = endpoint.rstrip("/") + "/models"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    models = [item.get("id") for item in payload.get("data", [])]
    if model not in models:
        raise RuntimeError(f"model {model!r} not listed by {url}; available={models}")
    return {"url": url, "models": models}


def run_sdk_expiry_preflight(env: dict[str, str]) -> dict[str, Any]:
    """Fail fast on SDK expiry/date handling before long benchmark rows."""
    code = """
from datetime import datetime, timezone
from cognitive_memory import Memory, SyncCognitiveMemory

mem = SyncCognitiveMemory(embedder='hash')
engine = mem.engine

plan = Memory(
    content='User plans to visit the dentist.',
    memory_type='plan',
    valid_until=datetime(2024, 1, 1, tzinfo=timezone.utc),
)
assert engine._is_expired(plan, datetime(2024, 1, 2))

transient = Memory(
    content='User is currently nervous.',
    memory_type='transient_state',
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    ttl_seconds=60,
)
assert engine._is_expired(transient, datetime(2024, 1, 1, 0, 2))

print('sdk-expiry-preflight-ok')
"""
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "returncode": proc.returncode,
        "elapsed_seconds": time.time() - started,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def selected_rows(names: list[str]) -> list[Row]:
    if not names:
        return ROWS
    by_name = {row.name: row for row in ROWS}
    unknown = sorted(set(names) - set(by_name))
    if unknown:
        raise ValueError(f"unknown rows: {', '.join(unknown)}")
    return [by_name[name] for name in names]


def parse_resume_trials(specs: list[str]) -> dict[str, str]:
    resume_trials = {}
    known_rows = {row.name for row in ROWS}
    for spec in specs:
        if "=" not in spec:
            raise ValueError("--resume-trial must use row=trial_id")
        row_name, trial_id = spec.split("=", 1)
        row_name = row_name.strip()
        trial_id = trial_id.strip()
        if row_name not in known_rows:
            raise ValueError(f"unknown resume row: {row_name}")
        if not trial_id.startswith("locomo-"):
            raise ValueError(f"resume trial must be a locomo trial id: {trial_id}")
        resume_trials[row_name] = trial_id
    return resume_trials


def build_command(
    row: Row,
    *,
    data: str,
    model: str,
    phase_prefix: str,
    max_conversations: int | None,
    resume_trial_id: str | None = None,
) -> list[str]:
    cmd = [
        sys.executable,
        "tuning/scripts/run_trial.py",
        "--benchmark",
        "locomo",
    ]
    if resume_trial_id:
        cmd.extend(["--trial-id", resume_trial_id])
    if row.config:
        cmd.extend(["--config", row.config])
    cmd.extend(
        [
            "--phase",
            f"{phase_prefix}_{row.phase_suffix}",
            "--score-keys",
            "aggregate.overall.mean_f1",
            "aggregate.by_category.multi-hop.mean_f1",
            "aggregate.by_category.temporal.mean_f1",
            "--",
            "--data",
            data,
            "--adapter",
            row.adapter,
            "--model",
            model,
            "--prompt-mode",
            "mem0",
            "--top-k",
            "60",
            "--resume",
            "--quiet",
        ]
    )
    if row.cognitive_flags:
        cmd.extend(["--dual-perspective", "--deep-recall", "--rerank", "--rerank-factor", "3"])
    if max_conversations is not None:
        cmd.extend(["--max-conversations", str(max_conversations)])
    return cmd


def run_row(row: Row, cmd: list[str], env: dict[str, str]) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.time() - started
    parsed_stdout = None
    if proc.stdout.strip():
        try:
            parsed_stdout = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            parsed_stdout = None
    return {
        "event": "row_finished",
        "ts_utc": utc_now(),
        "row": row.name,
        "label": row.label,
        "returncode": proc.returncode,
        "elapsed_seconds": elapsed,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "run_trial": parsed_stdout,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.getenv("OPENAI_CHAT_BASE_URL", ENDPOINT))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_CHAT_API_KEY", "lm-studio"))
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--data", default=DATA_PATH)
    parser.add_argument("--timeout", type=float, default=float(os.getenv("OPENAI_CHAT_TIMEOUT", "600")))
    parser.add_argument("--probe-timeout", type=float, default=10.0)
    parser.add_argument("--row", action="append", default=[], choices=[row.name for row in ROWS])
    parser.add_argument("--max-conversations", type=int, default=None)
    parser.add_argument("--phase-prefix", default="peer_review_local_lmstudio_locomo_test")
    parser.add_argument("--campaign-log", default=str(OUTPUT_DIR / "campaign.jsonl"))
    parser.add_argument("--resume-trial", action="append", default=[], help="Resume row from existing trial id: row=locomo-NNNN")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--skip-sdk-preflight", action="store_true")
    args = parser.parse_args()

    campaign_log = Path(args.campaign_log)
    rows = selected_rows(args.row)
    resume_trials = parse_resume_trials(args.resume_trial)
    probe = check_endpoint(args.endpoint, args.model, args.probe_timeout)

    env = {
        **os.environ,
        "OPENAI_CHAT_BASE_URL": args.endpoint,
        "OPENAI_CHAT_API_KEY": args.api_key,
        "OPENAI_CHAT_TIMEOUT": str(args.timeout),
    }

    sdk_preflight = None
    if not args.skip_sdk_preflight:
        sdk_preflight = run_sdk_expiry_preflight(env)
        preflight_event = {
            "event": "sdk_expiry_preflight",
            "ts_utc": utc_now(),
            **sdk_preflight,
        }
        append_event(campaign_log, preflight_event)
        print(json.dumps(preflight_event, sort_keys=True))
        if sdk_preflight["returncode"] != 0:
            return 1

    start_event = {
        "event": "campaign_started",
        "ts_utc": utc_now(),
        "endpoint": args.endpoint,
        "model": args.model,
        "data": args.data,
        "timeout": args.timeout,
        "rows": [row.name for row in rows],
        "resume_trials": resume_trials,
        "probe": probe,
        "sdk_preflight": sdk_preflight,
        "dry_run": args.dry_run,
    }
    append_event(campaign_log, start_event)
    print(json.dumps(start_event, sort_keys=True))

    failures = 0
    for row in rows:
        cmd = build_command(
            row,
            data=args.data,
            model=args.model,
            phase_prefix=args.phase_prefix,
            max_conversations=args.max_conversations,
            resume_trial_id=resume_trials.get(row.name),
        )
        row_started = {
            "event": "row_started",
            "ts_utc": utc_now(),
            "row": row.name,
            "label": row.label,
            "command": cmd,
        }
        append_event(campaign_log, row_started)
        print(json.dumps(row_started, sort_keys=True))
        if args.dry_run:
            continue
        result = run_row(row, cmd, env)
        append_event(campaign_log, result)
        print(json.dumps(result, sort_keys=True))
        if result["returncode"] != 0:
            failures += 1
            if args.stop_on_error:
                break

    finished = {
        "event": "campaign_finished",
        "ts_utc": utc_now(),
        "failures": failures,
        "dry_run": args.dry_run,
    }
    append_event(campaign_log, finished)
    print(json.dumps(finished, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
