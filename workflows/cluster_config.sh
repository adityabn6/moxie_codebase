#!/bin/bash
# Central Configuration for MOXIE Cluster Workflows
# This file is sourced by run_events.sh and run_processing.sh

# --- Paths ---
# The absolute path to your project on Greatlakes
export PROJECT_ROOT="/home/adityabn/Projects/moxie_codebase"

# Virtual Environment Path
export VENV_PATH="$PROJECT_ROOT/.venv"

# Input/Output
export CATALOG_FILE="$PROJECT_ROOT/processing_catalog.csv"
export OUTPUT_ROOT="$PROJECT_ROOT/Processed_Data"
export SCRIPT_DIR="$PROJECT_ROOT/processing"

# Ensure output directory exists when config is loaded
mkdir -p "$OUTPUT_ROOT"
