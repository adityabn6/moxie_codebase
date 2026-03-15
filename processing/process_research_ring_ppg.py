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

def process_bp(signal, fs, events_df, recording_start_unix):
    """
    Process BP signal treating it as PPG/Continuous Waveform.
    Outputs Cleaned Signal, Systolic (Peaks), Diastolic (Troughs), Rate.
    """
    print(f"Processing BP signal with sampling rate {fs} Hz")

    # 1. Clean (low-pass only, preserve DC component)
    bp_cleaned = nk.signal_filter(
        signal,
        sampling_rate=fs,
        lowcut=None,
        highcut=8,
        method='butterworth',
        order=4
    )

    try:
        # 2. Find Peaks (Systolic)
        info = nk.ppg_findpeaks(bp_cleaned, sampling_rate=fs)
        peaks = info['PPG_Peaks']

        # 3. Calculate Rate
        rate = nk.signal_rate(peaks, sampling_rate=fs, desired_length=len(bp_cleaned))

    except Exception as e:
        print(f"Peak detection failed: {e}")
        return pd.DataFrame()

    # Construct output DataFrame
    signals = pd.DataFrame({
        "BP_Raw": signal,
        "BP_Clean": bp_cleaned,
        "BP_Rate": rate
    })

    # Mark systolic peaks
    signals['BP_Systolic_Peak'] = 0
    signals.iloc[peaks, signals.columns.get_loc('BP_Systolic_Peak')] = 1

    # Find diastolic troughs (minimum between peaks)
    troughs = []
    for i in range(len(peaks) - 1):
        segment = bp_cleaned[peaks[i]:peaks[i+1]]
        min_loc = np.argmin(segment)
        troughs.append(peaks[i] + min_loc)

    signals['BP_Diastolic_Peak'] = 0
    signals.iloc[troughs, signals.columns.get_loc('BP_Diastolic_Peak')] = 1

    # Interpolated SBP
    sbp_series = pd.Series(np.nan, index=np.arange(len(signals)))
    sbp_series.iloc[peaks] = bp_cleaned[peaks]
    signals['BP_Systolic_Interp'] = sbp_series.interpolate().bfill()

    # Interpolated DBP
    dbp_series = pd.Series(np.nan, index=np.arange(len(signals)))
    dbp_series.iloc[troughs] = bp_cleaned[troughs]
    signals['BP_Diastolic_Interp'] = dbp_series.interpolate().bfill()

    # Add event labels
    if events_df is not None and not events_df.empty:
        signals['Event_Label'] = None
        for _, row in events_df.iterrows():
            relative_time = row['start_time'] - recording_start_unix
            start_idx = int(round(relative_time * fs))
            if 0 <= start_idx < len(signals):
                signals.at[start_idx, 'Event_Label'] = row['event_label']

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
    eda_file = os.path.join(args.ring_path, "ppgRaw.csv")
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
    signals_df = process_bp(data[1].values, fs, events_df, unix_start_time)
    signals_df["fs"] = np.nan  # create the column with NaNs
    signals_df.loc[0, "fs"] = fs  # set the first row to the framerate


    if not signals_df.empty:
        output_filename = f"processed_research_ring_ppg_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
        output_file = os.path.join(args.output_dir, output_filename)
        signals_df.to_csv(output_file, index=False)
        print(f"Processed PPG signals saved to {output_file}")
    else:
        print("No processed PPG data generated.")


if __name__ == "__main__":
    main()
