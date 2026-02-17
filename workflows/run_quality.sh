#!/bin/bash
# Layer 3: Signal Quality Assessment (Slurm Array Execution)
# Usage:
#   count=$(tail -n +2 processing_catalog.csv | wc -l)
#   sbatch --array=1-$count run_quality.sh

#SBATCH --job-name=moxie_quality
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

# ---------------- CONFIGURATION ----------------

CONFIG_FILE="/home/adityabn/Projects/moxie_codebase/workflows/cluster_config.sh"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

module load python
source "$VENV_PATH/bin/activate"

# ------------------------------------------------

ROW_INDEX=$SLURM_ARRAY_TASK_ID

# Allow local override (for manual testing)
if [ -z "$ROW_INDEX" ]; then
    ROW_INDEX=$1
fi

if [ -z "$ROW_INDEX" ]; then
    echo "Error: SLURM_ARRAY_TASK_ID not set."
    exit 1
fi

# Read catalog row
LINE=$(tail -n +2 "$CATALOG_FILE" | sed -n "${ROW_INDEX}p")

if [ -z "$LINE" ]; then
    echo "Row $ROW_INDEX is empty (End of Catalog). Exiting successfully."
    exit 0
fi

IFS=',' read -r PID VISIT DEVICE MODALITY FILE_PATH <<< "$LINE"

echo "Quality Job $ROW_INDEX"
echo "  Participant: $PID"
echo "  Visit: $VISIT"
echo "  Device: $DEVICE"
echo "  Modality: $MODALITY"
echo "  File: $FILE_PATH"


# Construct output directory
OUTPUT_DIR="$OUTPUT_ROOT/$PID/$VISIT"



if [ ! -f "$EVENTS_FILE" ]; then
    echo "Warning: Events file not found at $EVENTS_FILE"
fi

# Replace spaces in visit with underscores
VISIT_SAFE=$(echo "$VISIT" | tr ' ' '_')

# Construct processed filename (Layer 2 output)
PROCESSED_FILE="$OUTPUT_DIR/processed_${DEVICE}_${MODALITY}_${PID}_${VISIT_SAFE}.csv"

echo "  QC Input File: $PROCESSED_FILE"

if [ ! -f "$PROCESSED_FILE" ]; then
    echo "Processed file not found. Skipping."
    exit 0
fi

# Select QC Script
PYTHON_SCRIPT=""
case "$DEVICE" in
    "acq")
        PYTHON_SCRIPT="$QUALITY_SCRIPT_DIR/quality_acq_${MODALITY}.py"
        ;;
    "hexoskin")
        PYTHON_SCRIPT="$QUALITY_SCRIPT_DIR/quality_hexoskin_${MODALITY}.py"
        ;;
    "audio")
        PYTHON_SCRIPT="$QUALITY_SCRIPT_DIR/quality_audio_${MODALITY}.py"
        ;;
    "research_ring")
        PYTHON_SCRIPT="$QUALITY_SCRIPT_DIR/quality_research_ring_${MODALITY}.py"
        ;;
    *)
        echo "Error: Unknown device '$DEVICE'"
        exit 1
        ;;
esac

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Quality script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Execute QC Script
CMD="python $PYTHON_SCRIPT \
    --participant_id $PID \
    --visit_type \"$VISIT\" \
    --input_file \"$PROCESSED_FILE\" \
    --output_dir \"$OUTPUT_DIR\" \
    --file_path \"$FILE_PATH\""

echo "Running: $CMD"
eval $CMD

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Quality process failed with exit code $exit_code"
    exit $exit_code
fi

echo "Quality Job Complete."
