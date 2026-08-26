#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace klstream {

namespace detail {

// ── Standard SHA-256 implementation for model payload integrity ──────────
inline std::uint32_t rotr(std::uint32_t x, std::uint32_t n) {
    return (x >> n) | (x << (32 - n));
}

inline void sha256(const std::uint8_t* data, std::size_t len, std::array<std::uint8_t, 32>& digest) {
    static constexpr std::uint32_t K[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };

    std::uint32_t h[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    std::vector<std::uint8_t> msg(data, data + len);
    std::uint64_t bit_len = static_cast<std::uint64_t>(len) * 8;

    msg.push_back(0x80);
    while ((msg.size() % 64) != 56) {
        msg.push_back(0x00);
    }
    for (int i = 7; i >= 0; --i) {
        msg.push_back(static_cast<std::uint8_t>((bit_len >> (i * 8)) & 0xff));
    }

    for (std::size_t chunk = 0; chunk < msg.size(); chunk += 64) {
        std::uint32_t w[64];
        for (std::size_t i = 0; i < 16; ++i) {
            w[i] = (static_cast<std::uint32_t>(msg[chunk + i * 4]) << 24) |
                   (static_cast<std::uint32_t>(msg[chunk + i * 4 + 1]) << 16) |
                   (static_cast<std::uint32_t>(msg[chunk + i * 4 + 2]) << 8) |
                   (static_cast<std::uint32_t>(msg[chunk + i * 4 + 3]));
        }
        for (std::size_t i = 16; i < 64; ++i) {
            std::uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            std::uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }

        std::uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
        std::uint32_t e = h[4], f = h[5], g = h[6], h_val = h[7];

        for (std::size_t i = 0; i < 64; ++i) {
            std::uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            std::uint32_t ch = (e & f) ^ ((~e) & g);
            std::uint32_t temp1 = h_val + S1 + ch + K[i] + w[i];
            std::uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            std::uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            std::uint32_t temp2 = S0 + maj;

            h_val = g;
            g = f;
            f = e;
            e = d + temp1;
            d = c;
            c = b;
            b = a;
            a = temp1 + temp2;
        }

        h[0] += a; h[1] += b; h[2] += c; h[3] += d;
        h[4] += e; h[5] += f; h[6] += g; h[7] += h_val;
    }

    for (std::size_t i = 0; i < 8; ++i) {
        digest[i * 4]     = static_cast<std::uint8_t>((h[i] >> 24) & 0xff);
        digest[i * 4 + 1] = static_cast<std::uint8_t>((h[i] >> 16) & 0xff);
        digest[i * 4 + 2] = static_cast<std::uint8_t>((h[i] >> 8) & 0xff);
        digest[i * 4 + 3] = static_cast<std::uint8_t>(h[i] & 0xff);
    }
}

} // namespace detail

// ── ModelHeader ───────────────────────────────────────────────────────────
#pragma pack(push, 1)
struct ModelHeader {
    char                         magic[4]       = {'K', 'L', 'I', 'F'};
    std::uint32_t                format_version = 1;
    std::uint32_t                num_trees      = 0;
    std::uint32_t                subsample_size = 0;
    std::uint32_t                num_features   = 0;
    std::uint32_t                payload_size   = 0;
    double                       c_psi          = 0.0;
    std::array<std::uint8_t, 32> checksum{};
};
#pragma pack(pop)
static_assert(sizeof(ModelHeader) == 64, "ModelHeader must be exactly 64 bytes");


// ── IsolationTree ─────────────────────────────────────────────────────────
template <std::size_t D>
class IsolationTree {
public:
    using Point = std::array<float, D>;

    struct Node {
        int   feature      = -1;   // -1 marks a leaf
        float split        = 0.0f;
        int   left         = -1;   // index into nodes_, -1 if unset
        int   right        = -1;
        int   size_at_leaf = 0;    // points count at leaf for c(n) correction
    };

    void build(std::vector<Point> points, int height_limit, std::mt19937& rng) {
        nodes_.clear();
        nodes_.reserve(2 * points.size());
        root_ = build_node(points, 0, height_limit, rng);
    }

    [[nodiscard]] double path_length(const Point& x) const {
        if (nodes_.empty() || root_ < 0) return 0.0;
        int node_idx = root_;
        int depth = 0;
        while (node_idx >= 0 && node_idx < static_cast<int>(nodes_.size())) {
            const Node& n = nodes_[node_idx];
            if (n.feature == -1) {
                return depth + c_factor(n.size_at_leaf);
            }
            ++depth;
            node_idx = (x[n.feature] < n.split) ? n.left : n.right;
        }
        return depth;
    }

    static double c_factor(int n) {
        if (n <= 1) return 0.0;
        if (n == 2) return 1.0;
        constexpr double EULER_GAMMA = 0.5772156649015328606065;
        return 2.0 * (std::log(static_cast<double>(n - 1)) + EULER_GAMMA)
             - 2.0 * static_cast<double>(n - 1) / static_cast<double>(n);
    }

    void serialize_payload(std::vector<std::uint8_t>& buf) const {
        std::uint64_t n = nodes_.size();
        auto append = [&](const void* ptr, std::size_t sz) {
            const auto* byte_ptr = reinterpret_cast<const std::uint8_t*>(ptr);
            buf.insert(buf.end(), byte_ptr, byte_ptr + sz);
        };
        append(&n, sizeof(n));
        if (n > 0) append(nodes_.data(), n * sizeof(Node));
        append(&root_, sizeof(root_));
    }

    void deserialize_payload(const std::uint8_t*& ptr, const std::uint8_t* end) {
        if (ptr + sizeof(std::uint64_t) > end) {
            throw std::runtime_error("Corrupted payload: unexpected EOF reading node count");
        }
        std::uint64_t n = 0;
        std::memcpy(&n, ptr, sizeof(n));
        ptr += sizeof(n);

        if (n > 100'000'000 || ptr + n * sizeof(Node) > end) {
            throw std::runtime_error("Corrupted payload: node count exceeds payload boundary");
        }
        nodes_.resize(n);
        if (n > 0) {
            std::memcpy(nodes_.data(), ptr, n * sizeof(Node));
            ptr += n * sizeof(Node);
        }

        if (ptr + sizeof(root_) > end) {
            throw std::runtime_error("Corrupted payload: unexpected EOF reading root index");
        }
        std::memcpy(&root_, ptr, sizeof(root_));
        ptr += sizeof(root_);
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
        if (left_pts.empty() || right_pts.empty()) {
            n.size_at_leaf = static_cast<int>(points.size());
            nodes_.push_back(n);
            return static_cast<int>(nodes_.size()) - 1;
        }

        n.feature = feature;
        n.split   = split;
        int self_idx = static_cast<int>(nodes_.size());
        nodes_.push_back(n);
        int left_idx  = build_node(left_pts,  depth + 1, height_limit, rng);
        int right_idx = build_node(right_pts, depth + 1, height_limit, rng);
        nodes_[self_idx].left  = left_idx;
        nodes_[self_idx].right = right_idx;
        return self_idx;
    }

    std::vector<Node> nodes_;
    int               root_ = -1;
};

// ── IsolationForest ────────────────────────────────────────────────────────
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

    void fit(const std::vector<Point>& points) {
        int height_limit = static_cast<int>(std::ceil(std::log2(
            static_cast<double>(std::max(2, psi_)))));
        trees_.clear();
        trees_.reserve(n_estimators_);

        for (int t = 0; t < n_estimators_; ++t) {
            std::vector<Point> sample;
            sample.reserve(psi_);
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
        if (trees_.empty() || c_psi_ <= 0.0) return 0.5;
        double total = 0.0;
        for (const auto& tree : trees_) total += tree.path_length(x);
        double avg_path = total / static_cast<double>(trees_.size());
        return std::pow(2.0, -avg_path / c_psi_);
    }

    [[nodiscard]] std::size_t n_trees() const noexcept { return trees_.size(); }
    [[nodiscard]] int subsample_size() const noexcept { return psi_; }
    [[nodiscard]] double c_psi() const noexcept { return c_psi_; }

    void save(std::ostream& out) const {
        std::vector<std::uint8_t> payload;
        for (const auto& tree : trees_) {
            tree.serialize_payload(payload);
        }

        ModelHeader header;
        header.format_version = 1;
        header.num_trees      = static_cast<std::uint32_t>(trees_.size());
        header.subsample_size = static_cast<std::uint32_t>(psi_);
        header.num_features   = static_cast<std::uint32_t>(D);
        header.payload_size   = static_cast<std::uint64_t>(payload.size());
        header.c_psi          = c_psi_;

        detail::sha256(payload.data(), payload.size(), header.checksum);

        out.write(reinterpret_cast<const char*>(&header), sizeof(header));
        if (!payload.empty()) {
            out.write(reinterpret_cast<const char*>(payload.data()), payload.size());
        }
        out.flush();
    }

    void save(const std::string& path) const {
        std::ofstream out(path, std::ios::binary);
        if (!out) {
            throw std::runtime_error("Failed to open file for writing model: " + path);
        }
        save(out);
    }

    void load(std::istream& in) {
        ModelHeader header;
        in.read(reinterpret_cast<char*>(&header), sizeof(header));
        if (!in || in.gcount() < static_cast<std::streamsize>(sizeof(header))) {
            throw std::runtime_error("Invalid model file: truncated header");
        }

        if (std::memcmp(header.magic, "KLIF", 4) != 0) {
            throw std::runtime_error("Invalid model file: magic mismatch (expected 'KLIF')");
        }

        if (header.format_version != 1) {
            throw std::runtime_error("Unsupported model version: " + std::to_string(header.format_version));
        }

        if (header.num_features != D) {
            throw std::runtime_error("Feature dimension mismatch (expected " + std::to_string(D) +
                                     ", got " + std::to_string(header.num_features) + ")");
        }

        std::vector<std::uint8_t> payload(header.payload_size);
        if (header.payload_size > 0) {
            in.read(reinterpret_cast<char*>(payload.data()), header.payload_size);
            if (!in || in.gcount() < static_cast<std::streamsize>(header.payload_size)) {
                throw std::runtime_error("Invalid model file: truncated payload");
            }
        }

        std::array<std::uint8_t, 32> computed_checksum{};
        detail::sha256(payload.data(), payload.size(), computed_checksum);
        if (computed_checksum != header.checksum) {
            throw std::runtime_error("Model integrity check failed: payload checksum mismatch (corrupted model)");
        }

        trees_.clear();
        trees_.reserve(header.num_trees);
        const std::uint8_t* ptr = payload.data();
        const std::uint8_t* end = payload.data() + payload.size();

        for (std::uint32_t i = 0; i < header.num_trees; ++i) {
            IsolationTree<D> tree;
            tree.deserialize_payload(ptr, end);
            trees_.push_back(std::move(tree));
        }

        n_estimators_ = static_cast<int>(header.num_trees);
        psi_          = static_cast<int>(header.subsample_size);
        c_psi_        = header.c_psi;
    }

    void load(const std::string& path) {
        std::ifstream in(path, std::ios::binary);
        if (!in) {
            throw std::runtime_error("Failed to open file for reading model: " + path);
        }
        load(in);
    }

private:
    int                           n_estimators_;
    int                           psi_;
    std::mt19937                  rng_;
    double                        c_psi_ = 1.0;
    std::vector<IsolationTree<D>> trees_;
};

} // namespace klstream
