import argparse
import pandas as pd
import numpy as np
import sys
import os
import glob
import fnmatch
from datetime import datetime

if not hasattr(pd.DataFrame, "pad"):
    pd.DataFrame.pad = pd.DataFrame.ffill

import neurokit2 as nk

unix_start_time = None

def utc_string_to_unix(ts: str) -> float:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f%z")
    return dt.timestamp()

def find_hex_rsp_data(hex_dir):
    global unix_start_time

    csv_files = []
    
    if os.path.isfile(hex_dir):
        if hex_dir.endswith(".csv"):
            csv_files.append(hex_dir)
    else:
        for root, dirs, files in os.walk(hex_dir):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))
                
    found_data = {}
    
    for csv_file in csv_files:
        try:
            df_head = pd.read_csv(csv_file, nrows=1)
            cols = df_head.columns
            
            if 'respiration_thoracic' in cols and 'Thoracic' not in found_data:
                df = pd.read_csv(csv_file)
                if unix_start_time is None and 'record_time' in df.columns:
                    unix_start_time = utc_string_to_unix(df['record_time'].iloc[0])
                found_data['Thoracic'] = df['respiration_thoracic'].values
                
            if 'respiration_abdominal' in cols and 'Abdominal' not in found_data:
                df = pd.read_csv(csv_file)
                if unix_start_time is None and 'record_time' in df.columns:
                    unix_start_time = utc_string_to_unix(df['record_time'].iloc[0])
                found_data['Abdominal'] = df['respiration_abdominal'].values
                
        except Exception:
            pass
            
    if not found_data:
        return None, None
        
    fs = 256
    return found_data, fs

def process_single_rsp(data, fs, suffix, events_df=None):
    try:
        signals, info = nk.rsp_process(data, sampling_rate=fs, method="khodadad2018")
        rename_map = {col: f"{col}_{suffix}" for col in signals.columns}
        signals = signals.rename(columns=rename_map)
        
        if events_df is not None and not events_df.empty:
            signals['Event_Label'] = None
            for _, row in events_df.iterrows():
                label = row['event_label']
                event_unix = row['start_time']
                relative_time = event_unix - unix_start_time
                start_idx = int(round(relative_time * fs))
                if 0 <= start_idx < len(signals):
                    signals.at[start_idx, 'Event_Label'] = label
        
        return signals
    except Exception:
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--hex_path", required=True)
    parser.add_argument("--events_file", required=False)
    parser.add_argument("--output_dir", required=True)
    
    args = parser.parse_args()
    
    data_dict, fs = find_hex_rsp_data(args.hex_path)
    
    if data_dict is None:
        sys.exit(1)
        
    events_df = None
    if args.events_file and os.path.exists(args.events_file):
        events_df = pd.read_csv(args.events_file)
        
    all_signals = []
    
    if 'Thoracic' in data_dict:
        sig_t = process_single_rsp(data_dict['Thoracic'], fs, "Thoracic", events_df)
        if not sig_t.empty:
            all_signals.append(sig_t)
            
    if 'Abdominal' in data_dict:
        sig_a = process_single_rsp(data_dict['Abdominal'], fs, "Abdominal", events_df)
        if not sig_a.empty:
            all_signals.append(sig_a)
            
    if not all_signals:
        sys.exit(0)
        
    final_df = pd.concat(all_signals, axis=1)
    
    output_filename = f"processed_hex_rsp_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
    output_file = os.path.join(args.output_dir, output_filename)
    final_df.to_csv(output_file, index=False)

if __name__ == "__main__":
    main()
