import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

file_path = "processed_bp_126641_TSST_Visit.csv"

def verify_bp(file_path):
    print(f"Loading {file_path}...")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    # 1. Sanity Checks on Values
    sbp = df['BP_Systolic_Interp']
    dbp = df['BP_Diastolic_Interp']
    clean = df['BP_Clean']
    
    # Pulse Pressure
    pp = sbp - dbp
    
    print("\n--- Statistics ---")
    print(f"SBP Mean: {sbp.mean():.2f} (Std: {sbp.std():.2f})")
    print(f"DBP Mean: {dbp.mean():.2f} (Std: {dbp.std():.2f})")
    print(f"PP Mean:  {pp.mean():.2f}  (Std: {pp.std():.2f})")
    
    # Outliers (Physiological bounds)
    # SBP > 250 or < 50
    # DBP > 150 or < 30
    sbp_outliers = ((sbp > 250) | (sbp < 50)).sum()
    dbp_outliers = ((dbp > 150) | (dbp < 30)).sum()
    
    print(f"\n--- Outlier Check ---")
    print(f"SBP Outliers (>250 or <50): {sbp_outliers} ({sbp_outliers/len(df)*100:.2f}%)")
    print(f"DBP Outliers (>150 or <30): {dbp_outliers} ({dbp_outliers/len(df)*100:.2f}%)")
    
    # Negative values check (impossible for absolute BP)
    neg_values = (clean < 0).sum()
    print(f"Negative Signal Values: {neg_values} ({neg_values/len(df)*100:.2f}%)")

    # 2. Visualization
    # Plot a random 30-second segment (FS=2000, so 60000 samples)
    fs = 2000
    duration = 30
    n_samples = fs * duration
    
    # Pick a segment in the middle
    mid_idx = len(df) // 2
    start_idx = mid_idx
    end_idx = start_idx + n_samples
    
    if end_idx > len(df):
        end_idx = len(df)
        start_idx = end_idx - n_samples
    
    segment = df.iloc[start_idx:end_idx]
    time = np.arange(len(segment)) / fs
    
    plt.figure(figsize=(15, 6))
    plt.plot(time, segment['BP_Clean'], label='BP Signal (Clean)', color='black', alpha=0.7, linewidth=0.8)
    plt.plot(time, segment['BP_Systolic_Interp'], label='Systolic Envelope', color='red', linestyle='--', linewidth=1.5)
    plt.plot(time, segment['BP_Diastolic_Interp'], label='Diastolic Envelope', color='blue', linestyle='--', linewidth=1.5)
    
    plt.title(f"Blood Pressure Segment (30s) - Index {start_idx} to {end_idx}")
    plt.xlabel("Time (s)")
    plt.ylabel("Pressure (mmHg)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Save plot
    plot_file = "bp_verification_plot.png"
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

if __name__ == "__main__":
    verify_bp(file_path)
