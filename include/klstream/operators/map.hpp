#pragma once

/**
 * @file map.hpp
 * @brief Map transformation operator
 */

#include <functional>

#include "klstream/core/operator.hpp"

namespace klstream {

/**
 * @brief Map operator that transforms events
 */
template<typename MapFunc>
class MapOperator : public Operator {
public:
    MapOperator(std::string name, MapFunc func)
        : Operator(std::move(name))
        , func_(std::move(func)) {}
    
    void process(Event& event, OperatorContext& ctx) override {
        record_received();
        auto start = std::chrono::steady_clock::now();
        
        // Apply transformation
        if constexpr (std::is_invocable_r_v<Payload, MapFunc, const Payload&>) {
            Payload result = func_(event.payload());
            Event output{std::move(result), event.metadata()};
            ctx.emit(std::move(output));
            record_emitted();
        } else if constexpr (std::is_invocable_r_v<Event, MapFunc, const Event&>) {
            Event output = func_(event);
            ctx.emit(std::move(output));
            record_emitted();
        } else if constexpr (std::is_invocable_v<MapFunc, Event&, OperatorContext&>) {
            func_(event, ctx);
        }
        
        auto end = std::chrono::steady_clock::now();
        auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        record_processing_time(static_cast<std::uint64_t>(ns));
    }

private:
    MapFunc func_;
};

/**
 * @brief Factory function for map operators
 */
template<typename MapFunc>
auto make_map(std::string name, MapFunc&& func) {
    return std::make_unique<MapOperator<std::decay_t<MapFunc>>>(
        std::move(name), std::forward<MapFunc>(func)
    );
}

/**
 * @brief Integer transformation map
 */
inline auto make_int_map(std::string name, std::function<std::int64_t(std::int64_t)> func) {
    return make_map(std::move(name), [f = std::move(func)](const Payload& p) -> Payload {
        if (auto* val = std::get_if<std::int64_t>(&p)) {
            return f(*val);
        }
        return p;
    });
}

/**
 * @brief Double transformation map
 */
inline auto make_double_map(std::string name, std::function<double(double)> func) {
    return make_map(std::move(name), [f = std::move(func)](const Payload& p) -> Payload {
        if (auto* val = std::get_if<double>(&p)) {
            return f(*val);
        }
        return p;
    });
}

/**
 * @brief String transformation map
 */
inline auto make_string_map(std::string name, std::function<std::string(const std::string&)> func) {
    return make_map(std::move(name), [f = std::move(func)](const Payload& p) -> Payload {
        if (auto* val = std::get_if<std::string>(&p)) {
            return f(*val);
        }
        return p;
    });
}

} // namespace klstream
