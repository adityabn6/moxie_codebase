import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

file_path = "processed_eda_126641_TSST_Visit.csv"

def verify_eda(file_path):
    print(f"Loading {file_path}...")
    try:
        # Load columns
        # EDA_Clean, EDA_Tonic, EDA_Phasic, SCR_Peaks
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    # 1. Statistics
    clean = df['EDA_Clean']
    tonic = df['EDA_Tonic']
    phasic = df['EDA_Phasic'] # Driver
    
    # SCR Peaks (Binary column usually indicating peak location)
    # Check if SCR_Peaks exists
    if 'SCR_Peaks' in df.columns:
        scr_count = df['SCR_Peaks'].sum()
    else:
        scr_count = 0
        
    print("\n--- Statistics ---")
    print(f"EDA Mean:   {clean.mean():.2f} uS (Std: {clean.std():.2f})")
    print(f"Tonic Mean: {tonic.mean():.2f} uS")
    print(f"Phasic Max: {phasic.max():.2f} uS")
    print(f"Total SCRs detected: {scr_count} ({scr_count / (len(df)/2000/60):.2f} per minute)")
    
    # Check for negative values (EDA should generally be positive, uS)
    neg_values = (clean < 0).sum()
    print(f"\nNegative Signal Values: {neg_values} ({neg_values/len(df)*100:.2f}%)")

    # 2. Visualization
    # Plot a random 60-second segment (EDA changes slower than ECG)
    fs = 2000
    duration = 60
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
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    
    # Plot 1: Overall Signal + Tonic
    ax1.plot(time, segment['EDA_Clean'], label='EDA (Clean)', color='purple', alpha=0.7)
    ax1.plot(time, segment['EDA_Tonic'], label='Tonic Component', color='orange', linestyle='--', linewidth=2)
    
    # Mark SCR Peaks on the main signal
    if 'SCR_Peaks' in segment.columns:
        peaks = segment[segment['SCR_Peaks'] == 1].index
        if len(peaks) > 0:
            ax1.scatter(time[peaks], segment.loc[peaks, 'EDA_Clean'], color='red', s=50, zorder=5, label='SCR Peak')

    ax1.set_title(f"EDA Signal & Tonic Component (60s Segment)")
    ax1.set_ylabel("Conductance (uS)")
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Phasic Component (Driver)
    ax2.plot(time, segment['EDA_Phasic'], label='Phasic Component', color='green', alpha=0.8)
    ax2.set_title("Phasic Component (Rapid Changes)")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Conductance (uS)")
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    plot_file = "eda_verification_plot.png"
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

if __name__ == "__main__":
    verify_eda(file_path)
