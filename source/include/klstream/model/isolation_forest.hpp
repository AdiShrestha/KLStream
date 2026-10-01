#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <numeric>
#include <random>
#include <stdexcept>
#include <vector>

namespace klstream {
// In-memory reference implementation. Legacy binary/pickle formats are not
// accepted. Scores are anomaly rankings, never calibrated probabilities.
// Axis-aligned variant: choose uniformly among varying features at each node;
// exact harmonic correction. This is not Extended IF or sklearn bit parity.
template <std::size_t D> class IsolationForest {
    static_assert(D > 0, "Forest needs at least one feature");
public:
    struct Node { bool leaf{true}; std::size_t feature{0}, left{0}, right{0}; double split{0}, correction{0}; std::size_t sample_count{0}; };
    using Tree = std::vector<Node>;
    using Point = std::array<float, D>;
    IsolationForest(std::size_t trees = 100, std::size_t subsample = 256, std::uint32_t seed = 42)
        : tree_count_(trees), requested_(subsample), seed_(seed) {
        if (!trees || subsample < 2) throw std::invalid_argument("Forest requires trees and subsample >= 2");
    }
    // Exact finite-sample harmonic definition, not its large-n approximation.
    static double c_factor(std::size_t n) {
        if (n <= 1) return 0;
        double harmonic = 0;
        for (std::size_t i = 1; i < n; ++i) harmonic += 1.0 / static_cast<double>(i);
        return 2 * harmonic - 2 * static_cast<double>(n - 1) / static_cast<double>(n);
    }
    void fit(const std::vector<Point>& points) {
        if (points.size() < 2) throw std::invalid_argument("Forest training needs >= 2 rows");
        for (const auto& p : points) finite(p);
        const std::size_t effective = std::min(requested_, points.size());
        std::size_t height = 0;
        for (auto remainder = effective - 1; remainder; remainder >>= 1) ++height;
        std::mt19937 rng(seed_);
        std::vector<Tree> built;
        built.reserve(tree_count_);
        std::vector<std::size_t> indices(points.size());
        for (std::size_t t = 0; t < tree_count_; ++t) {
            std::iota(indices.begin(), indices.end(), 0);
            std::shuffle(indices.begin(), indices.end(), rng);
            std::vector<Point> sample;
            sample.reserve(effective);
            for (std::size_t i = 0; i < effective; ++i) sample.push_back(points[indices[i]]);
            Tree tree;
            build(tree, sample, 0, height, rng);
            built.push_back(std::move(tree));
        }
        trees_ = std::move(built);
        effective_ = effective;
        c_ = c_factor(effective_);
    }
    double anomaly_score(const Point& x) const {
        finite(x);
        if (trees_.empty()) throw std::logic_error("Forest has not been fitted");
        double sum = 0;
        for (const auto& tree : trees_) {
            std::size_t index = 0, depth = 0;
            while (!tree[index].leaf) {
                const auto& node = tree[index];
                index = x[node.feature] < node.split ? node.left : node.right;
                ++depth;
            }
            sum += static_cast<double>(depth) + tree[index].correction;
        }
        return std::exp2(-sum / static_cast<double>(trees_.size()) / c_);
    }
    // Read-only inspection for independent scoring/partition checks. No stable
    // persistence format is claimed; refit invalidates these references.
    const std::vector<Tree>& tree_snapshot() const noexcept { return trees_; }
    std::size_t n_trees() const noexcept { return trees_.size(); }
    std::size_t subsample_size() const noexcept { return effective_; }
    double c_psi() const noexcept { return c_; }
private:
    static void finite(const Point& p) { for (float x : p) if (!std::isfinite(x)) throw std::invalid_argument("Nonfinite forest feature"); }
    static std::size_t build(Tree& tree, const std::vector<Point>& points, std::size_t depth, std::size_t height, std::mt19937& rng) {
        const auto index = tree.size();
        tree.push_back(Node{}); tree[index].sample_count = points.size();
        if (points.size() <= 1 || depth >= height) { tree[index].correction = c_factor(points.size()); return index; }
        std::array<float, D> lows{}, highs{};
        std::vector<std::size_t> varying;
        for (std::size_t f = 0; f < D; ++f) {
            lows[f] = highs[f] = points.front()[f];
            for (const auto& p : points) { lows[f] = std::min(lows[f], p[f]); highs[f] = std::max(highs[f], p[f]); }
            if (lows[f] < highs[f]) varying.push_back(f);
        }
        if (varying.empty()) { tree[index].correction = c_factor(points.size()); return index; }
        const auto feature = varying[std::uniform_int_distribution<std::size_t>(0, varying.size() - 1)(rng)];
        double split = std::uniform_real_distribution<double>(lows[feature], highs[feature])(rng);
        // Keep the sampled threshold in double precision for float training/query points.
        if (split <= lows[feature]) split = std::nextafter(static_cast<double>(lows[feature]), static_cast<double>(highs[feature]));
        split = std::min(split, static_cast<double>(highs[feature]));
        std::vector<Point> left, right;
        for (const auto& p : points) (p[feature] < split ? left : right).push_back(p);
        if (left.empty() || right.empty()) throw std::logic_error("Invalid isolation partition");
        const auto li = build(tree, left, depth + 1, height, rng);
        const auto ri = build(tree, right, depth + 1, height, rng);
        tree[index] = Node{false, feature, li, ri, split, 0, points.size()};
        return index;
    }
    std::size_t tree_count_, requested_, effective_{0};
    std::uint32_t seed_; double c_{0}; std::vector<Tree> trees_;
};
}
