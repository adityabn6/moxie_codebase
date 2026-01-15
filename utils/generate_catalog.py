import os
import pandas as pd
import glob
import argparse

# Configuration
DATA_ROOT = r"N:\Aditya\Participant Data"
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
