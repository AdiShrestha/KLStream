# Formal Feature Specification Document — Contract KLS-05

**Scope:** Real-Time Streaming Anomaly Detection Feature Formulation for High-Frequency Crypto Tick Trades  
**Status:** ACCEPTED / CAUSAL_SPECIFICATION  
**Author:** KLStream Engineering  
**Standard:** C++17 Streaming Ingestion & Python Standard Library Causal Parsing  

---

## 1. Context & Ingress Schema

KLStream ingests high-frequency tick trade streams sourced from the Binance Public Data Archive (spot execution on `BTCUSDT`). Each raw trade observation is an execution record matching the canonical Binance schema:

| Raw Column | Type | Description | Invariant & Units |
|---|---|---|---|
| `id` | `uint64` | Monotonically increasing exchange trade identifier | Positive integer, strictly ordered per stream |
| `price` | `float64` | Asset execution price | Positive finite float ($p > 0$), USDT |
| `qty` | `float64` | Base asset execution volume | Positive finite float ($q > 0$), BTC |
| `quote_qty` | `float64` | Quote asset transaction amount ($p \times q$) | Positive finite float, USDT |
| `time` | `uint64` | Exchange execution timestamp in epoch milliseconds | Monotonic non-decreasing ($t_i \ge t_{i-1}$), ms |
| `is_buyer_maker` | `bool` | Aggressor order direction flag | `true` = seller is taker (market sell), `false` = buyer is taker (market buy) |
| `is_best_match` | `bool` | Optimal matching flag | Boolean metadata flag |

---

## 2. Mathematical Feature Definitions

For trade event $i \ge 0$, the causal feature vector $\mathbf{x}_i \in \mathbb{R}^7$ is defined by the following mathematical equations, physical units, raw dependencies, and boundary initializations:

### Feature 1: `price` ($x_{i, 1}$)
- **Equation:**
  $$x_{i, \text{price}} = p_i$$
- **Physical Units:** USDT (US Dollar Tether).
- **Raw Dependencies:** Raw column `price`.
- **Domain & Bounds:** $p_i \in (0, \infty)$, finite IEEE 754 float.
- **State Initialization:** Independent pointwise feature. No temporal state dependency.

---

### Feature 2: `qty` ($x_{i, 2}$)
- **Equation:**
  $$x_{i, \text{qty}} = q_i$$
- **Physical Units:** BTC (Bitcoin base volume).
- **Raw Dependencies:** Raw column `qty`.
- **Domain & Bounds:** $q_i \in (0, \infty)$, finite IEEE 754 float.
- **State Initialization:** Independent pointwise feature. No temporal state dependency.

---

### Feature 3: `quote_qty` ($x_{i, 3}$)
- **Equation:**
  $$x_{i, \text{quote\_qty}} = p_i \times q_i$$
- **Physical Units:** USDT (Total executed nominal value).
- **Raw Dependencies:** Raw columns `price`, `qty` (or direct raw column `quote_qty`).
- **Domain & Bounds:** $x_{i, \text{quote\_qty}} \in (0, \infty)$, finite IEEE 754 float.
- **State Initialization:** Independent pointwise feature. No temporal state dependency.

---

### Feature 4: `is_buyer_maker` ($x_{i, 4}$)
- **Equation:**
  $$x_{i, \text{is\_buyer\_maker}} = \begin{cases} 1.0 & \text{if } \text{is\_buyer\_maker} = \text{true} \\ 0.0 & \text{if } \text{is\_buyer\_maker} = \text{false} \end{cases}$$
- **Physical Units:** Dimensionless indicator flag $\in \{0.0, 1.0\}$.
- **Raw Dependencies:** Raw column `is_buyer_maker`.
- **Domain & Bounds:** Discrete binary float $\in \{0.0, 1.0\}$.
- **State Initialization:** Independent pointwise feature. No temporal state dependency.

---

### Feature 5: `interarrival_ms` ($x_{i, 5}$)
- **Equation:**
  $$\Delta t_i = \begin{cases} 0.0 & \text{if } i = 0 \\ t_i - t_{i-1} & \text{if } i > 0 \end{cases}$$
- **Physical Units:** Milliseconds (ms).
- **Raw Dependencies:** Raw column `time` of current event $i$ and antecedent event $i-1$.
- **Domain & Bounds:** $\Delta t_i \in [0.0, \infty)$, finite non-negative float.
- **State Initialization:** For the initial event $i = 0$, state is initialized as $t_{-1} := t_0$, yielding $\Delta t_0 = 0.0\,\text{ms}$. Non-monotonic timestamps ($t_i < t_{i-1}$) trigger fail-closed parse rejection.

---

### Feature 6: `log_return` ($x_{i, 6}$)
- **Equation:**
  $$r_i = \begin{cases} 0.0 & \text{if } i = 0 \\ \ln\left(\frac{p_i}{p_{i-1}}\right) & \text{if } i > 0 \end{cases}$$
- **Physical Units:** Dimensionless log price ratio (log return).
- **Raw Dependencies:** Raw column `price` of current event $i$ and antecedent event $i-1$.
- **Domain & Bounds:** $r_i \in (-\infty, \infty)$, finite float. Under stationary trading, typical values span $[-0.05, +0.05]$.
- **State Initialization:** For the initial event $i = 0$, state is initialized as $p_{-1} := p_0$, yielding $r_0 = \ln(1.0) = 0.0$.

---

### Feature 7: `trade_flow` ($x_{i, 7}$)
- **Equation:**
  $$V_{\text{flow}, i} = q_i \times (1.0 - 2.0 \times x_{i, \text{is\_buyer\_maker}})$$
  Equivalently:
  $$V_{\text{flow}, i} = \begin{cases} +q_i & \text{if } \text{is\_buyer\_maker} = \text{false} \quad (\text{Buyer is taker, market buy / aggressive inflow}) \\ -q_i & \text{if } \text{is\_buyer\_maker} = \text{true} \quad (\text{Seller is taker, market sell / aggressive outflow}) \end{cases}$$
- **Physical Units:** BTC (Signed order flow volume).
- **Raw Dependencies:** Raw columns `qty`, `is_buyer_maker`.
- **Domain & Bounds:** $V_{\text{flow}, i} \in (-\infty, \infty) \setminus \{0\}$, with $|V_{\text{flow}, i}| = q_i$.
- **State Initialization:** Pointwise execution direction calculation. No multi-event temporal memory required.

---

## 3. Causal Invariants & Future-Mutation Invariance

### Principle of Strict Causal Invariance:
Let $S = (e_0, e_1, \dots, e_N)$ be a sequence of raw trade observations, and let $\mathcal{F}(S) = (\mathbf{x}_0, \mathbf{x}_1, \dots, \mathbf{x}_N)$ be the derived sequence of feature vectors.

For any index $i \in [0, N]$:
1. **Past-Only Dependency:** Feature vector $\mathbf{x}_i$ is a pure mathematical function of $(e_0, e_1, \dots, e_i)$.
2. **Future Mutation Invariance:** If any future raw events $e_k$ for $k > i$ are modified, mutated, replaced, or deleted, the computed feature vector $\mathbf{x}_j$ for all antecedent indices $j \le i$ **must remain strictly bitwise identical**:
   $$\forall k > i, \quad \frac{\partial \mathbf{x}_j}{\partial e_k} = \mathbf{0} \quad (\forall j \le i)$$
3. **No Forward Peeking / Window Leakage:** No centering, global z-score normalization, forward moving averages, future price lookaheads, or end-of-batch backward adjustments are permitted.

---

## 4. Malformed Input & Boundary Rejection Rules

The parser enforces strict fail-closed validation rules. Any input violating the following criteria must trigger immediate rejection (`CausalParseError`):

1. **Non-Finite Values:** Any row containing `NaN`, `+Inf`, or `-Inf` in `price`, `qty`, `quote_qty`, or `time` is rejected immediately.
2. **Non-Positive Prices or Quantities:** Any trade with $p \le 0.0$ or $q \le 0.0$ is invalid and rejected.
3. **Non-Monotonic Exchange Timestamps:** Any trade record whose exchange timestamp retrogresses ($t_i < t_{i-1}$) is rejected as a sequence anomaly.
4. **Malformed Column Layouts:** Any CSV record containing fewer than 6 columns or unparseable float/integer syntax is rejected.

---

## 5. Deterministic Identity Join Specification

Raw archive records are deterministically joined to canonical cohort sample IDs according to:
$$\text{sample\_id} = \text{"t\_" } + \text{YYYYMMDD} + \text{"\_" } + \text{trade\_id}_{07d}$$
For example:
- Day: `2017-08-17`
- Raw trade ID: `8660`
- Sample ID: `t_20170817_0008660`

This ensures a deterministic, lossless 1-to-1 join between provider source records and evaluation cohorts without floating-point identity loss or mutable identifier confusion.
