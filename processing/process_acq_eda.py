import argparse
import pandas as pd
import numpy as np

# Monkey-patch numpy for neurokit2 compatibility with numpy 2.0
if not hasattr(np, 'trapz'):
    if hasattr(np, 'trapezoid'):
        np.trapz = np.trapezoid
    else:
        from scipy import integrate
        np.trapz = integrate.trapezoid

import bioread
import neurokit2 as nk
import sys
import os

def find_eda_channel(data):
    """
    Attempts to find the EDA channel by name.
    """
    # Common names for Electrodermal Activity
    # GSR = Galvanic Skin Response
    # EDA = Electrodermal Activity
    # SC = Skin Conductance
    target_names = ["EDA", "GSR", "SC", "SKIN"]
    
    for channel in data.channels:
        c_name = channel.name.upper()
        for t in target_names:
            if t in c_name:
                return channel
            
    # If not found, list available debugging
    print("EDA Channel not found. Available channels:")
    for c in data.channels:
        print(f" - {c.name}")
    return None

def process_eda(channel, fs, events_df):
    """
    Process EDA signal.
    Returns DataFrame with processed signals (Clean, Phasic, Tonic, SCR Onsets, etc.)
    """
    print(f"Processing {channel.name} with sampling rate {fs}Hz")
    
    # 1. Clean & Decompose
    # 'neurokit' method is standard
    try:
        signals, info = nk.eda_process(channel.data, sampling_rate=fs, method="neurokit")
    except Exception as e:
        print(f"EDA processing failed: {e}")
        return pd.DataFrame()
    
    # signals usually contains:
    # 'EDA_Raw', 'EDA_Clean', 'EDA_Tonic', 'EDA_Phasic', 'SCR_Onsets', 'SCR_Peaks', 'SCR_Height', 'SCR_Amplitude', 'SCR_RecoveryTime'
    
    # Add Event Label if matching
    if events_df is not None and not events_df.empty:
        signals['Event_Label'] = None
        for _, row in events_df.iterrows():
            label = row['event_label']
            start_time = row['start_time']
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
    parser.add_argument("--output_dir", required=True)
    
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
    eda_chan = find_eda_channel(data)
    if eda_chan is None:
        print("No EDA channel found.")
        sys.exit(0) # Exit gracefully if just no channel
        
    # Process
    signals_df = process_eda(eda_chan, data.samples_per_second, events_df)
    
    if not signals_df.empty:
        output_filename = f"processed_eda_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
        output_file = os.path.join(args.output_dir, output_filename)
        signals_df.to_csv(output_file, index=False)
        print(f"Processed EDA signals saved to {output_file}")
    else:
        print("No processed EDA data generated.")

if __name__ == "__main__":
    main()
