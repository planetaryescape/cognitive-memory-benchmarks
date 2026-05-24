from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import locomo_eval  # noqa: E402


def test_build_result_payload_marks_partial_checkpoint():
    payload = locomo_eval.build_result_payload(
        [
            {
                "conv_index": 2,
                "question_index": 0,
                "category": 1,
                "f1": 0.5,
                "f1_mem0": 0.25,
                "bleu1": 0.125,
            }
        ],
        status="partial",
        adapter_name="naive_rag",
        model="local-model",
        answer_temperature=0,
        answer_max_tokens=None,
        prompt_mode="mem0",
        dual_perspective=False,
        deep_recall=False,
        custom_extraction_instructions=None,
        rerank=False,
        rerank_factor=3,
        top_k=60,
        use_judge=False,
        requested_conversations=5,
        elapsed_seconds=12.0,
    )

    assert payload["status"] == "partial"
    assert payload["aggregate"]["overall"]["mean_f1"] == 0.5
    assert payload["aggregate"]["meta"]["completed_conversation_indices"] == [2]
    assert payload["aggregate"]["meta"]["num_conversations"] == 5


def test_write_result_payload_replaces_file_atomically(tmp_path):
    output = tmp_path / "result.json"
    payload = {"status": "partial", "aggregate": {}, "per_question": []}

    locomo_eval.write_result_payload(str(output), payload)

    assert json.loads(output.read_text()) == payload
    assert not (tmp_path / "result.json.tmp").exists()


def test_load_resume_checkpoint_returns_next_missing_conversation(tmp_path):
    output = tmp_path / "result.json"
    payload = {
        "status": "partial",
        "aggregate": {"meta": {"status": "partial"}},
        "per_question": [
            {"conv_index": 0, "question_index": 0, "category": 1, "f1": 1.0},
            {"conv_index": 1, "question_index": 0, "category": 1, "f1": 0.5},
        ],
    }
    output.write_text(json.dumps(payload))

    rows, start_from, complete = locomo_eval.load_resume_checkpoint(
        str(output),
        requested_conversations=5,
    )

    assert rows == payload["per_question"]
    assert start_from == 2
    assert complete is False


def test_load_resume_checkpoint_detects_complete_result(tmp_path):
    output = tmp_path / "result.json"
    payload = {
        "status": "complete",
        "aggregate": {"meta": {"status": "complete"}},
        "per_question": [
            {"conv_index": 0, "question_index": 0, "category": 1, "f1": 1.0},
            {"conv_index": 1, "question_index": 0, "category": 1, "f1": 0.5},
        ],
    }
    output.write_text(json.dumps(payload))

    _rows, start_from, complete = locomo_eval.load_resume_checkpoint(
        str(output),
        requested_conversations=2,
    )

    assert start_from == 2
    assert complete is True
