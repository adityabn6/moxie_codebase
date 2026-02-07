import os
import pandas as pd
import glob
import argparse

# Configuration
DATA_ROOT = r'/Volumes/lsa-annelism/MOXIE_Study/Participant Data'
# Save to repository root (one level up from utils)
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "processing_catalog.csv")

def scan_participants_modality_based(root_dir):
    catalog_data = []
    
    # Get all participant directories (assuming numeric IDs)
    participant_dirs = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d)) and d.isdigit()]
    
    print(f"Found {len(participant_dirs)} participant directories.")

    for pid in participant_dirs:
        p_path = os.path.join(root_dir, pid)
        visits = ["TSST Visit", "PDST Visit"]
        
        for visit in visits:
            visit_path = os.path.join(p_path, visit)
            
            if os.path.exists(visit_path):
                # --- ACQNOWLEDGE ---
                acq_path = os.path.join(visit_path, "Acqknowledge")
                if os.path.exists(acq_path):
                    acq_files = glob.glob(os.path.join(acq_path, "*.acq"))
                    if acq_files:
                        acq_file = acq_files[0]
                        # Add rows for each Acq modality
                        modalities = ['ecg', 'eda', 'rsp', 'bp', 'emg']
                        for mod in modalities:
                            catalog_data.append({
                                "participant_id": pid,
                                "visit_type": visit,
                                "device": "acq",
                                "modality": mod,
                                "file_path": acq_file
                            })

                # --- HEXOSKIN ---
                hex_path = os.path.join(visit_path, "Hexoskin")
                if os.path.exists(hex_path):
                    # Find best CSV
                    candidate_files = []
                    for root, dirs, files in os.walk(hex_path):
                        for file in files:
                            if file.endswith(".csv"):
                                candidate_files.append(os.path.join(root, file))
                    
                    if candidate_files:
                        try:
                            # Use largest CSV as data file
                            hex_file = max(candidate_files, key=os.path.getsize)
                            # Add rows for Hex modalities
                            modalities = ['ecg', 'rsp']
                            for mod in modalities:
                                catalog_data.append({
                                    "participant_id": pid,
                                    "visit_type": visit,
                                    "device": "hexoskin",
                                    "modality": mod,
                                    "file_path": hex_file
                                })
                        except:
                            pass

                # --- THOUGHT LISTING ---
                thought_path = os.path.join(visit_path, "Thought Listing")
                if os.path.exists(thought_path):
                    # Find all .wav files (case-insensitive)
                    wav_files = []
                    for file in os.listdir(thought_path):
                        if file.lower().endswith('.wav'):
                            wav_files.append(os.path.join(thought_path, file))
                    
                    for wav_file in wav_files:
                        catalog_data.append({
                            "participant_id": pid,
                            "visit_type": visit,
                            "device": "Audio",
                            "modality": "thoughts",
                            "file_path": wav_file
                        })
                # --- RESEARCH RING ---
                research_ring_string = None
                if visit == "TSST Visit":
                    research_ring_string = "TSST_Research_Ring"
                elif visit == "PDST Visit":
                    research_ring_string = "PDST_Research_Ring"

                if research_ring_string:
                    # Look for folders inside visit_path that start with research_ring_string
                    matching_folders = [
                        os.path.join(visit_path, f)
                        for f in os.listdir(visit_path)
                        if os.path.isdir(os.path.join(visit_path, f)) and f.startswith(research_ring_string)
                    ]
                    
                    if matching_folders:
                        # Take the first one (or handle multiple if needed)
                        final_research_ring_folder = matching_folders[0]
                        signal_files_folder = os.path.join(final_research_ring_folder, "signal_files")
                        final_folder = [
                            os.path.join(signal_files_folder, d)
                            for d in os.listdir(signal_files_folder)
                            if os.path.isdir(os.path.join(signal_files_folder, d)) and d.startswith("Senstream")
                        ]
                        # Optionally add it to the catalog
                        if final_folder:
                            final_research_ring_folder = final_folder[0]
                            modalities = ['eda', 'ppg', 'temp']
                            for mod in modalities:
                                catalog_data.append({
                                    "participant_id": pid,
                                    "visit_type": visit,
                                    "device": "Research_Ring",
                                    "modality": mod,
                                    "file_path": final_research_ring_folder
                                })
                    


    return pd.DataFrame(catalog_data)

if __name__ == "__main__":
    df = scan_participants_modality_based(DATA_ROOT)
    
    if not df.empty:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Catalog generated with {len(df)} rows at {OUTPUT_FILE}")
        # Print first few rows to confirm structure
        print(df.head(10))
    else:
        print("No matching data found.")
