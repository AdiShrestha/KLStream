import pandas as pd
from scipy.stats import spearmanr
import sys

def main():
    try:
        df_sk = pd.read_csv("data/replay/isoforest_validation_holdout.csv")
        df_cpp = pd.read_csv("data/replay/isoforest_validation_cpp_scores.csv")
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        sys.exit(1)

    if len(df_sk) != len(df_cpp):
        print(f"Row count mismatch! Sklearn: {len(df_sk)}, C++: {len(df_cpp)}")
        sys.exit(1)

    sk_scores = df_sk["sklearn_anomaly_score"].values
    cpp_scores = df_cpp["cpp_score"].values

    corr, p_value = spearmanr(sk_scores, cpp_scores)
    
    print(f"Spearman Correlation between Sklearn and Native C++ Isolation Forest: {corr:.4f}")
    if corr >= 0.85:
        print("✅ SUCCESS: Correlation >= 0.85. The native C++ implementation matches sklearn sufficiently.")
    else:
        print("❌ FAILURE: Correlation < 0.85. The native C++ implementation diverges significantly.")

if __name__ == "__main__":
    main()
