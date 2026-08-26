#include <gtest/gtest.h>
#include <klstream/model/isolation_forest.hpp>
#include <sstream>
#include <random>
#include <vector>

using namespace klstream;

namespace {

std::vector<IsolationForest<5>::Point> generate_test_points(int n, std::uint32_t seed) {
    std::mt19937 rng(seed);
    std::normal_distribution<float> norm(0.0f, 1.0f);
    std::vector<IsolationForest<5>::Point> pts;
    pts.reserve(n);
    for (int i = 0; i < n; ++i) {
        pts.push_back({norm(rng), norm(rng), norm(rng), norm(rng), norm(rng)});
    }
    return pts;
}

} // namespace

TEST(ModelSerializationTest, RoundTripExactScores) {
    auto train_pts = generate_test_points(200, 101);
    auto test_pts = generate_test_points(50, 202);

    IsolationForest<5> orig_model(25, 64, 42);
    orig_model.fit(train_pts);

    std::stringstream ss(std::ios::in | std::ios::out | std::ios::binary);
    orig_model.save(ss);

    IsolationForest<5> loaded_model(0, 0, 0);
    loaded_model.load(ss);

    EXPECT_EQ(loaded_model.n_trees(), orig_model.n_trees());
    EXPECT_EQ(loaded_model.subsample_size(), orig_model.subsample_size());
    EXPECT_DOUBLE_EQ(loaded_model.c_psi(), orig_model.c_psi());

    for (const auto& pt : test_pts) {
        double s_orig = orig_model.anomaly_score(pt);
        double s_loaded = loaded_model.anomaly_score(pt);
        EXPECT_DOUBLE_EQ(s_orig, s_loaded);
    }
}

TEST(ModelSerializationTest, CorruptedMagicThrowsException) {
    auto train_pts = generate_test_points(50, 303);
    IsolationForest<5> model(10, 32, 42);
    model.fit(train_pts);

    std::stringstream ss(std::ios::in | std::ios::out | std::ios::binary);
    model.save(ss);
    std::string bytes = ss.str();

    // Corrupt magic header byte
    bytes[0] = 'X';

    std::stringstream corrupt_ss(bytes, std::ios::in | std::ios::out | std::ios::binary);
    IsolationForest<5> target;
    EXPECT_THROW(target.load(corrupt_ss), std::runtime_error);
}

TEST(ModelSerializationTest, UnsupportedVersionThrowsException) {
    auto train_pts = generate_test_points(50, 404);
    IsolationForest<5> model(10, 32, 42);
    model.fit(train_pts);

    std::stringstream ss(std::ios::in | std::ios::out | std::ios::binary);
    model.save(ss);
    std::string bytes = ss.str();

    // Corrupt format_version field (bytes 4..7)
    bytes[4] = 2; // version 2

    std::stringstream corrupt_ss(bytes, std::ios::in | std::ios::out | std::ios::binary);
    IsolationForest<5> target;
    EXPECT_THROW(target.load(corrupt_ss), std::runtime_error);
}

TEST(ModelSerializationTest, TruncatedHeaderThrowsException) {
    std::string truncated = "KLIF123"; // Less than 64 bytes
    std::stringstream ss(truncated, std::ios::in | std::ios::out | std::ios::binary);
    IsolationForest<5> target;
    EXPECT_THROW(target.load(ss), std::runtime_error);
}

TEST(ModelSerializationTest, TruncatedPayloadThrowsException) {
    auto train_pts = generate_test_points(50, 505);
    IsolationForest<5> model(10, 32, 42);
    model.fit(train_pts);

    std::stringstream ss(std::ios::in | std::ios::out | std::ios::binary);
    model.save(ss);
    std::string bytes = ss.str();

    // Truncate payload in half
    std::string truncated = bytes.substr(0, bytes.size() / 2);

    std::stringstream corrupt_ss(truncated, std::ios::in | std::ios::out | std::ios::binary);
    IsolationForest<5> target;
    EXPECT_THROW(target.load(corrupt_ss), std::runtime_error);
}

TEST(ModelSerializationTest, CorruptedPayloadChecksumThrowsException) {
    auto train_pts = generate_test_points(50, 606);
    IsolationForest<5> model(10, 32, 42);
    model.fit(train_pts);

    std::stringstream ss(std::ios::in | std::ios::out | std::ios::binary);
    model.save(ss);
    std::string bytes = ss.str();

    // Flip a byte in the payload area (after 64-byte header)
    if (bytes.size() > 70) {
        bytes[68] ^= 0xff;
    }

    std::stringstream corrupt_ss(bytes, std::ios::in | std::ios::out | std::ios::binary);
    IsolationForest<5> target;
    EXPECT_THROW(target.load(corrupt_ss), std::runtime_error);
}
