import bioread
import pandas as pd
import numpy as np
import argparse
import os
from datetime import datetime, timedelta
import re

from datetime import datetime
from zoneinfo import ZoneInfo
import re

def extract_unix_time(line: str) -> float:
    match = re.search(
        r'\b[A-Z][a-z]{2} [A-Z][a-z]{2} \d{1,2} \d{4} \d{2}:\d{2}:\d{2}\.\d{3}',
        line
    )
    if not match:
        raise ValueError("No timestamp found in line")

    timestamp_str = match.group(0)

    dt_naive = datetime.strptime(
        timestamp_str, "%a %b %d %Y %H:%M:%S.%f"
    )

    # Attach Eastern Time zone (handles EST/EDT correctly)
    dt_et = dt_naive.replace(tzinfo=ZoneInfo("America/New_York"))

    return dt_et.timestamp()



def extract_events(acq_file, output_dir):
    print(f"Reading {acq_file}...")
    data = bioread.read_file(acq_file)
    
    events_list = []
    
    # 1. Check Named Event Markers (Text Labels)
    if hasattr(data, 'event_markers') and data.event_markers:
        print(f"Found {len(data.event_markers)} text markers.")
        fs = data.channels[0].samples_per_second if data.channels else 2000.0
        unix_time = None
        for i, m in enumerate(data.event_markers):
            if i==0:
                unix_time = extract_unix_time(m.text)
            if m.text is None:
                continue
            if m.text.startswith("ME") or m.text.startswith("NBP") or m.text.startswith("BPI"):
                continue  # Skip markers starting with ME or NBP

            # Clean label
            label = m.text.strip()
            # Calculate time
            start_time = m.sample_index / fs

            events_list.append({
                "event_label": label,
                "start_time": start_time + unix_time,
                "duration": 0,  # Point event by default
                "source_channel": "Marker"
            })

    # 2. Check Digital Channels (Fallback/Additional)
    for channel in data.channels:
        if "Digital" in channel.name or "Event" in channel.name:
            print(f"Processing Event Channel: {channel.name}")
            vals = channel.data
            # Detect rising edges
            threshold = (np.max(vals) + np.min(vals)) / 2
            binary = (vals > threshold).astype(int)
            diff = np.diff(binary, prepend=0)
            
            starts = np.where(diff == 1)[0]
            for i, start_idx in enumerate(starts):
                time_s = data.time_index[start_idx]
                label = f"{channel.name}_{i+1}"
                events_list.append({
                    "event_label": label,
                    "start_time": time_s,
                    "duration": 0,
                    "source_channel": channel.name
                })
    
    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)
    
    df = pd.DataFrame(events_list)
    output_file = os.path.join(output_dir, "events.csv")
    
    if not df.empty:
        df.to_csv(output_file, index=False)
        print(f"Extracted {len(df)} events to {output_file}")
    else:
        print("No events found. Creating empty key file.")
        pd.DataFrame(columns=["event_label", "start_time", "duration"]).to_csv(output_file, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--acq_file", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()
    
    extract_events(args.acq_file, args.output_dir)
