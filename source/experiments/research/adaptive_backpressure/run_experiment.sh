#!/usr/bin/env bash
# research/adaptive_backpressure/run_experiment.sh

BUILD=./build/research/adaptive_backpressure
RESULTS=./research/results
mkdir -p $RESULTS

for MODE in baseline adaptive; do
  for QSIZE in 256 1024 4096; do
    for BURST in low medium high; do
      echo "Mode=$MODE QSize=$QSIZE Burst=$BURST"
      $BUILD/adaptive_bp_experiment \
          --mode=$MODE \
          --queue_size=$QSIZE \
          --burst_level=$BURST \
          --duration=1 \
          > $RESULTS/bp_${MODE}_q${QSIZE}_${BURST}.csv
    done
  done
done
