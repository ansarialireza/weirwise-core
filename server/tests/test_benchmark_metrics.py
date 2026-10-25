def calculate_nested_recalls(exact_results: list[int], hnsw_results: list[int], top_k: int = 10):
    """Calculates standard IR Recall@5 and Recall@10 against the ground-truth relevant set."""
    gt_set = set(exact_results[:top_k])
    hnsw_5 = set(hnsw_results[:5])
    hnsw_10 = set(hnsw_results[:10])

    assert hnsw_5.issubset(hnsw_10), "Top-5 results must be a nested subset of Top-10 results"

    r5 = len(hnsw_5 & gt_set) / float(len(gt_set))
    r10 = len(hnsw_10 & gt_set) / float(len(gt_set))

    assert r5 <= r10, f"Recall@5 ({r5}) cannot exceed Recall@10 ({r10})"
    return r5, r10


def test_recall_metric_monotonicity_and_nesting():
    # Synthetic query results
    gt = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # Case 1: 3 hits in top-5, 6 hits in top-10
    hnsw1 = [1, 2, 3, 99, 98, 4, 5, 6, 97, 96]
    r5, r10 = calculate_nested_recalls(gt, hnsw1, top_k=10)
    assert r5 == 0.3
    assert r10 == 0.6
    assert r5 <= r10

    # Case 2: 5 hits in top-5, 5 hits in top-10 (no new hits in ranks 6-10)
    hnsw2 = [1, 2, 3, 4, 5, 99, 98, 97, 96, 95]
    r5, r10 = calculate_nested_recalls(gt, hnsw2, top_k=10)
    assert r5 == 0.5
    assert r10 == 0.5
    assert r5 <= r10

    # Case 3: 0 hits in top-5, 2 hits in top-10
    hnsw3 = [99, 98, 97, 96, 95, 1, 2, 94, 93, 92]
    r5, r10 = calculate_nested_recalls(gt, hnsw3, top_k=10)
    assert r5 == 0.0
    assert r10 == 0.2
    assert r5 <= r10
