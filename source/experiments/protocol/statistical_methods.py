#!/usr/bin/env python3
"""
statistical_methods.py — Rigorous Non-Parametric Statistical Evaluation Engine for KLStream.

Implements:
- Cliff's delta non-parametric effect size
- Paired two-tailed Wilcoxon signed-rank test
- 95% Non-parametric percentile bootstrap confidence intervals (N_boot = 10,000)
- Bonferroni-Holm step-down FWER p-value adjustment
"""

import itertools
import math
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

def cliffs_delta(sample_a: Union[List[float], np.ndarray],
                 sample_b: Union[List[float], np.ndarray]) -> float:
    """
    Computes Cliff's delta non-parametric effect size between sample A and sample B.
    delta = ( # (a > b) - # (a < b) ) / ( len(a) * len(b) )
    Returns value in [-1.0, +1.0].
    """
    a = np.asarray(sample_a, dtype=float)
    b = np.asarray(sample_b, dtype=float)
    
    if len(a) == 0 or len(b) == 0:
        return 0.0
        
    gt = 0
    lt = 0
    for x in a:
        gt += np.sum(x > b)
        lt += np.sum(x < b)
        
    return float((gt - lt) / (len(a) * len(b)))

def interpret_cliffs_delta(delta: float) -> str:
    """
    Returns standard qualitative interpretation of Cliff's delta per Romano et al. (2006).
    """
    abs_d = abs(delta)
    if abs_d < 0.147:
        return "negligible"
    elif abs_d < 0.330:
        return "small"
    elif abs_d < 0.474:
        return "medium"
    else:
        return "large"

def wilcoxon_paired_test(sample_a: Union[List[float], np.ndarray],
                         sample_b: Union[List[float], np.ndarray]) -> dict:
    """
    Computes exact paired two-tailed Wilcoxon signed-rank test on differences d = a - b.
    """
    a = np.asarray(sample_a, dtype=float)
    b = np.asarray(sample_b, dtype=float)
    
    if len(a) != len(b):
        raise ValueError(f"Paired test requires identical lengths, got {len(a)} vs {len(b)}")
        
    diffs = a - b
    non_zero = diffs[diffs != 0.0]
    n = len(non_zero)
    
    if n == 0:
        return {"statistic": 0.0, "p_value": 1.0, "n_effective": 0}
        
    abs_diffs = np.abs(non_zero)
    order = np.argsort(abs_diffs)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, n + 1)
    
    # Handle ties in absolute differences
    unique_vals, inv_idx, counts = np.unique(abs_diffs, return_inverse=True, return_counts=True)
    if len(unique_vals) < n:
        rank_sums = np.bincount(inv_idx, weights=ranks)
        tie_ranks = rank_sums / counts
        ranks = tie_ranks[inv_idx]
        
    w_pos = float(np.sum(ranks[non_zero > 0.0]))
    w_neg = float(np.sum(ranks[non_zero < 0.0]))
    stat = min(w_pos, w_neg)
    
    # Exact permutation p-value for n <= 20
    if n <= 20:
        total_perms = 2 ** n
        # Generate all 2^n sign assignments
        signs_all = list(itertools.product([-1.0, 1.0], repeat=n))
        all_stats = []
        for s in signs_all:
            s_arr = np.array(s)
            r_pos = np.sum(ranks[s_arr > 0])
            r_neg = np.sum(ranks[s_arr < 0])
            all_stats.append(min(r_pos, r_neg))
        p_val = float(np.sum(np.array(all_stats) <= stat) / total_perms)
    else:
        # Asymptotic normal approximation with continuity correction
        mean_w = n * (n + 1.0) / 4.0
        var_w = n * (n + 1.0) * (2.0 * n + 1.0) / 24.0
        z = (stat - mean_w + 0.5) / math.sqrt(var_w)
        # Normal CDF
        p_val = float(2.0 * 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))))
        
    return {
        "statistic": float(stat),
        "p_value": min(1.0, max(0.0, float(p_val))),
        "w_pos": w_pos,
        "w_neg": w_neg,
        "n_effective": n
    }

def bootstrap_ci_95(sample: Union[List[float], np.ndarray],
                    n_boot: int = 10000,
                    seed: int = 42) -> Tuple[float, float]:
    """
    Computes 95% percentile bootstrap confidence interval for the sample mean.
    """
    arr = np.asarray(sample, dtype=float)
    if len(arr) == 0:
        return (0.0, 0.0)
    if len(arr) == 1:
        return (float(arr[0]), float(arr[0]))
        
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        boot_sample = rng.choice(arr, size=len(arr), replace=True)
        boot_means[i] = np.mean(boot_sample)
        
    lower = float(np.percentile(boot_means, 2.5))
    upper = float(np.percentile(boot_means, 97.5))
    return (lower, upper)

def bonferroni_holm_adjust(p_values: List[float]) -> List[float]:
    """
    Applies the Bonferroni-Holm step-down procedure to adjust a list of p-values.
    """
    m = len(p_values)
    if m == 0:
        return []
        
    indexed_p = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    
    current_max = 0.0
    for rank, (orig_idx, p_val) in enumerate(indexed_p):
        multiplier = m - rank
        adj = min(1.0, multiplier * p_val)
        current_max = max(current_max, adj)
        adjusted[orig_idx] = current_max
        
    return adjusted
