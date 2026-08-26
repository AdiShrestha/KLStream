#!/usr/bin/env python3
"""
evaluation_metrics.py — High-Precision Metric Evaluation Engine for Streaming Anomaly Detection.

Implements:
- Pointwise AUC-ROC, PR-AUC, Precision, Recall, F1, and FPR (MAR-X3)
- Decomposed Latency Accounting: T_q (queuing) + T_freshness (window aggregation) + T_exec (scoring) (INV-010)
- Validation Threshold Tuning (MAR-3)
"""

import math
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

def compute_auc_roc(y_true: Union[List[int], np.ndarray], y_scores: Union[List[float], np.ndarray]) -> float:
    """
    Computes Pointwise Area Under the Receiver Operating Characteristic Curve (AUC-ROC)
    using rank-order Mann-Whitney U formulation.
    """
    y_t = np.asarray(y_true, dtype=int)
    y_s = np.asarray(y_scores, dtype=float)
    
    pos_idx = np.where(y_t == 1)[0]
    neg_idx = np.where(y_t == 0)[0]
    
    n_pos = len(pos_idx)
    n_neg = len(neg_idx)
    
    if n_pos == 0 or n_neg == 0:
        return 0.5 # Undefined/degenerate single-class baseline
        
    order = np.argsort(y_s)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_s) + 1)
    
    # Handle ties with mid-rank assignment
    unique_scores, inv_idx, counts = np.unique(y_s, return_inverse=True, return_counts=True)
    if len(unique_scores) < len(y_s):
        rank_sums = np.bincount(inv_idx, weights=ranks)
        tie_ranks = rank_sums / counts
        ranks = tie_ranks[inv_idx]
        
    pos_rank_sum = np.sum(ranks[pos_idx])
    u_stat = pos_rank_sum - (n_pos * (n_pos + 1.0)) / 2.0
    return float(u_stat / (n_pos * n_neg))

def compute_pr_auc(y_true: Union[List[int], np.ndarray], y_scores: Union[List[float], np.ndarray]) -> float:
    """
    Computes Area Under the Precision-Recall Curve (PR-AUC) using trapezoidal integration.
    """
    y_t = np.asarray(y_true, dtype=int)
    y_s = np.asarray(y_scores, dtype=float)
    
    n_pos = int(np.sum(y_t == 1))
    if n_pos == 0:
        return 0.0
        
    # Sort descending
    sort_idx = np.argsort(-y_s)
    y_sorted = y_t[sort_idx]
    
    tps = np.cumsum(y_sorted == 1)
    fps = np.cumsum(y_sorted == 0)
    
    recalls = tps / float(n_pos)
    precisions = tps / (tps + fps)
    
    # Prepend (Recall=0, Precision=1)
    r_padded = np.concatenate(([0.0], recalls))
    p_padded = np.concatenate(([1.0], precisions))
    
    # Trapezoidal integration
    diff_r = np.diff(r_padded)
    avg_p = 0.5 * (p_padded[:-1] + p_padded[1:])
    return float(np.sum(avg_p * diff_r))


def compute_binary_classification_metrics(y_true: Union[List[int], np.ndarray],
                                         y_scores: Union[List[float], np.ndarray],
                                         threshold: float) -> dict:
    """
    Computes Pointwise Precision, Recall, F1, FPR, and Confusion Matrix at fixed threshold.
    """
    y_t = np.asarray(y_true, dtype=int)
    y_s = np.asarray(y_scores, dtype=float)
    y_pred = (y_s >= threshold).astype(int)
    
    tp = int(np.sum((y_t == 1) & (y_pred == 1)))
    fp = int(np.sum((y_t == 0) & (y_pred == 1)))
    tn = int(np.sum((y_t == 0) & (y_pred == 0)))
    fn = int(np.sum((y_t == 1) & (y_pred == 0)))
    
    precision = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2.0 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / float(fp + tn) if (fp + tn) > 0 else 0.0
    accuracy = (tp + tn) / float(len(y_t)) if len(y_t) > 0 else 0.0
    
    return {
        "threshold": float(threshold),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "accuracy": float(accuracy)
    }

def compute_latency_summary(latencies_ns: Union[List[float], np.ndarray]) -> dict:
    """
    Computes standard latency percentiles with exact rank quantiles.
    """
    arr = np.asarray(latencies_ns, dtype=float)
    if len(arr) == 0:
        return {
            "count": 0,
            "min_ns": 0.0, "mean_ns": 0.0, "p50_ns": 0.0,
            "p90_ns": 0.0, "p95_ns": 0.0, "p99_ns": 0.0,
            "max_ns": 0.0, "std_ns": 0.0
        }
        
    return {
        "count": len(arr),
        "min_ns": float(np.min(arr)),
        "mean_ns": float(np.mean(arr)),
        "p50_ns": float(np.percentile(arr, 50)),
        "p90_ns": float(np.percentile(arr, 90)),
        "p95_ns": float(np.percentile(arr, 95)),
        "p99_ns": float(np.percentile(arr, 99)),
        "max_ns": float(np.max(arr)),
        "std_ns": float(np.std(arr))
    }

def compute_decomposed_latency_summary(t_q: List[float], t_freshness: List[float], t_exec: List[float]) -> dict:
    """
    Decomposes total end-to-end latency into Queuing, Freshness lag, and Execution time (INV-010).
    """
    q_arr = np.asarray(t_q, dtype=float)
    f_arr = np.asarray(t_freshness, dtype=float)
    e_arr = np.asarray(t_exec, dtype=float)
    e2e_arr = q_arr + f_arr + e_arr
    
    return {
        "queuing_latency": compute_latency_summary(q_arr),
        "freshness_lag": compute_latency_summary(f_arr),
        "execution_latency": compute_latency_summary(e_arr),
        "end_to_end_latency": compute_latency_summary(e2e_arr)
    }

def tune_validation_threshold(y_val_true: Union[List[int], np.ndarray],
                             y_val_scores: Union[List[float], np.ndarray],
                             target_fpr: float = 0.05) -> float:
    """
    Determines anomaly decision threshold tau on the Validation split (MAR-3).
    Selects threshold corresponding to the (1 - target_fpr) quantile of normal validation points.
    """
    y_t = np.asarray(y_val_true, dtype=int)
    y_s = np.asarray(y_val_scores, dtype=float)
    
    normal_scores = y_s[y_t == 0]
    if len(normal_scores) == 0:
        return float(np.percentile(y_s, (1.0 - target_fpr) * 100.0))
        
    return float(np.percentile(normal_scores, (1.0 - target_fpr) * 100.0))
