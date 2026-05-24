from shared.metrics import LOCOMO_CATEGORIES


def test_locomo_category_labels_match_dataset_counts():
    assert LOCOMO_CATEGORIES[1] == "multi-hop"
    assert LOCOMO_CATEGORIES[2] == "temporal"
    assert LOCOMO_CATEGORIES[3] == "open-domain"
    assert LOCOMO_CATEGORIES[4] == "single-hop"
