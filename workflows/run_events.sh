#!/bin/bash
# Layer 1: Event Extraction & Directory Creation
# Usage: ./run_events.sh <Data_Root> <Output_Root>

DATA_ROOT=$1
OUTPUT_ROOT=$2
SCRIPT_DIR="$(dirname "$0")/../processing"

if [ -z "$DATA_ROOT" ] || [ -z "$OUTPUT_ROOT" ]; then
    echo "Usage: $0 <Data_Root> <Output_Root>"
    exit 1
fi

echo "Starting Layer 1: Event Extraction..."
echo "Data Root: $DATA_ROOT"
echo "Output Root: $OUTPUT_ROOT"

# Find ACQ files for TSST and PDST visits
# Logic: Look for .acq files in "TSST Visit/Acqknowledge" or "PDST Visit/Acqknowledge"
# We'll use find command (or a python helper if complex)
# Simple loop over found files:

find "$DATA_ROOT" -type f -name "*.acq" | while read -r acq_file; do
    # Check if path contains TSST Visit or PDST Visit
    if [[ "$acq_file" == *"TSST Visit"* ]] || [[ "$acq_file" == *"PDST Visit"* ]]; then
        echo "Processing: $acq_file"
        
        # Extract metadata from path for output structure? 
        # Actually extract_events.py handles output dir creation if we pass the root output + let it infer or we pass specific.
        # But wait, extract_events.py (if unchanged) takes --output_dir.
        # The user said "generate the output directories by participant name and visit, similar to the input data folder structure"
        
        # We need to parse PID and Visit from path to construct sub-output dir?
        # Path example: N:\Aditya\Participant Data\126641\TSST Visit\Acqknowledge\....acq
        
        # Regex to extract PID and Visit
        # Assuming format .../Participant Data/<PID>/<Visit>/Acqknowledge/...
        
        # Simple extraction using awk or string manip
        # This part depends on strict path structure. 
        # Alternatively, we rely on extract_events.py to be smart?
        # Let's check extract_events.py logic. 
        # If it takes just --output_dir, it dumps results there.
        # So we MUST construct the specific output subfolder here.
        
        PID=$(echo "$acq_file" | grep -oE "[0-9]{5,}")
        VISIT=""
        if [[ "$acq_file" == *"TSST Visit"* ]]; then VISIT="TSST Visit"; fi
        if [[ "$acq_file" == *"PDST Visit"* ]]; then VISIT="PDST Visit"; fi
        
        if [ -n "$PID" ] && [ -n "$VISIT" ]; then
             TARGET_DIR="$OUTPUT_ROOT/$PID/$VISIT"
             mkdir -p "$TARGET_DIR"
             
             python "$SCRIPT_DIR/extract_events.py" --acq_file "$acq_file" --output_dir "$TARGET_DIR"
        else
            echo "SKIPPING: Could not parse PID/Visit from $acq_file"
        fi
    fi
done

echo "Layer 1 Complete."
