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

import bioread
import neurokit2 as nk
import sys
import os

def find_bp_channel(data):
    """
    Finds Blood Pressure / NIBP channel.
    """
    # Common keywords
    # NIBP, Blood Pressure, BP
    
    for channel in data.channels:
        name = channel.name.upper()
        if "NIBP" in name or "BLOOD PRESSURE" in name or "BP" in name:
            # Avoid triggers or aux channels if possible, but usually main channel has clear name
            return channel
            
    return None

def process_bp(channel, fs, events_df):
    """
    Process BP signal treating it as PPG/Continuous Waveform.
    Outputs Cleaned Signal, Systolic (Peaks), Diastolic (Troughs), Rate.
    """
    print(f"Processing {channel.name} with sampling rate {fs}Hz")
    
    # 1. Clean
    # "ppg_clean" often applies a high-pass filter which removes the DC component (absolute pressure).
    # For NIBP, we want to PRESERVE the absolute mmHg values. 
    # So we should only Low-Pass filter to remove high frequency noise.
    try:
        # Standard cutoff for BP/Pulse waves is often around 5-10Hz to smooth, 
        # or up to 40Hz if morphology is critical. 8Hz is a good balance for NIBP envelope.
        bp_cleaned = nk.signal_filter(channel.data, sampling_rate=fs, lowcut=None, highcut=8, method='butterworth', order=4)
    except Exception as e:
        print(f"BP cleaning failed: {e}")
        return pd.DataFrame()
        
    # 2. Find Peaks (Systolic)
    try:
        # ppg_findpeaks finds systolic peaks
        info = nk.ppg_findpeaks(bp_cleaned, sampling_rate=fs)
        peaks = info['PPG_Peaks']
        
        # 3. Calculate Rate
        rate = nk.signal_rate(peaks, sampling_rate=fs, desired_length=len(bp_cleaned))
        
        # 4. Identify Diastolic (Valleys)
        # In continuous BP, diastolic is the minimum between peaks.
        # NeuroKit's ppg_process usually does finding valleys too.
        # Let's try formatting it manually to be safe or use ppg_process if robust.
        # ppg_process returns a dataframe with PPG_Rate, PPG_Peaks. 
        # But for BP we explicitly want the AMPLITUDE at peaks (SBP) and valleys (DBP).
        
        # In a pressure signal (mmHg), the amplitude IS the pressure.
        # So Cleaned Signal value at Peak = SBP.
        # Cleaned Signal value at Trough = DBP.
        
        # Let's construct the output DataFrame
        signals = pd.DataFrame({
            "BP_Raw": channel.data,
            "BP_Clean": bp_cleaned,
            "BP_Rate": rate
        })
        
        # Create Peaks Column
        signals['BP_Systolic_Peak'] = 0
        signals.iloc[peaks, signals.columns.get_loc('BP_Systolic_Peak')] = 1
        
        # Find Troughs (Diastolic)
        # Simply invert signal and find peaks or use minimum between peaks
        # A simple approach: Minimum value between two systolic peaks
        troughs = []
        for i in range(len(peaks)-1):
            # slice between peaks
            segment = bp_cleaned[peaks[i]:peaks[i+1]]
            # find min index local to segment
            min_loc = np.argmin(segment)
            # absolute index
            troughs.append(peaks[i] + min_loc)
            
        signals['BP_Diastolic_Peak'] = 0
        signals.iloc[troughs, signals.columns.get_loc('BP_Diastolic_Peak')] = 1
        
        # Interpolate SBP and DBP curves for continuous view?
        # User wants "clean simple scripts". Time series of Pressure is good.
        # Let's verify the user's intent: "multiple channels for BP, example systolic, dyastolic"
        # Since we derived them, we can output the continuous estimates of SBP/DBP (e.g. sample-and-hold or interpolation)
        # Or just the cleaned wave (which is the pressure) and the markers.
        # The CLEANED WAVE essentially oscillates between SBP and DBP. 
        # So "BP_Clean" IS the pressure tracing. 
        
        # However, it's often useful to have the envelope.
        # Let's add interpolated SBP/DBP columns.
        
        # Create a series with only peak values, then interpolate
        sbp_series = pd.Series(np.nan, index=np.arange(len(signals)))
        sbp_series.iloc[peaks] = bp_cleaned[peaks]
        signals['BP_Systolic_Interp'] = sbp_series.interpolate(method='linear').bfill()
        
        dbp_series = pd.Series(np.nan, index=np.arange(len(signals)))
        dbp_series.iloc[troughs] = bp_cleaned[troughs]
        signals['BP_Diastolic_Interp'] = dbp_series.interpolate(method='linear').bfill()
        
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
        print(f"BP Processing failed: {e}")
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--acq_file", required=True)
    parser.add_argument("--events_file", required=True)
    
    args = parser.parse_args()
    
    # Load Data
    try:
        data = bioread.read_file(args.acq_file)
    except Exception as e:
        print(f"Error reading ACQ: {e}")
        sys.exit(1)
        
    # Find Channel
    bp_chan = find_bp_channel(data)
    
    if bp_chan is None:
        print("No Blood Pressure channel found.")
        sys.exit(0)
        
    # Load Events
    events_df = None
    if os.path.exists(args.events_file):
        events_df = pd.read_csv(args.events_file)
        
    # Process
    signals_df = process_bp(bp_chan, data.samples_per_second, events_df)
    
    if not signals_df.empty:
        output_file = f"processed_bp_{args.participant_id}_{args.visit_type.replace(' ', '_')}.csv"
        signals_df.to_csv(output_file, index=False)
        print(f"Processed BP signals saved to {output_file}")
    else:
        print("No BP data generated.")

if __name__ == "__main__":
    main()
