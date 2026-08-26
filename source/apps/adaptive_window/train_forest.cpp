#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <sstream>
#include "klstream/model/isolation_forest.hpp"

using namespace klstream;

int main() {
    std::cout << "Loading training data..." << std::endl;
    std::ifstream f("data/replay/isoforest_validation_train.csv");
    if (!f) {
        std::cerr << "Failed to open isoforest_validation_train.csv" << std::endl;
        return 1;
    }

    std::string line;
    std::getline(f, line); // header
    std::vector<std::array<float, 5>> train_data;
    while (std::getline(f, line)) {
        std::stringstream ss(line);
        std::string cell;
        float features[5];
        for (int i = 0; i < 5; ++i) {
            std::getline(ss, cell, ',');
            features[i] = std::stof(cell);
        }
        std::array<float, 5> p;
        for (int i=0; i<5; ++i) p[i] = features[i];
        train_data.push_back(p);
    }

    std::cout << "Loaded " << train_data.size() << " samples for training." << std::endl;
    std::cout << "Training Isolation Forest..." << std::endl;

    IsolationForest<5> forest(100, 256); // n_estimators=100, psi=256
    forest.fit(train_data);

    std::cout << "Training complete. Saving to data/forest.bin..." << std::endl;
    std::ofstream out("data/forest.bin", std::ios::binary);
    forest.save(out);
    out.close();

    std::cout << "Loading holdout data for validation..." << std::endl;
    std::ifstream f_test("data/replay/isoforest_validation_holdout.csv");
    if (!f_test) {
        std::cerr << "Failed to open validation holdout CSV" << std::endl;
        return 1;
    }

    std::getline(f_test, line); // header
    std::ofstream out_scores("data/replay/isoforest_validation_cpp_scores.csv");
    out_scores << "cpp_score\n";

    int count = 0;
    while (std::getline(f_test, line)) {
        std::stringstream ss(line);
        std::string cell;
        float features[5];
        for (int i = 0; i < 5; ++i) {
            std::getline(ss, cell, ',');
            features[i] = std::stof(cell);
        }
        std::array<float, 5> p;
        for (int i=0; i<5; ++i) p[i] = features[i];
        
        double score = forest.anomaly_score(p);
        out_scores << score << "\n";
        ++count;
    }
    std::cout << "Scored " << count << " holdout points." << std::endl;
    std::cout << "Validation scores saved to data/replay/isoforest_validation_cpp_scores.csv." << std::endl;

    return 0;
}
