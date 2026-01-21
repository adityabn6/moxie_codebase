import argparse
import pandas as pd
import numpy as np
import os
import sys

def load_data(processed_file, events_file):
    """
    Loads processed BP data and events.
    """
    print(f"Loading processed data: {processed_file}")
    try:
        bp_df = pd.read_csv(processed_file)
    except Exception as e:
        print(f"Error reading processed file: {e}")
        sys.exit(1)

    print(f"Loading events: {events_file}")
    try:
        events_df = pd.read_csv(events_file, header=None, names=['Event', 'Time', 'Duration', 'Type'], on_bad_lines='skip')
        events_df['Time'] = pd.to_numeric(events_df['Time'], errors='coerce')
        events_df = events_df.dropna(subset=['Time'])
    except Exception as e:
        print(f"Error reading events file: {e}")
        sys.exit(1)
        
    return bp_df, events_df

def filter_events(events_df, visit_type):
    """
    Filters events based on markers.
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

def label_conditions(bp_df, events_df, sampling_rate=1000):
    """
    Adds Condition column.
    """
    bp_df['Condition'] = None
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
            end_idx = len(bp_df)
            
        if start_idx < 0: start_idx = 0
        if end_idx > len(bp_df): end_idx = len(bp_df)
        
        if start_idx < len(bp_df):
            bp_df.loc[start_idx:end_idx, 'Condition'] = condition
            
    return bp_df

def find_column(columns, prefix):
    for col in columns:
        if col.startswith(prefix):
            return col
    return None

def compute_features(segment, sampling_rate):
    if segment.empty:
        return {}
        
    features = {}
    
    # Identify dynamic columns
    col_sys = find_column(segment.columns, 'BP_Systolic_Interp')
    col_dia = find_column(segment.columns, 'BP_Diastolic_Interp')
    col_clean = find_column(segment.columns, 'BP_Clean')
    col_rate = find_column(segment.columns, 'BP_Rate')
    
    # 1. Systolic
    if col_sys:
        features['BP_Systolic_Mean'] = segment[col_sys].mean()
        features['BP_Systolic_SD'] = segment[col_sys].std()
    else:
        features['BP_Systolic_Mean'] = np.nan
        features['BP_Systolic_SD'] = np.nan
        
    # 2. Diastolic
    if col_dia:
        features['BP_Diastolic_Mean'] = segment[col_dia].mean()
        features['BP_Diastolic_SD'] = segment[col_dia].std()
    else:
        features['BP_Diastolic_Mean'] = np.nan
        features['BP_Diastolic_SD'] = np.nan
        
    # 3. MAP (Mean Arterial Pressure)
    # Ideally from BP_Clean (continuous), but if missing, use approximation?
    # User plan said use BP_Clean.
    if col_clean:
        features['BP_MAP_Mean'] = segment[col_clean].mean()
        features['BP_MAP_SD'] = segment[col_clean].std()
    else:
        # Fallback if interp exists: MAP ~ 1/3 Sys + 2/3 Dia
        if col_sys and col_dia:
             sys_val = segment[col_sys].mean()
             dia_val = segment[col_dia].mean()
             features['BP_MAP_Mean'] = (sys_val + 2*dia_val) / 3
             features['BP_MAP_SD'] = np.nan # Hard to estimate SD from means
        else:
            features['BP_MAP_Mean'] = np.nan
            features['BP_MAP_SD'] = np.nan
            
    # 4. Pulse Pressure (Sys - Dia)
    if col_sys and col_dia:
        # Calculate point-wise PP if possible, or difference of means
        # Interp columns are continuous time series of peaks, so point-wise is valid
        pp_series = segment[col_sys] - segment[col_dia]
        features['BP_PulsePressure_Mean'] = pp_series.mean()
        features['BP_PulsePressure_SD'] = pp_series.std()
    else:
        features['BP_PulsePressure_Mean'] = np.nan
        features['BP_PulsePressure_SD'] = np.nan

    # 5. Heart Rate (from BP)
    if col_rate:
        features['BP_Rate_Mean'] = segment[col_rate].mean()
        features['BP_Rate_SD'] = segment[col_rate].std()
    else:
        features['BP_Rate_Mean'] = np.nan
        features['BP_Rate_SD'] = np.nan

    return features

def main():
    parser = argparse.ArgumentParser(description="Extract BP features.")
    parser.add_argument("--id", required=True)
    parser.add_argument("--visit", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--events_file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--window_size", type=float, default=1.0)
    parser.add_argument("--sampling_rate", type=int, default=1000)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    bp_df, events_full = load_data(args.file, args.events_file)
    events_filtered, markers = filter_events(events_full, args.visit)
    bp_df = label_conditions(bp_df, events_filtered, args.sampling_rate)
    
    # Event-Based
    print("Starting Event-Based Extraction...")
    event_features_list = []
    
    for _, row in events_filtered.iterrows():
        condition = row['Event']
        start_time = row['Time']
        
        next_events = events_filtered[events_filtered['Time'] > start_time]
        end_time = next_events['Time'].iloc[0] if not next_events.empty else len(bp_df)/args.sampling_rate
             
        start_idx = int(start_time * args.sampling_rate)
        end_idx = int(end_time * args.sampling_rate)
        
        segment = bp_df.iloc[start_idx:end_idx]
        
        if not segment.empty:
            feats = compute_features(segment, args.sampling_rate)
            feats['Condition'] = condition
            feats['Start_Time'] = start_time
            feats['Duration'] = end_time - start_time
            event_features_list.append(feats)
            
    if event_features_list:
        df_event = pd.DataFrame(event_features_list)
        cols = ['Condition', 'Start_Time', 'Duration'] + [c for c in df_event.columns if c not in ['Condition', 'Start_Time', 'Duration']]
        df_event = df_event[cols]
        out_name = f"features_bp_event_based_{args.id}_{args.visit.replace(' ', '_')}.csv"
        df_event.to_csv(os.path.join(args.out, out_name), index=False)
        print(f"Event-based features saved to {out_name}")

    # Window-Based
    print(f"Starting Window-Based Extraction ({args.window_size}s windows)...")
    window_samples = int(args.window_size * args.sampling_rate)
    window_features_list = []
    
    total_samples = len(bp_df)
    
    for start_idx in range(0, total_samples, window_samples):
        end_idx = start_idx + window_samples
        if end_idx > total_samples: break
            
        segment = bp_df.iloc[start_idx:end_idx]
        
        conditions = segment['Condition'].dropna()
        current_condition = conditions.mode()[0] if not conditions.empty else "Unknown"
            
        feats = compute_features(segment, args.sampling_rate)
        feats['Time'] = start_idx / args.sampling_rate
        feats['Condition'] = current_condition
        window_features_list.append(feats)
        
    if window_features_list:
        df_window = pd.DataFrame(window_features_list)
        cols = ['Time', 'Condition'] + [c for c in df_window.columns if c not in ['Time', 'Condition']]
        df_window = df_window[cols]
        win_str = str(args.window_size).replace('.', '_')
        out_name = f"features_bp_windowed_{win_str}s_{args.id}_{args.visit.replace(' ', '_')}.csv"
        df_window.to_csv(os.path.join(args.out, out_name), index=False)
        print(f"Window-based features saved to {out_name}")

if __name__ == "__main__":
    main()
