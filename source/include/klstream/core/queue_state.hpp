#pragma once

namespace klstream {
// Close publishes EOS after producer quiescence. Cancellation never publishes EOS.
enum class QueueState { Open, Closed, Cancelled };
}
