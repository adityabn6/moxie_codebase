import bioread
import pandas as pd
import numpy as np
import argparse
import os

def extract_events(acq_file, output_dir):
    print(f"Reading {acq_file}...")
    data = bioread.read_file(acq_file)
    
    # Identify Event Channels (Digital or specific labels)
    # Moxie study typically uses digital channels for markers: 'Digital input', 'Label', etc.
    # We look for channels with "Digital" or "Event" in name, or specific logic.
    
    # Common convention: Digital channels have 0/5V or 0/1 logic.
    # We will look for changes in digital channels.
    
    events_list = []
    
    # 1. Check Named Event Markers (Text Labels)
    if hasattr(data, 'event_markers') and data.event_markers:
        print(f"Found {len(data.event_markers)} text markers.")
        # Use FS from first channel for time conversion
        # (Acq files can have mixed FS, but usually markers are global or linked to global time)
        # Bioread markers have 'sample_index' relative to the file.
        fs = data.channels[0].samples_per_second if data.channels else 2000.0
        
        for m in data.event_markers:
            # Clean label
            label = m.text.strip() if m.text else "Unknown_Marker"
            # Calculate time
            start_time = m.sample_index / fs
            
            events_list.append({
                "event_label": label,
                "start_time": start_time,
                "duration": 0, # Point event by default
                "source_channel": "Marker"
            })

    # 2. Check Digital Channels (Fallback/Additional)
    for channel in data.channels:
        if "Digital" in channel.name or "Event" in channel.name:
            print(f"Processing Event Channel: {channel.name}")
            vals = channel.data
            # Detect rising edges
             # Threshold
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
    
    # Ensure output dir
    os.makedirs(output_dir, exist_ok=True)
    
    df = pd.DataFrame(events_list)
    output_file = os.path.join(output_dir, "events.csv")
    
    if not df.empty:
        # Deduplicate or clean?
        df.to_csv(output_file, index=False)
        print(f"Extracted {len(df)} events to {output_file}")
    else:
        print("No events found. Creating empty key file.")
        # Create empty with headers
        pd.DataFrame(columns=["event_label", "start_time", "duration"]).to_csv(output_file, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--acq_file", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()
    
    extract_events(args.acq_file, args.output_dir)
