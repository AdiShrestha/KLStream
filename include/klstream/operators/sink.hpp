#pragma once

/**
 * @file sink.hpp
 * @brief Sink operator implementations
 */

#include <iostream>
#include <fstream>
#include <functional>
#include <atomic>
#include <mutex>

#include "klstream/core/operator.hpp"

namespace klstream {

/**
 * @brief Console output sink
 */
class ConsoleSink : public SinkOperator {
public:
    struct Config {
        std::string prefix;
        bool show_timestamp{false};
        bool show_key{false};
    };
    
    explicit ConsoleSink(std::string name, Config config = {})
        : SinkOperator(std::move(name))
        , config_(std::move(config)) {}
    
    void consume(const Event& event) override {
        std::lock_guard<std::mutex> lock(mutex_);
        
        if (!config_.prefix.empty()) {
            std::cout << config_.prefix << ": ";
        }
        
        if (config_.show_key && event.key()) {
            std::cout << "[key=" << *event.key() << "] ";
        }
        
        std::visit([](const auto& value) {
            using T = std::decay_t<decltype(value)>;
            if constexpr (std::is_same_v<T, std::monostate>) {
                std::cout << "(empty)";
            } else if constexpr (std::is_same_v<T, std::int64_t>) {
                std::cout << value;
            } else if constexpr (std::is_same_v<T, double>) {
                std::cout << value;
            } else if constexpr (std::is_same_v<T, std::string>) {
                std::cout << value;
            } else if constexpr (std::is_same_v<T, Blob>) {
                std::cout << "(blob: " << value.size() << " bytes)";
            }
        }, event.payload());
        
        std::cout << std::endl;
        consumed_++;
    }
    
    [[nodiscard]] std::uint64_t consumed_count() const noexcept {
        return consumed_.load();
    }

private:
    Config config_;
    std::mutex mutex_;
    std::atomic<std::uint64_t> consumed_{0};
};

/**
 * @brief Null sink (discards all events)
 */
class NullSink : public SinkOperator {
public:
    explicit NullSink(std::string name)
        : SinkOperator(std::move(name)) {}
    
    void consume(const Event& /*event*/) override {
        consumed_++;
    }
    
    [[nodiscard]] std::uint64_t consumed_count() const noexcept {
        return consumed_.load();
    }

private:
    std::atomic<std::uint64_t> consumed_{0};
};

/**
 * @brief Counting sink (counts events)
 */
class CountingSink : public SinkOperator {
public:
    explicit CountingSink(std::string name)
        : SinkOperator(std::move(name)) {}
    
    void consume(const Event& /*event*/) override {
        count_.fetch_add(1, std::memory_order_relaxed);
    }
    
    [[nodiscard]] std::uint64_t count() const noexcept {
        return count_.load(std::memory_order_relaxed);
    }
    
    void reset() noexcept {
        count_.store(0, std::memory_order_relaxed);
    }

private:
    std::atomic<std::uint64_t> count_{0};
};

/**
 * @brief Aggregating sink (computes running aggregates)
 */
class AggregatingSink : public SinkOperator {
public:
    explicit AggregatingSink(std::string name)
        : SinkOperator(std::move(name)) {}
    
    void consume(const Event& event) override {
        if (auto* value = event.get_if<std::int64_t>()) {
            std::lock_guard<std::mutex> lock(mutex_);
            sum_ += *value;
            count_++;
            if (*value < min_) min_ = *value;
            if (*value > max_) max_ = *value;
        } else if (auto* dvalue = event.get_if<double>()) {
            std::lock_guard<std::mutex> lock(mutex_);
            sum_ += static_cast<std::int64_t>(*dvalue);
            count_++;
        }
    }
    
    [[nodiscard]] std::int64_t sum() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return sum_;
    }
    
    [[nodiscard]] std::uint64_t count() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return count_;
    }
    
    [[nodiscard]] double mean() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return count_ > 0 ? static_cast<double>(sum_) / static_cast<double>(count_) : 0.0;
    }
    
    [[nodiscard]] std::int64_t min() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return min_;
    }
    
    [[nodiscard]] std::int64_t max() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return max_;
    }

private:
    mutable std::mutex mutex_;
    std::int64_t sum_{0};
    std::uint64_t count_{0};
    std::int64_t min_{std::numeric_limits<std::int64_t>::max()};
    std::int64_t max_{std::numeric_limits<std::int64_t>::min()};
};

/**
 * @brief Function-based sink
 */
template<typename Func>
class FunctionSink : public SinkOperator {
public:
    FunctionSink(std::string name, Func func)
        : SinkOperator(std::move(name))
        , func_(std::move(func)) {}
    
    void consume(const Event& event) override {
        func_(event);
    }

private:
    Func func_;
};

/**
 * @brief Factory function for function-based sinks
 */
template<typename Func>
auto make_sink(std::string name, Func&& func) {
    return std::make_unique<FunctionSink<std::decay_t<Func>>>(
        std::move(name), std::forward<Func>(func)
    );
}

} // namespace klstream
