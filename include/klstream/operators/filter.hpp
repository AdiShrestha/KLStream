#pragma once

/**
 * @file filter.hpp
 * @brief Filter operator implementation
 */

#include <functional>

#include "klstream/core/operator.hpp"

namespace klstream {

/**
 * @brief Filter operator that selectively passes events
 */
template<typename Predicate>
class FilterOperator : public Operator {
public:
    FilterOperator(std::string name, Predicate pred)
        : Operator(std::move(name))
        , predicate_(std::move(pred)) {}
    
    void process(Event& event, OperatorContext& ctx) override {
        record_received();
        auto start = std::chrono::steady_clock::now();
        
        bool pass = false;
        if constexpr (std::is_invocable_r_v<bool, Predicate, const Event&>) {
            pass = predicate_(event);
        } else if constexpr (std::is_invocable_r_v<bool, Predicate, const Payload&>) {
            pass = predicate_(event.payload());
        }
        
        if (pass) {
            ctx.emit(std::move(event));
            record_emitted();
        } else {
            record_dropped();
        }
        
        auto end = std::chrono::steady_clock::now();
        auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        record_processing_time(static_cast<std::uint64_t>(ns));
    }

private:
    Predicate predicate_;
};

/**
 * @brief Factory function for filter operators
 */
template<typename Predicate>
auto make_filter(std::string name, Predicate&& pred) {
    return std::make_unique<FilterOperator<std::decay_t<Predicate>>>(
        std::move(name), std::forward<Predicate>(pred)
    );
}

/**
 * @brief Integer predicate filter
 */
inline auto make_int_filter(std::string name, std::function<bool(std::int64_t)> pred) {
    return make_filter(std::move(name), [p = std::move(pred)](const Payload& payload) {
        if (auto* val = std::get_if<std::int64_t>(&payload)) {
            return p(*val);
        }
        return false;
    });
}

/**
 * @brief Common filters
 */
namespace filters {

/**
 * @brief Filter for even integers
 */
inline auto even() {
    return [](const Payload& p) {
        if (auto* val = std::get_if<std::int64_t>(&p)) {
            return (*val % 2) == 0;
        }
        return false;
    };
}

/**
 * @brief Filter for odd integers
 */
inline auto odd() {
    return [](const Payload& p) {
        if (auto* val = std::get_if<std::int64_t>(&p)) {
            return (*val % 2) != 0;
        }
        return false;
    };
}

/**
 * @brief Filter for positive numbers
 */
inline auto positive() {
    return [](const Payload& p) {
        if (auto* val = std::get_if<std::int64_t>(&p)) {
            return *val > 0;
        }
        if (auto* val = std::get_if<double>(&p)) {
            return *val > 0.0;
        }
        return false;
    };
}

/**
 * @brief Filter for negative numbers
 */
inline auto negative() {
    return [](const Payload& p) {
        if (auto* val = std::get_if<std::int64_t>(&p)) {
            return *val < 0;
        }
        if (auto* val = std::get_if<double>(&p)) {
            return *val < 0.0;
        }
        return false;
    };
}

/**
 * @brief Filter by range
 */
template<typename T>
inline auto in_range(T min_val, T max_val) {
    return [min_val, max_val](const Payload& p) {
        if (auto* val = std::get_if<std::int64_t>(&p)) {
            return *val >= static_cast<std::int64_t>(min_val) && 
                   *val <= static_cast<std::int64_t>(max_val);
        }
        if (auto* val = std::get_if<double>(&p)) {
            return *val >= static_cast<double>(min_val) && 
                   *val <= static_cast<double>(max_val);
        }
        return false;
    };
}

} // namespace filters

} // namespace klstream
