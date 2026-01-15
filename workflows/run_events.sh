#!/bin/bash
# Layer 1: Event Extraction (Slurm Array Execution)
# Usage: 
#   count=$(tail -n +2 processing_catalog.csv | wc -l)
#   sbatch --array=1-$count run_events.sh <Catalog_File> <Output_Root>

#SBATCH --job-name=moxie_events
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=adityabn@umich.edu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4g
#SBATCH --time=00:30:00
#SBATCH --account=sungchoi99
#SBATCH --partition=standard
#SBATCH --output=%x-%A_%a.log
#SBATCH --array=1-200

# --- CONFIGURATION & ENVIRONMENT ---
# Load variables from cluster_config.sh
# Note: Since this script runs from OnDemand's temporary job dir, we point to the absolute path.
CONFIG_FILE="/home/adityabn/Projects/moxie_codebase/workflows/cluster_config.sh"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

module load python
source "$VENV_PATH/bin/activate"
# -----------------------------------

ROW_INDEX=$SLURM_ARRAY_TASK_ID

if [ -z "$ROW_INDEX" ]; then
    echo "Error: SLURM_ARRAY_TASK_ID not set."
    exit 1
fi

# 1. Read Catalog Row
# Catalog: participant_id,visit_type,device,modality,file_path
LINE=$(tail -n +2 "$CATALOG_FILE" | sed -n "${ROW_INDEX}p")

if [ -z "$LINE" ]; then
    echo "Row $ROW_INDEX is empty (End of Catalog). Exiting successfully."
    exit 0
fi

IFS=',' read -r PID VISIT DEVICE MODALITY FILE_PATH <<< "$LINE"

# 2. Smart Filtering
# We only want to run Event Extraction ONCE per Acqknowledge file.
# The catalog has multiple rows for the same file (ecg, eda, rsp, etc.).
# We designate 'ecg' as the "Trigger Modality" for event extraction.

if [ "$DEVICE" == "acq" ] && [ "$MODALITY" == "ecg" ]; then
    echo "Processing Job $ROW_INDEX (Triggered by $DEVICE - $MODALITY)"
    echo "  Participant: $PID"
    echo "  Visit: $VISIT"
    echo "  File: $FILE_PATH"

    # Construct Output
    TARGET_DIR="$OUTPUT_ROOT/$PID/$VISIT"
    mkdir -p "$TARGET_DIR"

    # Execute
    CMD="python $SCRIPT_DIR/extract_events.py --acq_file \"$FILE_PATH\" --output_dir \"$TARGET_DIR\""
    echo "Running: $CMD"
    eval $CMD
    
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Failed with exit code $exit_code"
        exit $exit_code
    fi

else
    echo "Skipping Job $ROW_INDEX ($DEVICE - $MODALITY): Not a primary event trigger."
    # We exit 0 so Slurm considers it a "success" (it just didn't need to do anything)
    exit 0
fi
