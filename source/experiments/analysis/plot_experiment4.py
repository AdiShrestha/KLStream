#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt

def plot_sensitivity_grid():
    df = pd.read_csv("results/experiment4_grid.csv")
    
    # Create a unified string identifier for the grid point
    df['Config'] = df.apply(lambda r: f"({r['occ_low']},{r['occ_high']})\n({r['shrink']},{r['grow']})", axis=1)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot Pareto Frontier
    sc = ax.scatter(df['p95_lat_ms'], df['pa20_f1'], s=100, c='blue', alpha=0.7)
    
    for i, row in df.iterrows():
        ax.annotate(row['Config'], (row['p95_lat_ms'], row['pa20_f1']), 
                    xytext=(5, 5), textcoords='offset points', fontsize=8, alpha=0.8)
                    
    # Optional: If you ran fixed and datadriven and have their stats, you could plot them as red/green stars here.
    # We will just plot the adaptive sweep for now.
    
    ax.set_title("Experiment 4: Sensitivity Grid (P95 Latency vs PA%20 F1)")
    ax.set_xlabel("P95 Latency (ms) - LOWER is better")
    ax.set_ylabel("PA%20 F1 Score - HIGHER is better")
    
    plt.tight_layout()
    plt.savefig("results/experiment4_pareto.png", dpi=300)
    print("Saved plot to results/experiment4_pareto.png")

if __name__ == "__main__":
    plot_sensitivity_grid()
