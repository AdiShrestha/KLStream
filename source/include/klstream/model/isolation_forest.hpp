#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <random>
#include <vector>

namespace klstream {

// ── IsolationTree ─────────────────────────────────────────────────────────
//
// A single random partition tree. Built once at training time from a
// random sub-sample of D-dimensional points. Each internal node picks a
// random feature and a random split value strictly between that feature's
// min and max within the current node's subset.
//
// Stored as a flat array of nodes (not pointer-linked) for cache locality
// during the scoring hot path — this matters because InferenceOp calls
// path_length() up to MAX_WINDOW_SIZE times per tick() (Section 7.2).
template <std::size_t D>
class IsolationTree {
public:
    using Point = std::array<float, D>;

    struct Node {
        int   feature   = -1;   // -1 marks a leaf
        float split      = 0.0f;
        int   left       = -1;  // index into nodes_, -1 if unset
        int   right      = -1;
        int   size_at_leaf = 0; // number of points that landed here (for c(n) correction)
    };

    // Builds the tree from `points` (a sub-sample already drawn by the
    // caller — IsolationForest::fit handles sampling, Section 12 below).
    void build(std::vector<Point> points, int height_limit, std::mt19937& rng) {
        nodes_.clear();
        nodes_.reserve(2 * points.size());
        root_ = build_node(points, 0, height_limit, rng);
    }

    // Path length for a single query point, with the Liu et al. correction
    // term c(size_at_leaf) added when recursion stops early due to the
    // height limit rather than true isolation (Eq. 2 in their paper).
    double path_length(const Point& x) const {
        int node_idx = root_;
        int depth = 0;
        while (true) {
            const Node& n = nodes_[node_idx];
            if (n.feature == -1) {
                return depth + c_factor(n.size_at_leaf);
            }
            ++depth;
            node_idx = (x[n.feature] < n.split) ? n.left : n.right;
        }
    }

    // c(n): average path length of an unsuccessful search in a BST of n
    // points (Liu et al. 2008, Eq. 2). Used both for leaf-size correction
    // above and for the forest-level normalisation in IsolationForest::score.
    static double c_factor(int n) {
        if (n <= 1) return 0.0;
        if (n == 2) return 1.0;
        constexpr double EULER_GAMMA = 0.5772156649015329;
        return 2.0 * (std::log(static_cast<double>(n - 1)) + EULER_GAMMA)
             - 2.0 * static_cast<double>(n - 1) / static_cast<double>(n);
    }

    void save(std::ostream& out) const {
        std::size_t n = nodes_.size();
        out.write(reinterpret_cast<const char*>(&n), sizeof(n));
        out.write(reinterpret_cast<const char*>(nodes_.data()), n * sizeof(Node));
        out.write(reinterpret_cast<const char*>(&root_), sizeof(root_));
    }

    void load(std::istream& in) {
        std::size_t n;
        in.read(reinterpret_cast<char*>(&n), sizeof(n));
        nodes_.resize(n);
        in.read(reinterpret_cast<char*>(nodes_.data()), n * sizeof(Node));
        in.read(reinterpret_cast<char*>(&root_), sizeof(root_));
    }

private:
    int build_node(std::vector<Point>& points, int depth, int height_limit,
                    std::mt19937& rng) {
        Node n;
        if (depth >= height_limit || points.size() <= 1) {
            n.size_at_leaf = static_cast<int>(points.size());
            nodes_.push_back(n);
            return static_cast<int>(nodes_.size()) - 1;
        }

        // Pick a random feature with non-degenerate range; bail to a leaf
        // after a bounded number of failed attempts (handles the case
        // where most/all features are constant in this subset).
        int feature = -1;
        float lo = 0.0f, hi = 0.0f;
        std::uniform_int_distribution<int> feat_dist(0, static_cast<int>(D) - 1);
        for (int attempt = 0; attempt < 8; ++attempt) {
            int f = feat_dist(rng);
            float mn = std::numeric_limits<float>::max();
            float mx = std::numeric_limits<float>::lowest();
            for (const auto& p : points) {
                mn = std::min(mn, p[f]);
                mx = std::max(mx, p[f]);
            }
            if (mx > mn) { feature = f; lo = mn; hi = mx; break; }
        }
        if (feature == -1) {
            n.size_at_leaf = static_cast<int>(points.size());
            nodes_.push_back(n);
            return static_cast<int>(nodes_.size()) - 1;
        }

        std::uniform_real_distribution<float> split_dist(lo, hi);
        float split = split_dist(rng);

        std::vector<Point> left_pts, right_pts;
        left_pts.reserve(points.size());
        right_pts.reserve(points.size());
        for (const auto& p : points) {
            (p[feature] < split ? left_pts : right_pts).push_back(p);
        }
        // Degenerate split guard (all points landed on one side).
        if (left_pts.empty() || right_pts.empty()) {
            n.size_at_leaf = static_cast<int>(points.size());
            nodes_.push_back(n);
            return static_cast<int>(nodes_.size()) - 1;
        }

        n.feature = feature;
        n.split   = split;
        int self_idx = static_cast<int>(nodes_.size());
        nodes_.push_back(n);                       // reserve slot first
        int left_idx  = build_node(left_pts,  depth + 1, height_limit, rng);
        int right_idx = build_node(right_pts, depth + 1, height_limit, rng);
        nodes_[self_idx].left  = left_idx;
        nodes_[self_idx].right = right_idx;
        return self_idx;
    }

    std::vector<Node> nodes_;
    int                root_ = -1;
};

// ── IsolationForest ────────────────────────────────────────────────────────
//
// An ensemble of IsolationTree<D>. Trained ONCE offline (Section 7.5) and
// reused, unmodified, across every window-strategy comparison.
//
// anomaly_score() implements Eq. 1 from Liu et al. 2008:
//     s(x, psi) = 2 ^ ( -E[h(x)] / c(psi) )
// Score approaches 1.0 for anomalies (short average path), approaches 0.5
// or below for normal points (path length near c(psi)).
template <std::size_t D>
class IsolationForest {
public:
    using Point = typename IsolationTree<D>::Point;

    IsolationForest(int n_estimators = 100, int sub_sample_size = 256,
                    std::uint32_t seed = 42)
        : n_estimators_(n_estimators)
        , psi_(sub_sample_size)
        , rng_(seed)
    {}

    // points: the full calm-period training set (Section 26 covers
    // validating this against sklearn on a held-out split).
    void fit(const std::vector<Point>& points) {
        int height_limit = static_cast<int>(std::ceil(std::log2(
            static_cast<double>(std::max(2, psi_)))));
        trees_.clear();
        trees_.reserve(n_estimators_);
        std::uniform_int_distribution<std::size_t> idx_dist(0, points.size() - 1);

        for (int t = 0; t < n_estimators_; ++t) {
            std::vector<Point> sample;
            sample.reserve(psi_);
            // Sampling without replacement within one tree, as in the
            // original paper; reseed per tree off the forest's own rng so
            // results are reproducible given a fixed `seed`.
            std::vector<std::size_t> indices(points.size());
            for (std::size_t i = 0; i < indices.size(); ++i) indices[i] = i;
            std::shuffle(indices.begin(), indices.end(), rng_);
            int take = std::min(psi_, static_cast<int>(points.size()));
            for (int i = 0; i < take; ++i) sample.push_back(points[indices[i]]);

            IsolationTree<D> tree;
            tree.build(std::move(sample), height_limit, rng_);
            trees_.push_back(std::move(tree));
        }
        c_psi_ = IsolationTree<D>::c_factor(psi_);
    }

    [[nodiscard]] double anomaly_score(const Point& x) const {
        double total = 0.0;
        for (const auto& tree : trees_) total += tree.path_length(x);
        double avg_path = total / static_cast<double>(trees_.size());
        return std::pow(2.0, -avg_path / c_psi_);
    }

    [[nodiscard]] std::size_t n_trees() const { return trees_.size(); }

    void save(std::ostream& out) const {
        out.write(reinterpret_cast<const char*>(&n_estimators_), sizeof(n_estimators_));
        out.write(reinterpret_cast<const char*>(&psi_), sizeof(psi_));
        out.write(reinterpret_cast<const char*>(&c_psi_), sizeof(c_psi_));
        std::size_t n_trees = trees_.size();
        out.write(reinterpret_cast<const char*>(&n_trees), sizeof(n_trees));
        for (const auto& tree : trees_) {
            tree.save(out);
        }
    }

    void load(std::istream& in) {
        in.read(reinterpret_cast<char*>(&n_estimators_), sizeof(n_estimators_));
        in.read(reinterpret_cast<char*>(&psi_), sizeof(psi_));
        in.read(reinterpret_cast<char*>(&c_psi_), sizeof(c_psi_));
        std::size_t n_trees;
        in.read(reinterpret_cast<char*>(&n_trees), sizeof(n_trees));
        trees_.resize(n_trees);
        for (auto& tree : trees_) {
            tree.load(in);
        }
    }

private:
    int                            n_estimators_;
    int                            psi_;
    std::mt19937                   rng_;
    double                         c_psi_ = 1.0;
    std::vector<IsolationTree<D>>  trees_;
};

} // namespace klstream
