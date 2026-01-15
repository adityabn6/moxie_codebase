#!/bin/bash
# Layer 2: Signal Processing (Slurm Array Execution)
# Usage: sbatch --array=1-N run_processing.sh <Catalog_File> <Output_Root>

#SBATCH --job-name=moxie_processing
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=adityabn@umich.edu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8g
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
# Skip header (tail -n +2), extract line N (sed -n "${ROW_INDEX}p")

LINE=$(tail -n +2 "$CATALOG_FILE" | sed -n "${ROW_INDEX}p")

if [ -z "$LINE" ]; then
    echo "Row $ROW_INDEX is empty (End of Catalog). Exiting successfully."
    exit 0
fi

# Parse CSV line (Handling potential commas in quotes? Simple CSV assumption here)
IFS=',' read -r PID VISIT DEVICE MODALITY FILE_PATH <<< "$LINE"

echo "Processing Job $ROW_INDEX"
echo "  Participant: $PID"
echo "  Visit: $VISIT"
echo "  Device: $DEVICE"
echo "  Modality: $MODALITY"
echo "  File: $FILE_PATH"

# Construct specific output directory (Must match Layer 1)
OUTPUT_DIR="$OUTPUT_ROOT/$PID/$VISIT"
EVENTS_FILE="$OUTPUT_DIR/events.csv"

# Check if events exist (Layer 1 Check)
if [ ! -f "$EVENTS_FILE" ]; then
    echo "WARNING: Events file not found at $EVENTS_FILE"
    # Proceed? Or Fail? 
    # Hexoskin RSP/ECG might need events. Acq scripts definitely do.
    # For now, we pass it. The python scripts should handle missing events gracefully if possible, or fail.
fi

# Select Script
PYTHON_SCRIPT=""
case "$DEVICE" in
    "acq")
        PYTHON_SCRIPT="$SCRIPT_DIR/process_acq_${MODALITY}.py"
        ;;
    "hexoskin")
        PYTHON_SCRIPT="$SCRIPT_DIR/process_hexoskin_${MODALITY}.py"
        ;;
    *)
        echo "Error: Unknown device '$DEVICE'"
        exit 1
        ;;
esac

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Script $PYTHON_SCRIPT not found."
    exit 1
fi

# Execute
# Note: Arguments vary by script. 
# Unified interface needed? Or specific mapping?
# Current scripts take: --participant_id --visit_type --acq_file/--hex_path --events_file
# Adapting args based on device type:

CMD="python $PYTHON_SCRIPT --participant_id $PID --visit_type \"$VISIT\" --events_file \"$EVENTS_FILE\""

if [ "$DEVICE" == "acq" ]; then
    CMD="$CMD --acq_file \"$FILE_PATH\""
elif [ "$DEVICE" == "hexoskin" ]; then
    # Hexoskin scripts expect --hex_path (which handles dir or file now)
    CMD="$CMD --hex_path \"$FILE_PATH\""
fi

# Append output directory argument
CMD="$CMD --output_dir \"$OUTPUT_DIR\""

echo "Running: $CMD"
eval $CMD

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Process failed with exit code $exit_code"
    exit $exit_code
fi

echo "Job Complete."
