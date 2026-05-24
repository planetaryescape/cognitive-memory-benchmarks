from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import create_peer_review_splits as splits  # noqa: E402


def test_locomo_split_is_by_conversation_and_deterministic():
    dev_a, test_a = splits.split_locomo(n_conversations=10, dev_count=5, seed=20260511)
    dev_b, test_b = splits.split_locomo(n_conversations=10, dev_count=5, seed=20260511)

    assert dev_a == dev_b
    assert test_a == test_b
    assert len(dev_a) == 5
    assert len(test_a) == 5
    assert set(dev_a).isdisjoint(test_a)
    assert sorted(dev_a + test_a) == list(range(10))


def test_longmemeval_split_preserves_type_and_abstention_strata():
    data = []
    for qt in ["single-session-user", "temporal-reasoning"]:
        for i in range(10):
            suffix = "_abs" if i % 2 == 0 else ""
            data.append({"question_id": f"{qt}-{i}{suffix}", "question_type": qt})

    dev, test = splits.split_longmemeval_ids(data, dev_frac=0.4, seed=1)
    assert set(dev).isdisjoint(test)
    assert len(dev) == 8
    assert len(test) == 12

    by_type_dev = splits.count_longmemeval_types(data, set(dev))
    by_type_test = splits.count_longmemeval_types(data, set(test))
    assert by_type_dev == {"single-session-user": 4, "temporal-reasoning": 4}
    assert by_type_test == {"single-session-user": 6, "temporal-reasoning": 6}

    for qt in ["single-session-user", "temporal-reasoning"]:
        dev_abs = [qid for qid in dev if qid.startswith(qt) and qid.endswith("_abs")]
        test_abs = [qid for qid in test if qid.startswith(qt) and qid.endswith("_abs")]
        assert len(dev_abs) == 2
        assert len(test_abs) == 3
