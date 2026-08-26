import pandas as pd
from scipy.stats import spearmanr
import sys

def main():
    try:
        sklearn_df = pd.read_csv("data/replay/isoforest_validation_holdout.csv")
        cpp_df = pd.read_csv("data/replay/isoforest_validation_cpp_scores.csv")
    except Exception as e:
        print(f"Error loading CSVs: {e}")
        sys.exit(1)

    if len(sklearn_df) != len(cpp_df):
        print(f"Row count mismatch: sklearn {len(sklearn_df)}, cpp {len(cpp_df)}")
        sys.exit(1)

    spearman, pval = spearmanr(sklearn_df["sklearn_anomaly_score"], cpp_df["cpp_score"])
    print(f"Spearman rank correlation: {spearman:.4f}")
    
    if spearman >= 0.85:
        print("PASS (>= 0.85)")
        sys.exit(0)
    else:
        print("FAIL (< 0.85)")
        sys.exit(1)

if __name__ == "__main__":
    main()
