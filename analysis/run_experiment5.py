#!/usr/bin/env python3
import subprocess

def run_experiment_5():
    print("--- Running Experiment 5: Controller Overhead ---")
    
    architectures = ["datadriven", "adaptive"]
    
    for arch in architectures:
        print(f"\nRunning architecture={arch} for 5s to measure overhead...")
        cmd = [
            "./build/adaptive_window/adaptive_window_main",
            f"--architecture={arch}",
            "--out=results/raw/exp5_temp.csv",
            "--duration=5"
        ]
        
        # Run and capture stdout to parse "Mean Controller Overhead"
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        for line in result.stdout.split('\n'):
            if "Mean Controller Overhead" in line:
                print(f"[{arch}] {line.strip()}")

if __name__ == "__main__":
    run_experiment_5()
