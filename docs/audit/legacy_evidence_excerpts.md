# Legacy evidence excerpts

These excerpts are historical code evidence. They are not active implementation or valid research results. Legacy source hashes are in the adjacent inventories.

## `source/experiments/preprocessing/download_sample.py`

```text
...
28:     return h.hexdigest()
29: 
30: def generate_academic_sample_fixture(dest_dir: Path):
31:     """
32:     Generates a deterministic Level-1 LOBSTER academic benchmark sample fixture.
...
84:     if not msg_path.exists() or not ob_path.exists():
85:         print("Generating deterministic academic sample fixture...")
86:         generate_academic_sample_fixture(SAMPLE_DIR)
87:     
88:     # Compute SHA-256 for all files in SAMPLE_DIR
...
102: 
103:     provenance = {
104:         "dataset_name": "LOBSTER Open Academic Benchmark Sample (AMZN 2012-06-21)",
105:         "source_url": SAMPLE_URL,
106:         "governing_policy": "DL-008 (Zero-Cost Academic Sample & Synthetic Order-Book Policy)",
107:         "intended_use": "Non-commercial academic systems evaluation and anomaly scoring benchmark",
108:         "retrieval_date": "2026-08-26",
109:         "files": files_info
110:     }
```

## `source/experiments/run_full_matrix.py`

```text
...
77:                       model,
78:                       tau: float,
79:                       t_fixed_ns: float = 500.0,
80:                       t_point_ns: float = 50.0) -> Dict[str, Any]:
81:     total_events = len(records)
...
95:     while i < total_events:
96:         vol = float(records[i].get("volume", 50.0) or 50.0)
97:         occupancy = min(1.0, current_queue_depth / 100.0 + (vol / 500.0) * 0.4)
98:         if occupancy >= 0.80:
99:             backpressure_count += 1
...
102:         batch_w = max(1, min(target_w, total_events - i))
103:         
104:         t_q = occupancy * 5000.0 # ns
105:         t_freshness = (batch_w - 1.0) * 150.0 # ns
106:         t_exec = (t_fixed_ns / batch_w) + t_point_ns
107:         
108:         for _ in range(batch_w):
...
126:             "events_ingested": total_events,
127:             "events_processed": total_events,
128:             "events_dropped": 0,
129:             "backpressure_activations": backpressure_count,
130:             "max_queue_occupancy": max_queue_depth
...
222:                 "events_ingested": run_result["event_accounting"]["events_ingested"],
223:                 "events_processed": run_result["event_accounting"]["events_processed"],
224:                 "events_dropped": run_result["event_accounting"]["events_dropped"],
225:                 "auc_roc": run_result["detection_metrics"]["auc_roc"],
226:                 "p99_latency_ns": run_result["latency_summary_ns"]["end_to_end_latency"]["p99_ns"],
...
237:         "total_runs": len(executed_runs),
238:         "total_events_processed": sum(r["events_processed"] for r in executed_runs),
239:         "total_events_dropped": sum(r["events_dropped"] for r in executed_runs),
240:         "execution_duration_sec": round(time.time() - start_time, 2),
241:         "runs": executed_runs
```

## `source/experiments/runners/experiment_runner.py`

```text
...
53:     end_row = None
54:     
55:     if manifest_path and Path(manifest_path).exists():
56:         with open(manifest_path, "r") as f:
57:             manifest = json.load(f)
...
111:     # Model inference scores
112:     # s(x) = 0.5 - decision_function(x) / 2.0
113:     scores = 0.5 - model.decision_function(X[:total_events])
114:     
115:     t_q_list = []
...
156:     pr_auc = compute_pr_auc(y[:total_events], scores)
157:     
158:     tau = tune_validation_threshold(y[:total_events], scores, target_fpr=0.05)
159:     cls_metrics = compute_binary_classification_metrics(y[:total_events], scores, threshold=tau)
160:     
...
193:     
194:     # Train Isolation Forest on normal background slice
195:     normal_mask = (y == 0)
196:     X_train = X[normal_mask] if np.sum(normal_mask) > 50 else X
197:     model = IsolationForest(n_estimators=100, max_samples=min(256, len(X_train)), random_state=42)
198:     model.fit(X_train)
199:     
200:     max_events = 500 if dry_run else None
```

## `source/experiments/plot_figures.py`

```text
...
130:     plt.close(fig)
131: 
132: def generate_figure_4_roc_pr(out_dir: Path):
133:     """Figure 4: Pointwise ROC and Precision-Recall Curves."""
134:     fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
...
136:     # Representative ROC curve
137:     fpr = np.linspace(0, 1, 100)
138:     tpr_normal = fpr ** 0.35
139:     ax1.plot(fpr, tpr_normal, color="#9b59b6", linewidth=2.2, label="Adaptive EMA (AUC = 0.85)")
140:     ax1.plot(fpr, fpr, linestyle="--", color="gray", label="Chance (AUC = 0.50)")
141:     ax1.set_xlabel("False Positive Rate (FPR)", fontsize=10)
142:     ax1.set_ylabel("True Positive Rate (TPR)", fontsize=10)
...
148:     recall = np.linspace(0, 1, 100)
149:     precision = np.clip(1.0 - 0.7 * (recall ** 0.5), 0.1, 1.0)
150:     ax2.plot(recall, precision, color="#e67e22", linewidth=2.2, label="Adaptive EMA (PR-AUC = 0.68)")
151:     ax2.axhline(0.05, linestyle="--", color="gray", label="Base Anomaly Rate (5%)")
152:     ax2.set_xlabel("Recall", fontsize=10)
153:     ax2.set_ylabel("Precision", fontsize=10)
```

## `source/experiments/evaluate_falsification.py`

```text
...
6: - SVI-003: Quantitative pre-registered falsification evaluation
7: - SVI-004: Cryptographic pre-registration hash verification
8: - MAR-7, MAR-X6: Anti-HARKing protocol verification
9: """
10: 
...
53:     f500 = p99_tests["fixed_w500"]
54:     c1_margin = (f500["comparator_mean"] - f500["adaptive_mean"]) / f500["comparator_mean"]
55:     c1_p = f500["raw_p_value"]
56:     c1_delta = abs(f500["cliffs_delta"])
57:     c1_passed = (c1_margin >= 0.15) and (c1_p < 0.05) and (c1_delta >= 0.330)
58:     verdicts["claim_1"] = {
59:         "claim_title": "Tail Latency Reduction vs Fixed-500",
60:         "verdict": "SUPPORTED" if c1_passed else "FALSIFIED",
61:         "target_margin_pct": 15.0,
62:         "empirical_margin_pct": round(c1_margin * 100, 2),
...
71:     unadapt = auc_tests["unadaptive_w1"]
72:     c2_diff = unadapt["comparator_mean"] - unadapt["adaptive_mean"]
73:     c2_passed = (c2_diff <= 0.03)
74:     verdicts["claim_2"] = {
75:         "claim_title": "Pointwise Detection Fidelity Invariance vs Unadaptive W=1",
76:         "verdict": "SUPPORTED" if c2_passed else "FALSIFIED",
77:         "target_max_auc_drop": 0.03,
78:         "empirical_auc_diff": round(c2_diff, 6),
...
85:     shuffled = p99_tests["shuffled_control"]
86:     c3_margin = (shuffled["comparator_mean"] - shuffled["adaptive_mean"]) / shuffled["comparator_mean"]
87:     c3_p = shuffled["raw_p_value"]
88:     c3_delta = abs(shuffled["cliffs_delta"])
89:     c3_passed = (c3_margin >= 0.10) and (c3_p < 0.05) and (c3_delta >= 0.330)
90:     verdicts["claim_3"] = {
91:         "claim_title": "Causal Superiority over Shuffled-Occupancy Control",
92:         "verdict": "SUPPORTED" if c3_passed else "FALSIFIED",
93:         "target_margin_pct": 10.0,
94:         "empirical_margin_pct": round(c3_margin * 100, 2),
...
125: | Claim | Objective & Comparison | Pre-Registered Falsification Bound | Empirical Finding | Verdict |
126: |---|---|---|---|---|
127: | **Claim 1** | Tail Latency vs Fixed-500 | Margin $< 15\%$ OR $p \ge 0.05$ OR $\delta < 0.330$ | **+{c1_margin*100:.2f}%** reduction ($p={c1_p:.4f}, \delta={c1_delta:.3f}$) | **SUPPORTED** |
128: | **Claim 2** | Detection Fidelity vs Unadaptive $W=1$ | AUC drop $> 0.03$ AND $p < 0.05$ | **0.0000** AUC drop (Invariance maintained) | **SUPPORTED** |
129: | **Claim 3** | Causal Feedback vs Shuffled Control | Margin $< 10\%$ OR $p \ge 0.05$ OR $\delta < 0.330$ | **+{c3_margin*100:.2f}%** reduction ($p={c3_p:.4f}, \delta={c3_delta:.3f}$) | **SUPPORTED** |
130: 
131: ---
...
141:   - Paired Wilcoxon p-value: `{c1_p:.4f}` ($< 0.05$)
142:   - Non-parametric Effect Size (Cliff's $\delta$): `{c1_delta:.3f}` (Large effect $\ge 0.330$)
143: - **Formal Verdict:** **SUPPORTED**
144: 
145: ---
...
151:   - Unadaptive ($W=1$) AUC-ROC: `{unadapt['comparator_mean']:.4f}`
152:   - Observed Difference: `{c2_diff:.4f}` (Zero degradation)
153: - **Formal Verdict:** **SUPPORTED**
154: 
155: ---
...
163:   - Paired Wilcoxon p-value: `{c3_p:.4f}` ($< 0.05$)
164:   - Non-parametric Effect Size (Cliff's $\delta$): `{c3_delta:.3f}` (Large effect $\ge 0.330$)
165: - **Formal Verdict:** **SUPPORTED**
166: 
167: ---
168: 
169: ## 3. Anti-HARKing Conclusion
170: All pre-registered decision criteria were evaluated strictly and transparently. No thresholds or metric definitions were modified post-hoc.
171: """
```

## `source/experiments/run_sensitivity.py`

```text
...
29: W_MAX_GRID = [100, 250, 500, 1000]
30: 
31: def simulate_step_load_shock(alpha: float = 0.2, deadband: float = 0.05, w_min: int = 10, w_max: int = 500) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
32:     """
33:     Simulates step-load surge (10x arrival shock) to evaluate controller transient response and stability.
...
46:     for t in range(total_steps):
47:         if t < 1000:
48:             target_rho = 0.10 + rng.normal(0, 0.02)
49:         elif t < 2000:
50:             target_rho = 0.90 + rng.normal(0, 0.02)
51:         else:
52:             target_rho = 0.10 + rng.normal(0, 0.02)
53:             
54:         rho = float(np.clip(target_rho, 0.0, 1.0))
55:         w = controller.get_window_size(rho)
56:         
...
80:     target_90 = w_min + 0.90 * (peak_w - w_min)
81:     
82:     rise_steps = 0
83:     for idx in range(surge_start, total_steps):
84:         if w_series[idx] >= target_90:
85:             rise_steps = idx - surge_start
86:             break
87:             
...
92:         "w_max": w_max,
93:         "peak_window_size": int(peak_w),
94:         "rise_time_steps": int(rise_steps),
95:         "chattering_index_baseline": chattering_baseline,
96:         "chattering_index_surge": chattering_surge,
97:         "chattering_index_recovery": chattering_recovery,
98:         "chattering_free": bool(chattering_surge < 2.0 and chattering_baseline < 1.0),
99:         "limit_cycle_detected": False
100:     }
101:     
```

## `source/experiments/preprocessing/preprocess.py`

```text
...
26: REQUIRED_PROCESSED_COLUMNS = [
27:     "seq", "timestamp_ns", "bid_px", "ask_px", "bid_sz", "ask_sz",
28:     "mid_price", "spread", "spread_bps", "log_return", "rolling_vol",
29:     "order_imbalance", "microprice", "volume", "is_anomaly", "anomaly_type", "is_burst_period"
30: ]
...
136:                 "bid_sz": bid_sz,
137:                 "ask_sz": ask_sz,
138:                 "mid_price": round(mid, 4),
139:                 "spread": round(spread, 4),
140:                 "spread_bps": round(spread_bps, 4),
141:                 "log_return": round(log_ret, 8),
142:                 "rolling_vol": round(vol_ema, 8),
143:                 "order_imbalance": round(imbalance, 6),
144:                 "microprice": round(microprice, 4),
145:                 "volume": round(vol_log, 6),
146:                 "is_anomaly": is_anom,
147:                 "anomaly_type": anom_type,
...
167:         vol_ema = 0.0
168:         
169:         for idx, (m_row, o_row) in enumerate(zip(m_reader, o_reader)):
170:             if len(m_row) < 6 or len(o_row) < 4:
171:                 raise ValueError(f"Incomplete row at index {idx}")
...
173:             t_sec = float(m_row[0])
174:             ts_ns = int(t_sec * 1_000_000_000)
175:             seq = int(m_row[2])
176:             
177:             ask_px = float(o_row[0]) / 100.0 # Convert ticks/cents to dollars
178:             ask_sz = int(o_row[1])
179:             bid_px = float(o_row[2]) / 100.0
180:             bid_sz = int(o_row[3])
181:             
...
211:                 "bid_sz": bid_sz,
212:                 "ask_sz": ask_sz,
213:                 "mid_price": round(mid, 4),
214:                 "spread": round(spread, 4),
215:                 "spread_bps": round(spread_bps, 4),
216:                 "log_return": round(log_ret, 8),
217:                 "rolling_vol": round(vol_ema, 8),
218:                 "order_imbalance": round(imbalance, 6),
219:                 "microprice": round(microprice, 4),
220:                 "volume": round(vol_log, 6),
221:                 "is_anomaly": 0,
222:                 "anomaly_type": "none",
```

## `source/include/klstream/core/worker.hpp`

```text
...
45: 
46:     void drain() {
47:         draining_.store(true, std::memory_order_release);
48:     }
49: 
...
78:             bool any_progress = false;
79:             for (auto* op : operators_) {
80:                 OpStatus s = op->tick();
81:                 if (s == OpStatus::Processed) any_progress = true;
82:             }
83:             if (!any_progress) {
84:                 if (draining_.load(std::memory_order_relaxed)) {
85:                     break;
86:                 }
...
104: 
105:         // Residual queue drain before shutdown
106:         constexpr int DRAIN_PASSES = 1000;
107:         for (int pass = 0; pass < DRAIN_PASSES; ++pass) {
108:             bool made_progress = false;
109:             for (auto* op : operators_) {
110:                 if (op->tick() == OpStatus::Processed) {
111:                     made_progress = true;
112:                 }
...
124:     CoreAffinity             affinity_{CoreAffinity::Any};
125:     std::atomic<bool>        running_{false};
126:     std::atomic<bool>        draining_{false};
127:     bool                     stopped_{false};
128:     std::mutex               stop_mutex_;
```

## `source/include/klstream/core/runtime.hpp`

```text
...
93:                 std::to_string(worker_id));
94:         }
95:         op->id = next_op_id_++;
96:         if (affinity != CoreAffinity::Any) {
97:             workers_[worker_id]->set_affinity(affinity);
...
154: 
155:         // Stop workers in reverse order to ensure downstream drains upstream
156:         for (auto it = workers_.rbegin(); it != workers_.rend(); ++it) {
157:             (*it)->stop();
158:         }
```

## `source/include/klstream/model/isolation_forest.hpp`

```text
...
133:     void build(std::vector<Point> points, int height_limit, std::mt19937& rng) {
134:         nodes_.clear();
135:         nodes_.reserve(2 * points.size());
136:         root_ = build_node(points, 0, height_limit, rng);
137:     }
...
171:     }
172: 
173:     void deserialize_payload(const std::uint8_t*& ptr, const std::uint8_t* end) {
174:         if (ptr + sizeof(std::uint64_t) > end) {
175:             throw std::runtime_error("Corrupted payload: unexpected EOF reading node count");
...
199:                    std::mt19937& rng) {
200:         Node n;
201:         if (depth >= height_limit || points.size() <= 1) {
202:             n.size_at_leaf = static_cast<int>(points.size());
203:             nodes_.push_back(n);
204:             return static_cast<int>(nodes_.size()) - 1;
...
208:         float lo = 0.0f, hi = 0.0f;
209:         std::uniform_int_distribution<int> feat_dist(0, static_cast<int>(D) - 1);
210:         for (int attempt = 0; attempt < 8; ++attempt) {
211:             int f = feat_dist(rng);
212:             float mn = std::numeric_limits<float>::max();
...
219:         }
220:         if (feature == -1) {
221:             n.size_at_leaf = static_cast<int>(points.size());
222:             nodes_.push_back(n);
223:             return static_cast<int>(nodes_.size()) - 1;
...
228: 
229:         std::vector<Point> left_pts, right_pts;
230:         left_pts.reserve(points.size());
231:         right_pts.reserve(points.size());
232:         for (const auto& p : points) {
233:             (p[feature] < split ? left_pts : right_pts).push_back(p);
234:         }
235:         if (left_pts.empty() || right_pts.empty()) {
236:             n.size_at_leaf = static_cast<int>(points.size());
237:             nodes_.push_back(n);
238:             return static_cast<int>(nodes_.size()) - 1;
...
276:             std::vector<Point> sample;
277:             sample.reserve(psi_);
278:             std::vector<std::size_t> indices(points.size());
279:             for (std::size_t i = 0; i < indices.size(); ++i) indices[i] = i;
280:             std::shuffle(indices.begin(), indices.end(), rng_);
281:             int take = std::min(psi_, static_cast<int>(points.size()));
282:             for (int i = 0; i < take; ++i) sample.push_back(points[indices[i]]);
283: 
...
286:             trees_.push_back(std::move(tree));
287:         }
288:         c_psi_ = IsolationTree<D>::c_factor(psi_);
289:     }
290: 
291:     [[nodiscard]] double anomaly_score(const Point& x) const {
292:         if (trees_.empty() || c_psi_ <= 0.0) return 0.5;
293:         double total = 0.0;
294:         for (const auto& tree : trees_) total += tree.path_length(x);
...
313:         header.num_features   = static_cast<std::uint32_t>(D);
314:         header.payload_size   = static_cast<std::uint64_t>(payload.size());
315:         header.c_psi          = c_psi_;
316: 
317:         detail::sha256(payload.data(), payload.size(), header.checksum);
...
373:         for (std::uint32_t i = 0; i < header.num_trees; ++i) {
374:             IsolationTree<D> tree;
375:             tree.deserialize_payload(ptr, end);
376:             trees_.push_back(std::move(tree));
377:         }
...
379:         n_estimators_ = static_cast<int>(header.num_trees);
380:         psi_          = static_cast<int>(header.subsample_size);
381:         c_psi_        = header.c_psi;
382:     }
383: 
```

## `source/include/klstream/window/adaptive_window_op.hpp`

```text
...
33:         , shrink_factor_(std::clamp(shrink_factor, 0.01, 0.99))
34:         , grow_factor_(std::max(1.01, grow_factor))
35:         , current_w_(w_max)
36:     {}
37: 
38:     std::uint32_t update(double ema_occupancy) {
39:         if (ema_occupancy > occ_high_) {
40:             auto next_w = static_cast<std::uint32_t>(std::floor(current_w_ * shrink_factor_));
41:             current_w_ = std::clamp(next_w, w_min_, w_max_);
...
61:     void track_direction(double ema_occupancy) {
62:         int dir = 0;
63:         if (ema_occupancy > occ_high_) dir = -1;
64:         else if (ema_occupancy < occ_low_) dir = 1;
65:         else return;
...
109:         }
110: 
111:         if (buffer_.count == 0) {
112:             auto start_t = std::chrono::steady_clock::now();
113:             tracker_.update();
...
135: 
136:         Event<WindowBatch> out_ev;
137:         out_ev.timestamp_ns = in_ev.timestamp_ns;
138:         out_ev.key  = 0;
139:         out_ev.seq  = in_ev.seq;
```

## `source/experiments/baselines/ema_window_controller.py`

```text
...
13:         self.deadband = float(deadband)
14:         self.target_occupancy = float(target_occupancy)
15:         self.current_w = int(w_min)
16:         self.ema_occ = 0.0
17:         self.initialized = False
...
30:             norm = (self.ema_occ - self.target_occupancy) / max(self.target_occupancy, 1.0 - self.target_occupancy)
31:             step = int(norm * (self.w_max - self.w_min) * 0.25)
32:             self.current_w = max(self.w_min, min(self.w_max, self.current_w + step))
33: 
34:         return self.current_w
35: 
36:     def reset(self) -> None:
37:         self.current_w = self.w_min
38:         self.ema_occ = 0.0
39:         self.initialized = False
```

## `source/apps/adaptive_window/main.cpp`

```text
...
35:     std::string architecture = "adaptive";   // fixed | datadriven | adaptive
36:     std::string replay_csv   = "data/replay/replay_AAPL_20120621.csv";
37:     std::string forest_path  = "data/forest.bin";
38:     std::string out_csv      = "results/raw/run.csv";
39:     int         duration_sec = 60;
...
52:         if (val("--architecture=")) architecture = a.substr(15);
53:         else if (val("--replay=")) replay_csv = a.substr(9);
54:         else if (val("--forest=")) forest_path = a.substr(9);
55:         else if (val("--out=")) out_csv = a.substr(6);
56:         else if (val("--duration=")) duration_sec = std::stoi(a.substr(11));
...
63:     }
64: 
65:     auto forest = load_forest(forest_path);
66:     auto rows   = load_replay_csv(replay_csv);
67: 
...
87:     AdaptiveWindowOp*    adaptive_ptr = nullptr;   // kept for occupancy logging below
88: 
89:     if (architecture == "fixed") {
90:         auto* op = new TumblingCountWindow<FeatureVector, WindowBatch>(
91:             "fixed_window", &q_src_feat, &q_win_inf, 128,
...
96:             });
97:         window_op.reset(op);
98:     } else if (architecture == "datadriven") {
99:         window_op = std::make_unique<DataDrivenWindowOp>(
100:             "data_driven_window", &q_src_feat, &q_win_inf);
...
142:             auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - start).count();
143:             log << ms << "," 
144:                 << adaptive_ptr->controller().current() << ","
145:                 << q_win_inf.occupancy() << ","
146:                 << q_win_inf.occupancy() * q_win_inf.capacity() << "\n";
147:         }
148:     });
...
159:                   << adaptive_ptr->controller().direction_changes() << "\n";
160:         std::cout << "Mean Controller Overhead: " << adaptive_ptr->mean_overhead_ns() << " ns/call\n";
161:     } else if (architecture == "datadriven" && window_op) {
162:         auto* dd_ptr = static_cast<DataDrivenWindowOp*>(window_op.get());
163:         std::cout << "Mean Controller Overhead: " << dd_ptr->mean_overhead_ns() << " ns/call\n";
```

## `scripts/verify_cert_independent.py`

```text
...
4: def main():
5:     # 69 total contracts across chunks 01-09 (C09-01..C09-05 complete at certification time)
6:     print(json.dumps({"total_contracts_examined": 69}))
7: if __name__ == "__main__":
8:     main()
```

## `scripts/verify_bundle_independent.py`

```text
...
4: def main():
5:     # Canonical: 67 artifacts in the reproduction archive
6:     print(json.dumps({"extracted_file_count": 67}))
7: if __name__ == "__main__":
8:     main()
```

## `paper/verify_eval_independent.py`

```text
...
7: def main():
8:     # Canonical Claim 1 empirical P99 latency reduction percentage (98.02%)
9:     print(json.dumps({"claim_1_margin_pct": 98.02}))
10: 
11: if __name__ == "__main__":
```

## `source/benchmarks/verify_e2e_independent.py`

```text
...
7: def main():
8:     # Canonical INV-007 invariant requirement: 0 dropped events
9:     print(json.dumps({"events_dropped": 0}))
10: 
11: if __name__ == "__main__":
```

## `source/experiments/analysis/compute_metrics.py`

```text
...
25: def pa_k_f1(predictions_df, ground_truth_df, threshold, k_fraction, segments):
26:     """segments: list of (start_seq, end_seq) ground-truth anomaly segments
27:        from injection_log.csv. Implements Kim et al. (AAAI 2022) PA%K:
28:        a segment counts as detected only if at least k_fraction of its
29:        ticks are individually flagged — NOT just one."""
...
92:         return float(rp), float(rr), float(rf1)
93: 
94:     except ImportError:
95:         # Manual fallback: simplified overlap-based range metrics
96:         # Recall: per real segment, what fraction of its ticks were detected?
...
131:     """Latency-Bounded Accuracy (LBA@T) F1 score.
132: 
133:     Discards any detection whose latency_ns exceeds the SLA bound before
134:     computing F1.  Only detections that arrive in time are considered.
135: 
...
147:     baseline's load-blindness, and worth stating explicitly in the paper.
148:     """
149:     valid_preds = predictions_df[predictions_df["latency_ns"] <= max_latency_ms * 1_000_000]
150:     return tick_level_f1(valid_preds, ground_truth_df, threshold)
151: 
...
184:         sys.exit(1)
185:         
186:     threshold = results["max_score"].quantile(0.95)
187:     print(f"Using threshold (95th percentile): {threshold:.4f}")
188:     
...
205:         
206:     p20, r20, f1_20 = pa_k_f1(results, gt, threshold, 0.20, segments)
207:     print(f"PA%20 F1: Precision={p20:.4f}, Recall={r20:.4f}, F1={f1_20:.4f}")
208:     
209:     p50, r50, f1_50 = pa_k_f1(results, gt, threshold, 0.50, segments)
210:     print(f"PA%50 F1:   Precision={p50:.4f}, Recall={r50:.4f}, F1={f1_50:.4f}")
211: 
212:     # LBA thresholds grounded in observed latency distribution (~P95=17-70ms)
```

