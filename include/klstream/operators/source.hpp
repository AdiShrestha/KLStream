#pragma once

/**
 * @file source.hpp
 * @brief Source operator implementations
 */

#include <random>
#include <functional>
#include <chrono>
#include <limits>

#include "klstream/core/operator.hpp"

namespace klstream {

/**
 * @brief Random number generator source
 */
class RandomSource : public SourceOperator {
public:
    struct Config {
        std::int64_t min_value{0};
        std::int64_t max_value{1000};
        std::uint64_t count{std::numeric_limits<std::uint64_t>::max()};
        std::chrono::microseconds delay{0};
    };
    
    explicit RandomSource(std::string name, Config config = {})
        : SourceOperator(std::move(name))
        , config_(config)
        , rng_(std::random_device{}())
        , dist_(config.min_value, config.max_value) {}
    
    bool generate(OperatorContext& ctx) override {
        if (should_stop() || generated_ >= config_.count) {
            return false;
        }
        
        std::int64_t value = dist_(rng_);
        Event event{value, generated_};
        
        if (ctx.emit(std::move(event)) > 0) {
            generated_++;
            record_emitted();
        } else {
            record_backpressure();
        }
        
        if (config_.delay.count() > 0) {
            std::this_thread::sleep_for(config_.delay);
        }
        
        return true;
    }

private:
    Config config_;
    std::mt19937_64 rng_;
    std::uniform_int_distribution<std::int64_t> dist_;
    std::uint64_t generated_{0};
};

/**
 * @brief Sequence generator source
 */
class SequenceSource : public SourceOperator {
public:
    struct Config {
        std::int64_t start{0};
        std::int64_t step{1};
        std::uint64_t count{std::numeric_limits<std::uint64_t>::max()};
        std::chrono::microseconds delay{0};
    };
    
    explicit SequenceSource(std::string name, Config config = {})
        : SourceOperator(std::move(name))
        , config_(config)
        , current_(config.start) {}
    
    bool generate(OperatorContext& ctx) override {
        if (should_stop() || generated_ >= config_.count) {
            return false;
        }
        
        Event event{current_, generated_};
        
        if (ctx.emit(std::move(event)) > 0) {
            current_ += config_.step;
            generated_++;
            record_emitted();
        } else {
            record_backpressure();
        }
        
        if (config_.delay.count() > 0) {
            std::this_thread::sleep_for(config_.delay);
        }
        
        return true;
    }

private:
    Config config_;
    std::int64_t current_;
    std::uint64_t generated_{0};
};

/**
 * @brief Generator source using a user-provided function
 */
template<typename Generator>
class FunctionSource : public SourceOperator {
public:
    FunctionSource(std::string name, Generator gen, std::uint64_t count = std::numeric_limits<std::uint64_t>::max())
        : SourceOperator(std::move(name))
        , generator_(std::move(gen))
        , max_count_(count) {}
    
    bool generate(OperatorContext& ctx) override {
        if (should_stop() || generated_ >= max_count_) {
            return false;
        }
        
        auto value = generator_();
        Event event{std::move(value), generated_};
        
        if (ctx.emit(std::move(event)) > 0) {
            generated_++;
            record_emitted();
        } else {
            record_backpressure();
        }
        
        return true;
    }

private:
    Generator generator_;
    std::uint64_t max_count_;
    std::uint64_t generated_{0};
};

/**
 * @brief Factory function for function-based sources
 */
template<typename Generator>
auto make_source(std::string name, Generator&& gen, std::uint64_t count = std::numeric_limits<std::uint64_t>::max()) {
    return std::make_unique<FunctionSource<std::decay_t<Generator>>>(
        std::move(name), std::forward<Generator>(gen), count
    );
}

} // namespace klstream
