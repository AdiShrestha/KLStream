#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <istream>
#include <numeric>
#include <ostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace klstream {
namespace detail {
inline std::uint32_t compute_crc32(const std::uint8_t* data, std::size_t length) {
    static const auto table = []() {
        std::array<std::uint32_t, 256> t{};
        for (std::uint32_t i = 0; i < 256; ++i) {
            std::uint32_t c = i;
            for (int k = 0; k < 8; ++k) {
                c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
            }
            t[i] = c;
        }
        return t;
    }();
    std::uint32_t crc = 0xFFFFFFFFu;
    for (std::size_t i = 0; i < length; ++i) {
        crc = table[(crc ^ data[i]) & 0xFFu] ^ (crc >> 8);
    }
    return crc ^ 0xFFFFFFFFu;
}

inline void write_u8(std::vector<std::uint8_t>& buf, std::uint8_t val) {
    buf.push_back(val);
}

inline void write_u32(std::vector<std::uint8_t>& buf, std::uint32_t val) {
    buf.push_back(static_cast<std::uint8_t>(val & 0xFF));
    buf.push_back(static_cast<std::uint8_t>((val >> 8) & 0xFF));
    buf.push_back(static_cast<std::uint8_t>((val >> 16) & 0xFF));
    buf.push_back(static_cast<std::uint8_t>((val >> 24) & 0xFF));
}

inline void write_u64(std::vector<std::uint8_t>& buf, std::uint64_t val) {
    for (int i = 0; i < 8; ++i) {
        buf.push_back(static_cast<std::uint8_t>((val >> (i * 8)) & 0xFF));
    }
}

inline void write_f64(std::vector<std::uint8_t>& buf, double val) {
    static_assert(sizeof(double) == 8, "double must be 8 bytes");
    std::uint64_t u = 0;
    std::memcpy(&u, &val, 8);
    write_u64(buf, u);
}

inline std::uint8_t read_u8(const std::uint8_t*& ptr, const std::uint8_t* end) {
    if (ptr >= end) throw std::runtime_error("Truncated model byte stream");
    return *ptr++;
}

inline std::uint32_t read_u32(const std::uint8_t*& ptr, const std::uint8_t* end) {
    if (ptr + 4 > end) throw std::runtime_error("Truncated model byte stream");
    std::uint32_t val = static_cast<std::uint32_t>(ptr[0]) |
                       (static_cast<std::uint32_t>(ptr[1]) << 8) |
                       (static_cast<std::uint32_t>(ptr[2]) << 16) |
                       (static_cast<std::uint32_t>(ptr[3]) << 24);
    ptr += 4;
    return val;
}

inline std::uint64_t read_u64(const std::uint8_t*& ptr, const std::uint8_t* end) {
    if (ptr + 8 > end) throw std::runtime_error("Truncated model byte stream");
    std::uint64_t val = 0;
    for (int i = 0; i < 8; ++i) {
        val |= (static_cast<std::uint64_t>(ptr[i]) << (i * 8));
    }
    ptr += 8;
    return val;
}

inline double read_f64(const std::uint8_t*& ptr, const std::uint8_t* end) {
    std::uint64_t u = read_u64(ptr, end);
    double val = 0.0;
    std::memcpy(&val, &u, 8);
    return val;
}
} // namespace detail
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

// Dynamic dimension variant for runtime-determined feature counts.
class DynamicIsolationForest {
public:
    struct Node { bool leaf{true}; std::size_t feature{0}, left{0}, right{0}; double split{0}, correction{0}; std::size_t sample_count{0}; };
    using Tree = std::vector<Node>;
    using Point = std::vector<float>;
    DynamicIsolationForest(std::size_t trees = 100, std::size_t subsample = 256, std::uint32_t seed = 42)
        : tree_count_(trees), requested_(subsample), seed_(seed) {
        if (!trees || subsample < 2) throw std::invalid_argument("Forest requires trees and subsample >= 2");
    }
    static double c_factor(std::size_t n) {
        if (n <= 1) return 0;
        double harmonic = 0;
        for (std::size_t i = 1; i < n; ++i) harmonic += 1.0 / static_cast<double>(i);
        return 2 * harmonic - 2 * static_cast<double>(n - 1) / static_cast<double>(n);
    }
    void fit(const std::vector<Point>& points) {
        if (points.size() < 2) throw std::invalid_argument("Forest training needs >= 2 rows");
        dimension_ = points.front().size();
        if (!dimension_) throw std::invalid_argument("Forest point dimension must be positive");
        for (const auto& p : points) {
            if (p.size() != dimension_) throw std::invalid_argument("Inconsistent point dimension in training set");
            finite(p);
        }
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
        if (x.size() != dimension_) throw std::invalid_argument("Query point dimension mismatch");
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
    const std::vector<Tree>& tree_snapshot() const noexcept { return trees_; }
    std::size_t n_trees() const noexcept { return trees_.size(); }
    std::size_t subsample_size() const noexcept { return effective_; }
    double c_psi() const noexcept { return c_; }
    std::size_t dimension() const noexcept { return dimension_; }
    std::uint32_t seed() const noexcept { return seed_; }
    bool is_fitted() const noexcept { return !trees_.empty(); }

    void save(std::ostream& os) const {
        if (trees_.empty()) {
            throw std::logic_error("Cannot serialize unfitted DynamicIsolationForest");
        }
        std::vector<std::uint8_t> tree_data;
        for (const auto& tree : trees_) {
            detail::write_u32(tree_data, static_cast<std::uint32_t>(tree.size()));
            for (const auto& node : tree) {
                detail::write_u8(tree_data, node.leaf ? 1 : 0);
                detail::write_u32(tree_data, static_cast<std::uint32_t>(node.feature));
                detail::write_f64(tree_data, node.split);
                detail::write_u32(tree_data, static_cast<std::uint32_t>(node.left));
                detail::write_u32(tree_data, static_cast<std::uint32_t>(node.right));
                detail::write_u64(tree_data, static_cast<std::uint64_t>(node.sample_count));
                detail::write_f64(tree_data, node.correction);
            }
        }
        std::uint32_t checksum = detail::compute_crc32(tree_data.data(), tree_data.size());

        // Header: 32 bytes
        std::vector<std::uint8_t> header;
        header.reserve(32);
        // Magic 4 bytes: "KLIF"
        header.push_back('K'); header.push_back('L'); header.push_back('I'); header.push_back('F');
        // Version = 1
        detail::write_u32(header, 1);
        // Number of trees
        detail::write_u32(header, static_cast<std::uint32_t>(trees_.size()));
        // Subsample size
        detail::write_u32(header, static_cast<std::uint32_t>(effective_));
        // Feature dimension
        detail::write_u32(header, static_cast<std::uint32_t>(dimension_));
        // Height limit
        std::size_t height = 0;
        for (auto remainder = effective_ - 1; remainder; remainder >>= 1) ++height;
        detail::write_u32(header, static_cast<std::uint32_t>(height));
        // Seed
        detail::write_u32(header, seed_);
        // CRC32 checksum over tree data
        detail::write_u32(header, checksum);

        os.write(reinterpret_cast<const char*>(header.data()), static_cast<std::streamsize>(header.size()));
        os.write(reinterpret_cast<const char*>(tree_data.data()), static_cast<std::streamsize>(tree_data.size()));
        if (!os.good()) {
            throw std::runtime_error("Failed to write model to output stream");
        }
    }

    void save_to_file(const std::string& path) const {
        std::ofstream ofs(path, std::ios::binary);
        if (!ofs.is_open()) {
            throw std::runtime_error("Cannot open model file for writing: " + path);
        }
        save(ofs);
    }

    static DynamicIsolationForest load(std::istream& is) {
        std::vector<std::uint8_t> buf((std::istreambuf_iterator<char>(is)), std::istreambuf_iterator<char>());
        if (buf.size() < 32) {
            throw std::runtime_error("Truncated model byte stream: file size (" +
                std::to_string(buf.size()) + ") smaller than 32-byte header");
        }

        // Validate Magic: 'K', 'L', 'I', 'F'
        if (buf[0] != 'K' || buf[1] != 'L' || buf[2] != 'I' || buf[3] != 'F') {
            throw std::runtime_error("Invalid model format magic: expected KLIF");
        }

        const std::uint8_t* ptr = buf.data() + 4;
        const std::uint8_t* end = buf.data() + buf.size();

        std::uint32_t version = detail::read_u32(ptr, end);
        if (version != 1) {
            throw std::runtime_error("Unsupported model version: " + std::to_string(version) + " (expected 1)");
        }

        std::uint32_t n_trees = detail::read_u32(ptr, end);
        std::uint32_t subsample_size = detail::read_u32(ptr, end);
        std::uint32_t feature_dim = detail::read_u32(ptr, end);
        std::uint32_t height_limit = detail::read_u32(ptr, end);
        (void)height_limit;
        std::uint32_t seed = detail::read_u32(ptr, end);
        std::uint32_t expected_checksum = detail::read_u32(ptr, end);

        if (n_trees == 0) {
            throw std::runtime_error("Invalid model header: tree count must be positive");
        }
        if (subsample_size < 2) {
            throw std::runtime_error("Invalid model header: subsample size must be >= 2");
        }
        if (feature_dim == 0) {
            throw std::runtime_error("Invalid model header: feature dimension must be positive");
        }

        // Checksum verification over tree data payload
        const std::uint8_t* tree_data_start = buf.data() + 32;
        std::size_t tree_data_len = buf.size() - 32;
        std::uint32_t actual_checksum = detail::compute_crc32(tree_data_start, tree_data_len);
        if (actual_checksum != expected_checksum) {
            throw std::runtime_error("Model checksum mismatch: corrupted tree payload (expected " +
                std::to_string(expected_checksum) + ", got " + std::to_string(actual_checksum) + ")");
        }

        ptr = tree_data_start;
        std::vector<Tree> loaded_trees;
        loaded_trees.reserve(n_trees);

        for (std::size_t t = 0; t < n_trees; ++t) {
            std::uint32_t node_count = detail::read_u32(ptr, end);
            if (node_count == 0) {
                throw std::runtime_error("Corrupted model: tree " + std::to_string(t) + " has zero nodes");
            }

            Tree tree;
            tree.reserve(node_count);
            for (std::size_t j = 0; j < node_count; ++j) {
                std::uint8_t leaf_flag = detail::read_u8(ptr, end);
                if (leaf_flag > 1) {
                    throw std::runtime_error("Invalid leaf flag " + std::to_string(static_cast<int>(leaf_flag)) + " in node " + std::to_string(j));
                }
                bool is_leaf = (leaf_flag == 1);
                std::uint32_t feat = detail::read_u32(ptr, end);
                double split = detail::read_f64(ptr, end);
                std::uint32_t left = detail::read_u32(ptr, end);
                std::uint32_t right = detail::read_u32(ptr, end);
                std::uint64_t sample_count = detail::read_u64(ptr, end);
                double correction = detail::read_f64(ptr, end);

                if (sample_count == 0) {
                    throw std::runtime_error("Invalid node sample count: zero in node " + std::to_string(j));
                }

                if (is_leaf) {
                    if (!std::isfinite(correction)) {
                        throw std::runtime_error("Non-finite harmonic correction in leaf node " + std::to_string(j));
                    }
                    if (correction < 0.0) {
                        throw std::runtime_error("Negative harmonic correction in leaf node " + std::to_string(j));
                    }
                } else {
                    if (feat >= feature_dim) {
                        throw std::runtime_error("Node split feature index out of bounds: " +
                            std::to_string(feat) + " >= dimension " + std::to_string(feature_dim));
                    }
                    if (!std::isfinite(split)) {
                        throw std::runtime_error("Non-finite split threshold in model node " + std::to_string(j));
                    }
                    if (left >= node_count || right >= node_count) {
                        throw std::runtime_error("Child node offset out of bounds in node " + std::to_string(j) +
                            ": left=" + std::to_string(left) + ", right=" + std::to_string(right) + ", count=" + std::to_string(node_count));
                    }
                    if (left <= j || right <= j) {
                        throw std::runtime_error("Corrupted tree topology: child offset invalid or circular in node " + std::to_string(j) +
                            ": left=" + std::to_string(left) + ", right=" + std::to_string(right));
                    }
                }

                tree.push_back(Node{is_leaf, feat, left, right, split, correction, static_cast<std::size_t>(sample_count)});
            }

            // Topology validation: single root at 0, every other node referenced exactly once
            std::vector<int> parent_count(node_count, 0);
            for (std::size_t j = 0; j < node_count; ++j) {
                if (!tree[j].leaf) {
                    parent_count[tree[j].left]++;
                    parent_count[tree[j].right]++;
                }
            }
            if (parent_count[0] != 0) {
                throw std::runtime_error("Corrupted tree topology: root node 0 has incoming edges in tree " + std::to_string(t));
            }
            for (std::size_t k = 1; k < node_count; ++k) {
                if (parent_count[k] != 1) {
                    throw std::runtime_error("Corrupted tree topology: node " + std::to_string(k) +
                        " has " + std::to_string(parent_count[k]) + " incoming edges in tree " + std::to_string(t));
                }
            }

            loaded_trees.push_back(std::move(tree));
        }

        if (ptr != end) {
            throw std::runtime_error("Trailing unparsed bytes (" + std::to_string(end - ptr) + " bytes) in model stream");
        }

        DynamicIsolationForest forest(n_trees, subsample_size, seed);
        forest.trees_ = std::move(loaded_trees);
        forest.tree_count_ = n_trees;
        forest.requested_ = subsample_size;
        forest.effective_ = subsample_size;
        forest.dimension_ = feature_dim;
        forest.seed_ = seed;
        forest.c_ = c_factor(forest.effective_);
        return forest;
    }

    static DynamicIsolationForest load_from_file(const std::string& path) {
        std::ifstream ifs(path, std::ios::binary);
        if (!ifs.is_open()) {
            throw std::runtime_error("Cannot open model file for reading: " + path);
        }
        return load(ifs);
    }
private:
    static void finite(const Point& p) { for (float x : p) if (!std::isfinite(x)) throw std::invalid_argument("Nonfinite forest feature"); }
    std::size_t build(Tree& tree, const std::vector<Point>& points, std::size_t depth, std::size_t height, std::mt19937& rng) {
        const auto index = tree.size();
        tree.push_back(Node{}); tree[index].sample_count = points.size();
        if (points.size() <= 1 || depth >= height) { tree[index].correction = c_factor(points.size()); return index; }
        std::vector<float> lows(dimension_), highs(dimension_);
        std::vector<std::size_t> varying;
        for (std::size_t f = 0; f < dimension_; ++f) {
            lows[f] = highs[f] = points.front()[f];
            for (const auto& p : points) { lows[f] = std::min(lows[f], p[f]); highs[f] = std::max(highs[f], p[f]); }
            if (lows[f] < highs[f]) varying.push_back(f);
        }
        if (varying.empty()) { tree[index].correction = c_factor(points.size()); return index; }
        const auto feature = varying[std::uniform_int_distribution<std::size_t>(0, varying.size() - 1)(rng)];
        double split = std::uniform_real_distribution<double>(lows[feature], highs[feature])(rng);
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
    std::size_t tree_count_, requested_, effective_{0}, dimension_{0};
    std::uint32_t seed_; double c_{0}; std::vector<Tree> trees_;
};
}

