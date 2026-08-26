#include <klstream/klstream.hpp>
#include <iostream>
#include <cassert>
#include <cstdint>

int main() {
    std::cout << "[Consumer Test] Initializing KLStream consumer application..." << std::endl;

    // Test SPSC queue
    klstream::SPSCQueue<uint64_t> queue(64);
    assert(queue.capacity() == 64);
    assert(queue.empty());

    bool pushed = queue.try_push(42);
    assert(pushed);
    assert(!queue.empty());

    uint64_t val = 0;
    bool popped = queue.try_pop(&val);
    assert(popped);
    assert(val == 42);
    assert(queue.empty());

    // Test Event construct
    auto evt = klstream::Event<uint64_t>::make(100);
    assert(evt.data == 100);

    std::cout << "[Consumer Test] Successfully exercised SPSCQueue and Event abstractions." << std::endl;
    std::cout << "[Consumer Test] PASSED" << std::endl;
    return 0;
}
