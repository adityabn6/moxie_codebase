import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys

# Default file
file_path = "processed_hex_rsp_124961_TSST_Visit.csv"
if len(sys.argv) > 1:
    file_path = sys.argv[1]

def verify_hexo_rsp(file_path):
    print(f"Loading {file_path}...")
    try:
        # Load header first
        df_head = pd.read_csv(file_path, nrows=1)
        all_cols = df_head.columns.tolist()
        
        # Identify Channels
        thoracic = [c for c in all_cols if "Thoracic" in c]
        abdominal = [c for c in all_cols if "Abdominal" in c]
        
        if not thoracic and not abdominal:
            print("No Thoracic or Abdominal columns found!")
            return
            
        print(f"Found Thoracic columns: {len(thoracic)}")
        print(f"Found Abdominal columns: {len(abdominal)}")
        
        # Load Full
        df = pd.read_csv(file_path)
        
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    fs = 256
    
    # Setup Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), sharex=True)
    
    # 1. Thoracic
    print("\n--- Thoracic ---")
    if 'RSP_Rate_Thoracic' in df.columns:
        rate = df['RSP_Rate_Thoracic']
        print(f"Rate Mean: {rate.mean():.2f} brpm (Std: {rate.std():.2f})")
    
    # 2. Abdominal
    print("\n--- Abdominal ---")
    if 'RSP_Rate_Abdominal' in df.columns:
        rate = df['RSP_Rate_Abdominal']
        print(f"Rate Mean: {rate.mean():.2f} brpm (Std: {rate.std():.2f})")

    # Check Events
    if 'Event_Label' in df.columns:
        labels = df['Event_Label'].unique()
        print(f"\nEvent Labels Found: {labels}")
    else:
        print("\nNo Event_Label column found.")

    # Visualization (60s segment)
    duration = 60
    n_samples = fs * duration
    mid_idx = len(df) // 2
    start_idx = mid_idx
    end_idx = start_idx + n_samples
    if end_idx > len(df):
        end_idx = len(df)
        start_idx = end_idx - n_samples
        
    segment = df.iloc[start_idx:end_idx].reset_index(drop=True)
    time = np.arange(len(segment)) / fs
    
    # Plot Thoracic
    if 'RSP_Clean_Thoracic' in segment.columns:
        ax1.plot(time, segment['RSP_Clean_Thoracic'], label='Thoracic (Clean)', color='teal')
        if 'RSP_Peaks_Thoracic' in segment.columns:
            peaks = segment[segment['RSP_Peaks_Thoracic'] == 1].index
            if len(peaks) > 0:
                ax1.scatter(time[peaks], segment.loc[peaks, 'RSP_Clean_Thoracic'], color='orange', s=30, zorder=5)
    
    # Plot Rate on twin
    if 'RSP_Rate_Thoracic' in segment.columns:
        ax1t = ax1.twinx()
        ax1t.plot(time, segment['RSP_Rate_Thoracic'], color='grey', linestyle='--', alpha=0.5, label='Rate')
        ax1t.set_ylabel("BRPM")
        
    ax1.set_title("Thoracic Respiration")
    ax1.legend(loc='upper right')
    
    # Plot Abdominal
    if 'RSP_Clean_Abdominal' in segment.columns:
        ax2.plot(time, segment['RSP_Clean_Abdominal'], label='Abdominal (Clean)', color='purple')
        if 'RSP_Peaks_Abdominal' in segment.columns:
            peaks = segment[segment['RSP_Peaks_Abdominal'] == 1].index
            if len(peaks) > 0:
                ax2.scatter(time[peaks], segment.loc[peaks, 'RSP_Clean_Abdominal'], color='orange', s=30, zorder=5)

    if 'RSP_Rate_Abdominal' in segment.columns:
        ax2t = ax2.twinx()
        ax2t.plot(time, segment['RSP_Rate_Abdominal'], color='grey', linestyle='--', alpha=0.5, label='Rate')
        ax2t.set_ylabel("BRPM")

    ax2.set_title("Abdominal Respiration")
    ax2.set_xlabel("Time (s)")
    ax2.legend(loc='upper right')

    plt.tight_layout()
    plot_file = "hex_rsp_verification_plot.png"
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

if __name__ == "__main__":
    verify_hexo_rsp(file_path)
