#!/bin/bash
#SBATCH --job-name=MOXIE_Processing
#SBATCH --output=logs/moxie_%A_%a.out
#SBATCH --error=logs/moxie_%A_%a.err
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --array=1-10%5 # Default placeholder, will be overridden by user or computed

# Configuration
CATALOG_FILE="processing_catalog.csv"
PYTHON_EXEC="c:/Users/Aditya/Work/MOXIE/venv/Scripts/python.exe"
SCRIPT_DIR="scripts"

# Get the specific line from the CSV (skipping header)
# array task id 1 matches line 2 (header is line 1)
LINE_NUM=$((SLURM_ARRAY_TASK_ID + 1))
LINE=$(sed "${LINE_NUM}q;d" $CATALOG_FILE)

# Parse CSV line (assuming format: participant_id,visit_type,has_acq,acq_path,has_hex,hex_path)
# We use python to parse the line reliably or just simple awk/cut if we trust the format (no commas in fields)
# Let's use a small python snippet to parse the line to handle potential quoting/commas safely
IFS=',' read -r pid visit has_acq acq_path has_hex hex_path <<< "$LINE"

echo "Processing Job ID: $SLURM_ARRAY_JOB_ID, Task ID: $SLURM_ARRAY_TASK_ID"
echo "Participant: $pid, Visit: $visit"

# Dispatch logic
# Check if we should run Acqknowledge
if [ "$has_acq" == "1" ]; then
    echo "Starting Acqknowledge Processing..."
    # Event Extraction
    $PYTHON_EXEC "$SCRIPT_DIR/extract_events.py" --participant_id "$pid" --visit_type "$visit" --acq_file "$acq_path"
    
    # Signal Processing - ECG
    $PYTHON_EXEC "$SCRIPT_DIR/process_acq_ecg.py" --participant_id "$pid" --visit_type "$visit" --acq_file "$acq_path" --events_file "events_${pid}_${visit// /_}.csv"

    # Signal Processing - EDA
    $PYTHON_EXEC "$SCRIPT_DIR/process_acq_eda.py" --participant_id "$pid" --visit_type "$visit" --acq_file "$acq_path" --events_file "events_${pid}_${visit// /_}.csv"

    # Signal Processing - Respiration (Thoracic + Abdominal)
    $PYTHON_EXEC "$SCRIPT_DIR/process_acq_rsp.py" --participant_id "$pid" --visit_type "$visit" --acq_file "$acq_path" --events_file "events_${pid}_${visit// /_}.csv"
    
    # Signal Processing - Blood Pressure
    $PYTHON_EXEC "$SCRIPT_DIR/process_acq_bp.py" --participant_id "$pid" --visit_type "$visit" --acq_file "$acq_path" --events_file "events_${pid}_${visit// /_}.csv"
    
    # Signal Processing - EMG
    $PYTHON_EXEC "$SCRIPT_DIR/process_acq_emg.py" --participant_id "$pid" --visit_type "$visit" --acq_file "$acq_path" --events_file "events_${pid}_${visit// /_}.csv"
fi

# Check if we should run Hexoskin
# (Assuming Hexoskin data might be present)
# Note: The original hex_path variable from the CSV is used.
# If a base_dir is intended, it needs to be defined and concatenated with hex_path.
$PYTHON_EXEC "$SCRIPT_DIR/process_hexoskin_ecg.py" --participant_id "$pid" --visit_type "$visit" --hex_path "$hex_path" --events_file "events_${pid}_${visit// /_}.csv"
$PYTHON_EXEC "$SCRIPT_DIR/process_hexoskin_rsp.py" --participant_id "$pid" --visit_type "$visit" --hex_path "$hex_path" --events_file "events_${pid}_${visit// /_}.csv"
fi

echo "Done."
