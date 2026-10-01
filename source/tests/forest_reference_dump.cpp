// Explicit test fixtures. Dumps observed tree structure for a separate Python
// oracle; these scores are never accepted research measurements.
#include <klstream/model/isolation_forest.hpp>
#include <iomanip>
#include <iostream>
int main() {
    using Forest=klstream::IsolationForest<3>;
    const std::vector<Forest::Point> training{{0,0,1},{0,1,1},{1,0,1},{1,1,1},{2,2,1},{3,-1,1},{9,4,1}};
    Forest forest(17,7,11);forest.fit(training);
    std::cout<<std::setprecision(17)<<"{\"psi\":"<<forest.subsample_size()<<",\"c\":"<<forest.c_psi()<<",\"trees\":[";
    bool first_tree=true;
    for(const auto& tree:forest.tree_snapshot()) {
        if(!first_tree)std::cout<<',';first_tree=false;std::cout<<'[';bool first=true;
        for(const auto& node:tree) {
            if(!first)std::cout<<',';first=false;
            std::cout<<'['<<node.leaf<<','<<node.feature<<','<<node.left<<','<<node.right<<','<<node.split<<','<<node.correction<<','<<node.sample_count<<']';
        }std::cout<<']';
    }
    std::cout<<"],\"training\":[";
    for(std::size_t i=0;i<training.size();++i) { if(i)std::cout<<',';const auto& p=training[i];std::cout<<'['<<p[0]<<','<<p[1]<<','<<p[2]<<']'; }
    std::cout<<"],\"queries\":[";
    const std::vector<Forest::Point> queries{{0,0,1},{.5f,.5f,1},{-5,3,1},{20,20,1},{9,4,1}};
    for(std::size_t i=0;i<queries.size();++i) { if(i)std::cout<<',';const auto& p=queries[i];std::cout<<'['<<p[0]<<','<<p[1]<<','<<p[2]<<','<<forest.anomaly_score(p)<<']'; }
    std::cout<<"]}\n";
}
