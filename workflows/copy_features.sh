#!/bin/bash
# Utility script to collect all feature CSVs into a single folder for analysis.
# Usage: ./copy_features.sh <Destination_Folder> [Source_Folder]

# Default Source from config if possible
# resolve directory of this script
SCRIPT_DIR_LOC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR_LOC/cluster_config.sh"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    SOURCE_DIR=${OUTPUT_ROOT}
else
    # Fallback if config not found
    SOURCE_DIR="./Processed_Data"
fi

DEST_DIR=$1
OVERRIDE_SOURCE=$2

if [ -z "$DEST_DIR" ]; then
    echo "Usage: $0 <Destination_Folder> [Source_Folder]"
    echo "  Destination_Folder: Where to copy the files."
    echo "  Source_Folder: (Optional) Root directory to search. Defaults to \$OUTPUT_ROOT from config ($SOURCE_DIR)."
    exit 1
fi

if [ -n "$OVERRIDE_SOURCE" ]; then
    SOURCE_DIR=$OVERRIDE_SOURCE
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory '$SOURCE_DIR' does not exist."
    exit 1
fi

# Create destination if it doesn't exist
if [ ! -d "$DEST_DIR" ]; then
    echo "Creating destination directory: $DEST_DIR"
    mkdir -p "$DEST_DIR"
fi

echo "Collecting feature CSVs..."
echo "  Source: $SOURCE_DIR"
echo "  Destination: $DEST_DIR"

# Find and copy
# We look for files starting with 'features_' and ending in '.csv'
count=0
# Using process substitution specifically for bash to update count variable
while IFS= read -r file; do
    filename=$(basename "$file")
    
    # Copy file, overwriting if exists
    cp "$file" "$DEST_DIR/"
    ((count++))
    
done < <(find "$SOURCE_DIR" -type f -name "features_*.csv")

echo "Successfully copied $count feature files to $DEST_DIR"
