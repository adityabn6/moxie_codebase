import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

file_path = "processed_ecg_126641_TSST_Visit.csv"

def verify_ecg(file_path):
    print(f"Loading {file_path}...")
    try:
        cols = ['ECG_Clean', 'ECG_Rate', 'ECG_R_Peaks']
        df = pd.read_csv(file_path, usecols=cols)
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    # 1. Statistics
    rate = df['ECG_Rate']
    print("\n--- Statistics ---")
    print(f"Heart Rate Mean: {rate.mean():.2f} bpm (Std: {rate.std():.2f})")
    print(f"Heart Rate Min:  {rate.min():.2f} bpm")
    print(f"Heart Rate Max:  {rate.max():.2f} bpm")
    
    hr_outliers = ((rate > 200) | (rate < 40)).sum()
    print(f"\n--- Outlier Check ---")
    print(f"HR Outliers (>200 or <40): {hr_outliers} ({hr_outliers/len(df)*100:.2f}%)")

    # 2. Visualization
    # Plot a random 10-second segment
    fs = 2000
    duration = 10
    n_samples = fs * duration
    
    # Pick a segment in the middle
    mid_idx = len(df) // 2
    start_idx = mid_idx
    end_idx = start_idx + n_samples
    
    if end_idx > len(df):
        end_idx = len(df)
        start_idx = end_idx - n_samples
    
    segment = df.iloc[start_idx:end_idx].reset_index(drop=True)
    time = np.arange(len(segment)) / fs
    
    # Use subplots to separate Signal and Rate (Improved View)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    
    # Top Plot: ECG Waveform
    ax1.plot(time, segment['ECG_Clean'], label='ECG (Clean)', color='black', alpha=0.8, linewidth=1)
    
    # Plot R-Peaks
    peaks = segment[segment['ECG_R_Peaks'] == 1].index
    if len(peaks) > 0:
        ax1.scatter(time[peaks], segment.loc[peaks, 'ECG_Clean'], color='red', s=50, zorder=5, label='R-Peaks')
    
    ax1.set_title(f"ECG Waveform (10s Segment, Index {start_idx}-{end_idx})")
    ax1.set_ylabel("Amplitude (mV)")
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Bottom Plot: Heart Rate
    ax2.plot(time, segment['ECG_Rate'], label='Heart Rate (bpm)', color='blue', linewidth=2)
    
    ax2.set_title("Instantaneous Heart Rate")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("BPM")
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    plot_file = "ecg_verification_plot.png"
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

if __name__ == "__main__":
    verify_ecg(file_path)
