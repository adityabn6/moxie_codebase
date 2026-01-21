import argparse
import pandas as pd
import numpy as np
import os
import sys

def load_data(processed_file, events_file):
    """
    Loads processed EDA data and events.
    """
    print(f"Loading processed data: {processed_file}")
    try:
        # Optimization: Read header first to exclude 'Event_Label' (mixed types, unused)
        header = pd.read_csv(processed_file, nrows=0).columns
        cols_to_use = [c for c in header if 'Event_Label' not in c]
        
        eda_df = pd.read_csv(processed_file, usecols=cols_to_use)
    except Exception as e:
        print(f"Error reading processed file: {e}")
        sys.exit(1)

    print(f"Loading events: {events_file}")
    try:
        # Load events with robust handling (same as ECG script)
        events_df = pd.read_csv(events_file, header=None, names=['Event', 'Time', 'Duration', 'Type'], on_bad_lines='skip')
        
        # Ensure Time is numeric
        events_df['Time'] = pd.to_numeric(events_df['Time'], errors='coerce')
        # Drop rows with invalid time
        events_df = events_df.dropna(subset=['Time'])
    except Exception as e:
        print(f"Error reading events file: {e}")
        sys.exit(1)
        
    return eda_df, events_df

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
        markers = [
            'Baseline Resting Period', 'Speech Period', 'Debrief Period', 'Recovery Period'
        ]
    else:
        print(f"Unknown visit type: {visit_type}. Using all events.")
        markers = events_df['Event'].unique().tolist()

    filtered_events = events_df[events_df['Event'].isin(markers)].copy()
    filtered_events = filtered_events.sort_values(by='Time').reset_index(drop=True)
    return filtered_events, markers

def label_conditions(eda_df, events_df, sampling_rate=1000):
    """
    Adds a 'Condition' column to the EDA DataFrame based on event time ranges.
    """
    eda_df['Condition'] = None
    
    events = events_df.sort_values(by='Time').reset_index(drop=True)
    
    for i in range(len(events)):
        current_event = events.iloc[i]
        start_time = current_event['Time']
        condition = current_event['Event']
        
        start_idx = int(start_time * sampling_rate)
        
        if i < len(events) - 1:
            end_time = events.iloc[i+1]['Time']
            end_idx = int(end_time * sampling_rate)
        else:
            end_idx = len(eda_df)
            
        if start_idx < 0: start_idx = 0
        if end_idx > len(eda_df): end_idx = len(eda_df)
        
        if start_idx < len(eda_df):
            eda_df.loc[start_idx:end_idx, 'Condition'] = condition
            
    return eda_df

def compute_features(segment, sampling_rate):
    """
    Extracts EDA features from a segment of data.
    """
    if segment.empty:
        return {}
        
    features = {}
    
    # 1. SCL (Skin Conductance Level) - Tonic Component
    # Mean of EDA_Tonic or EDA_Clean if Tonic unavailable (but processing likely computed it)
    if 'EDA_Tonic' in segment.columns:
        features['EDA_SCL_Mean'] = segment['EDA_Tonic'].mean()
        features['EDA_SCL_SD'] = segment['EDA_Tonic'].std()
    elif 'EDA_Clean' in segment.columns:
        features['EDA_SCL_Mean'] = segment['EDA_Clean'].mean()
        features['EDA_SCL_SD'] = segment['EDA_Clean'].std()
    else:
         features['EDA_SCL_Mean'] = np.nan
         
    # 2. Phasic Component
    if 'EDA_Phasic' in segment.columns:
        features['EDA_Phasic_Mean'] = segment['EDA_Phasic'].mean()
        features['EDA_Phasic_SD'] = segment['EDA_Phasic'].std()
        features['EDA_Phasic_Max'] = segment['EDA_Phasic'].max()
        
    # 3. SCR (Skin Conductance Responses)
    # Frequency
    duration_sec = len(segment) / sampling_rate
    if 'SCR_Peaks' in segment.columns:
        n_peaks = segment['SCR_Peaks'].sum()
        # SCR Frequency (per minute is standard, but for short windows maybe per sec?)
        # Let's do per minute for standard, but handle short windows caution
        if duration_sec > 0:
            features['EDA_SCR_Freq_PerMin'] = (n_peaks / duration_sec) * 60
            features['EDA_SCR_Count'] = n_peaks
        else:
            features['EDA_SCR_Freq_PerMin'] = 0
            
    # Amplitude & Rise Time
    # These are usually populated at the peak indices or non-zero.
    # We filter for where SCR_Peaks == 1
    if 'SCR_Peaks' in segment.columns and 'SCR_Amplitude' in segment.columns:
        peaks_mask = segment['SCR_Peaks'] == 1
        amplitudes = segment.loc[peaks_mask, 'SCR_Amplitude']
        if not amplitudes.empty:
            features['EDA_SCR_Amp_Mean'] = amplitudes.mean()
        else:
            features['EDA_SCR_Amp_Mean'] = np.nan # No peaks in this segment
            
    if 'SCR_Peaks' in segment.columns and 'SCR_RiseTime' in segment.columns:
        peaks_mask = segment['SCR_Peaks'] == 1
        rise_times = segment.loc[peaks_mask, 'SCR_RiseTime']
        if not rise_times.empty:
            features['EDA_SCR_RiseTime_Mean'] = rise_times.mean()
        else:
            features['EDA_SCR_RiseTime_Mean'] = np.nan

    return features

def main():
    parser = argparse.ArgumentParser(description="Extract EDA features based on events and windows.")
    parser.add_argument("--id", required=True, help="Participant ID")
    parser.add_argument("--visit", required=True, help="Visit Type")
    parser.add_argument("--file", required=True, help="Path to processed EDA file")
    parser.add_argument("--events_file", required=True, help="Path to events CSV file")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--window_size", type=float, default=1.0, help="Window size in seconds")
    parser.add_argument("--sampling_rate", type=int, default=1000, help="Sampling rate in Hz")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    # 1. Load Data
    eda_df, events_full = load_data(args.file, args.events_file)
    
    # 2. Filter Events & Label Data
    events_filtered, markers = filter_events(events_full, args.visit)
    eda_df = label_conditions(eda_df, events_filtered, args.sampling_rate)
    
    # ---------------------------------------------------------
    # 3. Event-Based Extraction
    # ---------------------------------------------------------
    print("Starting Event-Based Extraction...")
    event_features_list = []
    
    for _, row in events_filtered.iterrows():
        condition = row['Event']
        start_time = row['Time']
        
        next_events = events_filtered[events_filtered['Time'] > start_time]
        if not next_events.empty:
            end_time = next_events['Time'].iloc[0]
        else:
             end_time = len(eda_df) / args.sampling_rate
             
        start_idx = int(start_time * args.sampling_rate)
        end_idx = int(end_time * args.sampling_rate)
        
        segment = eda_df.iloc[start_idx:end_idx]
        
        if not segment.empty:
            feats = compute_features(segment, args.sampling_rate)
            feats['Condition'] = condition
            feats['Start_Time'] = start_time
            feats['Duration'] = end_time - start_time
            event_features_list.append(feats)
            
    if event_features_list:
        event_features_df = pd.DataFrame(event_features_list)
        cols = ['Condition', 'Start_Time', 'Duration'] + [c for c in event_features_df.columns if c not in ['Condition', 'Start_Time', 'Duration']]
        event_features_df = event_features_df[cols]
        
        out_name_event = f"features_eda_event_based_{args.id}_{args.visit.replace(' ', '_')}.csv"
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
    
    total_samples = len(eda_df)
    
    for start_idx in range(0, total_samples, window_samples):
        end_idx = start_idx + window_samples
        if end_idx > total_samples:
            break
            
        segment = eda_df.iloc[start_idx:end_idx]
        
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
        cols = ['Time', 'Condition'] + [c for c in window_features_df.columns if c not in ['Time', 'Condition']]
        window_features_df = window_features_df[cols]
        
        window_size_str = str(args.window_size).replace('.', '_')
        out_name_window = f"features_eda_windowed_{window_size_str}s_{args.id}_{args.visit.replace(' ', '_')}.csv"
        window_features_df.to_csv(os.path.join(args.out, out_name_window), index=False)
        print(f"Window-based features saved to {out_name_window}")
    else:
        print("No window-based features extracted.")

if __name__ == "__main__":
    main()
