#!/bin/bash
# Layer 3: Feature Extraction (Slurm Array Execution)
# Usage: sbatch --array=1-N run_features.sh <Catalog_File> <Output_Root>

#SBATCH --job-name=moxie_features
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=adityabn@umich.edu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32g
#SBATCH --time=00:45:00
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

# Allow local override
if [ -z "$ROW_INDEX" ]; then
    ROW_INDEX=$1
fi

if [ -z "$ROW_INDEX" ]; then
    echo "Error: SLURM_ARRAY_TASK_ID not set."
    exit 1
fi

# Read Catalog Row
# Catalog Cols: participant_id,visit_type,device,modality,file_path
LINE=$(tail -n +2 "$CATALOG_FILE" | sed -n "${ROW_INDEX}p")

if [ -z "$LINE" ]; then
    echo "Row $ROW_INDEX is empty (End of Catalog). Exiting successfully."
    exit 0
fi

# Parse CSV line
IFS=',' read -r PID VISIT DEVICE MODALITY FILE_PATH <<< "$LINE"

echo "Job $ROW_INDEX - Feature Extraction"
echo "  Participant: $PID"
echo "  Visit: $VISIT"
echo "  Device: $DEVICE"
echo "  Modality: $MODALITY"

# Only process Acqknowledge modalities for now (as per existing python scripts)
if [ "$DEVICE" != "acq" ]; then
    echo "Skipping Non-ACQ device: $DEVICE"
    exit 0
fi

# Construct Paths
# Output from Processing Layer (Layer 2) is the Input for this Layer
TARGET_DIR="$OUTPUT_ROOT/$PID/$VISIT"
EVENTS_FILE="$TARGET_DIR/events.csv"

# Construct Processed File Name: processed_{modality}_{pid}_{visit}.csv
# Note: Python scripts replace spaces in visit with underscores
VISIT_CLEAN=${VISIT// /_}
PROCESSED_FILE_NAME="processed_${MODALITY}_${PID}_${VISIT_CLEAN}.csv"
PROCESSED_FILE="$TARGET_DIR/$PROCESSED_FILE_NAME"

echo "  Input File: $PROCESSED_FILE"
echo "  Events File: $EVENTS_FILE"
echo "  Output Dir: $TARGET_DIR"

# Validation
if [ ! -f "$PROCESSED_FILE" ]; then
    echo "Error: Processed file not found: $PROCESSED_FILE"
    echo "Did Layer 2 (run_processing.sh) complete successfully?"
    exit 1
fi

if [ ! -f "$EVENTS_FILE" ]; then
    echo "Warning: Events file not found: $EVENTS_FILE"
    # Some features might extract without events, or script will fail.
    # Allowing script to decide.
fi

# Select Script
SCRIPT_NAME="features_acq_${MODALITY}.py"
PYTHON_SCRIPT="$PROJECT_ROOT/features_extraction/$SCRIPT_NAME"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Feature extraction script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Execute
# Usage: python features_acq_ecg.py --id <ID> --visit <VISIT> --file <FILE> --events_file <EVENTS> --out <OUT>

CMD="python $PYTHON_SCRIPT \
    --id \"$PID\" \
    --visit \"$VISIT\" \
    --file \"$PROCESSED_FILE\" \
    --events_file \"$EVENTS_FILE\" \
    --out \"$TARGET_DIR\""

echo "Running: $CMD"
eval $CMD

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Feature extraction failed with exit code $exit_code"
    exit $exit_code
fi

echo "Job Complete."
