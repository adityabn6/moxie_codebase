import argparse
import pandas as pd
import numpy as np

# Monkey-patch numpy for neurokit2 compatibility with numpy 2.0
if not hasattr(np, 'trapz'):
    if hasattr(np, 'trapezoid'):
        np.trapz = np.trapezoid
    else:
        # Fallback if even trapezoid isn't there (unlikely in 2.0, but safe)
        from scipy import integrate
        np.trapz = integrate.trapezoid

import bioread
import neurokit2 as nk
import sys
import os

def find_ecg_channel(data):
    """
    Attempts to find the ECG channel by name.
    """
    possible_names = ["ECG", "EKG", "RSP", "Thoracic"] # expanding search to fail gracefully or notify
    # Prioritize ECG
    for channel in data.channels:
        if "ECG" in channel.name.upper() or "EKG" in channel.name.upper():
            return channel
            
    # If not found, list available
    print("ECG Channel not found. Available channels:")
    for c in data.channels:
        print(f" - {c.name}")
    return None

def process_ecg(channel, fs, events_df):
    """
    Process ECG signal.
    """
    print(f"Processing {channel.name} with sampling rate {fs}Hz")
    
    # 1. Clean
    ecg_cleaned = nk.ecg_clean(channel.data, sampling_rate=fs, method="neurokit")
    
    # 2. Find Peaks
    # Using 'neurokit' method which is generally robust
    signals, info = nk.ecg_process(ecg_cleaned, sampling_rate=fs)
    
    # signals dataframe contains 'ECG_Rate', 'ECG_Quality', 'ECG_R_Peaks', 'ECG_Clean', etc.
    
    # Add time column relative to start
    # signals['Time_Seconds'] = np.arange(len(signals)) / fs
    
    # If events are provided, we could map them, but for "clean simple scripts" keeping the signal 
    # file pure and separate from events file is often better. 
    # However, adding a 'Label' column if it overlaps with an event is helpful context.
    
    if events_df is not None and not events_df.empty:
        signals['Event_Label'] = None
        for _, row in events_df.iterrows():
            label = row['event_label']
            start_time = row['start_time']
            # Assume 1 second duration for markers if not specified? 
            # Or just mark the closest sample?
            start_idx = int(start_time * fs)
            if 0 <= start_idx < len(signals):
                 signals.at[start_idx, 'Event_Label'] = label
                 
    return signals

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--acq_file", required=True)
    parser.add_argument("--events_file", required=True)
    
    args = parser.parse_args()
    
    # Load Data
    try:
        data = bioread.read_file(args.acq_file)
    except Exception as e:
        print(f"Error reading ACQ: {e}")
        sys.exit(1)
        
    # Load Events
    if os.path.exists(args.events_file):
        events_df = pd.read_csv(args.events_file)
    else:
        print("Events file not found.")
        events_df = None
        
    # Find Channel
    ecg_chan = find_ecg_channel(data)
    if ecg_chan is None:
        print("No ECG channel found.")
        sys.exit(1)
        
    # Process
    signals_df = process_ecg(ecg_chan, data.samples_per_second, events_df)
    
    # Save - using 'processed' prefix
    output_file = f"processed_ecg_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
    
    # Save slightly compressed or just raw csv? 
    # CSV is fine for now.
    signals_df.to_csv(output_file, index=False)
    print(f"Processed signals saved to {output_file}")

if __name__ == "__main__":
    main()
