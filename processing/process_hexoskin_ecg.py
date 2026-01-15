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

import neurokit2 as nk
import sys
import os
import glob
from scipy.io import wavfile

def load_hexoskin_ecg(hex_dir):
    """
    Loads ECG data from Hexoskin directory.
    Attempts to read 'ECG_I.wav' (256Hz) or 'ECG.csv'.
    """
    # Recursive search helper
    def find_file(pattern, search_root):
        import fnmatch
        for root, dirs, files in os.walk(search_root):
             for file in files:
                 if fnmatch.fnmatch(file, pattern):
                     return os.path.join(root, file)
        return None

    # 0. Check if input is already a file
    if os.path.isfile(hex_dir):
        if hex_dir.endswith(".csv"):
             # print(f"Loading specific file: {hex_dir}")
             try:
                 df_head = pd.read_csv(hex_dir, nrows=1)
                 # Check cols
                 if 'ecg_1' in df_head.columns:
                     df = pd.read_csv(hex_dir)
                     return df['ecg_1'].values, 256
                 if 'ecg1' in df_head.columns:
                     df = pd.read_csv(hex_dir)
                     return df['ecg1'].values, 256
                 # Fallback
                 # print("Specific file does not contain ecg_1/ecg1")
             except:
                 pass
        return None, None

    # 1. Try CSV (Preferred per user request)
    # Search for ANY .csv file that might contain the data
    # We will iterate through them to find the one with the right column
    import glob
    csv_files = []
    for root, dirs, files in os.walk(hex_dir):
        for file in files:
            if file.endswith(".csv"):
                csv_files.append(os.path.join(root, file))
    
    for ecg_csv in csv_files:
    # ecg_csv = find_file("*.csv", hex_dir) # This would only return the first one, we need to check content
    # Let's iterate found files
        # print(f"Checking {ecg_csv}...") 
        try:
            # Read first row only to check columns for speed
            df_head = pd.read_csv(ecg_csv, nrows=1)
            
            # Check for specific 'ecg_1' column as requested (Priority 1)
            if 'ecg_1' in df_head.columns:
                 print(f"Found 'ecg_1' in {ecg_csv}")
                 # Load full
                 df = pd.read_csv(ecg_csv)
                 data = df['ecg_1'].values
                 fs = 256 
                 return data, fs

            # Check for 'ecg1' (Priority 2)
            if 'ecg1' in df_head.columns:
                 print(f"Found 'ecg1' in {ecg_csv}")
                 df = pd.read_csv(ecg_csv)
                 data = df['ecg1'].values
                 fs = 256 
                 return data, fs
            
            # Fallback to case-insensitive 'ecg' - ONLY if we don't find the specific ones
            # But we should probably keep looking if we don't find the priority ones?
            # For now, let's keep the loop going.
                 
        except Exception as e:
            # print(f"Skipping {ecg_csv}: {e}")
            pass
            
    # If we are here, we didn't find the specific columns. 
    # Try one more pass for generic 'ecg' if needed, or just fail over to WAV.


    # 2. Try WAV (Fallback)
    # Search for *ECG*.wav
    ecg_wav = find_file("*ECG*.wav", hex_dir)
    
    if ecg_wav:
        print(f"Loading {ecg_wav}...")
        try:
            fs, data = wavfile.read(ecg_wav)
            return data, fs
        except ValueError:
            pass
    
    return None, None

def process_hex_ecg(data, fs, events_df=None):
    print(f"Processing Hexoskin ECG with sampling rate {fs}Hz")
    
    # 1. Clean
    ecg_cleaned = nk.ecg_clean(data, sampling_rate=fs, method="neurokit")
    
    # 2. Find Peaks & Process
    try:
        signals, info = nk.ecg_process(ecg_cleaned, sampling_rate=fs)
        # signals contains ['ECG_Raw', 'ECG_Clean', 'ECG_R_Peaks', 'ECG_Rate'...]
        
        # Add Event Labels
        if events_df is not None and not events_df.empty:
            signals['Event_Label'] = None
            for _, row in events_df.iterrows():
                label = row['event_label']
                start_time = row['start_time']
                start_idx = int(start_time * fs)
                if 0 <= start_idx < len(signals):
                     signals.at[start_idx, 'Event_Label'] = label
                     
        return signals
        
    except Exception as e:
        print(f"Processing failed: {e}")
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--hex_path", required=True)
    parser.add_argument("--events_file", required=False, help="Path to events CSV file")
    parser.add_argument("--output_dir", required=True)
    
    args = parser.parse_args()
    
    # Load Data
    data, fs = load_hexoskin_ecg(args.hex_path)
    
    if data is None:
        print("No Hexoskin ECG data found.")
        sys.exit(1)
        
    # Load Events
    events_df = None
    if args.events_file and os.path.exists(args.events_file):
        print(f"Loading events from {args.events_file}")
        events_df = pd.read_csv(args.events_file)
    elif args.events_file:
         print(f"Warning: Events file {args.events_file} not found.")
         
    # Process
    results = process_hex_ecg(data, fs, events_df)
    
    if not results.empty:
        # Hexoskin output usually doesn't need 'Participant' column IN the csv if 
        # it's a time series file. It's in the filename.
        
        output_filename = f"processed_hex_ecg_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
        output_file = os.path.join(args.output_dir, output_filename)
        results.to_csv(output_file, index=False)
        print(f"Processed signals saved to {output_file}")

if __name__ == "__main__":
    main()
