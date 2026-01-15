import argparse
import pandas as pd
import numpy as np
import bioread
import neurokit2 as nk
import sys
import os

def find_emg_channels(data):
    """
    Finds all EMG channels.
    """
    emg_channels = []
    print("Scanning for EMG channels...")
    for channel in data.channels:
        if "EMG" in channel.name.upper():
            print(f"  Found: {channel.name}")
            emg_channels.append(channel)
    return emg_channels

def process_single_emg(channel, fs, suffix):
    """
    Process a single EMG channel.
    """
    print(f"Processing {channel.name} (Suffix: {suffix})")
    
    try:
        # NeuroKit2 EMG Process
        # 1. Clean (Bandpass 100-900 usually? NK defaults are good: 100-500Hz for surface EMG)
        # 2. Activity (Activation detection)
        signals, info = nk.emg_process(channel.data, sampling_rate=fs)
        
        # Rename columns to be specific to this channel
        # Standard NK output: EMG_Raw, EMG_Clean, EMG_Amplitude, EMG_Activity, EMG_Onsets
        
        # We want to keep them distinct
        rename_map = {col: f"{col}_{suffix}" for col in signals.columns}
        signals = signals.rename(columns=rename_map)
        
        # Add raw if not in output (nk.emg_process returns a dataframe with Raw usually)
        if f"EMG_Raw_{suffix}" not in signals.columns:
             signals[f"EMG_Raw_{suffix}"] = channel.data
             
        return signals
        
    except Exception as e:
        print(f"Failed to process {channel.name}: {e}")
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--acq_file", required=True)
    parser.add_argument("--events_file", required=True)
    parser.add_argument("--output_dir", required=True)
    
    args = parser.parse_args()
    
    # Load Data
    try:
        data = bioread.read_file(args.acq_file)
    except Exception as e:
        print(f"Error reading ACQ: {e}")
        sys.exit(1)
        
    # Find Channels
    emg_channels = find_emg_channels(data)
    
    if not emg_channels:
        print("No EMG channels found.")
        sys.exit(0)
        
    # Load Events
    events_df = None
    if os.path.exists(args.events_file):
        events_df = pd.read_csv(args.events_file)
        
    # Process All Channels
    all_signals = []
    
    # We might have channel names like "EMG - Zygomatic", "EMG - Corrugator"
    # Or just "EMG1", "EMG2". 
    # Let's map them to manageable suffixes.
    
    for i, channel in enumerate(emg_channels):
        # Create a suffix based on channel name or index
        # remove spaces and weird chars
        safe_name = "".join([c for c in channel.name if c.isalnum() or c=='_'])
        suffix = f"Channel_{i+1}_{safe_name}"
        
        sig_df = process_single_emg(channel, data.samples_per_second, suffix)
        if not sig_df.empty:
            all_signals.append(sig_df)
            
    if not all_signals:
        print("No EMG signals generated.")
        sys.exit(0)
        
    # Concatenate columns
    final_df = pd.concat(all_signals, axis=1)
    
    # Add Event Labels (Just once)
    if events_df is not None and not events_df.empty:
        fs = data.samples_per_second
        final_df['Event_Label'] = None
        for _, row in events_df.iterrows():
            label = row['event_label']
            start_time = row['start_time']
            start_idx = int(start_time * fs)
            if 0 <= start_idx < len(final_df):
                 final_df.at[start_idx, 'Event_Label'] = label
                 
    # Save
    output_filename = f"processed_emg_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
    output_file = os.path.join(args.output_dir, output_filename)
    final_df.to_csv(output_file, index=False)
    print(f"Processed EMG signals saved to {output_file}")

if __name__ == "__main__":
    main()
