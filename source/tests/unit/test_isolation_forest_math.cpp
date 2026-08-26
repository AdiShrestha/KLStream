#include <gtest/gtest.h>
#include <klstream/model/isolation_forest.hpp>
#include <random>
#include <vector>
#include <cmath>

using namespace klstream;

TEST(IsolationForestMathTest, AveragePathLengthFormulaKnownAnswers) {
    EXPECT_DOUBLE_EQ(IsolationTree<5>::c_factor(0), 0.0);
    EXPECT_DOUBLE_EQ(IsolationTree<5>::c_factor(1), 0.0);
    EXPECT_DOUBLE_EQ(IsolationTree<5>::c_factor(2), 1.0);

    // Analytical verification for n = 10
    // c(10) = 2*(ln(9) + 0.5772156649) - 2*(9)/10
    constexpr double gamma = 0.5772156649015328606065;
    double expected_c10 = 2.0 * (std::log(9.0) + gamma) - 2.0 * 9.0 / 10.0;
    EXPECT_NEAR(IsolationTree<5>::c_factor(10), expected_c10, 1e-9);

    // Analytical verification for n = 256
    double expected_c256 = 2.0 * (std::log(255.0) + gamma) - 2.0 * 255.0 / 256.0;
    EXPECT_NEAR(IsolationTree<5>::c_factor(256), expected_c256, 1e-9);
}

TEST(IsolationForestMathTest, OutlierSeparationGaussian) {
    std::mt19937 rng(1337);
    std::normal_distribution<float> norm(0.0f, 1.0f);

    std::vector<IsolationForest<5>::Point> train_data;
    train_data.reserve(1000);
    for (int i = 0; i < 1000; ++i) {
        train_data.push_back({norm(rng), norm(rng), norm(rng), norm(rng), norm(rng)});
    }

    IsolationForest<5> forest(100, 256, 42);
    forest.fit(train_data);

    IsolationForest<5>::Point inlier{0.05f, -0.02f, 0.01f, -0.04f, 0.02f};
    IsolationForest<5>::Point outlier{8.0f, 8.0f, 8.0f, 8.0f, 8.0f};

    double inlier_score = forest.anomaly_score(inlier);
    double outlier_score = forest.anomaly_score(outlier);

    // Anomaly score: inliers ~0.35-0.55, anomalies >0.70
    EXPECT_LT(inlier_score, 0.55);
    EXPECT_GT(outlier_score, 0.70);
    EXPECT_GT(outlier_score, inlier_score + 0.20);
}

TEST(IsolationForestMathTest, DeterministicTrainingReproduction) {
    std::mt19937 rng(4242);
    std::normal_distribution<float> norm(0.0f, 1.0f);

    std::vector<IsolationForest<5>::Point> data;
    data.reserve(500);
    for (int i = 0; i < 500; ++i) {
        data.push_back({norm(rng), norm(rng), norm(rng), norm(rng), norm(rng)});
    }

    IsolationForest<5> model1(50, 128, 999);
    model1.fit(data);

    IsolationForest<5> model2(50, 128, 999);
    model2.fit(data);

    for (int i = 0; i < 50; ++i) {
        IsolationForest<5>::Point q{norm(rng), norm(rng), norm(rng), norm(rng), norm(rng)};
        double s1 = model1.anomaly_score(q);
        double s2 = model2.anomaly_score(q);
        EXPECT_DOUBLE_EQ(s1, s2);
    }
}
