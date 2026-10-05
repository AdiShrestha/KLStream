#pragma once

namespace klstream {
// Close publishes EOS after producer quiescence. Cancellation never publishes EOS.
// Drained represents a Closed queue that has been fully consumed. Cancelled never reports Drained.
enum class QueueState { Open, Closed, Cancelled, Drained };
}
