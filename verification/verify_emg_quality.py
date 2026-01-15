import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

file_path = "processed_emg_126641_TSST_Visit.csv"

def verify_emg(file_path):
    print(f"Loading {file_path}...")
    try:
        # Load first few rows to check columns
        df_iter = pd.read_csv(file_path, chunksize=1000)
        df_head = next(df_iter)
        all_cols = df_head.columns.tolist()
        
        # Identify Channels based on 'EMG_Clean_' prefix
        clean_cols = [c for c in all_cols if c.startswith("EMG_Clean_")]
        print(f"Found {len(clean_cols)} EMG Channels: {clean_cols}")
        
        # Load full
        df = pd.read_csv(file_path)
        
    except Exception as e:
        print(f"Failed to load: {e}")
        return

    fs = 2000
    
    # Setup Plot
    fig, axes = plt.subplots(len(clean_cols), 1, figsize=(15, 6 * len(clean_cols)), sharex=True)
    if len(clean_cols) == 1:
        axes = [axes]
        
    # Process each channel
    for i, clean_col in enumerate(clean_cols):
        # Extract suffix
        suffix = clean_col.replace("EMG_Clean_", "")
        amp_col = f"EMG_Amplitude_{suffix}"
        act_col = f"EMG_Activity_{suffix}"
        
        print(f"\n--- Channel: {suffix} ---")
        
        # Stats
        if amp_col in df.columns:
            amp = df[amp_col]
            print(f"Mean Amplitude: {amp.mean():.4f} V (Max: {amp.max():.4f})")
            
        if act_col in df.columns:
            activity_ratio = df[act_col].mean()
            print(f"Activity Ratio: {activity_ratio*100:.2f}% of time active")
        
        # Visualization (10s segment for EMG to see bursts)
        duration = 10
        n_samples = fs * duration
        mid_idx = len(df) // 2
        start_idx = mid_idx
        end_idx = start_idx + n_samples
        
        segment = df.iloc[start_idx:end_idx].reset_index(drop=True)
        time = np.arange(len(segment)) / fs
        
        ax = axes[i]
        
        # Plot Clean Signal
        ax.plot(time, segment[clean_col], label=f'EMG Clean', color='silver', alpha=0.8, linewidth=0.5)
        
        # Plot Amplitude Envelope
        if amp_col in segment.columns:
            ax.plot(time, segment[amp_col], label=f'Amplitude Envelope', color='red', linewidth=1.5)
            
        # Highlight Activity
        if act_col in segment.columns:
            # Scale activity for visibility overlay
            active_regions = segment[act_col] * segment[amp_col].max()
            ax.fill_between(time, 0, active_regions, where=segment[act_col]==1, color='orange', alpha=0.3, label='Detected Activity')
            
        ax.set_title(f"EMG Channel: {suffix}")
        ax.set_ylabel("Amplitude (V)")
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

    plt.xlabel("Time (s)")
    plt.tight_layout()
    
    # Save plot
    plot_file = "emg_verification_plot.png"
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

if __name__ == "__main__":
    verify_emg(file_path)
