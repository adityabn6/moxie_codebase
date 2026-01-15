import argparse
import pandas as pd
import numpy as np
import neurokit2 as nk
import sys
import os
import glob
import fnmatch

def find_hex_rsp_data(hex_dir):
    """
    Scans for CSV files containing Hexoskin respiration columns.
    Returns: data (dict of columns), fs (int)
    """
    
    # scan for all csvs
    csv_files = []
    
    if os.path.isfile(hex_dir):
        if hex_dir.endswith(".csv"):
            csv_files.append(hex_dir)
    else:
        for root, dirs, files in os.walk(hex_dir):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))
                
    # We want 'respiration_thoracic' and 'respiration_abdominal'
    # Data structure to hold what we find
    found_data = {}
    
    # Prioritize finding a single file with both, or multiple files
    for csv_file in csv_files:
        try:
            # Read header
            df_head = pd.read_csv(csv_file, nrows=1)
            cols = df_head.columns
            
            if 'respiration_thoracic' in cols and 'Thoracic' not in found_data:
                print(f"Found 'respiration_thoracic' in {csv_file}")
                df = pd.read_csv(csv_file)
                found_data['Thoracic'] = df['respiration_thoracic'].values
                
            if 'respiration_abdominal' in cols and 'Abdominal' not in found_data:
                print(f"Found 'respiration_abdominal' in {csv_file}")
                df = pd.read_csv(csv_file) # Re-read if same file, optimization possible but file size manageable
                found_data['Abdominal'] = df['respiration_abdominal'].values
                
        except Exception as e:
            pass
            
    if not found_data:
        return None, None
        
    # Hexoskin Respiration is typically 256Hz (same as ECG) or sometimes 128Hz?
    # Hexoskin API docs say: Respiration Raw is 256Hz.
    fs = 256 
    
    return found_data, fs

def process_single_rsp(data, fs, suffix):
    print(f"Processing {suffix} with sampling rate {fs}Hz")
    
    # Cleaning using khodadad2018 which is good for ambulatory
    try:
        signals, info = nk.rsp_process(data, sampling_rate=fs, method="khodadad2018")
        
        # Rename columns to be specific
        # Standard: RSP_Raw, RSP_Clean, RSP_Amplitude, RSP_Rate, RSP_Phase, RSP_Peaks...
        rename_map = {col: f"{col}_{suffix}" for col in signals.columns}
        signals = signals.rename(columns=rename_map)
        
        # Ensure Raw is there if NK didn't output it (it usually does as RSP_Raw)
        
        return signals
    except Exception as e:
        print(f"Failed to process {suffix}: {e}")
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--hex_path", required=True)
    parser.add_argument("--events_file", required=False)
    
    args = parser.parse_args()
    
    # Load Data
    data_dict, fs = find_hex_rsp_data(args.hex_path)
    
    if data_dict is None:
        print("No Hexoskin Respiration data found.")
        sys.exit(1)
        
    # Load Events
    events_df = None
    if args.events_file and os.path.exists(args.events_file):
        print(f"Loading events from {args.events_file}")
        events_df = pd.read_csv(args.events_file)
        
    all_signals = []
    
    # Process Thoracic
    if 'Thoracic' in data_dict:
        sig_t = process_single_rsp(data_dict['Thoracic'], fs, "Thoracic")
        if not sig_t.empty:
            all_signals.append(sig_t)
            
    # Process Abdominal
    if 'Abdominal' in data_dict:
        sig_a = process_single_rsp(data_dict['Abdominal'], fs, "Abdominal")
        if not sig_a.empty:
            all_signals.append(sig_a)
            
    if not all_signals:
        print("No respiration signals generated.")
        sys.exit(0)
        
    final_df = pd.concat(all_signals, axis=1)
    
    # Add Events
    if events_df is not None and not events_df.empty:
        final_df['Event_Label'] = None
        for _, row in events_df.iterrows():
            label = row['event_label']
            start_time = row['start_time']
            start_idx = int(start_time * fs)
            if 0 <= start_idx < len(final_df):
                 final_df.at[start_idx, 'Event_Label'] = label

    # Save
    output_file = f"processed_hex_rsp_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
    final_df.to_csv(output_file, index=False)
    print(f"Processed signals saved to {output_file}")

if __name__ == "__main__":
    main()
