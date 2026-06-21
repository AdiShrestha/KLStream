import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
import os

FEATURES = ["log_return", "rolling_vol", "order_imbalance", "spread_bps", "volume"]

csv_path = "data/replay/replay_AAPL_20120621.csv"
if not os.path.exists(csv_path):
    print(f"Error: {csv_path} not found. Please run synthetic fallback generator first.")
    exit(1)

df = pd.read_csv(csv_path)
calm = df[df["label"] == 0]
train, holdout = train_test_split(calm, test_size=0.2, random_state=42)

clf = IsolationForest(n_estimators=100, max_samples=256, random_state=42)
clf.fit(train[FEATURES])

# sklearn's score_samples: HIGHER = more normal (opposite sign convention
# from Liu et al.'s raw s(x) formula used in Section 12's C++ code).
# Convert to the SAME convention before comparing: anomaly_score = -score_samples
holdout = holdout.copy()
holdout["sklearn_anomaly_score"] = -clf.score_samples(holdout[FEATURES])

out_dir = "data/replay"
os.makedirs(out_dir, exist_ok=True)
train[FEATURES].to_csv(os.path.join(out_dir, "isoforest_validation_train.csv"), index=False)
holdout[["log_return","rolling_vol","order_imbalance","spread_bps","volume",
         "sklearn_anomaly_score"]].to_csv(
    os.path.join(out_dir, "isoforest_validation_holdout.csv"), index=False)
print("Wrote validation holdout to data/replay/isoforest_validation_holdout.csv")
