// Historical counterexamples against research-foundation-2026-10-01.
// Compile with that tag's include directory. These are disclosed audit fixtures.
#include <klstream/klstream.hpp>
#include <iostream>
#include <thread>
int main() {
    using namespace klstream;using namespace std::chrono_literals;
    SPSCQueue<Event<int>> queue(2);queue.stop();bool finished=false;
    SinkOperator<int> sink("cancel",&queue,[](const auto&){});
    try { finished=sink.tick()==OpStatus::Finished; } catch(const std::exception&){}
    LatencyHistogram histogram;for(int i=0;i<100;++i)histogram.record(i*1000);
    TokenBucketRateLimiter bucket(1000,1,1);(void)bucket.try_consume();
    std::this_thread::sleep_for(20ms);bucket.set_rate(1);const bool credited=bucket.try_consume();
    std::cout<<"{\"purpose\":\"audit fixtures, not research\",\"cancelled_is_drained\":"<<queue.is_drained()
        <<",\"cancelled_sink_finished\":"<<finished<<",\"seven_percentile_us\":"<<histogram.percentile(.07)
        <<",\"expected_seven_percentile_us\":6,\"preceding_rate_credit_available\":"<<credited<<"}\n";
}
