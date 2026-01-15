#!/bin/bash
# Layer 2: Signal Processing (Slurm Array Execution)
# Usage: sbatch --array=1-N ./run_processing.sh <Catalog_File> <Output_Root>
# Or locally: ./run_processing.sh <Catalog_File> <Output_Root> <Row_Index>

CATALOG_FILE=$1
OUTPUT_ROOT=$2
ROW_INDEX=$SLURM_ARRAY_TASK_ID

# Allow local override
if [ -z "$ROW_INDEX" ]; then
    ROW_INDEX=$3
fi

if [ -z "$CATALOG_FILE" ] || [ -z "$OUTPUT_ROOT" ] || [ -z "$ROW_INDEX" ]; then
    echo "Usage: $0 <Catalog_File> <Output_Root> [Row_Index (if not Slurm)]"
    exit 1
fi

SCRIPT_DIR="$(dirname "$0")/../processing"

# Read Catalog Row
# Catalog Cols: participant_id,visit_type,device,modality,file_path
# Skip header (tail -n +2), extract line N (sed -n "${ROW_INDEX}p")

LINE=$(tail -n +2 "$CATALOG_FILE" | sed -n "${ROW_INDEX}p")

if [ -z "$LINE" ]; then
    echo "Error: Row $ROW_INDEX empty in catalog."
    exit 1
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

echo "Running: $CMD"
eval $CMD

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Process failed with exit code $exit_code"
    exit $exit_code
fi

echo "Job Complete."
