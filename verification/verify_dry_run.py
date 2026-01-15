import pandas as pd
import subprocess
import os

CATALOG = "processing_catalog.csv"
PYTHON = r"c:\Users\Aditya\Work\MOXIE\venv\Scripts\python.exe"

def dry_run():
    if not os.path.exists(CATALOG):
        print("Catalog not found.")
        return

    df = pd.read_csv(CATALOG)
    print(f"Loaded catalog with {len(df)} rows.")

    # Pick a row with Acqknowledge
    acq_row = df[df['has_acqknowledge'] == 1].iloc[0] if not df[df['has_acqknowledge'] == 1].empty else None
    
    if acq_row is not None:
        print("\n--- Testing Acqknowledge Processing ---")
        pid = str(acq_row['participant_id'])
        visit = acq_row['visit_type']
        acq_path = acq_row['acq_file_path']
        
        print(f"Participant: {pid}, Visit: {visit}")
        print(f"Command 1: Extract Events")
        cmd1 = [PYTHON, "scripts/extract_events.py", "--participant_id", pid, "--visit_type", visit, "--acq_file", acq_path]
        print(" ".join(cmd1))
        # Uncomment to actually run 
        # subprocess.run(cmd1)

        print(f"Command 2: Process ECG")
        events_file = f"events_{pid}_{visit.replace(' ', '_')}.csv"
        cmd2 = [PYTHON, "scripts/process_acq_ecg.py", "--participant_id", pid, "--visit_type", visit, "--acq_file", acq_path, "--events_file", events_file]
        print(" ".join(cmd2))
        # subprocess.run(cmd2)

    # Pick a row with Hexoskin
    hex_row = df[df['has_hexoskin'] == 1].iloc[0] if not df[df['has_hexoskin'] == 1].empty else None
    
    if hex_row is not None:
        print("\n--- Testing Hexoskin Processing ---")
        pid = str(hex_row['participant_id'])
        visit = hex_row['visit_type']
        hex_path = hex_row['hex_file_path']
        
        print(f"Participant: {pid}, Visit: {visit}")
        print(f"Command: Process Hexoskin")
        cmd3 = [PYTHON, "scripts/process_hexoskin_ecg.py", "--participant_id", pid, "--visit_type", visit, "--hex_path", hex_path]
        print(" ".join(cmd3))
        # subprocess.run(cmd3)

if __name__ == "__main__":
    dry_run()
