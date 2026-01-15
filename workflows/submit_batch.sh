#!/bin/bash
# Master Submission Script for MOXIE Pipeline
# Usage: ./submit_batch.sh

# Configuration (Adjust paths for cluster)
REPO_ROOT=$(dirname "$(realpath "$0")")/..
DATA_ROOT="/nfs/turbo/lsa-aditya/Participant Data"  # Example Cluster Path
OUTPUT_ROOT="$REPO_ROOT/Processed_Data"
CATALOG_FILE="$REPO_ROOT/processing_catalog.csv"

# Check if catalog exists
if [ ! -f "$CATALOG_FILE" ]; then
    echo "Error: Catalog not found at $CATALOG_FILE"
    echo "Please run 'python utils/generate_catalog.py' first."
    exit 1
fi

# 1. Submit Layer 1: Event Extraction (Serial Job)
# We want this to finish before processing starts to ensure directories exist.
echo "Submitting Layer 1: Event Extraction..."
JID_EVENTS=$(sbatch --parsable "$REPO_ROOT/workflows/run_events.sh" "$DATA_ROOT" "$OUTPUT_ROOT")
echo " -> Submitted Events Job: $JID_EVENTS"

# 2. Submit Layer 2: Signal Processing (Array Job)
# Calculate array size dynamically from catalog
NUM_ROWS=$(tail -n +2 "$CATALOG_FILE" | grep -c .)

if [ "$NUM_ROWS" -eq 0 ]; then
    echo "No rows found in catalog. Exiting."
    exit 0
fi

echo "Found $NUM_ROWS tasks in catalog."
echo "Submitting Layer 2: Signal Processing..."

# Submit array job with dependency on Events job
# --dependency=afterok:JOBID ensures processing only starts if events finish successfully
sbatch --dependency=afterok:$JID_EVENTS --array=1-$NUM_ROWS "$REPO_ROOT/workflows/run_processing.sh" "$CATALOG_FILE" "$OUTPUT_ROOT"

echo " -> Submitted Processing Array: 1-$NUM_ROWS (Dependency: $JID_EVENTS)"
echo "Done."
