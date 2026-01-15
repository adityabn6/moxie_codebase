import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys

# Default file - updated dynamically if run via command line
file_path = "processed_hex_ecg_124961_TSST_Visit.csv"
if len(sys.argv) > 1:
    file_path = sys.argv[1]

def verify_hexo_ecg(file_path):
    print(f"Loading {file_path}...")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    # Check columns
    # Expected: ECG_Clean, ECG_Rate, ECG_R_Peaks
    required = ['ECG_Clean', 'ECG_Rate']
    msg = []
    for r in required:
        if r not in df.columns:
            msg.append(r)
    if msg:
        print(f"Missing columns: {msg}")
        return

    # 1. Statistics
    rate = df['ECG_Rate']
    print("\n--- Statistics ---")
    print(f"Hexoskin HR Mean: {rate.mean():.2f} bpm (Std: {rate.std():.2f})")
    print(f"Hexoskin HR Range: {rate.min():.2f} - {rate.max():.2f} bpm")
    
    # Outliers
    hr_outliers = ((rate > 200) | (rate < 40)).sum()
    print(f"HR Outliers (>200 or <40): {hr_outliers} ({hr_outliers/len(df)*100:.2f}%)")

    # 2. Visualization
    fs = 256
    duration = 10
    n_samples = fs * duration
    
    mid_idx = len(df) // 2
    start_idx = mid_idx
    end_idx = start_idx + n_samples
    if end_idx > len(df):
        end_idx = len(df)
        start_idx = end_idx - n_samples
        
    segment = df.iloc[start_idx:end_idx].reset_index(drop=True)
    time = np.arange(len(segment)) / fs
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    
    # Plot 1: Waveform
    ax1.plot(time, segment['ECG_Clean'], label='Hexoskin ECG (Clean)', color='blue', alpha=0.8)
    if 'ECG_R_Peaks' in segment.columns:
        peaks = segment[segment['ECG_R_Peaks'] == 1].index
        if len(peaks) > 0:
            ax1.scatter(time[peaks], segment.loc[peaks, 'ECG_Clean'], color='red', s=50, zorder=5, label='R-Peaks')
            
    ax1.set_title(f"Hexoskin ECG Segment (10s)")
    ax1.set_ylabel("Amplitude")
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Heart Rate
    ax2.plot(time, segment['ECG_Rate'], label='Heart Rate', color='darkred', linewidth=2)
    ax2.set_title("Heart Rate Trend")
    ax2.set_ylabel("BPM")
    ax2.set_xlabel("Time (s)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_file = "hex_ecg_verification_plot.png"
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

if __name__ == "__main__":
    verify_hexo_ecg(file_path)
