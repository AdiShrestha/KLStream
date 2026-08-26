# analysis/compute_metrics.py
import numpy as np
import pandas as pd
import sys

def tick_level_f1(predictions_df, ground_truth_df, threshold):
    """predictions_df: one row per DetectionResult (window-level).
       ground_truth_df: one row per tick, columns [seq, label]."""
    n_ticks = len(ground_truth_df)
    pred = np.zeros(n_ticks, dtype=bool)
    for _, row in predictions_df.iterrows():
        if row["max_score"] >= threshold:
            pred[int(row["first_seq"]):int(row["last_seq"]) + 1] = True
    truth = (ground_truth_df["label"].values != 0)

    tp = np.sum(pred & truth)
    fp = np.sum(pred & ~truth)
    fn = np.sum(~pred & truth)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def pa_k_f1(predictions_df, ground_truth_df, threshold, k_fraction, segments):
    """segments: list of (start_seq, end_seq) ground-truth anomaly segments
       from injection_log.csv. Implements Kim et al. (AAAI 2022) PA%K:
       a segment counts as detected only if at least k_fraction of its
       ticks are individually flagged — NOT just one."""
    n_ticks = len(ground_truth_df)
    raw_pred = np.zeros(n_ticks, dtype=bool)
    for _, row in predictions_df.iterrows():
        if row["max_score"] >= threshold:
            raw_pred[int(row["first_seq"]):int(row["last_seq"]) + 1] = True

    adjusted_pred = raw_pred.copy()
    for (s, e) in segments:
        seg_hits = raw_pred[s:e + 1].mean()
        if seg_hits >= k_fraction:
            adjusted_pred[s:e + 1] = True   # credit the whole segment
        # else: leave as-is (NOT credited) — this is the part naive PA skips
    truth = (ground_truth_df["label"].values != 0)
    tp = np.sum(adjusted_pred & truth)
    fp = np.sum(adjusted_pred & ~truth)
    fn = np.sum(~adjusted_pred & truth)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1

def range_f1(predictions_df, ground_truth_df, threshold, segments, alpha=0.0):
    """
    Computes Range-based Precision, Recall, and F1 following Tatbul et al.
    (NeurIPS 2018). Uses the PRTS library if available; falls back to a
    manual simplified implementation (flat cardinality, no position bias,
    existence-only overlap) if not.

    Args:
        predictions_df: DataFrame with columns [first_seq, last_seq, max_score]
        ground_truth_df: DataFrame with column [seq, label]
        threshold: float, anomaly score threshold
        segments: list of (start_seq, end_seq) tuples for each anomaly segment
        alpha: float in [0,1], weight for overlap vs. existence reward (0=flat)

    Returns:
        (range_precision, range_recall, range_f1_score): all floats in [0,1]
    """
    import numpy as np
    n_ticks = len(ground_truth_df)

    # Build binary prediction array at tick level (same as tick_level_f1)
    pred = np.zeros(n_ticks, dtype=bool)
    for _, row in predictions_df.iterrows():
        if row['max_score'] >= threshold:
            s = int(row['first_seq'])
            e = int(row['last_seq'])
            if s < n_ticks and e < n_ticks:
                pred[s:e + 1] = True

    truth = (ground_truth_df['label'].values != 0)

    try:
        from prts import ts_precision, ts_recall
        # PRTS expects integer 0/1 arrays
        pred_int  = pred.astype(int)
        truth_int = truth.astype(int)
        rp = ts_precision(truth_int, pred_int, alpha=alpha,
                          cardinality="reciprocal", bias="flat")
        rr = ts_recall(truth_int, pred_int, alpha=alpha,
                       cardinality="reciprocal", bias="flat")
        rf1 = (2 * rp * rr / (rp + rr)) if (rp + rr) > 0 else 0.0
        return float(rp), float(rr), float(rf1)

    except ImportError:
        # Manual fallback: simplified overlap-based range metrics
        # Recall: per real segment, what fraction of its ticks were detected?
        total_recall = 0.0
        for (s, e) in segments:
            seg_len = e - s + 1
            if seg_len == 0:
                continue
            detected = np.sum(pred[s:e + 1])
            existence_reward = 1.0 if detected > 0 else 0.0
            overlap_reward   = detected / seg_len
            seg_recall = alpha * overlap_reward + (1.0 - alpha) * existence_reward
            total_recall += seg_recall
        rr = total_recall / len(segments) if segments else 0.0

        # Precision: per predicted segment, what fraction overlaps a real anomaly?
        from itertools import groupby
        pred_segments = []
        for k, g in groupby(range(n_ticks), key=lambda i: pred[i]):
            grp = list(g)
            if k:
                pred_segments.append((grp[0], grp[-1]))

        total_precision = 0.0
        for (ps, pe) in pred_segments:
            seg_len = pe - ps + 1
            overlapping = np.sum(truth[ps:pe + 1])
            existence_reward = 1.0 if overlapping > 0 else 0.0
            overlap_reward   = overlapping / seg_len
            seg_prec = alpha * overlap_reward + (1.0 - alpha) * existence_reward
            total_precision += seg_prec
        rp = total_precision / len(pred_segments) if pred_segments else 0.0

        rf1 = (2 * rp * rr / (rp + rr)) if (rp + rr) > 0 else 0.0
        return float(rp), float(rr), float(rf1)

def lba_f1(predictions_df, ground_truth_df, threshold, max_latency_ms):
    """Latency-Bounded Accuracy (LBA@T) F1 score.

    Discards any detection whose latency_ns exceeds the SLA bound before
    computing F1.  Only detections that arrive in time are considered.

    NOTE: LBA@1ms is intentionally NOT exposed in CLI output — the adaptive
    architecture's best-case P95 latency is ~17ms, so no detection can ever
    qualify under a 1ms cap.  The metric has zero discriminating power at
    that threshold.  Use LBA@10ms / @25ms / @50ms instead, which span the
    observable latency distribution.

    NOTE on DataDriven determinism: DataDrivenWindowOp reads only the
    pre-computed rolling_vol column from the replay CSV.  That column is
    fixed regardless of replay speed or wall-clock pacing, so DataDriven's
    F1 and PA scores are structurally deterministic (std ≈ 0.0000).  This is
    not a measurement artifact — it is a principled consequence of the
    baseline's load-blindness, and worth stating explicitly in the paper.
    """
    valid_preds = predictions_df[predictions_df["latency_ns"] <= max_latency_ms * 1_000_000]
    return tick_level_f1(valid_preds, ground_truth_df, threshold)


def random_baseline_sanity_check(ground_truth_df, n_windows, window_size, seed=0):
    """Kim et al.'s own recommended check: confirm a random score achieves
       near-chance RAW (non-adjusted) F1 under your pipeline. Run this once
       and report the result in the paper as a methodology footnote."""
    rng = np.random.default_rng(seed)
    fake_scores = rng.uniform(0, 1, size=n_windows)
    
    predictions_list = []
    for i in range(n_windows):
        start = i * window_size
        end = min((i+1)*window_size - 1, len(ground_truth_df)-1)
        predictions_list.append({"max_score": fake_scores[i], "first_seq": start, "last_seq": end})
    
    predictions_df = pd.DataFrame(predictions_list)
    threshold = 0.95 # 95th percentile
    p, r, f1 = tick_level_f1(predictions_df, ground_truth_df, threshold)
    print(f"Random Baseline Sanity Check (seed={seed}): Precision={p:.4f}, Recall={r:.4f}, F1={f1:.4f}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 compute_metrics.py <results_csv> <ground_truth_csv>")
        sys.exit(1)
        
    res_path = sys.argv[1]
    gt_path = sys.argv[2]
    
    try:
        results = pd.read_csv(res_path)
        gt = pd.read_csv(gt_path)
    except Exception as e:
        print(f"Error loading files: {e}")
        sys.exit(1)
        
    threshold = results["max_score"].quantile(0.95)
    print(f"Using threshold (95th percentile): {threshold:.4f}")
    
    p, r, f1 = tick_level_f1(results, gt, threshold)
    print(f"Raw Tick-Level F1: Precision={p:.4f}, Recall={r:.4f}, F1={f1:.4f}")
    
    # Extract segments from ground truth (assuming consecutive non-zero labels form a segment)
    segments = []
    in_seg = False
    start = 0
    for i, label in enumerate(gt["label"]):
        if label != 0 and not in_seg:
            in_seg = True
            start = i
        elif label == 0 and in_seg:
            in_seg = False
            segments.append((start, i-1))
    if in_seg:
        segments.append((start, len(gt)-1))
        
    p20, r20, f1_20 = pa_k_f1(results, gt, threshold, 0.20, segments)
    print(f"PA%20 F1: Precision={p20:.4f}, Recall={r20:.4f}, F1={f1_20:.4f}")
    
    p50, r50, f1_50 = pa_k_f1(results, gt, threshold, 0.50, segments)
    print(f"PA%50 F1:   Precision={p50:.4f}, Recall={r50:.4f}, F1={f1_50:.4f}")

    # LBA thresholds grounded in observed latency distribution (~P95=17-70ms)
    # LBA@1ms is intentionally omitted — see lba_f1() docstring.
    p10, r10, f1_lba10 = lba_f1(results, gt, threshold, 10.0)
    print(f"LBA@10ms:   Precision={p10:.4f}, Recall={r10:.4f}, F1={f1_lba10:.4f}")

    p25, r25, f1_lba25 = lba_f1(results, gt, threshold, 25.0)
    print(f"LBA@25ms:   Precision={p25:.4f}, Recall={r25:.4f}, F1={f1_lba25:.4f}")

    p50l, r50l, f1_lba50 = lba_f1(results, gt, threshold, 50.0)
    print(f"LBA@50ms:   Precision={p50l:.4f}, Recall={r50l:.4f}, F1={f1_lba50:.4f}")

    random_baseline_sanity_check(gt, len(results), results["window_size_used"].median())
