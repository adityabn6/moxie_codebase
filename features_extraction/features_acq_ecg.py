import argparse
import pandas as pd
import numpy as np

import os
import sys

def load_data(processed_file, events_file):
    """
    Loads processed ECG data and events.
    """
    print(f"Loading processed data: {processed_file}")
    try:
        # Optimization: Read header first to exclude 'Event_Label' (mixed types, unused)
        header = pd.read_csv(processed_file, nrows=0).columns
        cols_to_use = [c for c in header if 'Event_Label' not in c]
        
        ecg_df = pd.read_csv(processed_file, usecols=cols_to_use)
    except Exception as e:
        print(f"Error reading processed file: {e}")
        sys.exit(1)

    print(f"Loading events: {events_file}")
    try:
        # Assuming typical event file structure: 'Event', 'Time', 'Duration', 'Type'
        # Or checking what we saw in `head`: 
        # The previous `head` of events.csv had no header? Using logic from inspection.
        # "ME-CVP value changed,46.11,0,Marker"
        # We'll stick to a robust read.
        events_df = pd.read_csv(events_file, header=None, names=['Event', 'Time', 'Duration', 'Type'], on_bad_lines='skip')
        
        # Ensure Time is numeric
        events_df['Time'] = pd.to_numeric(events_df['Time'], errors='coerce')
        # Drop rows with invalid time
        events_df = events_df.dropna(subset=['Time'])
    except Exception as e:
        print(f"Error reading events file: {e}")
        sys.exit(1)
        
    return ecg_df, events_df

def filter_events(events_df, visit_type):
    """
    Filters events based on meaningful markers for the visit type.
    """
    if "TSST" in visit_type:
        markers = [
            'Baseline Resting Period', 'Task Introduction', 'Speech Preperation', 
            'Speech Period', 'Arithmetic Period', 'Debrief Period', 'Recovery Period'
        ]
    elif "PDST" in visit_type:
        # Note: User confirmed 'Speech Period' for PDST
        markers = [
            'Baseline Resting Period', 'Speech Period', 'Debrief Period', 'Recovery Period'
        ]
    else:
        print(f"Unknown visit type: {visit_type}. Using all events.")
        markers = events_df['Event'].unique().tolist()

    filtered_events = events_df[events_df['Event'].isin(markers)].copy()
    
    # Sort events by time just in case
    filtered_events = filtered_events.sort_values(by='Time').reset_index(drop=True)
    return filtered_events, markers

def label_conditions(ecg_df, events_df, sampling_rate=1000):
    """
    Adds a 'Condition' column to the ECG DataFrame based on event time ranges.
    Assumes events mark the START of a phase. Determining END is tricky.
    We will assume a phase lasts until the next meaningful event or a reasonable cutoff?
    
    Actually, looking at the user request: "window for each feature being according to the different event markerks".
    Usually these markers are "Start" markers. 
    Format:
    Event1 (Time T1) -> Event2 (Time T2).
    Condition between T1 and T2 is Event1.
    """
    ecg_df['Condition'] = None
    
    # We need to map time in seconds to index
    # Assuming the processed CSV index 0 = Time 0.
    
    # Sort events
    events = events_df.sort_values(by='Time').reset_index(drop=True)
    
    for i in range(len(events)):
        current_event = events.iloc[i]
        start_time = current_event['Time']
        condition = current_event['Event']
        
        start_idx = int(start_time * sampling_rate)
        
        # Determine end time
        if i < len(events) - 1:
            end_time = events.iloc[i+1]['Time']
            end_idx = int(end_time * sampling_rate)
        else:
            # Last event: go to end of file
            end_idx = len(ecg_df)
            
        # Boundary checks
        if start_idx < 0: start_idx = 0
        if end_idx > len(ecg_df): end_idx = len(ecg_df)
        
        if start_idx < len(ecg_df):
            ecg_df.loc[start_idx:end_idx, 'Condition'] = condition
            
    return ecg_df

def compute_features(segment, sampling_rate):
    """
    Extracts ECG features from a segment of data.
    """
    if segment.empty:
        return {}
        
    # We need R-peaks. The processed file has 'ECG_R_Peaks' (binary 0/1).
    # recover indices
    r_peaks = np.where(segment['ECG_R_Peaks'] == 1)[0]
    
    features = {}

    # 1. Heart Rate (Prefer pre-calculated ECG_Rate)
    if 'ECG_Rate' in segment.columns and not segment['ECG_Rate'].isna().all():
        features['ECG_Rate_Mean'] = segment['ECG_Rate'].mean()
        features['ECG_Rate_SD'] = segment['ECG_Rate'].std()
    else:
        # Fallback to peaks if Rate column missing
        if len(r_peaks) >= 2:
            rr = np.diff(r_peaks) / sampling_rate * 1000
            features['ECG_Rate_Mean'] = 60000 / np.mean(rr)
            features['ECG_Rate_SD'] = np.std(rr)
        else:
            features['ECG_Rate_Mean'] = np.nan
            features['ECG_Rate_SD'] = np.nan

    # 2. HRV (Time Domain) - Requires R-peaks
    if len(r_peaks) >= 2:
        rr = np.diff(r_peaks) / sampling_rate * 1000
        features['HRV_RMSSD'] = np.sqrt(np.mean(np.square(np.diff(rr))))
        features['HRV_SDNN'] = np.std(rr)
        features['HRV_CVSD'] = features['HRV_RMSSD'] / np.mean(rr)
        features['HRV_CVNN'] = features['HRV_SDNN'] / np.mean(rr)
        features['HRV_MeanNN'] = np.mean(rr)
        features['HRV_MedianNN'] = np.median(rr)
        features['HRV_pNN50'] = np.sum(np.abs(np.diff(rr)) > 50) / len(rr) * 100
    else:
        # Not enough peaks for HRV
        features['HRV_RMSSD'] = np.nan
        features['HRV_SDNN'] = np.nan
        features['HRV_CVSD'] = np.nan
        features['HRV_CVNN'] = np.nan
        features['HRV_MeanNN'] = np.nan
        features['HRV_MedianNN'] = np.nan
        features['HRV_pNN50'] = np.nan
    
    # Frequency domain requires more continuous data and is slow on windows.
    # For now, stick to time domain for robustness on short windows.
    # If user wants freq, we can add later.
    
    return features

def main():
    parser = argparse.ArgumentParser(description="Extract ECG features based on events and windows.")
    parser.add_argument("--id", required=True, help="Participant ID")
    parser.add_argument("--visit", required=True, help="Visit Type (e.g., 'TSST Visit')")
    parser.add_argument("--file", required=True, help="Path to processed ECG file")
    parser.add_argument("--events_file", required=True, help="Path to events CSV file")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--window_size", type=float, default=1.0, help="Window size in seconds for windowed analysis")
    parser.add_argument("--sampling_rate", type=int, default=1000, help="Sampling rate in Hz")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    # 1. Load Data
    ecg_df, events_full = load_data(args.file, args.events_file)
    
    # 2. Filter Events & Label Data
    events_filtered, markers = filter_events(events_full, args.visit)
    ecg_df = label_conditions(ecg_df, events_filtered, args.sampling_rate)
    
    # ---------------------------------------------------------
    # 3. Event-Based Extraction
    # ---------------------------------------------------------
    print("Starting Event-Based Extraction...")
    event_features_list = []
    
    # Group by Condition (this handles the "window for each feature being according to different event markers")
    # Note: Because we labeled by flooding between events, 'Condition' is contiguous blocks.
    # However, if an event repeats (unlikely in this protocol order), groupby handles it.
    # Ideally we process strictly by the event order defined in filter_events to preserve order.
    
    for _, row in events_filtered.iterrows():
        condition = row['Event']
        start_time = row['Time']
        
        # Determine specific end time for this occurrence
        # Find next event time
        next_events = events_filtered[events_filtered['Time'] > start_time]
        if not next_events.empty:
            end_time = next_events['Time'].iloc[0]
        else:
             end_time = len(ecg_df) / args.sampling_rate
             
        start_idx = int(start_time * args.sampling_rate)
        end_idx = int(end_time * args.sampling_rate)
        
        segment = ecg_df.iloc[start_idx:end_idx]
        
        if not segment.empty:
            feats = compute_features(segment, args.sampling_rate)
            feats['Condition'] = condition
            feats['Start_Time'] = start_time
            feats['Duration'] = end_time - start_time
            event_features_list.append(feats)
            
    if event_features_list:
        event_features_df = pd.DataFrame(event_features_list)
        # Reorder columns
        cols = ['Condition', 'Start_Time', 'Duration'] + [c for c in event_features_df.columns if c not in ['Condition', 'Start_Time', 'Duration']]
        event_features_df = event_features_df[cols]
        
        out_name_event = f"features_ecg_event_based_{args.id}_{args.visit.replace(' ', '_')}.csv"
        event_features_df.to_csv(os.path.join(args.out, out_name_event), index=False)
        print(f"Event-based features saved to {out_name_event}")
    else:
        print("No event-based features extracted.")

    # ---------------------------------------------------------
    # 4. Window-Based Extraction
    # ---------------------------------------------------------
    print(f"Starting Window-Based Extraction ({args.window_size}s windows)...")
    window_samples = int(args.window_size * args.sampling_rate)
    window_features_list = []
    
    # We iterate over the whole file in steps of window_size
    # This might be slow for huge files, but standard for this type of analysis.
    
    total_samples = len(ecg_df)
    
    for start_idx in range(0, total_samples, window_samples):
        end_idx = start_idx + window_samples
        if end_idx > total_samples:
            break # Drop last partial window
            
        segment = ecg_df.iloc[start_idx:end_idx]
        
        # Determine dominant condition
        # (Mode of 'Condition' column, ignoring None)
        conditions = segment['Condition'].dropna()
        if not conditions.empty:
            current_condition = conditions.mode()[0]
        else:
            current_condition = "Unknown"
            
        feats = compute_features(segment, args.sampling_rate)
        feats['Time'] = start_idx / args.sampling_rate
        feats['Condition'] = current_condition
        window_features_list.append(feats)
        
    if window_features_list:
        window_features_df = pd.DataFrame(window_features_list)
        # Reorder
        cols = ['Time', 'Condition'] + [c for c in window_features_df.columns if c not in ['Time', 'Condition']]
        window_features_df = window_features_df[cols]
        
        window_size_str = str(args.window_size).replace('.', '_')
        out_name_window = f"features_ecg_windowed_{window_size_str}s_{args.id}_{args.visit.replace(' ', '_')}.csv"
        window_features_df.to_csv(os.path.join(args.out, out_name_window), index=False)
        print(f"Window-based features saved to {out_name_window}")
    else:
        print("No window-based features extracted.")

if __name__ == "__main__":
    main()
