# Active engine contract — foundation 0.3.1

This is a correctness foundation, not a full application or a validated performance
contribution. Headers are under `source/include/klstream`, tests under `source/tests`.
No legacy results, generated academic data, trained models, pickle loaders, legacy
simulator, paper figures or claimed certificate are active dependencies.

## Ownership, capacity and progress

SPSC has exactly one producer and one consumer; requested capacity is power-of-two
at least two and usable capacity is C−1. MPMC has C usable slots. Both require
trivially copyable, default constructible and assignable values. Typed arrays start
object lifetimes in C++17; capacity validation also operates in release builds.
Destruction requires all callers to have stopped and joined. Queue close is a
publication of producer completion, after producers are quiescent. Do not race
close against producers still reserving slots: this API is not a producer-reference
counting system. `stop()` may wake blocked callers during cancellation, but does
not imply lossless EOS: join all producers/consumers before inspecting terminal
state. The one-producer operator pipeline closes each edge on EOS.

Approximate occupancy is a control observation, not an exact conservation proof.
MPMC reservations and committed payloads differ. Never use empty/approximate size
alone as global EOS. Atomic operations do not by themselves establish formal lock
freedom; the bounded MPMC algorithm can depend on a paused slot owner. No such
progress theorem is claimed. Padding is a configured layout choice, not measured
cache geometry or proof of an M3 optimization.

## Runtime and lifecycle

Each operator has one owning worker; duplicate/null registrations fail. Configure
before start; the runtime is one-shot. Operators and queues must outlive it. Workers
invoke successful initialization/shutdown exactly once and preserve exceptions.
Callbacks must return; cancellation cannot forcibly interrupt a blocking callback.
Coordinator calls are serialized and must not be invoked inside operator callbacks.
A coordinator waiting with a deadline holds the coordination mutex until it returns.

`Idle` means temporary absence of progress. `Finished` means permanent EOS after
pending outputs were delivered and downstream completion was published.
`wait_until_done(timeout)` returns false on timeout and leaves the runtime alive.
`drain(timeout)` requests that sources stop admitting new work, flush pending work,
and propagate EOS; true means all registered operators finished. A timeout is not
a successful drain. `stop()` cancels immediately and may leave queued events; it
must never be reported as a zero-loss run. Join then inspect cancellation/error
status. Worker exceptions fail the run, even if some outputs were already written.

Source generator `false` means permanent EOS. It is not a pause/retry signal.
Source throttling is explicit. Token accounting and rate changes share a mutex; no
implicit occupancy-based source pacing occurs. Research harnesses must separately
measure offered work, source delay and admission so backpressure cannot conceal
an overloaded offered stream. Legacy restart/work stealing APIs were removed.

## Operators and event identities

Map/filter/sink/running aggregate flush pending work without executing the transform
twice. Filtered IDs need explicit reason records in a research harness. Aggregation
currently shares one state across keys. Count windows are nonkeyed; a final partial
window is flushed. An aggregate output's oldest input time is metadata, not a
per-event latency observation or complete lineage. Add explicit member-ID lineage
before using aggregates in an experiment.

`EventBatch<T,Max>` retains all constituent Events, including sequence IDs and
source creation timestamps. The deadline opens at first-item receipt before target selection, including selector cost.
The target selector runs at batch start; target is checked
in [1,Max]. Batch size is bounded by the template maximum, not a secret universal
256-event assumption. A processing-time deadline requests partial readiness; scheduler delay and output
backpressure can delay publication. EOS flushes partial batches.
It is a batching primitive; it does not itself infer, emit one score per point,
measure source latency, or implement market replay. Those are future contracts.

Event times share a process steady-clock domain. `latency_ns()` rejects a future
timestamp rather than substituting zero. Event::make stamps creation before a possible pending source push, so it is
creation-to-observation time. It is not a measured admission-to-observation or
offered-to-decision interval. The research harness must log separate offered,
release and successful-admission observations. Never compare it directly with exchange wall times.

## Controller and model

Occupancy control requires an explicit grow/shrink direction, observation edge,
min/max/initial batch sizes, alpha, thresholds, gain and hysteresis ratio. The
controller is owned by one thread; concurrent telemetry must copy a synchronized
snapshot. No stability, optimality or universal feedback-sign claim is made.

Isolation Forest validates finite, nonempty training inputs with at least two
rows and positive estimator/subsample counts. Effective psi is min(requested,n).
Normalization uses exact harmonic numbers; height is ceil(log2(psi)). It selects
among actually varying features, builds a validated in-memory forest, and rejects
unfitted/nonfinite scoring. Repeated fits recreate the seeded generator. Scores
are anomaly rankings, not calibrated probabilities. The exact harmonic convention
can differ from common asymptotic implementations; compare conventions explicitly.
Tree RNG and floating arithmetic may differ across standard libraries; portable
bitwise equality is not promised. There is no disk-model loader or legacy KLIF
compatibility. Portable serialization, golden trees and reference parity are KLS-06.

## Telemetry and verification boundary

Diagnostic latency histograms compute the mean from actual nanosecond observations.
Quantiles are lower bucket boundaries in microseconds; overflow returns infinity,
not a clipped finite tail. Empty distributions are errors. Use lossless event
telemetry and offline exact quantiles for research, not this diagnostic histogram.
Counters are thread-safe but counter equality is not ID conservation. Apple QoS
requests are scheduling hints, not guaranteed P/E core pinning. GPU work is absent.

Executed on the current Mac: release correctness tests, ASan/UBSan tests, a ThreadSanitizer fixture run, and
independent compilation of 21 public headers. Tested fixtures cover queue capacity,
concurrency/unique IDs, completion/drain, partial batches, pending transforms,
exceptions, parameter rejection, overflow and small-sample model normalization.
These checks are not formal verification, exhaustive race detection,
cross-platform validation, production readiness or research performance evidence.

## Second-pass corrections and verification

Queue state distinguishes Open, Closed and Cancelled. Cancellation never reports
drained EOS, and later close cannot replace cancellation. Operators reject cancelled
input and premature output closure; a failed run cannot look like normal Finished.
Close still requires producer quiescence. Source assigns monotone sequence IDs even
when generators return Event::make; harness IDs must additionally bind run/source.
Defaults initialize event fields, and diagnostic counter overflow raises an error.

Rate changes credit elapsed time at the preceding rate. Explicit initial-clock,
consume_at and set_rate_at APIs permit deterministic budget checks; callers must
share a monotone clock domain. Rate is bounded by declared floor/nominal values;
throttle validates [0,1]. EMA starts from its first valid observation and uses one
cached raw pressure observation per update. This does not make approximate queue
occupancy an exact conservation measure. Mutex overhead must be measured in pilots.

Histogram ranks use integer fractions. Named p50/p95/p99 are exact rational ranks;
the convenience floating API uses a documented 1e-9 grid and rejects finer values.
Bucket lower bounds and infinite overflow remain diagnostic, not exact event tails.
Negative drain deadlines fail before requesting source termination. Unknown worker
statuses fail rather than looping. Cancellation still cannot interrupt a callback.

The forest retains double split thresholds, calculates height in integer arithmetic
and exposes read-only tree nodes/sample counts. Fit invalidates inspection references;
this is not a stable disk format. A separate Python oracle reconstructs fixture
partitions and path scores. This establishes limited independent arithmetic checks,
not EIF equivalence, sklearn compatibility or market validity. Portable export and
broader reference comparison remain KLS-06.

Read docs/audit/SECOND_PASS.md and second_pass_verification.json for current repairs,
executed commands, raw log hashes and residual limits. ASan/UBSan and TSan are separate
builds. Tests use explicitly declared fixtures. No benchmark or publication result
is accepted by the engine test executable.
