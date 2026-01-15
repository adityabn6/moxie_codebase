import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

file_path = "processed_rsp_126641_TSST_Visit.csv"

def verify_rsp(file_path):
    print(f"Loading {file_path}...")
    try:
        # Load first few rows to check columns
        df_iter = pd.read_csv(file_path, chunksize=1000)
        df_head = next(df_iter)
        all_cols = df_head.columns.tolist()
        
        # Identify Channels based on 'RSP_Clean_' prefix
        clean_cols = [c for c in all_cols if c.startswith("RSP_Clean_")]
        print(f"Found {len(clean_cols)} Respiration Channels: {clean_cols}")
        
        # Now load full file (or enough chunks)
        # For verification, we can just load the whole thing
        df = pd.read_csv(file_path)
        
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    fs = 2000
    
    # Setup Plot
    fig, axes = plt.subplots(len(clean_cols), 1, figsize=(15, 5 * len(clean_cols)), sharex=True)
    if len(clean_cols) == 1:
        axes = [axes]
        
    # Process each channel
    for i, clean_col in enumerate(clean_cols):
        # Extract suffix
        suffix = clean_col.replace("RSP_Clean_", "")
        rate_col = f"RSP_Rate_{suffix}"
        peaks_col = f"RSP_Peaks_{suffix}"
        
        print(f"\n--- Channel: {suffix} ---")
        
        # Stats
        if rate_col in df.columns:
            rate = df[rate_col]
            print(f"Resp Rate Mean: {rate.mean():.2f} brpm (Std: {rate.std():.2f})")
            print(f"Resp Rate Range: {rate.min():.2f} - {rate.max():.2f} brpm")
        else:
            print("Rate column not found.")
            
        if peaks_col in df.columns:
            peak_count = df[peaks_col].sum()
            duration_min = len(df) / fs / 60
            print(f"Total Breaths: {peak_count} ({peak_count/duration_min:.2f} per min)")
        
        # Visualization (60s segment)
        duration = 60
        n_samples = fs * duration
        mid_idx = len(df) // 2
        start_idx = mid_idx
        end_idx = start_idx + n_samples
        
        segment = df.iloc[start_idx:end_idx].reset_index(drop=True)
        time = np.arange(len(segment)) / fs
        
        ax = axes[i]
        ax.plot(time, segment[clean_col], label=f'RSP Clean ({suffix})', color='teal', alpha=0.8)
        
        # Plot Peaks
        if peaks_col in segment.columns:
            peaks = segment[segment[peaks_col] == 1].index
            if len(peaks) > 0:
                ax.scatter(time[peaks], segment.loc[peaks, clean_col], color='orange', s=50, zorder=5, label='Inhalation Peak')
        
        # Plot Rate on twin axis
        if rate_col in segment.columns:
            ax2 = ax.twinx()
            ax2.plot(time, segment[rate_col], color='grey', linestyle='--', alpha=0.5, label='Rate Trend')
            ax2.set_ylabel("Rate (brpm)", color='grey')
            
        ax.set_title(f"Respiration Channel: {suffix}")
        ax.set_ylabel("Volts")
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    plt.xlabel("Time (s)")
    plt.tight_layout()
    
    # Save plot
    plot_file = "rsp_verification_plot.png"
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

if __name__ == "__main__":
    verify_rsp(file_path)
