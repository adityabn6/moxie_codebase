import argparse
import pandas as pd
if not hasattr(pd.DataFrame, "pad"):
    pd.DataFrame.pad = pd.DataFrame.ffill
import numpy as np
from datetime import datetime

unix_start_time = None

def utc_string_to_unix(ts: str) -> float:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f%z")
    return dt.timestamp()

if not hasattr(np, 'trapz'):
    if hasattr(np, 'trapezoid'):
        np.trapz = np.trapezoid
    else:
        from scipy import integrate
        np.trapz = integrate.trapezoid


import neurokit2 as nk
import sys
import os
from scipy.io import wavfile

def load_hexoskin_ecg(hex_dir):
    def find_file(pattern, search_root):
        import fnmatch
        for root, dirs, files in os.walk(search_root):
            for file in files:
                if fnmatch.fnmatch(file, pattern):
                    return os.path.join(root, file)
        return None

    global unix_start_time

    if os.path.isfile(hex_dir):
        if hex_dir.endswith(".csv"):
            try:
                df_head = pd.read_csv(hex_dir, nrows=1)
                if 'ecg_1' in df_head.columns or 'ecg1' in df_head.columns:
                    df = pd.read_csv(hex_dir)
                    if unix_start_time is None and 'record_time' in df.columns:
                        unix_start_time = utc_string_to_unix(df['record_time'].iloc[0])
                    if 'ecg_1' in df.columns:
                        return df['ecg_1'].values, 256
                    if 'ecg1' in df.columns:
                        return df['ecg1'].values, 256
            except:
                pass
        return None, None

    csv_files = []
    for root, dirs, files in os.walk(hex_dir):
        for file in files:
            if file.endswith(".csv"):
                csv_files.append(os.path.join(root, file))

    for ecg_csv in csv_files:
        try:
            df_head = pd.read_csv(ecg_csv, nrows=1)
            if 'ecg_1' in df_head.columns or 'ecg1' in df_head.columns:
                df = pd.read_csv(ecg_csv)
                if unix_start_time is None and 'record_time' in df.columns:
                    unix_start_time = utc_string_to_unix(df['record_time'].iloc[0])
                if 'ecg_1' in df.columns:
                    return df['ecg_1'].values, 256
                if 'ecg1' in df.columns:
                    return df['ecg1'].values, 256
        except:
            pass

    ecg_wav = find_file("*ECG*.wav", hex_dir)
    if ecg_wav:
        try:
            fs, data = wavfile.read(ecg_wav)
            return data, fs
        except ValueError:
            pass

    return None, None

def process_hex_ecg(data, fs, events_df=None):
    ecg_cleaned = nk.ecg_clean(data, sampling_rate=fs, method="neurokit")
    try:
        signals, info = nk.ecg_process(ecg_cleaned, sampling_rate=fs)
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

    data, fs = load_hexoskin_ecg(args.hex_path)

    if data is None:
        sys.exit(1)

    events_df = None
    if args.events_file and os.path.exists(args.events_file):
        events_df = pd.read_csv(args.events_file)

    results = process_hex_ecg(data, fs, events_df)

    if not results.empty:
        output_filename = f"processed_hex_ecg_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
        output_file = os.path.join(args.output_dir, output_filename)
        results.to_csv(output_file, index=False)

if __name__ == "__main__":
    main()
