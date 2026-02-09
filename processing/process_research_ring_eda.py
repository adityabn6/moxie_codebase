import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import re
from zoneinfo import ZoneInfo



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


def get_unix_start_from_file(ring_path: str) -> float:
    """
    Reads ring_path/time.txt which contains:
    YYYY-MM-DD HH:MM:SS
    Interprets it as America/New_York time and converts to Unix timestamp.
    """
    time_file = os.path.join(ring_path, "time.txt")

    if not os.path.exists(time_file):
        raise FileNotFoundError(f"time.txt not found at {time_file}")

    with open(time_file, "r") as f:
        line = f.readline().strip()

    # Parse naive datetime
    dt_naive = datetime.strptime(line, "%Y-%m-%d %H:%M:%S")

    # Attach Eastern timezone (handles DST automatically)
    dt_et = dt_naive.replace(tzinfo=ZoneInfo("America/New_York"))
    return dt_et.timestamp()


def process_eda(channel, fs, events_df, recording_start_unix):
    """
    Process EDA signal.
    Returns DataFrame with processed signals.
    """
    print(f"Processing EDA with sampling rate {fs}Hz")

    try:
        signals, info = nk.eda_process(channel, sampling_rate=fs, method="neurokit")
    except Exception as e:
        print(f"EDA processing failed: {e}")
        return pd.DataFrame()

    if events_df is not None and not events_df.empty:
        signals['Event_Label'] = None
        for _, row in events_df.iterrows():
            label = row['event_label']
            event_unix = row['start_time']
            relative_time = event_unix - recording_start_unix
            start_idx = int(round(relative_time * fs))
            if 0 <= start_idx < len(signals):
                signals.at[start_idx, 'Event_Label'] = label

    return signals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--ring_path", required=True)
    parser.add_argument("--events_file", required=True)
    parser.add_argument("--output_dir", required=True)

    args = parser.parse_args()

    # Get Unix start time from time.txt
    try:
        unix_start_time = get_unix_start_from_file(args.ring_path)
        print(f"Recording start (Unix): {unix_start_time}")
    except Exception as e:
        print(f"Error reading start time: {e}")
        sys.exit(1)

    # Load EDA CSV
    eda_file = os.path.join(args.ring_path, "edaRaw.csv")
    try:
        data = pd.read_csv(eda_file, header=None)
    except Exception as e:
        print(f"Error reading EDA CSV: {e}")
        sys.exit(1)

    # Load Events
    if os.path.exists(args.events_file):
        events_df = pd.read_csv(args.events_file)
    else:
        print("Events file not found.")
        events_df = None
    first_value = data.iloc[0, 0]
    second_value = data.iloc[1, 0]
    fs = 1000000/(second_value - first_value)
    print(fs)

    # Process (assuming column 1 is EDA values)
    signals_df = process_eda(data[1].values, fs, events_df, unix_start_time)

    if not signals_df.empty:
        output_filename = f"processed_eda_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
        output_file = os.path.join(args.output_dir, output_filename)
        signals_df.to_csv(output_file, index=False)
        print(f"Processed EDA signals saved to {output_file}")
    else:
        print("No processed EDA data generated.")


if __name__ == "__main__":
    main()
