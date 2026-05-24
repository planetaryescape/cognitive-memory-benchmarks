from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import run_local_architecture_control  # noqa: E402


def test_build_command_uses_cognitive_flags_for_full_row():
    row = run_local_architecture_control.ROWS[0]

    cmd = run_local_architecture_control.build_command(
        row,
        data="data.json",
        model="local-model",
        phase_prefix="phase",
        max_conversations=1,
        resume_trial_id=None,
    )

    assert "--dual-perspective" in cmd
    assert "--deep-recall" in cmd
    assert "--rerank" in cmd
    assert "--resume" in cmd
    assert cmd[-2:] == ["--max-conversations", "1"]


def test_build_command_omits_cognitive_flags_for_vector_only():
    row = next(row for row in run_local_architecture_control.ROWS if row.name == "vector_only")

    cmd = run_local_architecture_control.build_command(
        row,
        data="data.json",
        model="local-model",
        phase_prefix="phase",
        max_conversations=None,
        resume_trial_id="locomo-1234",
    )

    assert "--trial-id" in cmd
    assert "locomo-1234" in cmd
    assert "--dual-perspective" not in cmd
    assert "--deep-recall" not in cmd
    assert "--rerank" not in cmd


def test_parse_resume_trials():
    assert run_local_architecture_control.parse_resume_trials(["full=locomo-0029"]) == {
        "full": "locomo-0029"
    }
