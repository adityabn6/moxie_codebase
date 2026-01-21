import argparse
import pandas as pd
import numpy as np
import os
import sys

def load_data(processed_file, events_file):
    """
    Loads processed RSP data and events.
    """
    print(f"Loading processed data: {processed_file}")
    try:
        # Optimization: Read header first to exclude 'Event_Label' (mixed types, unused)
        header = pd.read_csv(processed_file, nrows=0).columns
        cols_to_use = [c for c in header if 'Event_Label' not in c]
        print(f"Loading columns: {len(cols_to_use)} / {len(header)}")
        
        rsp_df = pd.read_csv(processed_file, usecols=cols_to_use)
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
        
    return rsp_df, events_df

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

def label_conditions(rsp_df, events_df, sampling_rate=1000):
    """
    Adds a 'Condition' column to the RSP DataFrame based on event time ranges.
    """
    rsp_df['Condition'] = None
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
            end_idx = len(rsp_df)
            
        if start_idx < 0: start_idx = 0
        if end_idx > len(rsp_df): end_idx = len(rsp_df)
        
        if start_idx < len(rsp_df):
            rsp_df.loc[start_idx:end_idx, 'Condition'] = condition
            
    return rsp_df

def find_column(columns, prefix):
    """
    Finds the first column that starts with the given prefix.
    """
    for col in columns:
        if col.startswith(prefix):
            return col
    return None

def compute_features(segment, sampling_rate, gradient_threshold=None):
    """
    Extracts RSP features from a segment of data.
    """
    if segment.empty:
        return {}
        
    features = {}
    
    # Identify dynamic column names
    col_rate = find_column(segment.columns, 'RSP_Rate')
    col_amp = find_column(segment.columns, 'RSP_Amplitude')
    col_phase = find_column(segment.columns, 'RSP_Phase')
    col_clean = find_column(segment.columns, 'RSP_Clean')
    
    # 1. Rate
    if col_rate:
        features['RSP_Rate_Mean'] = segment[col_rate].mean()
        features['RSP_Rate_SD'] = segment[col_rate].std()
    else:
        features['RSP_Rate_Mean'] = np.nan
        features['RSP_Rate_SD'] = np.nan
        
    # 2. Amplitude
    if col_amp:
        features['RSP_Amp_Mean'] = segment[col_amp].mean()
        features['RSP_Amp_SD'] = segment[col_amp].std()
    else:
        features['RSP_Amp_Mean'] = np.nan
        features['RSP_Amp_SD'] = np.nan
        
    # 3. Respiratory Phase (Inhale/Exhale/Hold) - Slope Based
    if col_clean and gradient_threshold is not None:
        # Calculate Gradient (Slope)
        signal_clean = segment[col_clean].values
        gradient = np.gradient(signal_clean)
        
        # Use passed global threshold
        threshold = gradient_threshold
        
        # Classify
        # Inhale: Slope > Threshold
        # Exhale: Slope < -Threshold
        # Hold:   |Slope| <= Threshold
        
        is_inhale = gradient > threshold
        is_exhale = gradient < -threshold
        is_hold = np.abs(gradient) <= threshold
        
        n_samples = len(gradient)
        if n_samples > 0:
            features['RSP_Slope_Inhale_Ratio'] = np.sum(is_inhale) / n_samples
            features['RSP_Slope_Exhale_Ratio'] = np.sum(is_exhale) / n_samples
            features['RSP_Slope_Hold_Ratio'] = np.sum(is_hold) / n_samples
            
            # Dominant Phase (Slope Based)
            counts = {
                'Inhale': np.sum(is_inhale),
                'Exhale': np.sum(is_exhale),
                'Hold': np.sum(is_hold)
            }
            features['RSP_Slope_Dominant'] = max(counts, key=counts.get)
        else:
             features['RSP_Slope_Inhale_Ratio'] = np.nan
             features['RSP_Slope_Exhale_Ratio'] = np.nan
             features['RSP_Slope_Hold_Ratio'] = np.nan
             features['RSP_Slope_Dominant'] = "Unknown"
    else:
        features['RSP_Slope_Inhale_Ratio'] = np.nan
        features['RSP_Slope_Exhale_Ratio'] = np.nan
        features['RSP_Slope_Hold_Ratio'] = np.nan
        features['RSP_Slope_Dominant'] = "Unknown"

    # 4. Respiratory Phase (NeuroKit Based - Legacy/Check)
    if col_phase:
        phase_counts = segment[col_phase].value_counts(normalize=True)
        # Fraction of Inhale (1) and Exhale (0)
        features['RSP_Inhale_Ratio'] = phase_counts.get(1.0, 0.0)
        features['RSP_Exhale_Ratio'] = phase_counts.get(0.0, 0.0)
        
        # Dominant Phase
        mode_val = segment[col_phase].mode()
        if not mode_val.empty:
            dom_phase = mode_val[0]
            if dom_phase == 1.0:
                features['RSP_Phase_Dominant'] = "Inhale"
            elif dom_phase == 0.0:
                features['RSP_Phase_Dominant'] = "Exhale"
            else:
                 features['RSP_Phase_Dominant'] = "Unknown"
        else:
            features['RSP_Phase_Dominant'] = "Unknown"
    else:
        features['RSP_Inhale_Ratio'] = np.nan
        features['RSP_Exhale_Ratio'] = np.nan
        features['RSP_Phase_Dominant'] = np.nan

    return features

def main():
    parser = argparse.ArgumentParser(description="Extract RSP features based on events and windows.")
    parser.add_argument("--id", required=True, help="Participant ID")
    parser.add_argument("--visit", required=True, help="Visit Type")
    parser.add_argument("--file", required=True, help="Path to processed RSP file")
    parser.add_argument("--events_file", required=True, help="Path to events CSV file")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--window_size", type=float, default=1.0, help="Window size in seconds")
    parser.add_argument("--sampling_rate", type=int, default=1000, help="Sampling rate in Hz")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    # 1. Load Data
    rsp_df, events_full = load_data(args.file, args.events_file)
    
    # Determine Global Gradient Threshold
    gradient_threshold = None
    col_clean = find_column(rsp_df.columns, 'RSP_Clean')
    if col_clean:
        print("Calculating global gradient threshold for 'Hold' detection...")
        signal_clean = rsp_df[col_clean].values
        # Drop NaNs if any
        signal_clean = signal_clean[~np.isnan(signal_clean)]
        if len(signal_clean) > 0:
            gradient = np.gradient(signal_clean)
            grad_std = np.std(gradient)
            # Threshold = 5% of global gradient standard deviation
            gradient_threshold = 0.05 * grad_std
            print(f"Global Gradient Std: {grad_std:.6f}, Threshold: {gradient_threshold:.6f}")
        else:
            print("Warning: RSP_Clean empty, cannot calculate threshold.")
    
    # 2. Filter Events & Label Data
    events_filtered, markers = filter_events(events_full, args.visit)
    rsp_df = label_conditions(rsp_df, events_filtered, args.sampling_rate)
    
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
             end_time = len(rsp_df) / args.sampling_rate
             
        start_idx = int(start_time * args.sampling_rate)
        end_idx = int(end_time * args.sampling_rate)
        
        segment = rsp_df.iloc[start_idx:end_idx]
        
        if not segment.empty:
            feats = compute_features(segment, args.sampling_rate, gradient_threshold)
            feats['Condition'] = condition
            feats['Start_Time'] = start_time
            feats['Duration'] = end_time - start_time
            event_features_list.append(feats)
            
    if event_features_list:
        event_features_df = pd.DataFrame(event_features_list)
        cols = ['Condition', 'Start_Time', 'Duration'] + [c for c in event_features_df.columns if c not in ['Condition', 'Start_Time', 'Duration']]
        event_features_df = event_features_df[cols]
        
        out_name_event = f"features_rsp_event_based_{args.id}_{args.visit.replace(' ', '_')}.csv"
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
    
    total_samples = len(rsp_df)
    
    for start_idx in range(0, total_samples, window_samples):
        end_idx = start_idx + window_samples
        if end_idx > total_samples:
            break
            
        segment = rsp_df.iloc[start_idx:end_idx]
        
        conditions = segment['Condition'].dropna()
        if not conditions.empty:
            current_condition = conditions.mode()[0]
        else:
            current_condition = "Unknown"
            
        feats = compute_features(segment, args.sampling_rate, gradient_threshold)
        feats['Time'] = start_idx / args.sampling_rate
        feats['Condition'] = current_condition
        window_features_list.append(feats)
        
    if window_features_list:
        window_features_df = pd.DataFrame(window_features_list)
        cols = ['Time', 'Condition'] + [c for c in window_features_df.columns if c not in ['Time', 'Condition']]
        window_features_df = window_features_df[cols]
        
        window_size_str = str(args.window_size).replace('.', '_')
        out_name_window = f"features_rsp_windowed_{window_size_str}s_{args.id}_{args.visit.replace(' ', '_')}.csv"
        window_features_df.to_csv(os.path.join(args.out, out_name_window), index=False)
        print(f"Window-based features saved to {out_name_window}")
    else:
        print("No window-based features extracted.")

if __name__ == "__main__":
    main()
