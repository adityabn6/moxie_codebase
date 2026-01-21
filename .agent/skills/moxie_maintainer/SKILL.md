---
name: MOXIE Pipeline Maintainer
description: Guidelines and architectural rules for maintaining and extending the MOXIE signal processing pipeline.
---

# MOXIE Pipeline Maintainer Skill

## Context
This skill contains the architectural knowledge required to maintain and extend the MOXIE processing codebase (`moxie_codebase`). The system allows for modular processing of physiological data from various devices (Acqknowledge, Hexoskin, etc.) using a sequential, layered approach.

## Architecture Overview
The pipeline operates in two sequential layers, driven by a master CSV catalog.

### Core Components
1.  **Catalog (`utils/generate_catalog.py`)**:
    *   **Rule**: Generates one row per **Modality** (e.g., `12345,TSST,acq,ecg,...`).
    *   **Rule**: Does NOT map events. Events are inferred by directory structure.
    *   **Output**: `processing_catalog.csv`.


2.  **Layer 1: Events (`workflows/run_events.sh` -> `processing/extract_events.py`)**:
    *   **Goal**: Create output directory structure and `events.csv`.
    *   **Rule**: Must run **before** Layer 2.
    *   **Output**: `[Output_Root]/[PID]/[Visit]/events.csv`.

3.  **Layer 2: Processing (`workflows/run_processing.sh` -> `processing/process_*.py`)**:
    *   **Goal**: Clean and process raw signals (filtering, artifact removal).
    *   **Mechanism**: Slurm Array jobs based on `processing_catalog.csv`.
    *   **Input**: Reads row from catalog -> Finds `events.csv` -> Executes specific script.
    *   **Output**: `processed_[DEVICE]_[MODALITY]_[PID]_[VISIT].csv`.

4.  **Layer 3: Feature Extraction (`workflows/run_features.sh` -> `features_extraction/features_*.py`)**:
    *   **Goal**: Extract physiological features (HRV, breathing rate, etc.) from processed data.
    *   **Input**: `processed_*.csv` and `events.csv`.
    *   **Output**: `features_[DEVICE]_[MODALITY]_[PID]_[VISIT].csv`.

## Development Rules

### 1. Naming Conventions
*   **Processing Scripts**: `processing/process_[DEVICE]_[MODALITY].py` (e.g., `process_hexoskin_rsp.py`).
*   **Feature Scripts**: `features_extraction/features_[DEVICE]_[MODALITY].py` (e.g., `features_acq_rsp.py`).
*   **Verification**: `verification/verify_[MODALITY]_quality.py`.
*   **Output Files**:
    *   Processing: `processed_[DEVICE]_[MODALITY]_[PID]_[VISIT].csv`.
    *   Features: `features_[DEVICE]_[MODALITY]_[PID]_[VISIT].csv`.

### 2. Script Arguments
All processing and feature scripts MUST accept the following standard arguments:
*   `--participant_id` (str)
*   `--visit_type` (str)
*   `--events_file` (str) - **CRITICAL**: Script must handle if this file doesn't exist (warn, don't crash).
*   Device-specific input:
    *   Acqknowledge: `--acq_file` (or `--file` for feature scripts)
    *   Hexoskin: `--hex_path` (accepts file or directory)

### 3. Adding a New Modality
When adding a new sensor or signal type:
1.  **Imitate Existing Scripts**:
    *   Processing: Copy `process_acq_ecg.py` or `process_hexoskin_ecg.py`.
    *   Features: Copy `features_acq_ecg.py`.
2.  **Update Catalog**: Modify `utils/generate_catalog.py` to scan for and list the new modality.
3.  **Update Workflows**:
    *   `workflows/run_processing.sh`: Add case for new device/modality.
    *   `workflows/run_features.sh`: Add case for new modality detection.

### 4. Verification
*   Always create a `verify_*.py` script that loads the output CSV.
*   The script should print basic stats (Mean, Std) and save a plot.

## Common Pitfalls
*   **Events**: Do not hardcode event lookup in the catalog. It breaks the sequential logic. Layer 2 finds events dynamically.
*   **Paths**: Always use absolute paths in the catalog.
*   **Hexoskin**: Directory structure varies. The scripts allow passing the specific CSV file to avoid ambiguity.
