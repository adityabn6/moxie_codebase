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

def find_rsp_channels(data):
    """
    Finds all respiration channels.
    """
    rsp_channels = []
    
    for channel in data.channels:
        name = channel.name.upper()
        # Fallback to just "RSP" if specific names aren't found
        if "RSP" in name:
            rsp_channels.append(channel)
            
    return rsp_channels

def process_single_rsp(channel, fs, suffix):
    print(f"Processing {suffix} ({channel.name}) with sampling rate {fs}Hz")
    try:
        # NeuroKit cleaning and processing
        signals, info = nk.rsp_process(channel.data, sampling_rate=fs, method="khodadad2018")
        
        # Rename columns
        signals.columns = [f"{col}_{suffix}" for col in signals.columns]
        return signals
    except Exception as e:
        print(f"Failed to process {suffix}: {e}")
        return pd.DataFrame()

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
        
    # Find Channels
    rsp_channels = find_rsp_channels(data)
    
    if not rsp_channels:
        print("No Respiration channels found (RSP).")
        sys.exit(0)
        
    fs = data.samples_per_second
    
    combined = pd.DataFrame()
    
    # Process each found channel
    for i, chan in enumerate(rsp_channels):
        # Suffix using part of the name to be distinct but readable
        # e.g. RSP2208000207 -> RSP_1_2208000207
        # or just RSP_1, RSP_2
        suffix = f"Channel_{i+1}_{chan.name.replace(' ', '_')}"
        
        df_res = process_single_rsp(chan, fs, suffix)
        
        if not df_res.empty:
            if combined.empty:
                combined = df_res
            else:
                combined = pd.concat([combined, df_res], axis=1)

    # Add Event Labels if exists
    if os.path.exists(args.events_file) and not combined.empty:
        events_df = pd.read_csv(args.events_file)
        combined['Event_Label'] = None
        # Assuming same FS for alignment
        for _, row in events_df.iterrows():
            label = row['event_label']
            start_time = row['start_time']
            start_idx = int(start_time * fs)
            if 0 <= start_idx < len(combined):
                 combined.at[start_idx, 'Event_Label'] = label

    # Save
    if not combined.empty:
        output_file = f"processed_rsp_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
        combined.to_csv(output_file, index=False)
        print(f"Processed RSP signals saved to {output_file}")
    else:
        print("No RSP data generated.")

if __name__ == "__main__":
    main()
